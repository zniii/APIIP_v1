import argparse
import numpy as np
import pandas as pd
from data_loader import (
    get_portfolio,
    ticker_prices,
    get_history_with_volume,
    get_market_prices,
)

TRADING_DAYS = 252
FORECAST_HORIZON_DAYS = 21
SIMULATIONS = 10_000
SEED = 42

# Weight on recent days in the covariance estimate (higher = longer memory)
EWMA_LAMBDA = 0.97

# Expected return = DRIFT_SAMPLE_WEIGHT x the stock's own past return
# + the rest x (risk free + beta x market premium). The past return alone is too noisy.
DRIFT_SAMPLE_WEIGHT = 0.25
RISK_FREE_RATE = 0.04
MARKET_PREMIUM = 0.05

BEST_CASE_PERCENTILE = 95
WORST_CASE_PERCENTILE = 5

MIN_HISTORY_DAYS = 250
SUFFICIENT_HISTORY_DAYS = 750
VOLUME_RECENT_DAYS = 21

# Confidence is a heuristic, not a probability. A band wider than WIDTH_CAP of the
# expected price scores 0 for tightness.
WIDTH_CAP = 0.5
CONFIDENCE_WEIGHTS = {
    "tightness": 0.6,
    "history": 0.2,
    "volume": 0.2,
}

BACKTEST_ORIGINS = 24
BACKTEST_SIMULATIONS = 2_000


def log_returns(prices):
    return np.log(prices / prices.shift(1)).dropna()

def align_history(prices, volume, market_prices):
    """
    Put prices, volume and the market on the same dates and check there is enough history
    """
    common = prices.index.intersection(market_prices.index)
    prices = prices.loc[common]
    volume = volume.reindex(common)
    market_prices = market_prices.loc[common]

    short = prices.columns[prices.count() < MIN_HISTORY_DAYS].tolist()

    if short:
        raise ValueError(
            f"Fewer than {MIN_HISTORY_DAYS} days of history for: {', '.join(short)}"
        )

    prices = prices.dropna()

    return prices, volume.reindex(prices.index), market_prices.loc[prices.index]

def ewma_covariance(returns, decay=EWMA_LAMBDA):
    """
    Daily covariance matrix where recent days count more
    """
    values = returns.to_numpy()
    weights = decay ** np.arange(len(values) - 1, -1, -1)
    weights = weights / weights.sum()

    covariance = (values * weights[:, None]).T @ values

    return pd.DataFrame(covariance, index=returns.columns, columns=returns.columns)

def estimate_beta(returns, market_returns):
    market = market_returns.reindex(returns.index)

    return returns.apply(lambda stock: stock.cov(market)) / market.var()

def expected_annual_return(returns, market_returns):
    """
    Blend of each stock's own past return and the market-implied (CAPM) return
    """
    sample = returns.mean() * TRADING_DAYS + 0.5 * returns.var() * TRADING_DAYS
    market_implied = RISK_FREE_RATE + estimate_beta(returns, market_returns) * MARKET_PREMIUM

    return DRIFT_SAMPLE_WEIGHT * sample + (1 - DRIFT_SAMPLE_WEIGHT) * market_implied

def draw_shocks(covariance, horizon, simulations, rng):
    """
    Random horizon-long moves with the given daily covariance, correlated across stocks
    """
    matrix = covariance.to_numpy() * horizon
    matrix = matrix + np.eye(len(matrix)) * 1e-12
    cholesky = np.linalg.cholesky(matrix)

    standard_normal = rng.standard_normal((simulations, len(matrix)))

    return standard_normal @ cholesky.T

def simulate_terminal_log_returns(
    returns,
    market_returns,
    horizon=FORECAST_HORIZON_DAYS,
    simulations=SIMULATIONS,
    seed=SEED,
):
    """
    Simulated log returns over the horizon: one row per scenario, one column per stock
    """
    covariance = ewma_covariance(returns)
    annual_return = expected_annual_return(returns, market_returns)

    daily_drift = annual_return.to_numpy() / TRADING_DAYS - 0.5 * np.diag(covariance)

    rng = np.random.default_rng(seed)
    shocks = draw_shocks(covariance, horizon, simulations, rng)

    return horizon * daily_drift + shocks

