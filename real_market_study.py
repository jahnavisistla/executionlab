"""Analyse a locally supplied Cboe public delayed TRADE CSV (no redistribution).

Run: python3 real_market_study.py /path/to/cboe.csv
Standard library only. This is observed trade-activity research, NOT client TCA.
"""
import csv
import html
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

if len(sys.argv) < 2:
    raise SystemExit("Usage: python3 real_market_study.py /path/to/one_or_more_cboe_trade_files.csv")
sources = [Path(p) for p in sys.argv[1:]]
by_symbol = defaultdict(list)
processed, excluded = 0, 0
by_venue=defaultdict(int)
for source in sources:
    with source.open(newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
          try:
            symbol = r["Symbol"].strip()
            price = float(r["Price"])
            quantity = float(r["Executed Shares"])
            ts = r["Trading Date Time"].strip()
            currency = r["Price Currency"].strip()
            venue = r["Execution Venue"].strip()
            modification = r.get("Modification Indicator", "").strip()
            if not symbol or price <= 0 or quantity <= 0 or not ts or modification:
                excluded += 1
                continue
            by_symbol[(symbol, currency)].append((ts, price, quantity))
            by_venue[venue]+=1
            processed += 1
          except (ValueError, KeyError):
            excluded += 1

def summarise(rows):
    rows.sort(key=lambda x:x[0])
    volume = sum(r[2] for r in rows)
    vwap = sum(r[1]*r[2] for r in rows)/volume
    prices = [r[1] for r in rows]
    # Time-series of traded prices; not quote-based market volatility.
    returns = [math.log(prices[i]/prices[i-1]) for i in range(1,len(prices))]
    ret_std = statistics.stdev(returns)*10000 if len(returns)>1 else 0
    return volume,vwap,ret_std,prices[0],prices[-1]

eligible = [(key, rows) for key,rows in by_symbol.items() if len(rows)>=100]
eligible.sort(key=lambda item: len(item[1]), reverse=True)
top = eligible[:12]
table_rows = []
for (isin,currency), rows in top:
    vol,vwap,retstd,first,last = summarise(rows)
    table_rows.append(f"<tr><td>{html.escape(isin)}</td><td>{html.escape(currency)}</td><td>{len(rows):,}</td><td>{vol:,.0f}</td><td>{vwap:.4f}</td><td>{retstd:.2f}</td></tr>")

total = processed+excluded
template = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Observed European Equity Trades</title><style>body{background:#f3f5f8;color:#18243a;font:16px/1.55 Arial;margin:0}main{max-width:980px;margin:40px auto;background:white;padding:44px}h1{font:38px Georgia,serif}h2{border-bottom:1px solid #c8d0d9;padding-bottom:8px}table{border-collapse:collapse;width:100%;font-size:13px}td,th{text-align:left;border-bottom:1px solid #dfe3ea;padding:8px}th{background:#e9eef5}code{background:#e9eef5;padding:3px}small{color:#53647c}.notice{background:#fff0ca;padding:14px;border-left:4px solid #a07815}@media(max-width:700px){main{padding:15px;overflow:auto}}</style></head><body><main><small>EXECUTIONLAB 2.0 / OBSERVED MARKET DATA</small><h1>European Equity Intraday Trade Activity</h1><p>Jahnavi Sistla · Independent research prototype · November 2026</p><div class="notice"><b>Actual trade records, not client execution records.</b> Source: Cboe Europe MiFID delayed public trade files, {filename}. Individual market-data files are not redistributed with this report. Respect the provider's non-commercial-use terms.</div><h2>Data quality overview</h2><p>Processed <b>{processed:,}</b> positive-price, positive-size, non-modification records; excluded <b>{excluded:,}</b> records. Distinct ISIN/currency pairs: <b>{pairs:,}</b>. This is a <b>limited one-hour, multi-book sample</b>, not a consolidated European market sample.</p><h2>Most frequently traded instruments in this file</h2><table><tr><th>ISIN</th><th>CCY</th><th>Trades</th><th>Shares</th><th>Trade VWAP</th><th>Trade-to-trade log-return SD (bps)</th></tr>{rows}</table><p><small>VWAP = Σ(price × shares) / Σ(shares). The standard deviation shown is for consecutive recorded trade-price log returns and is sensitive to microstructure noise, sampling and trade conditions; it is not a volatility forecast. Do not compare prices across currencies.</small></p><h2>Research interpretation</h2><p>The files support observed trade activity, turnover and price-path analysis. They do not supply contemporaneous bid/ask quotes, market-depth snapshots, order intentions or a client's executed fills. Therefore effective spread, order-book liquidity, actual client slippage and market impact <b>cannot</b> be identified from these files alone.</p><h2>Next empirical step</h2><ol><li>Obtain a permitted Cboe Trades &amp; Quotes sample or licensed quote history.</li><li>As-of join quotes to trades with explicit timestamp tolerances.</li><li>Calculate quoted and effective spreads, trade-size buckets and volatility regimes.</li><li>Overlay separately labelled synthetic orders and fill models for benchmark simulations.</li><li>Expand across days and venues, harmonising flags and controlling for venue/instrument selection.</li></ol><h2>Reproducibility</h2><p>Run <code>python3 real_market_study.py &lt;one_or_more_downloaded_files.csv&gt;</code>. The analysis uses only Python's standard library.</p></main></body></html>'''
out = template
for key, value in {"filename":html.escape(", ".join(p.name for p in sources)), "processed":f"{processed:,}",
                   "excluded":f"{excluded:,}", "pairs":f"{len(by_symbol):,}",
                   "rows":"\n".join(table_rows)}.items():
    out = out.replace("{"+key+"}", str(value))
venue_table = "<h2>Records by execution venue</h2><table><tr><th>Venue code</th><th>Records</th></tr>" + "".join(f"<tr><td>{html.escape(k)}</td><td>{v:,}</td></tr>" for k,v in sorted(by_venue.items())) + "</table>"
out = out.replace("<h2>Most frequently traded instruments",venue_table+"<h2>Most frequently traded instruments")
(Path(__file__).parent/"observed_trade_report.html").write_text(out,encoding="utf8")
print(f"Observed {processed:,} valid trades, {excluded:,} excluded, {len(by_symbol):,} ISIN/currency pairs; report written")
