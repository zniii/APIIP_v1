import pandas as pd
import yfinance as yf

def get_portfolio(file_path="data/portfolios.csv"):
    """
    Load Portfolio
    """
    portfolio = pd.read_csv(file_path)

    portfolio = portfolio[portfolio["Portfolio_ID"] == "P001"]

    return portfolio

if __name__ == "__main__":
    portfolio = get_portfolio()

def get_current_prices(tickers):
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


def ticker_prices():
    tickers = get_portfolio()
    tickers_list = tickers["Ticker"].tolist()

    return get_current_prices(tickers_list)

def portfolio_with_prices():
    portfolio_prices = []
    portfolio_prices = get_portfolio().merge(
        ticker_prices(),
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


def load_sector_allocation(file_path = "data/ticker_metadata.csv"):
    sec_allocation = pd.read_csv(file_path)

    return sec_allocation