def volume_ratio(volume):
    recent = volume.tail(VOLUME_RECENT_DAYS).mean()
    longer = volume.tail(TRADING_DAYS).mean()

    return recent / longer

def confidence_score(width_ratio, observations, volume_change):
    """
    0-100 heuristic: tight range, plenty of history and steady volume score higher
    """
    tightness = min(max(1 - width_ratio / WIDTH_CAP, 0.0), 1.0)
    history = min(observations / SUFFICIENT_HISTORY_DAYS, 1.0)

    if np.isfinite(volume_change) and volume_change > 0:
        volume = min(volume_change, 1 / volume_change)
    else:
        volume = 0.0

    parts = {"tightness": tightness, "history": history, "volume": volume}

    return 100 * sum(CONFIDENCE_WEIGHTS[name] * value for name, value in parts.items())

def forecast_stocks(last_prices, terminal_log_returns, observations, volume_changes):
    """
    Per-stock forecast table from the simulated scenarios
    """
    prices = last_prices.to_numpy() * np.exp(terminal_log_returns)

    expected = prices.mean(axis=0)
    best = np.percentile(prices, BEST_CASE_PERCENTILE, axis=0)
    worst = np.percentile(prices, WORST_CASE_PERCENTILE, axis=0)

    current = last_prices.to_numpy()

    return pd.DataFrame({
        "Ticker": last_prices.index,
        "Current_Price": current,
        "Expected_Price": expected,
        "Expected_Return_Pct": (expected / current - 1) * 100,
        "Best_Case_Price": best,
        "Best_Case_Return_Pct": (best / current - 1) * 100,
        "Worst_Case_Price": worst,
        "Worst_Case_Return_Pct": (worst / current - 1) * 100,
        "Confidence_Score": [
            confidence_score((b - w) / e, observations, v)
            for b, w, e, v in zip(best, worst, expected, volume_changes.reindex(last_prices.index))
        ],
    })

def forecast_portfolio_value(shares, last_prices, terminal_log_returns, observations, volume_changes):
    """
    Forecast of the whole portfolio. Scenarios are summed per run, so the range
    reflects how the stocks move together.
    """
    shares = shares.reindex(last_prices.index)

    scenario_values = (last_prices.to_numpy() * np.exp(terminal_log_returns) * shares.to_numpy()).sum(axis=1)

    current = float((last_prices * shares).sum())
    expected = float(scenario_values.mean())
    best = float(np.percentile(scenario_values, BEST_CASE_PERCENTILE))
    worst = float(np.percentile(scenario_values, WORST_CASE_PERCENTILE))

    position_weights = (last_prices * shares) / current
    portfolio_volume_change = float((position_weights * volume_changes.reindex(last_prices.index)).sum())

    return {
        "Current_Value": current,
        "Expected_Value": expected,
        "Expected_Return_Pct": (expected / current - 1) * 100,
        "Best_Case_Value": best,
        "Best_Case_Return_Pct": (best / current - 1) * 100,
        "Worst_Case_Value": worst,
        "Worst_Case_Return_Pct": (worst / current - 1) * 100,
        "Confidence_Score": confidence_score((best - worst) / expected, observations, portfolio_volume_change),
    }

