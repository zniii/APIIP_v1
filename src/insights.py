from portfolio_analysis import MAX_SECTOR_PERCENTAGE
from risk_analysis import RISK_WEIGHTS


def _signed(value):
    return f"{value:+.1f}%"

def _names(items):
    items = list(items)

    if len(items) <= 1:
        return "".join(items)

    return ", ".join(items[:-1]) + " and " + items[-1]

def portfolio_health_insights(analysis):
    found = analysis["insights"]
    top = analysis["top_holdings"]
    performers = analysis["performers"].set_index("Performance")
    messages = []

    reasons = []
    if found["dominant_sector_percentage"] > MAX_SECTOR_PERCENTAGE:
        reasons.append(
            f"{found['dominant_sector']} makes up {found['dominant_sector_percentage']:.1f}% "
            f"of the portfolio (limit {MAX_SECTOR_PERCENTAGE:.0f}%)"
        )
    if found["largest_holding_percentage"] > found["holding_limit_percentage"]:
        reasons.append(
            f"{found['largest_holding']} is {found['largest_holding_percentage']:.1f}% "
            f"of the portfolio (limit {found['holding_limit_percentage']:.0f}%)"
        )

    if reasons:
        messages.append("Over-concentrated: " + "; ".join(reasons) + ".")
    else:
        messages.append(
            f"Balanced: no sector is above {MAX_SECTOR_PERCENTAGE:.0f}% and no holding is above "
            f"{found['holding_limit_percentage']:.0f}%. The largest sector is {found['dominant_sector']} "
            f"at {found['dominant_sector_percentage']:.1f}%."
        )

    shares = ", ".join(f"{p:.1f}%" for p in top["Allocation_Percentage"])
    messages.append(
        f"{_names(top['Ticker'])} contribute most to the portfolio ({shares}, "
        f"{top['Allocation_Percentage'].sum():.1f}% together)."
    )

    messages.append(
        f"Diversification score is {analysis['diversification_score']:.0f}/100 "
        "(100 means spread evenly across all sectors, 0 means everything in one)."
    )

    best, worst = performers.loc["Best"], performers.loc["Worst"]
    messages.append(
        f"Over the past year the best performer was {best['Ticker']} ({_signed(best['Return_Percentage'])}) "
        f"and the worst was {worst['Ticker']} ({_signed(worst['Return_Percentage'])})."
    )

    return messages

def risk_insights(risk):
    contributions = {
        name: RISK_WEIGHTS[name] * score for name, score in risk["factors"].items()
    }
    driver = max(contributions, key=contributions.get)

    return [
        f"Risk score is {risk['risk_score']:.1f}/100, which is {risk['risk_level']}.",
        f"The biggest driver is {driver.replace('_', ' ')}, adding {contributions[driver]:.1f} of "
        f"the {risk['risk_score']:.1f} points.",
        f"Portfolio volatility is {risk['portfolio_volatility']:.1%} a year, and the worst "
        f"peak-to-trough fall over the past year was {risk['max_drawdown']:.1%}.",
    ]

def forecast_insights(forecast):
    portfolio = forecast["portfolio"]
    stocks = forecast["stocks"]
    check = forecast.get("backtest")

    messages = [
        f"Over the next {forecast['horizon_days']} trading days the portfolio is expected to move "
        f"{_signed(portfolio['Expected_Return_Pct'])}, with a worst case of "
        f"{_signed(portfolio['Worst_Case_Return_Pct'])} and a best case of "
        f"{_signed(portfolio['Best_Case_Return_Pct'])}.",
        f"Confidence is {portfolio['Confidence_Score']:.0f}/100. This is a heuristic based on how "
        "narrow the range is, how much history there is and how steady trading volume is. "
        "It is not a probability.",
    ]

    least_sure = stocks.loc[stocks["Confidence_Score"].idxmin()]
    messages.append(
        f"The least certain forecast is {least_sure['Ticker']} "
        f"(confidence {least_sure['Confidence_Score']:.0f}, range "
        f"{_signed(least_sure['Worst_Case_Return_Pct'])} to {_signed(least_sure['Best_Case_Return_Pct'])})."
    )

    if check is not None:
        messages.append(
            f"In past tests the real price landed inside this kind of range {check['coverage']:.0%} "
            "of the time (the target is 90%)."
        )

    return messages

def build_insights(analysis, risk=None, forecast=None):
    """
    Plain-language findings, grouped by section. Risk and forecast are optional.
    """
    sections = {"Portfolio health": portfolio_health_insights(analysis)}

    if risk is not None:
        sections["Risk"] = risk_insights(risk)

    if forecast is not None:
        sections["Forecast"] = forecast_insights(forecast)

    return sections
