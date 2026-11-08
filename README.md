# APIIP: AI-Powered Investment Intelligence Platform

Know how healthy, how risky and how likely to move a stock portfolio is, in one dashboard. Enter your holdings and APIIP shows what you own, where the risk sits and what the next month might look like, in plain language.

> **Not investment advice.** Forecasts are estimates from past price behaviour. The bundled sample portfolios are AI-generated placeholders, and prices come from Yahoo Finance and may be delayed.

## What it does

**Portfolio health.** Total value, allocation by holding and by sector, best and worst performer over the past year, and a 0-100 diversification score. It answers: is the portfolio balanced, which holdings and sectors dominate, is it over-concentrated?

**Risk assessment.** A 0-100 risk score with a level (Low, Medium, High, Very High), built from four factors:

| Factor | Weight |
|---|---|
| Sector concentration | 40% |
| Volatility | 25% |
| Asset concentration | 20% |
| Historical drawdown | 15% |

**Forecast.** A one-month (21 trading day) outlook for each stock and the whole portfolio: expected value, best case, worst case and a confidence score. The range is shown alongside every forecast, because a range is more honest than a single number.

**Insights.** Plain-language findings for all of the above, so the numbers come with an explanation.

**Your own portfolio.** Switch to *My portfolio* to type in tickers and share counts, or upload a CSV, and get the same analysis. Your holdings stay in your browser session and are not stored or shared. Sector and company names are looked up automatically.

## How it works

- **Diversification score:** a normalised Herfindahl-Hirschman Index (HHI) across 11 sectors, so spreading money evenly across sectors scores high and putting it all in one scores zero.
- **Risk score:** each of the four factors is scaled to 0-100 and combined with the weights above. Volatility is measured on the portfolio as a whole, from how the holdings move together, so diversification between stocks counts.
- **Forecast:** a correlated Monte Carlo simulation. It runs 10,000 possible months using five years of price history, a covariance estimate that gives recent days more weight, and an expected return blended from each stock's own past and the market (CAPM). The best and worst cases are the 95th and 5th percentiles.
- **Validation:** the forecast is backtested by forecasting from past dates and checking where the real price landed. In that test the real price fell inside the best-to-worst range about 89% of the time against a 90% target. Fat-tailed and bootstrap variants were tried and did not improve on the simple model, so they were not kept.

The full method, formulas, worked examples and test results are in [docs/METHODOLOGY.md](docs/METHODOLOGY.md).

## Try it

You need Python 3.11 or newer and an internet connection (prices are downloaded from Yahoo Finance).

```bash
git clone https://github.com/zniii/APIIP_v1.git
cd APIIP_v1
python -m venv .venv
.venv\Scripts\activate          # Windows (source .venv/bin/activate on macOS or Linux)
pip install -r requirements.txt
streamlit run app.py
```

The dashboard opens on the sample portfolios in `data/sample/portfolios.csv`. Pick one, or choose *My portfolio* to analyse your own.

### Using your own data

Upload or type holdings with two columns:

```csv
Ticker,Shares
AAPL,10
JPM,5
XOM,8
```

Use Yahoo Finance ticker symbols, with up to 30 holdings. Duplicate tickers are merged.

### Command line

The analysis also runs without the dashboard. Copy a portfolio file to `data/portfolios.csv` (columns `Portfolio_ID,Portfolio_Name,Ticker,Shares`, as in the sample file), then run from the project root:

```bash
python src/portfolio_analysis.py P002   # holdings, sectors, diversification
python src/risk_analysis.py P002        # risk score and factor breakdown
python src/forecasting.py P002          # forecast and backtest
```

## Project structure

```
app.py                     Streamlit dashboard (layout only)
src/
  data_loader.py           prices, ticker metadata and holdings validation (Yahoo Finance)
  portfolio_analysis.py    allocation, sectors, diversification score
  risk_analysis.py         volatility, drawdown, weighted risk score
  forecasting.py           Monte Carlo forecast, confidence score, backtest
  insights.py              plain-language findings
  charts.py                Plotly charts
data/sample/               demo portfolios
docs/METHODOLOGY.md        how the models work and how they were tested
```

## Limitations

- Risk thresholds were tuned on five synthetic portfolios; real portfolios may need recalibration.
- The forecast assumes normally distributed price moves, so it can understate crash risk. Expected return is its least reliable output; trust the range more.
- "Best" and "worst" performers are each stock's 1-year price change, not your own gain or loss, because holdings have no purchase price.

More detail is in the [methodology](docs/METHODOLOGY.md#7-limitations).

## Built with

Python, pandas, NumPy, yfinance, Streamlit and Plotly.
