from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import yfinance as yf

# Resolved from the project root so the app and scripts work from any working directory
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PORTFOLIOS_FILE = DATA_DIR / "portfolios.csv"
SAMPLE_PORTFOLIOS_FILE = DATA_DIR / "sample" / "portfolios.csv"
TICKER_METADATA_FILE = DATA_DIR / "ticker_metadata.csv"

MAX_HOLDINGS = 30
UNKNOWN_SECTOR = "Other"

# Ticker -> (company, sector). Only successful lookups are kept, so a rate-limited
# request is retried next time instead of being remembered as "Other".
_metadata_cache = {}

def get_portfolio(portfolio_id, file_path=PORTFOLIOS_FILE):
    """
    Load the holdings of one portfolio
    """
    portfolio = pd.read_csv(file_path)

    portfolio = portfolio[portfolio["Portfolio_ID"] == portfolio_id]

    if portfolio.empty:
        raise ValueError(f"No holdings found for portfolio '{portfolio_id}'")

    return portfolio

def get_current_prices(tickers):
    """
    Load Current Prices from Tickers
    """
    data = yf.download(
            tickers,
            period="1d",
            progress=False,
            auto_adjust=True
        )

    if data.empty:
        names = tickers if isinstance(tickers, str) else ", ".join(tickers)
        raise ValueError(f"No price data found for: {names}")

    close = data["Close"]

    # A single ticker can come back as a Series, depending on the yfinance version
    if isinstance(close, pd.Series):
        close = close.to_frame(name=tickers)

    prices = close.iloc[-1]

    return pd.DataFrame({
        "Ticker":prices.index,
        "Current_Price":prices.values
    })

def get_historical_prices(tickers, period="1y"):
    """
    Load historical closing prices from ticker (1 year by default)
    """
    hist_data = yf.download(
       tickers,
       period=period,
       auto_adjust=True,
       progress=False
    )

    price_reset = hist_data["Close"]

    return price_reset

def get_history_with_volume(tickers, period="5y"):
    """
    Load closing prices and trading volume from one download
    """
    hist_data = yf.download(
       tickers,
       period=period,
       auto_adjust=True,
       progress=False
    )

    close = hist_data["Close"]
    volume = hist_data["Volume"]

    # A single ticker can come back as a Series, depending on the yfinance version
    if isinstance(close, pd.Series):
        close = close.to_frame(name=tickers)
        volume = volume.to_frame(name=tickers)

    return close, volume

def get_market_prices(period="5y", symbol="^GSPC"):
    """
    Load the closing prices of a market index (S&P 500 by default)
    """
    market = yf.download(
       symbol,
       period=period,
       auto_adjust=True,
       progress=False
    )["Close"]

    if isinstance(market, pd.DataFrame):
        market = market.iloc[:, 0]

    return market.rename("Market")

#Ticker prices
def ticker_prices(portfolio):
    tickers_list = portfolio["Ticker"].tolist()
    return tickers_list

#Merging ticker prices with the portfolio data
def portfolio_with_prices(portfolio, current_prices):
    portfolio_prices = portfolio.merge(
        current_prices,
        on="Ticker",
        how="left"
    )

    missing = portfolio_prices.loc[
        portfolio_prices["Current_Price"].isna(), "Ticker"
    ].tolist()

    if missing:
        raise ValueError(f"No current price found for: {', '.join(missing)}")

    portfolio_prices["Market_Value"] = (
        portfolio_prices["Shares"] * portfolio_prices["Current_Price"]
    )

    total_value = total_portfolio_value(portfolio_prices)

    portfolio_prices["Allocation_Percentage"] = (
        (portfolio_prices["Market_Value"] / total_value) * 100
    )
    return portfolio_prices

def total_portfolio_value(portfolio_prices):
    return portfolio_prices["Market_Value"].sum()


def clean_holdings(holdings):
    """
    Validate user-entered holdings (Ticker, Shares) and return a tidy copy.
    Tickers are upper-cased, duplicates are merged by summing shares.
    """
    if not {"Ticker", "Shares"} <= set(holdings.columns):
        raise ValueError("Holdings need the columns Ticker and Shares")

    holdings = holdings[["Ticker", "Shares"]].copy()
    holdings["Ticker"] = holdings["Ticker"].astype("string").str.strip().str.upper()
    holdings["Shares"] = pd.to_numeric(holdings["Shares"], errors="coerce")
    holdings = holdings.dropna(subset=["Ticker", "Shares"], how="all")
    holdings = holdings[holdings["Ticker"].fillna("") != ""]

    if holdings["Shares"].isna().any():
        raise ValueError("Every ticker needs a numeric number of shares")
    if (holdings["Shares"] <= 0).any():
        raise ValueError("Shares must be greater than zero")

    holdings = holdings.groupby("Ticker", as_index=False, sort=False)["Shares"].sum()

    if holdings.empty:
        raise ValueError("Add at least one holding")
    if len(holdings) > MAX_HOLDINGS:
        raise ValueError(f"At most {MAX_HOLDINGS} holdings are supported")

    holdings["Ticker"] = holdings["Ticker"].astype(str)

    return holdings

def _fetch_ticker_metadata(ticker):
    """
    Company name and sector from Yahoo Finance. Returns None if the lookup fails.
    """
    try:
        info = yf.Ticker(ticker).info
    except Exception:
        return None

    company = info.get("longName") or info.get("shortName") or ticker
    sector = info.get("sector") or UNKNOWN_SECTOR

    return company, sector

def get_ticker_metadata(tickers):
    """
    Ticker, Company and Sector for each ticker, looked up from Yahoo Finance.
    Tickers without a sector (funds, failed lookups) are labelled "Other".
    """
    tickers = list(dict.fromkeys(tickers))
    missing = [ticker for ticker in tickers if ticker not in _metadata_cache]

    if missing:
        with ThreadPoolExecutor(max_workers=8) as pool:
            for ticker, result in zip(missing, pool.map(_fetch_ticker_metadata, missing)):
                if result is not None:
                    _metadata_cache[ticker] = result

    rows = [
        (ticker, *_metadata_cache.get(ticker, (ticker, UNKNOWN_SECTOR)))
        for ticker in tickers
    ]

    return pd.DataFrame(rows, columns=["Ticker", "Company", "Sector"])

def load_sector_allocation(tickers, file_path=TICKER_METADATA_FILE):
    """
    Ticker metadata for the given tickers. Rows in the optional local file
    data/ticker_metadata.csv override what Yahoo Finance returns.
    """
    try:
        overrides = pd.read_csv(file_path)
    except FileNotFoundError:
        return get_ticker_metadata(tickers)

    unknown = [ticker for ticker in tickers if ticker not in set(overrides["Ticker"])]
    fetched = get_ticker_metadata(unknown) if unknown else overrides.iloc[0:0]

    return pd.concat([overrides, fetched], ignore_index=True)
