# APIIP – AI-Powered Investment Intelligence Platform

APIIP helps portfolio managers monitor investments, assess risk and forecast future performance. It loads holdings, fetches prices and sector data from Yahoo Finance, and shows the results in a Streamlit dashboard.

> The sample holdings in `data/sample/` are AI-generated placeholders. Forecasts are estimates, not investment advice.

## Features

- **Portfolio analysis**: total value, allocation per holding and sector, best and worst performer (1-year price change), diversification score and a concentration check. The score is a 0–100 normalised Herfindahl-Hirschman Index measured against a fixed list of 11 sectors (`SECTOR_UNIVERSE`).
- **Risk assessment**: a 0–100 risk score and level (Low / Medium / High / Very High) from four factors: sector concentration (40%), volatility (25%), asset concentration (20%) and historical drawdown (15%).
- **Forecasting**: a 21-trading-day correlated Monte Carlo forecast with expected price and return, best and worst case, a heuristic confidence score and a walk-forward backtest.
- **Dashboard**: KPI cards, allocation charts, performance trend, forecast panel and plain-language insights. Visitors can pick a sample portfolio or enter, upload and download their own (kept only in their browser session).
- **Automatic ticker metadata**: company name and sector are fetched from Yahoo Finance, so no metadata file is needed.

## Project structure

```
APIIP_v1/
├── app.py                     # Streamlit dashboard (layout only)
├── data/
│   ├── sample/portfolios.csv  # committed demo portfolios
│   ├── portfolios.csv         # optional private portfolios for the CLI (git-ignored)
│   ├── ticker_metadata.csv    # optional override of fetched sector data (git-ignored)
│   └── expected_assessment.csv  # optional reference results (git-ignored)
├── src/
│   ├── data_loader.py         # CSV loading, yfinance prices, ticker metadata, holdings validation
│   ├── portfolio_analysis.py  # holdings, sector allocation, diversification score
│   ├── risk_analysis.py       # volatility, drawdown, weighted risk score
│   ├── forecasting.py         # Monte Carlo forecast, confidence, backtest
│   ├── insights.py            # plain-language findings
│   └── charts.py              # Plotly figure builders
└── docs/                      # ROADMAP.md, decisions.md
```

## Setup

You need Python 3.11 or newer (developed on 3.12) and an internet connection, because prices are downloaded from Yahoo Finance.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (source .venv/bin/activate elsewhere)
pip install -r requirements.txt
```

## Run the dashboard

```bash
streamlit run app.py
```

It opens on the sample portfolios. Switch to **My portfolio** to enter tickers and share counts (Yahoo Finance symbols, up to 30 holdings) or upload a CSV with `Ticker,Shares` columns.

## Command-line reports

Run from the project root. These read `data/portfolios.csv` (same columns as the sample file: `Portfolio_ID,Portfolio_Name,Ticker,Shares`), which is git-ignored, so copy the sample file there to try them:

```bash
python src/portfolio_analysis.py P002   # holdings, sectors, diversification
python src/risk_analysis.py P002        # risk score and factor breakdown
python src/forecasting.py P002          # forecast and backtest
```

Importing the modules does not load data or use the network. `analyse_holdings(df)` and `forecast_holdings(df)` take a DataFrame with `Ticker` and `Shares` columns; `analyse_portfolio(id)` and `forecast_portfolio(id)` read a portfolio from the CSV.

An optional `data/ticker_metadata.csv` (`Ticker,Company,Sector`) overrides the fetched sector for the tickers it lists. Use Yahoo's sector names, otherwise they count as extra sectors in the diversification score.

## Deploy on Streamlit Community Cloud

1. Push the repo to GitHub.
2. At share.streamlit.io choose **Create app**: repository `zniii/APIIP_v1`, branch `main`, main file `app.py`.
3. Under **Advanced settings** pick Python 3.12.

Yahoo Finance may rate-limit shared cloud IPs; prices are cached for 15 minutes and sector lookups for the life of the server process.

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md) for next steps and [docs/decisions.md](docs/decisions.md) for why choices were made.
