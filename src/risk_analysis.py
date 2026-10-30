import argparse
import pandas as pd
import numpy as np
from data_loader import get_portfolio, ticker_prices, get_historical_prices

def daily_returns(historical_price):
    data = historical_price.copy()

    price_columns = data.columns

    data[price_columns] = data[price_columns].pct_change()

    data = data.dropna()

    return data

def daily_volatility(daily_returns):
    stock_returns = daily_returns

    daily_volatility = stock_returns.std()

    return daily_volatility

def calculate_stock_volatility(daily_volatility):
    annualise_volatility = daily_volatility * np.sqrt(252)
    return annualise_volatility


def main():
    parser = argparse.ArgumentParser(description="Annualised volatility per ticker")
    parser.add_argument("portfolio_id", nargs="?", default="P001")
    args = parser.parse_args()

    portfolio = get_portfolio(args.portfolio_id)
    historical_price_data = get_historical_prices(ticker_prices(portfolio))

    daily_return = daily_returns(historical_price_data)
    volatility = daily_volatility(daily_return)
    annualise_volatility = calculate_stock_volatility(volatility)

    print(annualise_volatility)


if __name__ == "__main__":
    main()
