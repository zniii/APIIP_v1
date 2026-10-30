import argparse
import pandas as pd
import numpy as np
from portfolio_analysis import (
    analyse_portfolio,
    holding_limit,
    MAX_SECTOR_PERCENTAGE,
)

# Weight of each factor in the portfolio risk score. Must add up to 1.
RISK_WEIGHTS = {
    "sector_concentration": 0.40,
    "volatility": 0.25,
    "asset_concentration": 0.20,
    "drawdown": 0.15,
}

# Portfolio volatility and drawdown at or above these (as fractions) score 100.
VOLATILITY_CAP = 0.50
DRAWDOWN_CAP = 0.40

# (upper bound of the score, level). Anything above the last bound is Very High.
# Tuned on the five synthetic portfolios in data/, so revisit with real portfolios.
RISK_LEVEL_BANDS = [
    (30, "Low"),
    (45, "Medium"),
    (60, "High"),
]


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

def portfolio_volatility(returns, weights):
    """
    Annualised volatility of the whole portfolio (as a fraction), from the
    covariance of daily returns, so diversification between stocks is counted
    """
    w = weights.reindex(returns.columns).to_numpy()
    covariance = returns.cov().to_numpy() * 252

    return float(np.sqrt(w @ covariance @ w))

def max_drawdown(value_history):
    """
    Largest peak-to-trough fall in portfolio value, as a positive fraction
    """
    drawdown = value_history / value_history.cummax() - 1

    return float(-drawdown.min())

def scale_to_100(value, cap):
    return min(max(value / cap, 0.0), 1.0) * 100

def asset_concentration_risk(allocation):
    """
    0 when every holding has the same share, 100 when one holding is everything
    """
    num_holdings = len(allocation)

    if num_holdings == 1:
        return 100.0

    even_split = 100 / num_holdings
    largest = allocation["Allocation_Percentage"].max()

    return (largest - even_split) / (100 - even_split) * 100

def sector_exposure_risk(sector_summary):
    exposure = sector_summary.copy()
    exposure["Exceeds_Limit"] = exposure["Allocation_Percentage"] > MAX_SECTOR_PERCENTAGE

    return exposure

def risk_level(score):
    for upper_bound, level in RISK_LEVEL_BANDS:
        if score <= upper_bound:
            return level

    return "Very High"

def expected_assessment(portfolio_id, file_path="data/expected_assessment.csv"):
    """
    The reference risk level for a portfolio, or None if there is no reference
    """
    try:
        expected = pd.read_csv(file_path)
    except FileNotFoundError:
        return None

    row = expected[expected["Portfolio_ID"] == portfolio_id]

    if row.empty:
        return None

    return row.iloc[0]

def assess_risk(portfolio_id, analysis=None):
    """
    Pass an existing analyse_portfolio() result as analysis to avoid downloading prices again
    """
    if analysis is None:
        analysis = analyse_portfolio(portfolio_id)

    allocation = analysis["allocation"]

    weights = allocation.set_index("Ticker")["Allocation_Percentage"] / 100
    returns = daily_returns(analysis["historical_prices"])

    volatility = portfolio_volatility(returns, weights)
    drawdown = max_drawdown(analysis["value_history"])

    factors = {
        "sector_concentration": 100 - analysis["diversification_score"],
        "volatility": scale_to_100(volatility, VOLATILITY_CAP),
        "asset_concentration": asset_concentration_risk(allocation),
        "drawdown": scale_to_100(drawdown, DRAWDOWN_CAP),
    }

    risk_score = sum(RISK_WEIGHTS[name] * score for name, score in factors.items())

    return {
        "risk_score": risk_score,
        "risk_level": risk_level(risk_score),
        "factors": factors,
        "portfolio_volatility": volatility,
        "max_drawdown": drawdown,
        "sector_exposure": sector_exposure_risk(analysis["sector_summary"]),
        "exceeds_holding_limit": bool(
            allocation["Allocation_Percentage"].max() > holding_limit(len(allocation))
        ),
        # Same number as the sector concentration factor, reported under its V1 name
        "diversification_risk": factors["sector_concentration"],
    }


def main():
    parser = argparse.ArgumentParser(description="Portfolio risk assessment")
    parser.add_argument("portfolio_id", nargs="?", default="P001")
    args = parser.parse_args()

    result = assess_risk(args.portfolio_id)
    expected = expected_assessment(args.portfolio_id)

    print(f"Portfolio {args.portfolio_id}")
    print(f"Risk score: {result['risk_score']:.1f}/100 ({result['risk_level']})")
    if expected is not None:
        print(f"Expected risk level: {expected['Expected_Risk_Level']}")

    print("\nFactor scores (0-100, higher is riskier):")
    for name, score in result["factors"].items():
        print(f"  {name:<22} {score:5.1f}  x {RISK_WEIGHTS[name]:.2f}")

    print(f"\nPortfolio volatility (annualised): {result['portfolio_volatility']:.1%}")
    print(f"Max drawdown over the year: {result['max_drawdown']:.1%}")
    print(f"Diversification risk: {result['diversification_risk']:.1f}/100")
    print(
        "Single holding above its limit: "
        f"{'yes' if result['exceeds_holding_limit'] else 'no'}"
    )
    print(f"\nSector exposure (limit {MAX_SECTOR_PERCENTAGE:.0f}%):")
    print(result["sector_exposure"])


if __name__ == "__main__":
    main()
