# ExecutionLab

I work on electronic trading systems, so I wanted to follow an order beyond the point where it gets routed. What did it cost to execute? How much did the answer depend on the benchmark? And what happens if the order never finishes?

ExecutionLab is a Python research project for asking those questions in European equities. It brings together a TCA engine, historical market-data analysis, simulated orders and a dashboard you can explore locally.

## Start here

You only need Python 3 and a browser. Open `dashboard.html` to browse the bundled reports and try the editable TCA calculator. To run the checks and reproduce the synthetic report:

```bash
python3 -m unittest discover -p 'test_*.py'
python3 analysis.py
```

Try changing the side, fill quantity or end price in the calculator. A partially filled order can look good against VWAP and still have expensive implementation shortfall once you account for the shares left behind.

## What I measured

| Part | Data | What it shows |
| --- | --- | --- |
| Trade analysis | Cboe Europe delayed prints from selected hours on 30 October and 2 November 2026 | Trade counts, volume, trade VWAP and price variation |
| Strategy comparison | Observed trade paths with hypothetical orders and fills | How immediate, equal-slice and volume-adaptive schedules behave under the model's assumptions |
| Quote replay | Separate Cboe BXE Trades & Quotes sample from 1 September 2020 | Top-of-book reconstruction and quoted spread diagnostics for two sample instruments |

The initial hour included 301,871 trade records across 2,651 instrument and currency pairs. The expanded run covered 436,424 trade records and 336 hypothetical scenarios. These are narrow samples. The 2020 quotes and 2026 trades stay separate, and there are no observed client fills. See [the research notes](RESEARCH.md) and [the replay validation log](VALIDATION.md) for the results and their limitations.

## Reproduce the market studies

Download permitted data from [Cboe Europe](https://www.cboe.com/europe/equities/trade_data) or [Cboe DataShop](https://datashop.cboe.com/). The raw files stay local under the provider's terms. Pass all the desired trade files to each script and substitute your own filenames.

```bash
python3 real_market_study.py path/to/bxe.csv path/to/cxe.csv
python3 strategy_study.py path/to/bxe.csv path/to/cxe.csv
python3 research_v4.py path/to/bxe.csv path/to/cxe.csv
python3 build_dashboard.py
python3 quote_sample_report.py path/to/cboe_taq_sample.zip
```

Open `dashboard_interactive.html` after the build for the instrument and venue explorer and scenario drill-down. The generated dashboard and its data payloads stay local.

## Where the logic lives

- `tca_engine.py` calculates arrival-price shortfall, missed-fill opportunity cost, fees, fill rate and VWAP slippage. Positive cost means worse execution for both buys and sells.
- `research_v4.py` groups trade prints into minute bars and compares schedules across repeated hypothetical parent orders.
- `cboe_sample_book.py` replays visible order events to reconstruct the best bid and ask. The validation log explains what was checked and where an independent exchange snapshot would help.
- `quote_analysis.py` matches trades to the latest eligible quote at or before the trade on the same instrument and venue, within a configurable age limit. For quotes with the same timestamp it uses the last valid update in file order. Effective spread requires a supplied buy or sell side.

## What I’d test next

I’d reconcile the replay against independent snapshots, collect more matched trade and quote sessions, and test the simulation on later dates with a wider range of participation, spread and impact assumptions. [The prospective study design](STUDY_DESIGN.md) spells out the hypotheses and data rules. To make claims about client execution quality, I’d also need actual parent orders and fills.

This is independent research using public market samples and synthetic orders. It uses no employer systems, client information or proprietary code.
