# ExecutionLab — Research notes (November 2026)

## Question

How do different execution schedules behave under a controlled set of hypothetical client orders when conditioned on observed European equity trade-price and volume paths?

This is an exploratory **simulation study**, not a historical measurement of actual client transaction costs.

## What is observed

Public Cboe Europe delayed trade CSV files from BXE, CXE and DXE, covering selected hours on 30 October and 2 November 2026. The analysis runs on locally downloaded data and does not redistribute raw market records. Available inputs cover a narrow, non-representative subset of market activity.

- 436,424 positive-price and positive-size records processed in the expanded sample (some files contain multiple execution-venue codes).
- 24 highly active instrument/venue/session series selected for sufficiently dense minute-level coverage.
- Instrument-level trade volume, first/last trade prices and minute VWAP aggregated from observed records.

## What is simulated

For each selected price/volume path, the study creates BUY and SELL parent orders at two order-size levels and four possible start times. This produces 336 scenarios of 15 minutes each. Every scenario is evaluated using the same price path under three schedules:

1. **Immediate:** seek as much quantity as the model permits in each minute.
2. **TWAP-style:** request an even target quantity per minute.
3. **Adaptive:** vary requested participation based on previously observed minute volume and a fixed reference.

All client orders, child fills, tradeable capacity, spread costs and market impact are hypothetical. The fill price assumes the minute's first trade plus 1bp half-spread and a nonlinear participation penalty. Fees are set to 0.3bp and the maximum fill is 8% of observed minute volume. Those values are modelling choices, not calibrated empirical estimates. Some fill-capacity assumptions use same-minute realised market volume and therefore cannot represent a live executable strategy.

## TCA accounting

The core engine models a parent order and child fills and calculates:

- Executed quantity and fill rate.
- Signed execution-price difference from the parent arrival price.
- Opportunity cost on unexecuted quantity, marked to an end price.
- Explicit fees and total implementation shortfall in currency and basis points.
- VWAP slippage on executed quantity.

Effective and realised spread functions are present, but should only be applied once genuine matched bid/ask quote data is supplied. The quote module uses backward as-of timestamp alignment, rejects future and stale quotes, and does not infer aggressor side when it is unknown.

## Preliminary results (simulation only)

Across 336 scenarios, mean simulated implementation shortfall was approximately:

| Schedule | Mean shortfall (bps) |
|---|---:|
| Immediate | 7.45 |
| TWAP-style | 4.44 |
| Adaptive | 4.51 |

These are **not real trading performance estimates**. They depend materially on the synthetic fill/cost model and on the selected observed price paths. The generated `validation_report.html` provides mean fill rates and paired comparisons.

The report contains exploratory scenario-level bootstrap intervals. Because scenarios overlap within instruments and trading sessions, those intervals do not support statistical-significance claims. This small two-date sample cannot establish robust market structure patterns.

## Why the analysis is limited

- **Selection:** series are chosen for minute coverage and activity, favouring liquid instruments.
- **Sampling:** only selected recent files, dates and hours are included.
- **No quotes:** trade prints are not bid/ask quotes; quoted or effective spreads cannot yet be measured empirically.
- **No client fills:** actual implementation shortfall is unavailable without investor order and fill records.
- **Counterfactuals:** executing the hypothetical order could alter the market; our simulation does not account for that feedback.
- **Uncertainty:** scenarios are correlated; scenario-level bootstrap intervals are descriptive, not robust inference.
- **Licensing:** Cboe data remains local and must be used in accordance with provider terms.

## Follow-up research

1. Obtain licensed or explicitly permitted historical trade-and-quote records, then align timestamps and calculate quoted/effective spreads.
2. Expand to more trading days and instrument/venue combinations.
3. Replace simple fill assumptions with calibrated queue, capacity, spread and impact models.
4. Apply instrument-day clustered resampling and evaluate out of sample.
5. Compare performance and completion risk under multiple fee and volatility assumptions.

## Reproduce

With Python 3 and locally downloaded Cboe trade CSVs:

```bash
python3 -m unittest discover -p 'test_*.py'
python3 research_v4.py path/to/cboe_*.csv
python3 build_dashboard.py
```

Open `dashboard_interactive.html` alongside `validation_report.html`, `observed_trade_report.html` and `strategy_report.html`. The interactive dashboard embeds aggregated market and scenario data so it can be used locally without a server.

The data model, calculations and interpretation are open for review. The project does not use Citi proprietary data or code.
