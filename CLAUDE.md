# APIIP – AI-Powered Investment Intelligence Platform (v1)

APIIP helps portfolio managers monitor investments, assess risk, forecast future performance and make informed decisions. This is **v1**: portfolio analysis, risk assessment, forecasting, and a dashboard.

**Data note:** the holdings and ticker metadata in `data/` are AI-generated placeholders. Prices come from Yahoo Finance (`yfinance`). The code must work unchanged with genuine asset data, so never hard-code tickers, portfolio IDs or sector mappings in logic, and keep data access behind `src/data_loader.py`.

## Commands

Run everything **from the project root**. Data paths are relative to the root and `src/` modules import each other by bare name (`from data_loader import ...`).

```bash
.venv\Scripts\activate              # Windows (source .venv/bin/activate elsewhere)
pip install pandas numpy yfinance   # no requirements.txt yet
python src/portfolio_analysis.py P002   # full portfolio report (portfolio ID optional, default P001)
python src/risk_analysis.py P002        # annualised volatility per ticker
```

There is no test suite, linter or build step yet. Python 3.10+ (developed on 3.12). Prices are downloaded on each run, so network access is required.

## Layout

```
app.py                     # dashboard entry point (placeholder)
data/                      # git-ignored input CSVs
  portfolios.csv           # Portfolio_ID, Portfolio_Name, Ticker, Shares
  ticker_metadata.csv      # Ticker, Company, Sector
  expected_assessment.csv  # Portfolio_ID, Expected_Risk_Level, Diversification, Rationale (reference for checking results)
src/
  data_loader.py           # CSV loading, yfinance prices, market value and allocation %
  portfolio_analysis.py    # holdings, sector allocation, diversification score
  risk_analysis.py         # daily returns, volatility
  forecasting.py           # placeholder
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
- The framework has not been chosen yet (Streamlit is the likely fit for a pandas/yfinance stack). Confirm with the user before adding a dependency.

## Current status

Implemented: total portfolio value, market value and allocation %, top holdings by allocation, best/worst performer by 1-year price change, sector allocation and summary, sector diversification score (normalised HHI over all sectors in `ticker_metadata.csv`, 0–100), concentration insights (`analyse_portfolio()` in `portfolio_analysis.py` returns everything as a dict for the dashboard), daily returns and annualised volatility (daily std × √252).

Not yet built: asset concentration score, drawdown, composite risk score, forecasting, dashboard, performance trend. Best/worst performer uses 1-year price change because `portfolios.csv` has no purchase price.

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
