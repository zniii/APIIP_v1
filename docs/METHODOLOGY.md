# Methodology

How APIIP turns a list of holdings into a health check, a risk score and a forecast. Each section starts in plain language and then gives the exact rules, so you can check or challenge them. Every constant named here is defined once in the source file shown beside it.

> **Read this first.** The sample holdings in `data/sample/` are AI-generated placeholders. Prices come from Yahoo Finance and may be delayed. Nothing here is investment advice: the forecast is an estimate from past price behaviour, and the risk score is a screening tool, not a guarantee.

## Contents

1. [Data](#1-data)
2. [Portfolio analysis](#2-portfolio-analysis)
3. [Risk assessment](#3-risk-assessment)
4. [Forecasting model](#4-forecasting-model)
5. [Validation: the backtest](#5-validation-the-backtest)
6. [Insights and dashboard](#6-insights-and-dashboard)
7. [Limitations](#7-limitations)

---

## 1. Data

| Input | Source | Used for |
|---|---|---|
| Holdings (`Ticker`, `Shares`) | Sample file, an uploaded CSV, or the table you type in | Everything |
| Current price | Yahoo Finance (`yfinance`), latest close | Market value, allocation |
| 1 year of daily closes | Yahoo Finance | Best/worst performer, trend chart, volatility, drawdown |
| 5 years of daily closes and volume | Yahoo Finance | Forecast |
| S&P 500 (`^GSPC`) closes | Yahoo Finance | Forecast (market return and beta) |
| Company name and sector | Yahoo Finance, looked up per ticker | Sector analysis |

- **Sectors** use Yahoo's 11 names: Technology, Healthcare, Financial Services, Consumer Cyclical, Consumer Defensive, Communication Services, Industrials, Energy, Utilities, Real Estate and Basic Materials. The list is fixed (`SECTOR_UNIVERSE` in `src/portfolio_analysis.py`), so a portfolio's score never depends on what other portfolios hold. A ticker with no sector, such as many funds, is labelled "Other".
- **Entered holdings** are cleaned before use: tickers are upper-cased, duplicate tickers are merged by adding their shares, shares must be above zero, and at most 30 holdings are accepted.
- **Missing prices stop the analysis** with a clear error instead of being skipped, because skipping a holding would silently skew every percentage.

## 2. Portfolio analysis

Code: `src/portfolio_analysis.py`, `src/data_loader.py`.

**Value and allocation.** Market value is `shares × current price`. A holding's allocation is its market value divided by the portfolio total, as a percentage.

**Best and worst performer.** The holdings with the highest and lowest price change over the past year. Holdings carry no purchase price, so this is the *stock's* 1-year move, not your own gain or loss.

**Sector allocation.** Allocations summed by sector.

**Diversification score (0-100).** It measures how evenly money is spread across sectors, using the normalised Herfindahl-Hirschman Index (HHI):

```
HHI        = sum over sectors of (share of portfolio)^2          (shares as fractions)
min HHI    = 1 / number of sectors
normalised = (HHI - min HHI) / (1 - min HHI)
score      = (1 - normalised) × 100
```

100 means an even split across every sector; 0 means everything is in one sector. The score is measured against **all 11 sectors**, not just the ones held. Otherwise a 50/50 split across two sectors would score a perfect 100, when it only uses two of eleven.

*Example:* 50% / 30% / 20% across three sectors. HHI = 0.25 + 0.09 + 0.04 = 0.38; min HHI = 1/11 = 0.0909; normalised = 0.318; score = **68.2**.

**Concentration check.** A portfolio is flagged as concentrated if either limit is broken:

- **Sector limit:** no sector above 40%.
- **Holding limit:** no holding above `max(25%, 2 × an even split)`. A flat 25% would flag every 5-stock portfolio for ordinary drift, since an even split is already 20%. In practice the limit is 66.7% for 3 holdings, 40% for 5, and 25% from 8 holdings up.

## 3. Risk assessment

Code: `src/risk_analysis.py`.

The portfolio risk score is a weighted sum of four factors. Each factor is first scaled to the same 0-100 range (0 = no risk, 100 = maximum), so the weights are comparable.

| Factor | Weight | How it is scored (0-100) |
|---|---|---|
| Sector concentration | 40% | `100 - diversification score` |
| Volatility | 25% | Portfolio volatility ÷ 50%, capped at 100 |
| Asset concentration | 20% | How far the largest holding sits above an even split |
| Historical drawdown | 15% | Worst peak-to-trough fall ÷ 40%, capped at 100 |

```
risk score = 0.40 × sector + 0.25 × volatility + 0.20 × asset + 0.15 × drawdown
```

The weights are the named constants `RISK_WEIGHTS`; the caps are `VOLATILITY_CAP` (0.50) and `DRAWDOWN_CAP` (0.40).

- **Portfolio volatility** is the annualised standard deviation of the portfolio's daily returns, computed from the covariance matrix of the holdings: `sqrt(w' Σ w) × √252`, where `w` are the allocation weights and `Σ` the daily covariance. Using the covariance means holdings that move against each other lower the portfolio's volatility, so diversification between stocks is rewarded. One year of daily returns is used.
- **Asset concentration** is `(largest share - even split) ÷ (100 - even split) × 100`. It is 0 when every holding is the same size and 100 when one holding is everything. A single-holding portfolio scores 100.
- **Max drawdown** is the largest fall from a running peak in the portfolio's daily value over the past year, using today's share counts.

**Risk levels** (`RISK_LEVEL_BANDS`):

| Score | Level |
|---|---|
| up to 30 | Low |
| above 30, up to 45 | Medium |
| above 45, up to 60 | High |
| above 60 | Very High |

*Example:* diversification score 68.2 (sector factor 31.8), portfolio volatility 22% (factor 44), three holdings at 50/30/20 (factor 25), max drawdown 18% (factor 45). Score = 0.40 × 31.8 + 0.25 × 44 + 0.20 × 25 + 0.15 × 45 = **35.5, Medium**.

The report also shows sector exposure (which sectors exceed the 40% limit), portfolio volatility and max drawdown in their own units, and "diversification risk", which is the same number as the sector concentration factor under its V1 name.

**Why these choices.** Sector concentration carries the most weight because it is the most common way a portfolio that looks diversified by ticker count turns out not to be. Scaling every factor to 0-100 with explicit caps keeps the weights meaningful and makes each factor easy to explain. The caps and level bands are **tuned on five synthetic portfolios**, so they should be revisited with real portfolios; a 30-stock portfolio, for instance, would score low on volatility and drawdown. Because sectors come from Yahoo's classification, a portfolio of "technology" companies can be split between Technology and Communication Services (Meta and Alphabet are both Communication Services), which lowers its concentration score.

## 4. Forecasting model

Code: `src/forecasting.py`.

**What it produces.** For each stock and for the whole portfolio, over the next 21 trading days (about one month): an expected price and return, a best case, a worst case and a confidence score. The best and worst cases are the 95th and 5th percentiles of the simulated outcomes, so they bracket the middle 90% of what the model considers plausible.

**Why a Monte Carlo simulation.** Over a month, stock prices are close to a random walk, so an honest forecast is a range, not a single number. Simulating many possible months gives the expected price and the range directly, treats the portfolio as a set of correlated stocks, and can be explained to a non-specialist. Machine-learning models were not used first: there is little data (about 250 trading days a year), they overfit easily, they are hard to explain, and there was no evidence they would predict better out of sample.

**How a forecast is built.**

1. **History.** Five years of daily closes for the holdings and for the S&P 500 are aligned on common dates. A stock with fewer than 250 days of history stops the forecast with an error.
2. **Log returns** are computed from the closes.
3. **Covariance.** An exponentially weighted (EWMA) covariance matrix gives recent days more weight, with decay factor `EWMA_LAMBDA = 0.97`. This captures both each stock's volatility and how the stocks move together.
4. **Drift (expected return).** Each stock's annual expected return is a blend:
   `25% × its own past return + 75% × (risk-free rate + beta × market premium)`.
   The second term is the Capital Asset Pricing Model (CAPM) with a 4% risk-free rate and 5% market premium, and beta measured against the S&P 500. Past returns alone are very noisy, so most of the weight goes to the market-implied figure.
5. **Scenarios.** 10,000 random one-month moves are drawn from a normal distribution with the EWMA covariance (using a Cholesky factor so the stocks stay correlated), then combined with the drift.
6. **Outputs.** Scenario prices are `current price × exp(simulated log return)`. Expected price is the scenario average; best and worst case are the 95th and 5th percentiles. For the **portfolio**, each scenario's stock values are added up before taking percentiles, so the portfolio range reflects how the stocks move together rather than adding up each stock's extremes.

A fixed random seed (42) makes forecasts repeatable.

**Confidence score (0-100).** A heuristic combining three things:

```
confidence = 100 × (0.6 × tightness + 0.2 × history + 0.2 × volume stability)
tightness  = 1 - ((best case - worst case) / expected price) ÷ 0.5   (limited to 0-1)
history    = observations ÷ 750                                      (limited to 0-1)
volume     = recent volume ÷ yearly volume, or its inverse if above 1 (steadier = closer to 1)
```

Here "recent volume" is the average of the last 21 trading days and "yearly volume" the average of the last 252. *Example:* a range 20% as wide as the expected price, 1,250 days of history and recent volume at 90% of normal gives 0.6 × 0.6 + 0.2 × 1 + 0.2 × 0.9 = **74**.

The confidence score is **not a probability** and is not calibrated against outcomes. Its job is to tell you which forecasts are tighter and better supported, not how likely they are to come true. The dashboard shows it next to the full best-to-worst range every time.

## 5. Validation: the backtest

To check whether the ranges are honest, the model is run in the past. From each of 24 monthly starting dates, it forecasts using **only data available up to that date**, then compares the real price 21 trading days later with the 5th-95th percentile band (a "walk-forward" test, with 2,000 scenarios per forecast to keep it fast).

Two measures are reported:

- **Coverage:** how often the real price fell inside the band. A well-calibrated 5th-95th band should cover about 90%.
- **Winkler interval score** (lower is better): the band's width plus a penalty for each miss. It stops a band from looking good just by being very wide.

**Result on the sample portfolios:** the real price landed inside the band about **89% of the time** against a 90% target. Per portfolio the figure ranged from 86% to 90%.

**Upgrades that were tried and not kept.** A change is kept only if the backtest shows a benefit. Tested on 336 forecasts (24 origins × 14 sample stocks):

| Variant | Coverage | Interval score |
|---|---|---|
| Baseline, lambda 0.97 (**kept**) | 88.7% | 0.3509 |
| lambda 0.94 (shorter memory) | 85.7% | 0.3567 |
| lambda 0.985 (longer memory) | 89.0% | 0.3475 |
| Student-t shocks, 5 degrees of freedom (fatter tails) | 86.9% | 0.3501 |
| Student-t shocks, 8 degrees of freedom | 88.1% | 0.3508 |
| Bootstrap of historical days | 88.1% | 0.3472 |

None moved coverage closer to 90% while also lowering the score by more than noise, so the plain normal-shock model stays and the rejected code was removed. The 336 forecasts come from 14 correlated stocks over roughly two years, so differences of a couple of points are within noise.

**Limits of this test.**

- The window may have been a calm market. Fat-tailed models matter most in a crash, so a longer test that includes 2020 and 2022 is still to do.
- Small portfolios give few observations, so their coverage figure is noisy.
- Expected return is the least reliable output. Expect the range to be more trustworthy than the single expected-price number.

## 6. Insights and dashboard

Code: `src/insights.py`, `src/charts.py`, `app.py`.

**Insights.** `build_insights()` turns the numbers into short sentences in three groups:

- **Portfolio health:** is it balanced (no sector above 40%, no holding above its limit), which sector dominates, which holdings contribute most.
- **Risk:** the risk level and the factors driving it, plus portfolio volatility and worst drawdown.
- **Forecast:** the expected move, the best-to-worst range, the confidence score, the least certain stock, and how often past ranges contained the real price.

**Dashboard.** Five KPI cards (portfolio value, risk score, diversification score, best and worst performer), sector and holding allocation charts, the 1-year value trend, the forecast panel and the insights. Share-of-portfolio charts are ranked horizontal bars rather than pies, with the concentration limit drawn as a line. Every chart has a "View as table" option. Prices and analysis are cached for 15 minutes, and the Refresh button clears the cache.

**Your own portfolio.** Entered or uploaded holdings live only in your browser session. They are not stored on a server or shared with other visitors.

## 7. Limitations

- **Placeholder data.** The bundled portfolios are AI-generated. Real portfolios may behave differently, especially larger ones.
- **Risk calibration.** Caps and level bands were tuned on five synthetic portfolios, and sector classification comes from Yahoo Finance; both change scores.
- **Forecast assumptions.** The model uses normal shocks, a blended drift and past correlations. A sudden regime change, such as a crash or a company-specific shock, is not captured well. Expected return is the weakest output.
- **No cost basis.** Best and worst performers are the stocks' 1-year moves, not your own profit or loss.
- **Data quality.** Yahoo Finance prices are free, unaudited and may be delayed or briefly unavailable. Very short price histories (under 250 days) are rejected for forecasting.
- **Not advice.** APIIP is an analysis tool. It does not account for taxes, fees, your goals or your risk tolerance.
