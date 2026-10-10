import pandas as pd
import yfinance as yf

def get_portfolio(file_path="data/portfolios.csv"):
    """
    Load Portfolio
    """
    portfolio = pd.read_csv(file_path)

    portfolio = portfolio[portfolio["Portfolio_ID"] == "P001"]

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

    if isinstance(tickers, str):
        price = data["Close"].iloc[-1]
        return pd.DataFrame({
            "Ticker": [tickers],
            "Current_Price":[price]
        })
    else:
        prices = data["Close"].iloc[-1]
        return pd.DataFrame({
            "Ticker":prices.index,
            "Current_Price":prices.values
        })

def get_historical_prices(tickers):
    """
    Load 1 year data from ticker
    """
    hist_data = yf.download(
       tickers,
       period="1y",
       auto_adjust=True,
       progress=False
    )

    price_reset = hist_data["Close"]

    return price_reset

#Ticker prices
def ticker_prices():
    tickers = portfolio_data
    tickers_list = tickers["Ticker"].tolist()
    return tickers_list

#Merging ticker prices with the portfolio data
def portfolio_with_prices(data):
    portfolio_prices = data.merge(
        current_price_data,
        on="Ticker",
        how="left"
    )

    portfolio_prices["Market_Value"] = (
        portfolio_prices["Shares"] * portfolio_prices["Current_Price"]
    )

    total_value = portfolio_prices["Market_Value"].sum()

    portfolio_prices["Allocation_Percentage"] = (
        (portfolio_prices["Market_Value"] / total_value) * 100
    )
    return portfolio_prices


#Loading sector allocation
def load_sector_allocation(file_path = "data/ticker_metadata.csv"):
    sec_allocation = pd.read_csv(file_path)

    return sec_allocation


if __name__ == "__main__":
    portfolio = get_portfolio()


portfolio_data = get_portfolio()
ticker_data = ticker_prices()
current_price_data = get_current_prices(ticker_data)
historical_price_data = get_historical_prices(ticker_data)
portfolio_w_prices = portfolio_with_prices(portfolio_data)
load_sec_allocation = load_sector_allocation()