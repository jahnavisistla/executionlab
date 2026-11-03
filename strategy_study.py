"""Illustrative execution simulations conditioned on OBSERVED Cboe trades.

No actual client orders or fills, no order book, and no causal strategy claims.
Python standard library only. Supply local Cboe public trade CSVs as arguments.
"""
import csv
import html
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from tca_engine import ParentOrder, Fill, analyse

if len(sys.argv)<2:
    raise SystemExit("Usage: python3 strategy_study.py /path/to/cboe_bxe.csv [more_files.csv ...]")

data=defaultdict(lambda:defaultdict(list))
for fn in sys.argv[1:]:
    with open(fn,newline="",encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                if r.get("Modification Indicator","").strip():
                    continue
                isin=r["Symbol"].strip()
                ccy=r["Price Currency"].strip()
                timestamp=r["Trading Date Time"]
                minute=int(timestamp[14:16])
                price=float(r["Price"])
                quantity=float(r["Executed Shares"])
                if price>0 and quantity>0 and 0<=minute<60:
                    data[(isin,ccy)][minute].append((timestamp,price,quantity))
            except (ValueError,KeyError,IndexError):
                pass

# Choose by full minute coverage first, then transactions; this is a convenience
# sampling rule, not a representative instrument selection methodology.
eligible=[(key,by_min) for key,by_min in data.items() if len(by_min)>=55]
eligible.sort(key=lambda x:(sum(len(v) for v in x[1].values())),reverse=True)
if not eligible:
    raise SystemExit("No instrument with at least 55 populated minutes")
(isin,ccy),by_min=eligible[0]
bars=[]
for minute in range(60):
    rows=sorted(by_min.get(minute,[]))
    if not rows:
        bars.append(None)
        continue
    vol=sum(x[2] for x in rows)
    bars.append({"first":rows[0][1],"last":rows[-1][1],"vwap":sum(x[1]*x[2] for x in rows)/vol,"volume":vol})

market_vwap=sum(b["vwap"]*b["volume"] for b in bars if b)/sum(b["volume"] for b in bars if b)
first=next(b for b in bars if b)
last=next(b for b in reversed(bars) if b)
market_volume=sum(b["volume"] for b in bars if b)
parent_qty=max(100,int(.012*market_volume/100)*100)

# Explicit stylised assumptions: at most 8% of observed minute volume can be
# simulated as executed, with +1bp half-spread and nonlinear participation impact.
# These are not estimated venue parameters. No child order influences real tape.
FEE_BPS=.3
HALF_SPREAD_BPS=1.0
CAP=.08

def simulate(strategy):
    parent=ParentOrder(strategy,"BUY",parent_qty,first["first"],last["last"])
    fills=[]
    left=parent_qty
    observed_previous_volume=market_volume/60
    for minute,bar in enumerate(bars):
        if bar is None or left<=0:
            continue
        capacity=int(CAP*bar["volume"])
        if strategy=="immediate":
            desired=left
        elif strategy=="twap":
            desired=math.ceil(parent_qty/60)
        else:
            # Uses PREVIOUS minute's volume, not future realised volume.
            remaining_minutes=max(1,60-minute)
            baseline=left/remaining_minutes
            intensity=max(.5,min(1.5,observed_previous_volume/(market_volume/60)))
            desired=math.ceil(baseline*intensity)
        quantity=min(left,capacity,desired)
        if quantity>0:
            part=quantity/max(bar["volume"],1)
            impact_bps=2.5*math.sqrt(part*100)
            fill_price=bar["first"]*(1+(HALF_SPREAD_BPS+impact_bps)/10000)
            fees=fill_price*quantity*FEE_BPS/10000
            fills.append(Fill(strategy,f"{strategy}-{minute}",minute,quantity,fill_price,fees))
            left-=quantity
        observed_previous_volume=bar["volume"]
    return analyse(parent,fills,market_vwap)

results={name:simulate(name) for name in ("immediate","twap","adaptive")}

def fmt(x):return "n/a" if x is None else f"{x:,.2f}"
rows=[]
for name,r in results.items():
    rows.append(f"<tr><td>{name.title()}</td><td>{r['fill_rate']:.1%}</td><td>{fmt(r['implementation_shortfall_bps'])}</td><td>{fmt(r['vwap_slippage_bps'])}</td><td>{fmt(r['opportunity_cost'])}</td><td>{fmt(r['fees'])}</td></tr>")

report='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ExecutionLab Strategy Study</title><style>body{background:#f3f5f7;color:#152138;font:16px/1.6 Arial;margin:0}main{max-width:960px;margin:30px auto;background:white;padding:45px}h1{font:36px Georgia,serif}h2{border-bottom:1px solid #cdd5df;padding-bottom:6px}table{border-collapse:collapse;width:100%}td,th{padding:12px;border-bottom:1px solid #e1e5ec;text-align:left}th{background:#edf1f6}.warning{background:#fff0c9;border-left:4px solid #b88e16;padding:15px}small{color:#627088}@media(max-width:650px){main{padding:14px;overflow:auto}}</style></head><body><main><small>EXECUTIONLAB / CONTROLLED STRATEGY EXPERIMENT</small><h1>Execution Strategy Comparison</h1><p>Jahnavi Sistla · November 2026</p><p class="warning"><b>Illustrative simulations on an observed trade-price path.</b> The Cboe trades are real; parent orders, fills, execution capacity, half-spread and impact are simulated. This is not realised client TCA, a historical backtest with a full order book, or evidence of strategy superiority.</p><h2>Experiment design</h2><p>Instrument: <b>{isin}</b> ({ccy}); period: 2 November 2026, 13:00–14:00 UTC; simulated BUY parent: <b>{qty:,}</b> shares ({parent_pct:.2%} of observed volume). Benchmark: observed trade VWAP <b>{vwap:.4f}</b>. Execution capacity capped at 8% of each minute's observed shares.</p><p>Strategies: immediate (seek completion earliest), TWAP-style (equal target quantity per minute), adaptive (target intensity based on the <i>previous</i> minute's volume). Simulated fills use the first observed trade price in a minute plus an assumed 1bp half-spread and a nonlinear participation-impact penalty; fees are 0.3bp of fill notional.</p><h2>Simulated outcomes</h2><table><tr><th>Strategy</th><th>Fill rate</th><th>Total IS (bps)</th><th>VWAP slippage (bps)</th><th>Opportunity cost ({ccy})</th><th>Fees ({ccy})</th></tr>{rows}</table><p><small>Positive slippage and shortfall mean worse-than-benchmark execution for a buy. Full implementation shortfall includes residual opportunity cost marked to the final observed trade price.</small></p><h2>What can and cannot be concluded</h2><p>This controlled comparison demonstrates order/fill accounting and how different schedules interact with one observed price/volume path. It does not infer the real fill probability or market impact of a client order. Results on one selected instrument and hour provide no basis for generalising to European equity execution. All strategies share assumptions, but their counterfactual executions cannot be validated without order-book and fill data.</p><h2>Next research controls</h2><ul><li>Repeat across multiple dates, instruments, sides and order-size buckets.</li><li>As-of join real best bid/offer quotes and test timestamp sensitivity.</li><li>Calibrate cost and fill parameters, model queue effects and test fee schedules.</li><li>Apply bootstrap confidence intervals and walk-forward partitions by day.</li><li>Compare against a deliberately simple baseline, including incomplete orders.</li></ul></main></body></html>'''
replacements={"isin":html.escape(isin),"ccy":html.escape(ccy),"qty:,":f"{parent_qty:,}","parent_pct:.2%":f"{parent_qty/market_volume:.2%}","vwap:.4f":f"{market_vwap:.4f}","rows":"\n".join(rows)}
for k,v in replacements.items():report=report.replace("{"+k+"}",v)
Path(__file__).with_name("strategy_report.html").write_text(report)
print(f"Instrument {isin}/{ccy}, {parent_qty} synthetic shares; " + ", ".join(f"{k}: fill={v['fill_rate']:.1%}, IS={v['implementation_shortfall_bps']:.2f}bps" for k,v in results.items()))
