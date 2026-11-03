# ExecutionLab — empirical study design

Status: **prospective design for additional data**. The initial exploratory results and prototype were developed before this plan. This document must not be described as a preregistration of earlier analyses.

## Primary question

How do quoted spreads and displayed liquidity vary by time of day and volatility regime across a defined set of European equity instruments and venues?

## Secondary simulation question

Conditional on observed trade/quote paths, how sensitive are hypothetical execution schedules to order size, market conditions and the assumptions of the fill/impact model?

## Hypotheses to test on future data

- H1: Within instrument/venue, quoted spreads are higher in the first and final 30 continuous-trading minutes than in a midday reference window.
- H2: Higher short-horizon realised volatility is associated with wider contemporaneous quoted spreads, controlling for instrument, date and time-of-day effects.
- H3 (simulation only): A schedule conditioned on ex-ante liquidity signals has different estimated shortfall and completion risk than an equal-slice schedule. Direction is not assumed.

## Data requirements and inclusion policy

- Obtain properly licensed, exchange-specific trade and quote histories over at least 20 trading dates, with timestamp, instrument ID, venue, best bid/ask and sizes, trade price/size and trade conditions.
- Define the instrument universe before evaluating outcomes (for example, a preselected basket of liquid UK and EU equities).
- Record the time zone, timestamp granularity, venue trading hours, currency and corporate actions.
- Exclude out-of-session, auction, correction, crossed/locked and clearly stale quote observations from the continuous-session primary sample; report exclusion rates separately.
- Use only quotes timestamped at or before the associated trade; state any as-of tolerance and conduct tolerance sensitivity checks.
- Do not merge the 2020 Cboe quote sample with 2026 trade prints. They are separate demonstration datasets.

## Estimands

- Quoted spread (bps): 10,000 × (ask − bid) / midpoint.
- Time-weighted quoted spread by instrument/venue/date/session, using quote validity intervals.
- Effective spread when an independently known trade direction is available: 20,000 × side × (trade price − midpoint) / midpoint.
- Realised spread at defined forward horizons, requiring a later valid midpoint and defensible trade-side inference.
- Simulated implementation shortfall and completion rate, clearly separate from observed market statistics.

## Statistical plan

1. Analyse each instrument/venue/date as the basic dependence cluster.
2. Plot descriptive distributions with coverage and exclusion counts.
3. Estimate within-instrument time-of-day differences with date/instrument fixed effects where sample size permits.
4. Use clustered standard errors or block/bootstrap resampling at the date/instrument level—not independent resampling of overlapping orders.
5. Split dates chronologically into research and holdout windows for any strategy parameter choices.
6. Report confidence intervals, effect sizes and negative findings. Avoid interpreting observational associations as causality.

## Simulation safeguards

- Treat orders, fill probabilities, market impact and opportunity costs as hypothetical unless client fills are available.
- Estimate any volume profile from prior dates only, never the tested session.
- Use identical parent scenarios when comparing strategies, including penalties for non-completion.
- Conduct a grid sensitivity analysis over participation limits, spread assumptions, latency, fees and impact coefficients.
- Provide results by side, order-size bucket and regime, not just one overall average.

## Stop conditions / claims we will not make

- No claims of real client execution performance without parent orders and fills.
- No claims of actual quote-based spread results from trade-only files.
- No cross-date matching of unrelated sample quote and trade datasets.
- No live strategy superiority claim from uncalibrated replay simulations.
- No claim that a two-day convenience sample generalises to European markets.

## Reproducibility

Pin input file identifiers and checksums locally, keep raw licensed data out of public GitHub, version the calculation code, test sign conventions and quote joins, and distinguish observed results from simulation in every output.
