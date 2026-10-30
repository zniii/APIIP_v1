# APIIP – AI-Powered Investment Intelligence Platform (v1)

APIIP helps portfolio managers monitor investments, assess risk, forecast future performance and make informed decisions. This is **v1**: portfolio analysis, risk assessment, forecasting, and a dashboard.

**Data note:** the holdings and ticker metadata in `data/` are AI-generated placeholders. Prices come from Yahoo Finance (`yfinance`). The code must work unchanged with genuine asset data, so never hard-code tickers, portfolio IDs or sector mappings in logic, and keep data access behind `src/data_loader.py`.

## Commands

Run everything **from the project root**. Data paths are relative to the root and `src/` modules import each other by bare name (`from data_loader import ...`).

```bash
.venv\Scripts\activate              # Windows (source .venv/bin/activate elsewhere)
pip install -r requirements.txt     # pandas, numpy, yfinance, streamlit, plotly
python src/portfolio_analysis.py P002   # full portfolio report (portfolio ID optional, default P001)
python src/risk_analysis.py P002        # risk score, factor breakdown, sector exposure
python src/forecasting.py P002          # 1-month forecast, confidence, backtest
streamlit run app.py                    # dashboard (opens in the browser)
```

There is no test suite, linter or build step yet. Python 3.10+ (developed on 3.12). Prices are downloaded on each run, so network access is required.

## Layout

```
app.py                     # Streamlit dashboard (layout only; run from the project root)
data/                      # git-ignored input CSVs
  portfolios.csv           # Portfolio_ID, Portfolio_Name, Ticker, Shares
  ticker_metadata.csv      # Ticker, Company, Sector
  expected_assessment.csv  # Portfolio_ID, Expected_Risk_Level, Diversification, Rationale (reference for checking results)
src/
  data_loader.py           # CSV loading, yfinance prices, market value and allocation %
  portfolio_analysis.py    # holdings, sector allocation, diversification score
  risk_analysis.py         # daily returns, volatility
  forecasting.py           # 21-day Monte Carlo forecast, confidence score, walk-forward backtest
  insights.py              # build_insights(): plain-language findings (pure, no Streamlit)
  charts.py                # Plotly figure builders and chart theme tokens (pure, no Streamlit)
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

Implemented: total portfolio value, market value and allocation %, top holdings by allocation, best/worst performer by 1-year price change, sector allocation and summary, sector diversification score (normalised HHI over all sectors in `ticker_metadata.csv`, 0–100), concentration insights (`analyse_portfolio()` in `portfolio_analysis.py` returns everything as a dict for the dashboard), daily returns and annualised volatility (daily std × √252), portfolio value history (`value_history`, for the performance trend chart), and the full risk assessment (`assess_risk()` in `risk_analysis.py`: four factors scored 0–100, weighted by `RISK_WEIGHTS`, plus risk level, portfolio volatility, max drawdown, sector exposure and diversification risk).

Risk caveats: `VOLATILITY_CAP`, `DRAWDOWN_CAP` and `RISK_LEVEL_BANDS` are tuned on five synthetic portfolios, so revisit them with real data. P001, P003, P004 and P005 match `expected_assessment.csv`; P002 scores Low (17.5) where the file says Medium, because it is the best-diversified portfolio and the file's labels rank it riskier than P003. Don't distort the weights to force a match; treat that label as the questionable one.

Forecasting is implemented in `forecasting.py` (`forecast_portfolio(portfolio_id)` returns per-stock and portfolio expected price, expected return %, best/worst case, confidence score, plus backtest results). Method: 21-trading-day horizon, 10,000 correlated scenarios from an EWMA covariance (lambda 0.97), normal shocks, drift blended 25% own history / 75% CAPM (beta vs `^GSPC`), best/worst case = 95th/5th percentile. It uses 5 years of history (`get_history_with_volume`), while risk analysis still uses 1 year. Confidence is a heuristic (range tightness, history length, volume stability), not a probability.

Forecast caveats: the walk-forward backtest checks how often the real price landed inside the 5-95 band (about 89% across all 14 tickers vs the 90% target; 336 forecasts, and the stocks are correlated, so differences of a couple of points are noise). Student-t shocks, bootstrap resampling and other EWMA lambdas were tried against that backtest and none was clearly better, so the plain normal-shock model stays; GARCH was not tried because the baseline gap was too small to justify a new dependency. Re-run that comparison on real portfolios or a longer history before adding model complexity. Expected return is the least reliable output.

The dashboard (`app.py`) is implemented: five KPI cards, sector and holding allocation bars, performance trend line, forecast panel with a range chart, and an insights section built by `insights.py`. It passes a headless `AppTest` run for P001-P005 and the server boots, but it has not been checked visually in a browser (no browser tool was available), so open it and check layout and dark mode by eye.

Follow-ups, in order (see the roadmap in the README): re-test forecasting fat-tail upgrades on 10 years of history; harden for larger real portfolios (shrinkage covariance above about 30 stocks, short-history tickers truncating everyone's data in `align_history`, re-tune risk caps and bands); the diversification score depends on how many sectors are in `ticker_metadata.csv`; confirm the P002 label. Best/worst performer uses 1-year price change because `portfolios.csv` has no purchase price.

## Conventions and gotchas

- **No import-time work:** importing any `src/` module must not load data or hit the network. Keep logic in functions that take data as parameters, and script behaviour under `main()` / `if __name__ == "__main__":`.
- **Portfolio ID is a parameter:** `get_portfolio(portfolio_id)` and the CLI scripts take it (default `P001` on the CLI only). Never hard-code it.
- **Concentration thresholds:** in `portfolio_analysis.py`, the holding limit is `max(MAX_HOLDING_PERCENTAGE, EQUAL_WEIGHT_MULTIPLE × 100 / N)` (25% cap, or 2× an even split for small portfolios; see `holding_limit()`), and `MAX_SECTOR_PERCENTAGE` is 40. Reuse `holding_limit()` for the asset concentration risk score so the two agree.
- **Fail loudly on missing prices:** `portfolio_with_prices` raises if a ticker has no price rather than skewing allocations.
- **yfinance shape:** a single ticker returns a Series, multiple tickers a DataFrame. `get_current_prices` handles both; keep new price code consistent with that.
- Every ticker in `portfolios.csv` needs a row in `ticker_metadata.csv`, otherwise it drops out of sector analysis (inner merge).
- Allocation is stored as a percentage (0–100), not a fraction. Convert explicitly when using HHI.
- Style: pandas-first, small pure functions with docstrings, snake_case. Match the existing files.
- `data/` and `.venv` are git-ignored. Don't commit data files or secrets.
