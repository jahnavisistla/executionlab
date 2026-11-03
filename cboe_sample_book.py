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
SYMBOL_CLEAR=104  # 0x68: not in this sample's observed event types


def process_events(rows):
    book={}
    snapshots=[]
    stats=defaultdict(int)
    prev_top=None
    for row in rows:
        if len(row)<4:continue
        try:
            code=int(row[0]);ts=int(row[2])
            if code in ADD:
                oid=row[3];side=row[4];size=int(row[5]);price=float(row[7])
                if side in ("B","S") and size>0 and price>0:
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
                    if remaining>0:book[oid]=(side,remaining,price)
                    else:book.pop(oid,None)
                else:stats["unknown_reductions"]+=1
            elif code==36:
                # Execute-at-price/size may not equal a displayed decrement;
                # leave resting book unchanged rather than assuming a reduction.
                stats["at_price_size_unhandled"]+=1
            else:stats["other_events"]+=1
        except (ValueError,IndexError):
            stats["malformed"]+=1
            continue
        if code not in ADD|EXECUTE|REDUCE|MODIFY|{DELETE}:continue
        bids=[(p,s) for side,s,p in book.values() if side=="B"]
        asks=[(p,s) for side,s,p in book.values() if side=="S"]
        if not bids or not asks:continue
        bid=max(p for p,_ in bids);ask=min(p for p,_ in asks)
        if bid>=ask:
            stats["crossed_or_locked_updates"]+=1
            continue
        top=(bid,ask)
        if top!=prev_top:
            spread=(ask-bid)/((bid+ask)/2)*10000
            snapshots.append((ts,bid,ask,spread))
            prev_top=top
    return snapshots,dict(stats)


def summarise(snapshots):
    if len(snapshots)<2:raise ValueError("Insufficient valid top-of-book snapshots")
    # End of sample bounded to last observed snapshot; don't extrapolate.
    durations=[max(0,snapshots[i+1][0]-snapshots[i][0]) for i in range(len(snapshots)-1)]
    weights=sum(durations)
    time_weighted=sum(snapshots[i][3]*durations[i] for i in range(len(durations)))/weights
    spreads=[x[3] for x in snapshots]
    return {"snapshots":len(snapshots),"median_event_spread_bps":statistics.median(spreads),
            "mean_time_weighted_spread_bps":time_weighted,"min_spread_bps":min(spreads),
            "max_spread_bps":max(spreads),"duration_minutes":weights/60e9}


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
