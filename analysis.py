"""Reproducible SYNTHETIC European-equity execution-cost study.

No proprietary, live, or historical exchange data is used. Standard-library only.
Run: python3 analysis.py
"""
import csv
import math
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RNG = random.Random(20261103)
N = 2400
ROWS = []
SESSIONS = ["open", "midday", "close"]
VENUES = ["lit", "auction", "alternative"]

for i in range(N):
    session = SESSIONS[i % 3]
    venue = VENUES[(i // 3) % 3]
    side = "buy" if RNG.random() < .5 else "sell"
    # Deliberate modelling assumptions, not observed European market facts.
    session_spread = {"open": 3.0, "midday": 1.7, "close": 2.2}[session]
    session_vol = {"open": 1.55, "midday": .75, "close": 1.10}[session]
    spread_bps = max(.3, RNG.gauss(session_spread, .45))
    volatility = max(.15, RNG.gauss(session_vol, .22))
    participation_pct = RNG.uniform(2, 22)
    quantity = RNG.randrange(500, 20001, 100)
    arrival = RNG.uniform(20, 200)
    venue_effect = {"lit": .4, "auction": -.25, "alternative": .1}[venue]
    impact_bps = .12 * participation_pct + .95 * volatility + .35 * spread_bps + venue_effect
    noise = RNG.gauss(0, 1.4)
    slippage_bps = impact_bps + noise
    direction = 1 if side == "buy" else -1
    fill = arrival * (1 + direction * slippage_bps / 10000)
    cost = direction * (fill - arrival) * quantity
    ROWS.append({"order_id": i + 1, "session": session, "venue_type": venue,
                 "side": side, "quantity": quantity, "arrival_price": round(arrival, 6),
                 "fill_price": round(fill, 6), "spread_bps": round(spread_bps, 4),
                 "volatility_proxy": round(volatility, 4),
                 "participation_pct": round(participation_pct, 4),
                 "shortfall_bps": round(slippage_bps, 5), "signed_cost": round(cost, 4)})

with (ROOT / "synthetic_orders.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=ROWS[0].keys())
    writer.writeheader()
    writer.writerows(ROWS)

def mean(rows, key):
    return statistics.mean(x[key] for x in rows)

overall = mean(ROWS, "shortfall_bps")
session_means = {s: mean([r for r in ROWS if r["session"] == s], "shortfall_bps") for s in SESSIONS}
venue_means = {v: mean([r for r in ROWS if r["venue_type"] == v], "shortfall_bps") for v in VENUES}

def correlation(a, b):
    mx, my = statistics.mean(a), statistics.mean(b)
    numerator = sum((x-mx)*(y-my) for x,y in zip(a,b))
    denominator = math.sqrt(sum((x-mx)**2 for x in a)*sum((y-my)**2 for y in b))
    return numerator / denominator

corr_part = correlation([r["participation_pct"] for r in ROWS], [r["shortfall_bps"] for r in ROWS])
corr_spread = correlation([r["spread_bps"] for r in ROWS], [r["shortfall_bps"] for r in ROWS])

def bars(mapping, high=12):
    out = []
    for k,v in mapping.items():
        width = max(1, min(100, 100 * v / high))
        out.append(f'<div class="barline"><span>{k.title()}</span><div class="track"><div style="width:{width:.1f}%"></div></div><b>{v:.2f} bps</b></div>')
    return "\n".join(out)

html = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ExecutionLab — Synthetic TCA Research</title><style>
body{{font:16px/1.6 Arial,sans-serif;color:#172235;background:#f4f5f7;margin:0}}main{{max-width:900px;margin:auto;background:white;padding:48px 58px;box-shadow:0 1px 15px #ddd}}h1{{font: bold 40px Georgia,serif;line-height:1.15;margin:0}}h2{{font: bold 22px Georgia,serif;border-bottom:1px solid #c8d0da;padding-bottom:8px;margin-top:34px}}.eyebrow{{letter-spacing:2px;font-weight:700;font-size:12px;color:#596a85}}.tag{{display:inline-block;background:#fff0ca;padding:5px 10px;border-radius:4px;color:#6f4e00;font-weight:bold;font-size:12px;margin:15px 0}}.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}.stat{{background:#edf1f7;padding:18px}}.stat strong{{display:block;font-size:28px}}.stat small{{color:#536176}}.barline{{display:grid;grid-template-columns:100px 1fr 85px;align-items:center;gap:12px;margin:12px 0;font-size:13px}}.track{{height:17px;background:#edf1f7}}.track div{{background:#1c416c;height:100%}}table{{border-collapse:collapse;width:100%}}td,th{{padding:9px;border-bottom:1px solid #e1e4e9;text-align:left}}.muted{{color:#526078}}code{{background:#edf1f7;padding:2px 4px}}@media(max-width:650px){{main{{padding:22px}}.stats{{grid-template-columns:1fr}}.barline{{grid-template-columns:70px 1fr 70px}}}}
</style></head><body><main><div class="eyebrow">EXECUTIONLAB / REPRODUCIBLE MINI-STUDY</div><h1>Execution Cost &amp; European Equity Market Microstructure</h1><p class="muted">Jahnavi Sistla · Independent quantitative research prototype · November 2026</p><div class="tag">SYNTHETIC DATA — NOT AN EMPIRICAL MARKET FINDING</div>
<p><b>Research question:</b> How do spreads, volatility, trading-session conditions and order participation relate to execution shortfall in a controlled simulation of European-equity-style orders?</p>
<div class="stats"><div class="stat"><strong>{N:,}</strong><small>Simulated orders</small></div><div class="stat"><strong>{overall:.2f} bps</strong><small>Mean simulated shortfall</small></div><div class="stat"><strong>3</strong><small>Session regimes</small></div></div>
<h2>1. Methodology</h2><p>Generate reproducible order records with buy/sell direction, arrival price, fill price, quantity, a stylised spread, volatility proxy, participation rate and venue type. All prices are arbitrary currency units. The simulation assumes an additive cost process: participation, spread, volatility and venue effects plus random noise. These assumptions deliberately create relationships for testing the analytics pipeline.</p>
<p><b>Implementation shortfall (bps):</b> <code>side_sign × (fill − arrival) / arrival × 10,000</code>; +1 for buys, −1 for sells. Signed cost equals <code>side_sign × (fill − arrival) × quantity</code>. Positive values indicate adverse execution. This is a <i>filled-order arrival-price shortfall</i> measure, not a complete portfolio-level implementation shortfall calculation.</p>
<h2>2. Simulated results</h2><h3>Average shortfall by trading session</h3>{bars(session_means)}<h3>Average shortfall by stylised venue type</h3>{bars(venue_means)}
<table><tr><th>Relationship</th><th>Pearson correlation</th></tr><tr><td>Participation vs shortfall</td><td>{corr_part:.3f}</td></tr><tr><td>Spread vs shortfall</td><td>{corr_spread:.3f}</td></tr></table>
<p>These results follow from the data-generating assumptions. They do <b>not</b> demonstrate how European venues actually perform, establish causality or validate a trading strategy.</p>
<h2>3. Execution and market-structure interpretation</h2><p>In real European equities, execution quality depends on venue fragmentation, order type, lit versus dark liquidity, periodic auctions, spread, queue priority, market impact and the chosen benchmark. A credible TCA comparison must control for differences in order difficulty and market state; raw venue averages are especially prone to selection bias.</p>
<h2>4. Limitations and next experiment</h2><ul><li>No observed market data or true venue-level liquidity; labels are simplified and are not claims about specific exchanges.</li><li>No partial fills, opportunity cost, bid/ask quotes, timestamps, fees, impact decay or dynamic order-book evolution.</li><li>Research extension: obtain licensed historical quotes/trades, calculate mid-price and effective spread, implement VWAP/time-weighted benchmarks, and compare execution cohorts using matching or regression controls.</li><li>Further extension: test outcomes of alternative participation schedules with walk-forward validation and realistic transaction fees.</li></ul>
<h2>5. Reproduction</h2><p>Run <code>python3 analysis.py</code> using Python 3. The script generates <code>synthetic_orders.csv</code> and regenerates this report with a fixed random seed. No third-party packages or credentials required.</p>
<p class="muted">Portfolio demonstration of TCA calculation, reproducible statistical workflows and awareness of European equity market-structure research requirements.</p></main></body></html>'''
(ROOT / "research_report.html").write_text(html)
print(f"Created {N} synthetic orders. Mean shortfall={overall:.3f} bps; participation correlation={corr_part:.3f}")
