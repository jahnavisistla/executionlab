# ExecutionLab — Synthetic TCA & European Equity Microstructure

Independent portfolio mini-study by Jahnavi Sistla (November 2026).

## What this demonstrates

- Correctly signed arrival-price execution shortfall for buy and sell orders.
- Reproducible Python analytics and order-level data generation.
- Segmentation by stylised trading-session and venue regimes.
- Awareness of European equity market microstructure and selection-bias limitations.
- Clear separation of simulation results from real market claims.

## Run

`python3 analysis.py`

Open `research_report.html` in a browser. The generated `synthetic_orders.csv` provides 2,400 simulated records. Python standard library only.

## Caveat

**All observations are synthetic.** The assumptions build cost relationships into the simulation. Findings are tests of analytical methods, not empirical conclusions about European markets or specific trading venues. No employer data, code or client information is used.

## Additional real-market-data module (ExecutionLab 2.0)

`real_market_study.py` independently analyses a Cboe Europe delayed public trade CSV supplied by the researcher. It produces `observed_trade_report.html` with observed trade counts, instrument-level VWAP, volumes and a trade-price variability proxy. This is a separate empirical *trade-activity* analysis; it must not be confused with client TCA.

An example source file is the Cboe Europe MiFID public trade file for CXE, 2 November 2026 at 13:00 UTC. **Raw Cboe market data is deliberately excluded from the distributed project**. Data is subject to Cboe's non-commercial-use conditions: https://www.cboe.com/europe/equities/trade_data

Run the module with `python3 real_market_study.py /path/to/your_downloaded_cboe_file.csv`.

## TCA 3.0 engine and controlled strategy experiment

- `tca_engine.py`: typed parent-order/fill structures; direction-aware implementation shortfall, residual opportunity cost, explicit fees, fill rate, VWAP slippage; optional effective/realised-spread formulas when **genuine matched quote data** exists.
- `test_tca_engine.py`: unit tests for full/partial/unfilled orders, both sides, fee logic and invalid fills.
- `strategy_study.py`: compares immediate, TWAP-style and previous-volume-adaptive simulated execution schedules using **observed** Cboe trade-price/volume paths but **hypothetical** parent orders, fill capacities, spreads and impact.
- `strategy_report.html`: generated strategy experiment, with assumptions and limitations prominently identified.

Run from this directory:

```
python3 -m unittest test_tca_engine.py
python3 strategy_study.py /path/to/cboe_bxe.csv /path/to/cboe_cxe.csv /path/to/cboe_dxe.csv
```

Do not pass observed exchange trades off as fills of a real customer order. Quotes, order book, multiple days and robust strategy validation remain necessary before claiming empirical strategy performance.

## Interactive dashboard

Open `dashboard.html` next to the generated HTML reports. Its five tabs cover the overview, observed trades, a live editable TCA workbench, execution strategy experiments and methodological limitations. It runs locally without a server, external JavaScript dependencies or an account.

## Next steps for a genuine empirical study

1. Acquire properly licensed historical European equity trade/quote data.
2. Join order and market-data timestamps; account for clock precision and corporate actions.
3. Calculate effective/quoted spreads, VWAP, arrival-price shortfall and fees.
4. Compare venues or order schedules with appropriate controls for market conditions and order-selection bias.
5. Add confidence intervals, out-of-sample tests, reproducible research notes and a concise client-facing summary.

## CV wording (only after independently running and understanding this work)

"Built a reproducible Python TCA research prototype using 2,400 synthetic equity orders, measuring signed arrival-price shortfall and evaluating simulated relationships between execution cost, liquidity proxies and participation rates; documented market-microstructure assumptions and validation limitations."
