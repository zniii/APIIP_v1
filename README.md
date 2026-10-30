# APIIP – Portfolio Analysis

A Python toolkit for analysing stock portfolios. It loads holdings from CSV, fetches live and historical prices from Yahoo Finance, and works out allocation, sector diversification and volatility.

> **Status:** early development. Portfolio and risk analysis work; `src/forecasting.py` and `app.py` are empty placeholders for now.

## Features

- **Portfolio valuation**: total portfolio value, plus current market value and allocation percentage for each holding
- **Holdings summary**: the top holdings by allocation, and the best and worst performers by 1-year price change
- **Sector allocation**: total allocation per sector, using ticker metadata
- **Diversification score**: a 0–100 score based on a normalised Herfindahl-Hirschman Index (HHI) across sectors, measured against every sector in `ticker_metadata.csv`. 100 means allocation is spread evenly across all of them; 0 means it is all in one.
- **Concentration check**: flags a portfolio as over-concentrated when one sector is above 40%, or one holding is above its limit. The holding limit is 25%, or twice an even split for portfolios with fewer than 8 holdings (40% for 5 holdings).
- **Risk analysis**: daily returns and annualised volatility (daily std × √252) for each ticker, over one year of price history

## Project structure

```
APIIP_v1/
├── app.py                     # Entry point (placeholder)
├── data/                      # Input CSVs (git-ignored, see below)
│   ├── portfolios.csv
│   ├── ticker_metadata.csv
│   └── expected_assessment.csv
└── src/
    ├── data_loader.py         # Loads CSVs and fetches prices from yfinance
    ├── portfolio_analysis.py  # Holdings, performers, sector allocation, diversification score, concentration check
    ├── risk_analysis.py       # Daily returns and annualised volatility
    └── forecasting.py         # Placeholder
```

## Setup

You need Python 3.10 or newer. The project is developed on 3.12.

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install pandas numpy yfinance
```

You also need an internet connection, because prices are downloaded from Yahoo Finance each time the scripts run.

## Data files

`data/` is listed in `.gitignore`, so a fresh clone won't include it. Create these files yourself:

**`data/portfolios.csv`**: the holdings in each portfolio

```csv
Portfolio_ID,Portfolio_Name,Ticker,Shares
P001,Aggressive Growth,NVDA,25
P001,Aggressive Growth,TSLA,20
P001,Aggressive Growth,MSFT,30
```

**`data/ticker_metadata.csv`**: the company name and sector for each ticker

```csv
Ticker,Company,Sector
NVDA,NVIDIA,Technology
TSLA,Tesla,Automotive
MSFT,Microsoft,Technology
```

**`data/expected_assessment.csv`**: the expected risk and diversification for each portfolio, kept as a reference to check results against

```csv
Portfolio_ID,Expected_Risk_Level,Diversification,Rationale
P001,High,Low,High growth stocks and heavy technology exposure
```

Every ticker in `portfolios.csv` needs a row in `ticker_metadata.csv`. Otherwise it is left out of the sector analysis.

## Usage

Run the scripts **from the project root**. The data paths are relative to the root, and the modules import each other by bare name (`from data_loader import ...`):

```bash
# Portfolio report: total value, top holdings, best/worst performer,
# sector allocation, diversification score and concentration check
python src/portfolio_analysis.py

# Same report for another portfolio (default is P001)
python src/portfolio_analysis.py P002

# Annualised volatility for each ticker
python src/risk_analysis.py P002
```

Importing the modules does not load data or use the network, so the functions can be reused from other code. For example, `analyse_portfolio(portfolio_id)` in [src/portfolio_analysis.py](src/portfolio_analysis.py) returns every result as a dict. Prices are downloaded when you call the functions or run the scripts, and a missing price raises an error rather than silently skewing allocations.

## Roadmap

- [ ] Price forecasting (`src/forecasting.py`)
- [ ] App or dashboard entry point (`app.py`)
- [ ] Asset concentration, historical drawdown and the weighted portfolio risk score
- [ ] Portfolio-level volatility and risk-level classification, compared against `expected_assessment.csv`
- [ ] `requirements.txt`
