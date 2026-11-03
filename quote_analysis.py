"""Time-aligned quote metrics. No live quote data is bundled.

Input CSV columns: timestamp,isin,venue,bid,ask (UTC ISO timestamps).
Trades CSV columns: timestamp,isin,venue,price,side (BUY/SELL optional).
Metrics require an actual bid/ask observation at or before each trade.
"""
import bisect
import csv
import re
import math
from operator import itemgetter
from collections import defaultdict
from datetime import datetime, timezone


def utc_seconds(value):
    value=value.strip().replace("Z","+00:00")
    # Older Python versions reject non-padded fractional seconds such as .5.
    value=re.sub(r"\.(\d{1,6})(?=\+|-|$)",
                 lambda match: "."+match.group(1).ljust(6,"0"), value)
    dt=datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError("Timestamp must include timezone")
    return dt.astimezone(timezone.utc).timestamp()


def load_quotes(path):
    grouped=defaultdict(list)
    with open(path,newline="") as f:
        for row in csv.DictReader(f):
            bid,ask=float(row["bid"]),float(row["ask"])
            if not (math.isfinite(bid) and math.isfinite(ask) and 0 < bid < ask):
                continue
            key=(row["isin"].strip(),row["venue"].strip())
            grouped[key].append((utc_seconds(row["timestamp"]),bid,ask))
    # Preserve source order for equal timestamps so the last update wins.
    for rows in grouped.values():
        rows.sort(key=itemgetter(0))
    return grouped


def join_trades(trade_path, quotes, tolerance_seconds=1.0):
    if not math.isfinite(tolerance_seconds) or tolerance_seconds < 0:
        raise ValueError("Tolerance must be finite and non-negative")
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
            if not math.isfinite(price) or price <= 0:
                continue
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
