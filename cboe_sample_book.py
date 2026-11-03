"""Reconstruct top of book from Cboe Europe Trades & Quotes *sample*.

The sample is supplied as zipped per-symbol CSV.gz event files. Numeric message
codes are decimal equivalents of Cboe Europe PITCH message types. This module
tracks visible order adds, modifications, reductions, executions and deletes.

Source and rights: Cboe DataShop sample /download/sample/197; no vendor records
are embedded in the distributed project.
"""
import csv
import gzip
import io
import json
import statistics
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

ADD={34,64}       # 0x22 short / 0x40 long
EXECUTE={35,36}   # 0x23 / 0x24; see caveat for at-price/size
REDUCE={37,38}    # 0x25 / 0x26
MODIFY={39,40}    # 0x27 / 0x28
DELETE=41         # 0x29


def process_events(rows):
    book={}
    snapshots=[]
    stats=defaultdict(int)
    prev_top=None
    last_sequence=None
    last_timestamp=None
    for row in rows:
        if len(row)<4:continue
        try:
            code=int(row[0]);sequence=int(row[1]);ts=int(row[2])
            if last_sequence is not None and sequence<=last_sequence:stats["non_increasing_sequence"]+=1
            if last_timestamp is not None and ts<last_timestamp:stats["non_monotonic_timestamp"]+=1
            last_sequence=sequence;last_timestamp=ts
            if code in ADD:
                oid=row[3];side=row[4];size=int(row[5]);price=float(row[7])
                if side in ("B","S") and size>0 and price>0:
                    if oid in book:stats["duplicate_order_ids"]+=1
                    book[oid]=(side,size,price)
                    stats["adds"]+=1
            elif code==DELETE:
                if book.pop(row[3],None) is None:stats["unknown_deletes"]+=1
                stats["deletes"]+=1
            elif code in MODIFY:
                oid=row[3]
                if oid in book:
                    side,_,_=book[oid]
                    size=int(row[4]);price=float(row[5])
                    if size>0 and price>0:book[oid]=(side,size,price)
                    else:book.pop(oid,None)
                else:stats["unknown_modifies"]+=1
            elif code in REDUCE or code==35:
                oid=row[3]
                if oid in book:
                    side,size,price=book[oid]
                    remaining=size-int(row[4])
                    if remaining<0:stats["over_reductions"]+=1
                    if remaining>0:book[oid]=(side,remaining,price)
                    else:book.pop(oid,None)
                else:stats["unknown_reductions"]+=1
            elif code==36:
                # Cboe PITCH 0x24 explicitly supplies Remaining Shares.
                oid=row[3]
                if oid in book:
                    side,_,price=book[oid]
                    remaining=int(row[5])
                    if remaining>0:book[oid]=(side,remaining,price)
                    else:book.pop(oid,None)
                else:stats["unknown_at_price_size"]+=1
            else:stats["other_events"]+=1
        except (ValueError,IndexError):
            stats["malformed"]+=1
            continue
        if code not in ADD|EXECUTE|REDUCE|MODIFY|{DELETE}:continue
        bids=[(p,s) for side,s,p in book.values() if side=="B"]
        asks=[(p,s) for side,s,p in book.values() if side=="S"]
        if not bids or not asks:
            if prev_top is not None:
                snapshots.append((ts,None,None,None))
                prev_top=None
            continue
        bid=max(p for p,_ in bids);ask=min(p for p,_ in asks)
        if bid>=ask:
            stats["crossed_or_locked_updates"]+=1
            if prev_top is not None:
                snapshots.append((ts,None,None,None))
                prev_top=None
            continue
        top=(bid,ask)
        if top!=prev_top:
            spread=(ask-bid)/((bid+ask)/2)*10000
            snapshots.append((ts,bid,ask,spread))
            prev_top=top
    return snapshots,dict(stats)


def summarise(snapshots):
    valid=[x for x in snapshots if x[3] is not None]
    if len(valid)<2:raise ValueError("Insufficient valid top-of-book snapshots")
    # Do not carry a valid quote through missing or crossed-book states.
    weighted=[]
    for current,nxt in zip(snapshots,snapshots[1:]):
        duration=max(0,nxt[0]-current[0])
        if current[3] is not None and duration:weighted.append((current[3],duration))
    weights=sum(duration for _,duration in weighted)
    if weights<=0:raise ValueError("No observed valid-quote duration")
    time_weighted=sum(spread*duration for spread,duration in weighted)/weights
    spreads=[x[3] for x in valid]
    return {"snapshots":len(valid),"invalid_state_transitions":len(snapshots)-len(valid),
            "median_event_spread_bps":statistics.median(spreads),
            "mean_time_weighted_spread_bps":time_weighted,"min_spread_bps":min(spreads),
            "max_spread_bps":max(spreads),"duration_minutes":weights/60e9,
            "fraction_valid_time_spread_over_100bps":sum(duration for spread,duration in weighted if spread>100)/weights}


def run(path):
    outputs={}
    with zipfile.ZipFile(path) as z:
        for filename in sorted(n for n in z.namelist() if n.endswith(".csv.gz")):
            with gzip.open(io.BytesIO(z.read(filename)),"rt",newline="") as f:
                rows=csv.reader(f)
                snapshots,stats=process_events(rows)
            if len(snapshots)<2:continue
            summary=summarise(snapshots)
            outputs[filename]={"summary":summary,"quality":stats}
    if not outputs:raise ValueError("No reconstructable symbols")
    return outputs


if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("Usage: python3 cboe_sample_book.py local_sample.zip")
    result=run(sys.argv[1])
    for name,data in result.items():
        print(name,json.dumps(data,indent=2))