def backtest(
    prices,
    market_prices,
    origins=BACKTEST_ORIGINS,
    horizon=FORECAST_HORIZON_DAYS,
    simulations=BACKTEST_SIMULATIONS,
    seed=SEED,
):
    """
    Walk-forward check: forecast from past dates using only data up to then, and see
    how often the real price landed inside the best/worst-case band.
    """
    alpha = 1 - (BEST_CASE_PERCENTILE - WORST_CASE_PERCENTILE) / 100
    covered = []
    widths = []
    scores = []
    below = []
    above = []

    for step in range(origins, 0, -1):
        origin = len(prices) - 1 - step * horizon

        train_prices = prices.iloc[: origin + 1]
        returns = log_returns(train_prices)
        market_returns = log_returns(market_prices.iloc[: origin + 1])

        simulated = simulate_terminal_log_returns(
            returns, market_returns, horizon, simulations, seed
        )

        # Compare in simple-return terms so stocks with different prices are comparable
        low = np.exp(np.percentile(simulated, WORST_CASE_PERCENTILE, axis=0)) - 1
        high = np.exp(np.percentile(simulated, BEST_CASE_PERCENTILE, axis=0)) - 1
        actual = (prices.iloc[origin + horizon] / prices.iloc[origin]).to_numpy() - 1

        covered.append((actual >= low) & (actual <= high))
        below.append(actual < low)
        above.append(actual > high)
        widths.append(high - low)

        # Winkler interval score: width plus a penalty for each miss, so a wider band
        # cannot look better just by being wider
        scores.append(
            (high - low)
            + (2 / alpha) * (low - actual) * (actual < low)
            + (2 / alpha) * (actual - high) * (actual > high)
        )

    return {
        "coverage": float(np.mean(covered)),
        "below_worst_case": float(np.mean(below)),
        "above_best_case": float(np.mean(above)),
        "mean_width": float(np.mean(widths)),
        "interval_score": float(np.mean(scores)),
        "observations": int(np.size(covered)),
    }

def run_forecast(prices, volume, market_prices, shares, include_backtest=True):
    prices, volume, market_prices = align_history(prices, volume, market_prices)

    returns = log_returns(prices)
    market_returns = log_returns(market_prices.to_frame()).iloc[:, 0]

    simulated = simulate_terminal_log_returns(returns, market_returns)

    last_prices = prices.iloc[-1]
    volume_changes = volume_ratio(volume)
    observations = len(returns)

    result = {
        "horizon_days": FORECAST_HORIZON_DAYS,
        "stocks": forecast_stocks(last_prices, simulated, observations, volume_changes),
        "portfolio": forecast_portfolio_value(shares, last_prices, simulated, observations, volume_changes),
    }

    if include_backtest:
        result["backtest"] = backtest(prices, market_prices)

    return result

def forecast_portfolio(portfolio_id, include_backtest=True):
    portfolio = get_portfolio(portfolio_id)
    tickers = ticker_prices(portfolio)

    prices, volume = get_history_with_volume(tickers)
    market_prices = get_market_prices()

    return run_forecast(
        prices,
        volume,
        market_prices,
        portfolio.set_index("Ticker")["Shares"],
        include_backtest,
    )


def main():
    parser = argparse.ArgumentParser(description="Portfolio forecast")
    parser.add_argument("portfolio_id", nargs="?", default="P001")
    args = parser.parse_args()

    result = forecast_portfolio(args.portfolio_id)
    portfolio = result["portfolio"]

    print(f"Portfolio {args.portfolio_id}: {result['horizon_days']}-trading-day forecast")
    print(
        f"Current value {portfolio['Current_Value']:,.2f} -> expected {portfolio['Expected_Value']:,.2f} "
        f"({portfolio['Expected_Return_Pct']:+.1f}%)"
    )
    print(
        f"Best case {portfolio['Best_Case_Value']:,.2f} ({portfolio['Best_Case_Return_Pct']:+.1f}%), "
        f"worst case {portfolio['Worst_Case_Value']:,.2f} ({portfolio['Worst_Case_Return_Pct']:+.1f}%), "
        f"confidence {portfolio['Confidence_Score']:.0f}/100"
    )

    print("\nPer stock:")
    print(result["stocks"].round(2).to_string(index=False))

    check = result["backtest"]
    print(
        f"\nBacktest ({check['observations']} past forecasts): the real price landed inside the "
        f"best/worst-case band {check['coverage']:.0%} of the time (target "
        f"{BEST_CASE_PERCENTILE - WORST_CASE_PERCENTILE}%). "
        f"Below the worst case {check['below_worst_case']:.0%}, above the best case {check['above_best_case']:.0%}."
    )
    print("These are estimates from past price behaviour, not advice. Confidence is a heuristic score, not a probability.")


if __name__ == "__main__":
    main()
