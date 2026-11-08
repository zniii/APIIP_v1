# APIIP – AI-Powered Investment Intelligence Platform (v1)

APIIP helps portfolio managers monitor investments, assess risk, forecast future performance and make informed decisions. This is **v1**: portfolio analysis, risk assessment, forecasting, and a dashboard.

**Data note:** the holdings and ticker metadata in `data/` are AI-generated placeholders. Prices come from Yahoo Finance (`yfinance`). The code must work unchanged with genuine asset data, so never hard-code tickers, portfolio IDs or sector mappings in logic, and keep data access behind `src/data_loader.py`.

## Commands

Run everything **from the project root**. Data paths are resolved from the project root (`DATA_DIR` in `data_loader.py`) and `src/` modules import each other by bare name (`from data_loader import ...`).

```bash
.venv\Scripts\activate              # Windows (source .venv/bin/activate elsewhere)
pip install -r requirements.txt     # pandas, numpy, yfinance, streamlit, plotly
python src/portfolio_analysis.py P002   # full portfolio report (portfolio ID optional, default P001)
python src/risk_analysis.py P002        # risk score, factor breakdown, sector exposure
python src/forecasting.py P002          # 1-month forecast, confidence, backtest
streamlit run app.py                    # dashboard (opens in the browser)
```

There is no test suite, linter or build step yet. Python 3.11+ (developed on 3.12; the pinned pandas 3 needs 3.11). Prices are downloaded on each run, so network access is required.

## Layout

```
app.py                     # Streamlit dashboard (layout only; run from the project root)
data/                      # input CSVs, git-ignored except data/sample/
  sample/portfolios.csv    # committed demo portfolios (placeholders); the dashboard's sample source
  portfolios.csv           # Portfolio_ID, Portfolio_Name, Ticker, Shares
  ticker_metadata.csv      # optional local override of Ticker, Company, Sector (normally fetched from Yahoo Finance)
  expected_assessment.csv  # Portfolio_ID, Expected_Risk_Level, Diversification, Rationale (reference for checking results)
src/
  data_loader.py           # CSV loading, yfinance prices, market value and allocation %
  portfolio_analysis.py    # holdings, sector allocation, diversification score
  risk_analysis.py         # daily returns, volatility
  forecasting.py           # 21-day Monte Carlo forecast, confidence score, walk-forward backtest
  insights.py              # build_insights(): plain-language findings (pure, no Streamlit)
  charts.py                # Plotly figure builders and chart theme tokens (pure, no Streamlit)
docs/
  METHODOLOGY.md           # public: how the risk score, forecast and backtest work, with formulas and test results
```

## V1 scope

### 1. Portfolio analysis: current portfolio health
- **Inputs:** user holdings, current stock prices.
- **Outputs:** total portfolio value, best performing holding, worst performing holding, portfolio allocation, sector allocation, diversification score.
- **Insights to answer:** Is the portfolio balanced? Which holdings contribute most? Which sectors dominate? Is it over-concentrated?

### 2. Risk assessment: risk exposure
Portfolio risk score is a weighted sum of four factors:

| Factor | Weight |
|---|---|
| Sector concentration | 40% |
| Volatility | 25% |
| Asset concentration | 20% |
| Historical drawdown | 15% |

- **Outputs:** portfolio risk score, volatility score, sector exposure risk, asset concentration risk, diversification risk.
- Keep the weights as named constants in one place, not scattered literals. Normalise each factor to the same 0–100 scale before weighting.
- Validate results against `data/expected_assessment.csv` (e.g. P001 should come out High risk, Low diversification).

### 3. Forecasting: future performance
- **Inputs:** historical prices, trading volume, market indicators.
- **Outputs:** expected future price, expected return (%), confidence score, best-case scenario, worst-case scenario.
- Forecasts are estimates, not advice. Surface the confidence score and scenario range wherever a forecast is shown.

### 4. Dashboard (`app.py`)
- **KPI cards:** portfolio value, portfolio risk score, diversification score, best performer, worst performer.
- **Charts:** sector allocation, portfolio (holding) allocation, portfolio performance trend.
- **Insights section:** plain-language answers to the portfolio-analysis questions above, plus risk and forecast takeaways.
- Built with Streamlit and Plotly. Keep `app.py` to layout; put findings in `insights.py` and figures in `charts.py`.
- Chart rules (from the dataviz skill): part-to-whole with more than 6 parts is ranked horizontal bars in one hue, not a donut; one axis; thin marks (bars about 22px); limits drawn as solid hairlines; values at the bar tip; every chart has a "View as table" twin; colors come from the theme tokens in `charts.py`, validated for both light and dark. Load the dataviz skill before changing charts.
- Portfolio data is cached for 15 minutes with `st.cache_data`; the Refresh button clears it.

## Current status

