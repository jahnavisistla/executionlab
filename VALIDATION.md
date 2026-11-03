# Order-book reconstruction validation log

Date: 3 November 2026

## Scope

Cboe Europe DataShop downloadable BXE Trades & Quotes sample, 1 September 2020, accessed without a subscription. The local ZIP contains several per-symbol PITCH-derived CSV event files. Raw event records are excluded from GitHub.

Official specification consulted: [Cboe Europe Multicast PITCH](https://cdn.cboe.com/resources/participant_resources/BATS_Europe_MC_PITCH_Specification.pdf).

## Checks and corrections

| Area | What was checked or changed |
|---|---|
| Message map | Verified decimal CSV codes against PITCH hex types for add, execute, reduce, modify and delete. |
| At-price execution | Corrected type 0x24 (decimal 36) to use its explicit `Remaining Shares` field instead of ignoring it. |
| Book validity | Stop carrying a valid quote across empty or locked/crossed-book states. Exclude those intervals from time-weighted spread denominators. |
| Sequence audit | Track non-increasing event sequence numbers and backward timestamps. |
| Order state | Count duplicate order IDs, unknown deletes/modifies/reductions and over-reductions. |
| Sensitivity diagnostics | Report the fraction of valid quote time with spreads wider than 100bps, alongside median and time-weighted mean. |
| Tests | Added cases for at-price remaining quantity, invalid intervals and sequence reversals. All 13 tests pass. |

## Sample-derived diagnostics

| Symbol | Reconstructed valid top changes | Time-weighted mean quoted spread | Event median quoted spread | Valid observed quote time |
|---|---:|---:|---:|---:|
| ORAp | 35,204 | 15.56 bps | 15.20 bps | 520.4 minutes |
| ACXd | 135 | 385.83 bps | 393.26 bps | 499.3 minutes |

These are only diagnostics from sample records, not market-wide estimates. The extreme ACXd spread and ORAp outliers should be investigated in context rather than used to infer general trading costs. The full high-level diagnostics are generated in `quote_sample_report.html`.

## What this does **not** validate

- No independent exchange snapshot was available to reconcile the reconstructed book at a known point in time.
- The replay is not a certified full-depth exchange parser; less-common message types, auction states and reset conditions need additional work.
- There is no matched client-order data and no observed implementation shortfall.
- The 2020 quote sample cannot be time-aligned with the project's separate 2026 transaction files.
- One day and two sample instruments cannot support general conclusions about European equity microstructure.

## Reproduction

```bash
python3 -m unittest discover -p 'test_*.py'
python3 quote_sample_report.py path/to/cboe_taq_sample.zip
```

The raw ZIP is available from Cboe DataShop's public sample link, subject to its conditions. The repository deliberately excludes it.
