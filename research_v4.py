"""Multi-session observed market summaries + repeated *simulated* TCA scenarios.

Usage: python3 research_v4.py local_cboe_public_trade_file.csv [...]
Does not redistribute exchange data or claim actual client execution performance.
"""
import csv
import html
import json
import math
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from tca_engine import ParentOrder, Fill, analyse

if len(sys.argv)<2:raise SystemExit("Provide at least one local Cboe trade CSV")
base=Path(__file__).parent
observed=defaultdict(lambda:defaultdict(list))
counts=defaultdict(int)
for filename in sys.argv[1:]:
    with open(filename,newline="",encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                if r.get("Modification Indicator","").strip():continue
                ts=r["Trading Date Time"]
                day=ts[:10];hour=int(ts[11:13]);minute=int(ts[14:16])
                isin=r["Symbol"].strip();ccy=r["Price Currency"].strip();venue=r["Execution Venue"].strip()
                price=float(r["Price"]);qty=float(r["Executed Shares"])
                if not isin or price<=0 or qty<=0:continue
                key=(day,hour,venue,isin,ccy)
                observed[key][minute].append((ts,price,qty))
                counts[(day,hour,venue)]+=1
            except (ValueError,KeyError,IndexError):continue

def bars_for(data):
    bars=[]
    for minute in range(60):
        trades=sorted(data.get(minute,[]))
        if not trades:bars.append(None);continue
        vol=sum(t[2] for t in trades)
        bars.append({"minute":minute,"price":trades[0][1],
                     "last":trades[-1][1],"vwap":sum(t[1]*t[2] for t in trades)/vol,
                     "volume":vol,"trades":len(trades)})
    return bars

ranked=sorted(observed.items(),key=lambda x:sum(len(v) for v in x[1].values()),reverse=True)
selected=[(key,bars_for(data)) for key,data in ranked if len(data)>=45][:24]
if not selected:raise SystemExit("No instruments with sufficient minute coverage")

# Public dashboard payload: aggregated bars ONLY, no raw vendor transactions.
dashboard=[]
for key,bars in selected:
    day,hour,venue,isin,ccy=key
    dashboard.append({"id":"|".join(map(str,key)),"day":day,"hour":hour,"venue":venue,
                      "isin":isin,"currency":ccy,"bars":bars})
(base/"ui_data.json").write_text(json.dumps({"source":"Cboe public delayed trade files",
    "scope":"Selected instruments and minute aggregates, not raw trades",
    "series":dashboard},separators=(",",":")))

def simulate(key,bars,start,side,qty,strategy):
    horizon=15
    window=bars[start:start+horizon]
    if len(window)!=horizon or any(x is None for x in window):return None
    arrival=window[0]["price"];end=window[-1]["last"]
    market_volume=sum(x["volume"] for x in window)
    benchmark=sum(x["vwap"]*x["volume"] for x in window)/market_volume
    parent=ParentOrder("study",side,qty,arrival,end)
    left=qty;fills=[]
    # Ex-ante fixed reference volume; no future window volume used to schedule.
    prior=1000.0
    reference_volume=1000.0
    for n,b in enumerate(window):
        if left<=0:break
        cap=math.floor(.08*b["volume"])
        if strategy=="immediate":desired=left
        elif strategy=="twap":desired=math.ceil(qty/horizon)
        else:
            # Only lagged volume is used for adaptive scheduling.
            target=left/(horizon-n)
            desired=math.ceil(target*max(.5,min(1.5,prior/reference_volume)))
        fillqty=min(left,cap,desired)
        if fillqty:
            impact=2.5*math.sqrt(fillqty/max(b["volume"],1)*100)
            sign=1 if side=="BUY" else -1
            price=b["price"]*(1+sign*(1+impact)/10000)
            fees=.3/10000*price*fillqty
            fills.append(Fill("study",f"{strategy}-{n}",start+n,fillqty,price,fees))
            left-=fillqty
        prior=b["volume"]
    return analyse(parent,fills,benchmark)

scenarios=[]
for key,bars in selected:
    for start in (0,15,30,45):
        window=bars[start:start+15]
        if len(window)<15 or any(x is None for x in window):continue
        turnover=sum(x["volume"] for x in window)
        for side in ("BUY","SELL"):
            for pct in (.005,.02):
                qty=max(1,int(turnover*pct))
                vals={s:simulate(key,bars,start,side,qty,s) for s in ("immediate","twap","adaptive")}
                if all(vals.values()):
                    scenarios.append({"id":len(scenarios)+1,"instrument":key[3],"venue":key[2],
                                      "day":key[0],"hour":key[1],"start_minute":start,"side":side,
                                      "quantity":qty,"results":{s:{"shortfall_bps":round(v["implementation_shortfall_bps"],5),
                                      "fill_rate":round(v["fill_rate"],5),"vwap_slippage_bps":round(v["vwap_slippage_bps"],5) if v["vwap_slippage_bps"] is not None else None}
                                      for s,v in vals.items()}})

if not scenarios:raise SystemExit("No complete 15-minute scenarios")
(base/"scenario_data.json").write_text(json.dumps({"disclaimer":"Simulated orders/fills on observed Cboe trade-price paths; not real TCA","scenarios":scenarios},separators=(",",":")))

means={s:statistics.mean(x["results"][s]["shortfall_bps"] for x in scenarios) for s in ("immediate","twap","adaptive")}
fills={s:statistics.mean(x["results"][s]["fill_rate"] for x in scenarios) for s in means}

# Scenario-level bootstrap of *paired* differences; exploratory only because
# scenarios overlap by instrument/session and the observed sample is narrow.
rng=random.Random(20261103)
def bootstrap_diff(a,b,replications=1500):
    diffs=[x["results"][a]["shortfall_bps"]-x["results"][b]["shortfall_bps"] for x in scenarios]
    n=len(diffs);averages=[]
    for _ in range(replications):averages.append(sum(diffs[rng.randrange(n)] for _ in range(n))/n)
    averages.sort()
    return statistics.mean(diffs),averages[int(.025*replications)],averages[int(.975*replications)]

comparisons={"adaptive - twap":bootstrap_diff("adaptive","twap"),
             "adaptive - immediate":bootstrap_diff("adaptive","immediate")}

summary_rows="".join(f"<tr><td>{s.title()}</td><td>{means[s]:.2f}</td><td>{fills[s]:.1%}</td></tr>" for s in means)
comp_rows="".join(f"<tr><td>{html.escape(k)}</td><td>{v[0]:.2f}</td><td>[{v[1]:.2f}, {v[2]:.2f}]</td></tr>" for k,v in comparisons.items())
coverage_rows="".join(f"<tr><td>{day}</td><td>{hour:02d}:00 UTC</td><td>{venue}</td><td>{count:,}</td></tr>" for (day,hour,venue),count in sorted(counts.items()))
report=f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ExecutionLab multi-session validation</title><style>body{{font:15px/1.6 Arial;color:#18243a;background:#f4f6f9}}main{{max-width:930px;margin:25px auto;background:white;padding:40px}}h1{{font:35px Georgia,serif}}h2{{border-bottom:1px solid #d3dbe4;padding-bottom:8px}}table{{border-collapse:collapse;width:100%}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #e2e7ed}}th{{background:#edf2f7}}.note{{background:#fff0c7;padding:14px;border-left:4px solid #b78b28}}small{{color:#68778d}}@media(max-width:700px){{main{{padding:16px;overflow:auto}}}}</style></head><body><main><small>EXECUTIONLAB / EXPERIMENTAL RESEARCH</small><h1>Multi-session execution scenario study</h1><p>Jahnavi Sistla · November 2026</p><div class="note"><b>Interpretation boundary:</b> observed Cboe market trade prices/volumes, but hypothetical investor orders, fills, spread and market impact. Results are not actual client transaction costs. The sample covers a small number of recent files.</div><h2>Data coverage</h2><p>Selected {len(selected)} instrument/venue/session series with at least 45 populated minutes; generated {len(scenarios)} repeated 15-minute scenarios (BUY/SELL, two order-size levels, multiple start times). This is not a representative sample of European equity trading.</p><table><tr><th>Date</th><th>Hour</th><th>Venue</th><th>Trade records</th></tr>{coverage_rows}</table><h2>Simulated strategy outcomes</h2><table><tr><th>Strategy</th><th>Mean shortfall (bps)</th><th>Mean fill rate</th></tr>{summary_rows}</table><h2>Paired comparison</h2><table><tr><th>Comparison</th><th>Mean difference (bps)</th><th>Naive scenario bootstrap interval</th></tr>{comp_rows}</table><p><small>Positive difference means the first strategy has higher simulated cost. These naive intervals resample scenarios as though independent; overlapping scenarios and shared market paths mean they <b>must not be interpreted as statistical significance</b>. More dates and clustered resampling are required.</small></p><h2>Assumptions and limitations</h2><ul><li>Each strategy has the same parent size, side and 15-minute observed trade-price path.</li><li>Execution capacity is capped at 8% of observed minute volume. Hypothetical fill price is first observed trade price plus a 1bp half-spread and nonlinear participation penalty; fees are 0.3bp.</li><li>The adaptive policy uses prior-minute volume against a fixed, ex-ante 1,000-share reference. It does not use future volume to schedule; the fixed reference is arbitrary and should ultimately be replaced with a calibrated historical profile.</li><li>Fill capacity is based on same-minute realised volume and is therefore an ex-post simulated constraint, not a live execution model.</li><li>Fill probability, queue position, displayed liquidity, auction conditions and venue fees are not calibrated.</li><li>Instrument selection is based on activity and minute coverage, which biases the sample toward liquid series.</li></ul><h2>What comes next</h2><p>Add licensed quote history, apply strict quote-to-trade as-of joins, calibrate execution assumptions, extend to more days, and use instrument-day clustered uncertainty estimates.</p></main></body></html>'''
(base/"validation_report.html").write_text(report)
print(f"Observed {sum(counts.values()):,} trade records across {len(counts)} file-venue slices; {len(scenarios)} scenarios; mean IS bps: {means}")
