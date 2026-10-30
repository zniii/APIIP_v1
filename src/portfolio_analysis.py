import argparse
import warnings
import pandas as pd
from data_loader import (
    get_portfolio,
    ticker_prices,
    get_current_prices,
    get_historical_prices,
    portfolio_with_prices,
    total_portfolio_value,
    load_sector_allocation,
)

# A portfolio is flagged as concentrated above either limit (percent of portfolio value).
# The holding limit is MAX_HOLDING_PERCENTAGE, or EQUAL_WEIGHT_MULTIPLE times an even split
# if that is higher, so small portfolios are not flagged for ordinary drift.
MAX_HOLDING_PERCENTAGE = 25.0
EQUAL_WEIGHT_MULTIPLE = 2.0
MAX_SECTOR_PERCENTAGE = 40.0


def top_holdings(data, n=3):
    """
    Holdings contributing most to the portfolio, by allocation
    """
    ranked = data.sort_values("Allocation_Percentage", ascending=False)

    return ranked[["Ticker", "Market_Value", "Allocation_Percentage"]].head(n)

def holding_returns(historical_price):
    """
    Price change over the history window, in percent, per ticker
    """
    first = historical_price.bfill().iloc[0]
    last = historical_price.ffill().iloc[-1]

    returns = (last / first - 1) * 100

    return pd.DataFrame({
        "Ticker": returns.index,
        "Return_Percentage": returns.values
    })

def portfolio_value_history(historical_price, portfolio):
    """
    Daily portfolio value over the history window, at the current share counts
    """
    shares = portfolio.set_index("Ticker")["Shares"]
    prices = historical_price.ffill().bfill()

    return (prices[shares.index] * shares).sum(axis=1)

def best_and_worst_performers(returns):
    best = returns.loc[[returns["Return_Percentage"].idxmax()]].assign(Performance="Best")
    worst = returns.loc[[returns["Return_Percentage"].idxmin()]].assign(Performance="Worst")

    return pd.concat([best, worst], ignore_index=True)

def sector_allocation(data, metadata):
    missing = sorted(set(data["Ticker"]) - set(metadata["Ticker"]))

    if missing:
        warnings.warn(
            f"No sector in ticker metadata for: {', '.join(missing)}. "
            "They are left out of the sector analysis."
        )

    sector_data = metadata.merge(
        data,
        on="Ticker",
        how="inner"
    )

    return sector_data

def sector_allocation_summary(data):
    sector_summary = data.groupby("Sector")[["Allocation_Percentage"]].sum()

    return sector_summary.sort_values("Allocation_Percentage", ascending=False)

def sector_diversification_score(data, total_sectors):
    """
    0-100 score from the normalised HHI across sectors.
    total_sectors is every sector the portfolio could hold, not just the held ones,
    so holding few sectors scores low even when they are evenly weighted.
    """
    hhi = ((data["Allocation_Percentage"] / 100) ** 2).sum()

    if total_sectors <= 1:
        return 0.0

    minimum_hhi = 1/total_sectors
    normalized_hhi = (hhi - minimum_hhi) / (1-minimum_hhi)
    diversification_score = (1 - normalized_hhi) * 100

    return diversification_score

def holding_limit(num_holdings):
    """
    Largest share (percent) one holding can have before the portfolio counts as concentrated
    """
    return max(MAX_HOLDING_PERCENTAGE, EQUAL_WEIGHT_MULTIPLE * 100 / num_holdings)

def portfolio_insights(top, sector_summary, num_holdings):
    """
    Plain answers to: is it balanced, what contributes most, what dominates
    """
    largest_holding = top.iloc[0]
    dominant_sector = sector_summary["Allocation_Percentage"].idxmax()
    dominant_share = sector_summary["Allocation_Percentage"].max()
    limit = holding_limit(num_holdings)

    concentrated = (
        largest_holding["Allocation_Percentage"] > limit
        or dominant_share > MAX_SECTOR_PERCENTAGE
    )

    return {
        "largest_holding": largest_holding["Ticker"],
        "largest_holding_percentage": largest_holding["Allocation_Percentage"],
        "holding_limit_percentage": limit,
        "dominant_sector": dominant_sector,
        "dominant_sector_percentage": dominant_share,
        "is_concentrated": bool(concentrated),
    }

def analyse_portfolio(portfolio_id):
    portfolio = get_portfolio(portfolio_id)
    tickers = ticker_prices(portfolio)

    portfolio_prices = portfolio_with_prices(portfolio, get_current_prices(tickers))
    historical_prices = get_historical_prices(tickers)
    returns = holding_returns(historical_prices)

    metadata = load_sector_allocation()
    sector = sector_allocation(portfolio_prices, metadata)
    sector_summary = sector_allocation_summary(sector)

    top = top_holdings(portfolio_prices)

    return {
        "total_value": total_portfolio_value(portfolio_prices),
        "allocation": portfolio_prices,
        "top_holdings": top,
        "performers": best_and_worst_performers(returns),
        "historical_prices": historical_prices,
        "value_history": portfolio_value_history(historical_prices, portfolio),
        "sector_summary": sector_summary,
        "diversification_score": sector_diversification_score(
            sector_summary, metadata["Sector"].nunique()
        ),
        "insights": portfolio_insights(top, sector_summary, len(portfolio_prices)),
    }


def main():
    parser = argparse.ArgumentParser(description="Portfolio analysis")
    parser.add_argument("portfolio_id", nargs="?", default="P001")
    args = parser.parse_args()

    result = analyse_portfolio(args.portfolio_id)
    insights = result["insights"]

    print(f"Portfolio {args.portfolio_id}")
    print(f"Total value: {result['total_value']:,.2f}")
    print("\nTop holdings:")
    print(result["top_holdings"].to_string(index=False))
    print("\nBest / worst performer (1y price change):")
    print(result["performers"].to_string(index=False))
    print("\nSector allocation:")
    print(result["sector_summary"])
    print(f"\nDiversification score: {result['diversification_score']:.1f}/100")
    print(
        f"Largest holding: {insights['largest_holding']} "
        f"({insights['largest_holding_percentage']:.1f}%), "
        f"dominant sector: {insights['dominant_sector']} "
        f"({insights['dominant_sector_percentage']:.1f}%)"
    )
    print(
        "Over-concentrated "
        f"(holding > {insights['holding_limit_percentage']:.0f}% or sector > {MAX_SECTOR_PERCENTAGE:.0f}%): "
        f"{'yes' if insights['is_concentrated'] else 'no'}"
    )


if __name__ == "__main__":
    main()