Implemented: total portfolio value, market value and allocation %, top holdings by allocation, best/worst performer by 1-year price change, sector allocation and summary, sector diversification score (normalised HHI over the fixed `SECTOR_UNIVERSE` of 11 Yahoo Finance sectors, 0–100), concentration insights (`analyse_holdings(holdings)` in `portfolio_analysis.py` returns everything as a dict for the dashboard; `analyse_portfolio(id)` is the CSV wrapper), automatic ticker metadata (`get_ticker_metadata()` in `data_loader.py`, sector and company from Yahoo Finance, "Other" when missing), validated user holdings (`clean_holdings()`), daily returns and annualised volatility (daily std × √252), portfolio value history (`value_history`, for the performance trend chart), and the full risk assessment (`assess_risk()` in `risk_analysis.py`: four factors scored 0–100, weighted by `RISK_WEIGHTS`, plus risk level, portfolio volatility, max drawdown, sector exposure and diversification risk).

Risk caveats: `VOLATILITY_CAP`, `DRAWDOWN_CAP` and `RISK_LEVEL_BANDS` are tuned on five synthetic portfolios, so revisit them with real data. P001, P003, P004 and P005 match `expected_assessment.csv`; P002 scores Low (17.5) where the file says Medium, because it is the best-diversified portfolio and the file's labels rank it riskier than P003. Don't distort the weights to force a match; treat that label as the questionable one.

Forecasting is implemented in `forecasting.py` (`forecast_holdings(holdings)` / `forecast_portfolio(portfolio_id)` return per-stock and portfolio expected price, expected return %, best/worst case, confidence score, plus backtest results). Method: 21-trading-day horizon, 10,000 correlated scenarios from an EWMA covariance (lambda 0.97), normal shocks, drift blended 25% own history / 75% CAPM (beta vs `^GSPC`), best/worst case = 95th/5th percentile. It uses 5 years of history (`get_history_with_volume`), while risk analysis still uses 1 year. Confidence is a heuristic (range tightness, history length, volume stability), not a probability.

Forecast caveats: the walk-forward backtest puts the real price inside the 5-95 band about 89% of the time against a 90% target. The upgrades tried (Student-t shocks, bootstrap, other EWMA lambdas) did not clearly help, so the plain normal-shock model stays. That test may have used a calm window, so a re-test on 10 years of history is still to do; test numbers are in `docs/METHODOLOGY.md`. Expected return is the least reliable output.

The dashboard (`app.py`) is implemented: five KPI cards, sector and holding allocation bars, performance trend line, forecast panel with a range chart, and an insights section built by `insights.py`. It passes a headless `AppTest` run for P001-P005 and the server boots, but it has not been checked visually in a browser (no browser tool was available), so open it and check layout and dark mode by eye.

## Methodology and project notes

`docs/METHODOLOGY.md` is the public description of the methods, constants and test results: keep it in step with the code, and read it before changing a method, a threshold or a chart. The maintainer may also keep private, git-ignored notes (`docs/ROADMAP.md`, `docs/decisions.md`) loaded through `CLAUDE.local.md`. If they exist, read `decisions.md` before changing a method and update both when a step finishes or a choice is made; they are not part of the repository.

## Working agreements

- Make changes locally. The user commits and pushes; don't commit or push unless asked in that session.
- When the user asks how a method works or whether something is possible, explain it in plain language with a small example and the trade-offs before building anything. Don't assume approval.
- Keep a model upgrade only if a backtest shows a benefit; otherwise remove its code instead of leaving it disabled.

## Conventions and gotchas

- **No import-time work:** importing any `src/` module must not load data or hit the network. Keep logic in functions that take data as parameters, and script behaviour under `main()` / `if __name__ == "__main__":`.
- **Portfolio ID is a parameter:** `get_portfolio(portfolio_id)` and the CLI scripts take it (default `P001` on the CLI only). Never hard-code it. The dashboard analyses a holdings DataFrame (`Ticker`, `Shares`) so visitors can enter their own; those live only in `st.session_state`.
- **Concentration thresholds:** in `portfolio_analysis.py`, the holding limit is `max(MAX_HOLDING_PERCENTAGE, EQUAL_WEIGHT_MULTIPLE × 100 / N)` (25% cap, or 2× an even split for small portfolios; see `holding_limit()`), and `MAX_SECTOR_PERCENTAGE` is 40. Reuse `holding_limit()` for the asset concentration risk score so the two agree.
- **Fail loudly on missing prices:** `portfolio_with_prices` raises if a ticker has no price rather than skewing allocations.
- **yfinance shape:** a single ticker returns a Series, multiple tickers a DataFrame. `get_current_prices` handles both; keep new price code consistent with that.
- Sector metadata is fetched from Yahoo Finance for any ticker; rows in a local `data/ticker_metadata.csv` override it. Sectors outside `SECTOR_UNIVERSE` (an override file's custom labels, or "Other") enlarge the universe count in `count_sectors()`, so keep override labels to the Yahoo names.
- Allocation is stored as a percentage (0–100), not a fraction. Convert explicitly when using HHI.
- Style: pandas-first, small pure functions with docstrings, snake_case. Match the existing files.
- `data/*` (except `data/sample/`) and `.venv` are git-ignored. Don't commit private data files or secrets. A fresh clone runs the dashboard on `data/sample/portfolios.csv`; the CLI scripts still read `data/portfolios.csv`.
- Deployed on Streamlit Community Cloud (main file `app.py`, Python 3.12). Yahoo Finance may rate-limit its shared IPs, so keep the caches.
