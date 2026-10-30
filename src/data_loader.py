import pandas as pd
import yfinance as yf

def get_portfolio(portfolio_id, file_path="data/portfolios.csv"):
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


#Loading sector allocation
def load_sector_allocation(file_path = "data/ticker_metadata.csv"):
    sec_allocation = pd.read_csv(file_path)

    return sec_allocation
