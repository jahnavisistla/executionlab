"""Time-aligned quote metrics. No live quote data is bundled.

Input CSV columns: timestamp,isin,venue,bid,ask (UTC ISO timestamps).
Trades CSV columns: timestamp,isin,venue,price,side (BUY/SELL optional).
Metrics require an actual bid/ask observation at or before each trade.
"""
import bisect
import csv
from collections import defaultdict
from datetime import datetime, timezone


def utc_seconds(value):
    dt=datetime.fromisoformat(value.strip().replace("Z","+00:00"))
    if dt.tzinfo is None:
        raise ValueError("Timestamp must include timezone")
    return dt.astimezone(timezone.utc).timestamp()


def load_quotes(path):
    grouped=defaultdict(list)
    with open(path,newline="") as f:
        for row in csv.DictReader(f):
            bid,ask=float(row["bid"]),float(row["ask"])
            if bid<=0 or ask<bid:
                continue
            key=(row["isin"].strip(),row["venue"].strip())
            grouped[key].append((utc_seconds(row["timestamp"]),bid,ask))
    for rows in grouped.values():rows.sort()
    return grouped


def join_trades(trade_path, quotes, tolerance_seconds=1.0):
    if tolerance_seconds<0:raise ValueError("Negative tolerance")
    indexes={key:[r[0] for r in rows] for key,rows in quotes.items()}
    metrics=[]
    with open(trade_path,newline="") as f:
        for row in csv.DictReader(f):
            key=(row["isin"].strip(),row["venue"].strip())
            if key not in quotes:continue
            timestamp=utc_seconds(row["timestamp"])
            i=bisect.bisect_right(indexes[key],timestamp)-1
            if i<0:continue
            qt,bid,ask=quotes[key][i]
            if timestamp-qt>tolerance_seconds:continue
            midpoint=(bid+ask)/2
            price=float(row["price"])
            spread=(ask-bid)/midpoint*10000
            side=row.get("side","").strip().upper()
            # Without an independently known aggressor side, effective spread
            # cannot be signed reliably and is intentionally omitted.
            effective=None
            if side in ("BUY","SELL"):
                sign=1 if side=="BUY" else -1
                effective=2*sign*(price-midpoint)/midpoint*10000
            metrics.append({"isin":key[0],"venue":key[1],"timestamp":timestamp,
                            "quote_age_seconds":timestamp-qt,"quoted_spread_bps":spread,
                            "effective_spread_bps":effective})
    return metrics
