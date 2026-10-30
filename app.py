import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
import streamlit as st

from portfolio_analysis import analyse_portfolio, MAX_SECTOR_PERCENTAGE
from risk_analysis import assess_risk
from forecasting import forecast_portfolio
from insights import build_insights
from charts import (
    allocation_bars,
    performance_line,
    forecast_ranges,
    group_small_holdings,
)

PORTFOLIOS_FILE = "data/portfolios.csv"
CACHE_SECONDS = 15 * 60
CURRENCY = "$"


def current_theme():
    try:
        return "dark" if st.context.theme.type == "dark" else "light"
    except Exception:
        return "light"

def portfolio_names(file_path=PORTFOLIOS_FILE):
    portfolios = pd.read_csv(file_path)

    return portfolios.drop_duplicates("Portfolio_ID").set_index("Portfolio_ID")["Portfolio_Name"]

# Every call downloads prices, so results are cached for a while per portfolio
@st.cache_data(ttl=CACHE_SECONDS, show_spinner="Loading prices and analysing the portfolio...")
def load_analysis(portfolio_id):
    analysis = analyse_portfolio(portfolio_id)

    return analysis, assess_risk(portfolio_id, analysis)

@st.cache_data(ttl=CACHE_SECONDS, show_spinner="Running the forecast...")
def load_forecast(portfolio_id):
    return forecast_portfolio(portfolio_id)

def money(value):
    return f"{CURRENCY}{value:,.0f}"

def show_kpis(analysis, risk):
    performers = analysis["performers"].set_index("Performance")
    best, worst = performers.loc["Best"], performers.loc["Worst"]

    columns = st.columns(5)
    columns[0].metric("Portfolio value", money(analysis["total_value"]))
    columns[1].metric(
        "Risk score",
        f"{risk['risk_score']:.1f}/100",
        risk["risk_level"],
        delta_color="off",
        delta_arrow="off",
    )
    columns[2].metric("Diversification score", f"{analysis['diversification_score']:.0f}/100")
    columns[3].metric(
        "Best performer",
        best["Ticker"],
        f"{best['Return_Percentage']:+.1f}% over 1 year",
    )
    columns[4].metric(
        "Worst performer",
        worst["Ticker"],
        f"{worst['Return_Percentage']:+.1f}% over 1 year",
    )

def show_allocation(analysis, theme):
    sector = analysis["sector_summary"].reset_index()
    holdings = group_small_holdings(analysis["allocation"])
    holding_limit = analysis["insights"]["holding_limit_percentage"]

    left, right = st.columns(2)

    with left:
        st.subheader("Sector allocation")
        st.caption("Share of portfolio value by sector")
        st.plotly_chart(
            allocation_bars(sector, "Sector", "Allocation_Percentage", MAX_SECTOR_PERCENTAGE, theme),
            width="stretch",
            config={"displayModeBar": False},
        )
        with st.expander("View as table"):
            st.dataframe(
                sector.rename(columns={"Allocation_Percentage": "Share (%)"}),
                hide_index=True,
                column_config={"Share (%)": st.column_config.NumberColumn(format="%.1f")},
            )

    with right:
        st.subheader("Portfolio allocation")
        st.caption("Share of portfolio value by holding")
        st.plotly_chart(
            allocation_bars(holdings, "Ticker", "Allocation_Percentage", holding_limit, theme),
            width="stretch",
            config={"displayModeBar": False},
        )
        with st.expander("View as table"):
            table = analysis["allocation"][["Ticker", "Shares", "Current_Price", "Market_Value", "Allocation_Percentage"]]
            st.dataframe(
                table.rename(columns={"Allocation_Percentage": "Share (%)"}),
                hide_index=True,
                column_config={
                    "Current_Price": st.column_config.NumberColumn("Price", format=f"{CURRENCY}%.2f"),
                    "Market_Value": st.column_config.NumberColumn("Value", format=f"{CURRENCY}%.0f"),
                    "Share (%)": st.column_config.NumberColumn(format="%.1f"),
                },
            )

def show_trend(analysis, theme):
    history = analysis["value_history"]

    st.subheader("Portfolio performance trend")
    st.caption("Daily value of today's holdings over the past year")
    st.plotly_chart(
        performance_line(history, theme, CURRENCY),
        width="stretch",
        config={"displayModeBar": False},
    )
    with st.expander("View as table"):
        table = history.rename("Value").rename_axis("Date").reset_index().sort_values("Date", ascending=False)
        st.dataframe(
            table,
            hide_index=True,
            column_config={"Value": st.column_config.NumberColumn(format=f"{CURRENCY}%.0f")},
        )

def show_forecast(forecast, theme):
    portfolio = forecast["portfolio"]

    st.subheader(f"Forecast: next {forecast['horizon_days']} trading days")

    columns = st.columns(4)
    columns[0].metric(
        "Expected value",
        money(portfolio["Expected_Value"]),
        f"{portfolio['Expected_Return_Pct']:+.1f}%",
    )
    columns[1].metric(
        "Worst case",
        money(portfolio["Worst_Case_Value"]),
        f"{portfolio['Worst_Case_Return_Pct']:+.1f}%",
    )
    columns[2].metric(
        "Best case",
        money(portfolio["Best_Case_Value"]),
        f"{portfolio['Best_Case_Return_Pct']:+.1f}%",
    )
    columns[3].metric(
        "Confidence",
        f"{portfolio['Confidence_Score']:.0f}/100",
        "heuristic, not a probability",
        delta_color="off",
        delta_arrow="off",
    )

    st.caption("Per stock: the bar spans worst case to best case, the dot is the expected return")
    st.plotly_chart(
        forecast_ranges(forecast["stocks"], theme),
        width="stretch",
        config={"displayModeBar": False},
    )
    with st.expander("View as table"):
        st.dataframe(
            forecast["stocks"],
            hide_index=True,
            column_config={
                "Current_Price": st.column_config.NumberColumn("Price", format=f"{CURRENCY}%.2f"),
                "Expected_Price": st.column_config.NumberColumn(format=f"{CURRENCY}%.2f"),
                "Best_Case_Price": st.column_config.NumberColumn(format=f"{CURRENCY}%.2f"),
                "Worst_Case_Price": st.column_config.NumberColumn(format=f"{CURRENCY}%.2f"),
                "Expected_Return_Pct": st.column_config.NumberColumn("Expected return (%)", format="%.1f"),
                "Best_Case_Return_Pct": st.column_config.NumberColumn("Best case (%)", format="%.1f"),
                "Worst_Case_Return_Pct": st.column_config.NumberColumn("Worst case (%)", format="%.1f"),
                "Confidence_Score": st.column_config.NumberColumn("Confidence", format="%.0f"),
            },
        )

def show_insights(analysis, risk, forecast):
    st.subheader("Insights")

    sections = build_insights(analysis, risk, forecast)
    columns = st.columns(len(sections))

    for column, (title, messages) in zip(columns, sections.items()):
        with column:
            st.markdown(f"**{title}**")
            for message in messages:
                st.markdown(f"- {message}")


def main():
    st.set_page_config(page_title="APIIP", layout="wide")
    st.title("APIIP: Investment Intelligence")

    names = portfolio_names()

    picker, refresh, _ = st.columns([3, 1, 6], vertical_alignment="bottom")
    portfolio_id = picker.selectbox(
        "Portfolio",
        names.index,
        format_func=lambda portfolio: f"{portfolio}: {names[portfolio]}",
    )
    if refresh.button("Refresh data", width="stretch"):
        st.cache_data.clear()

    try:
        analysis, risk = load_analysis(portfolio_id)
    except Exception as error:
        st.error(f"Could not analyse portfolio {portfolio_id}: {error}")
        st.stop()

    forecast = None
    try:
        forecast = load_forecast(portfolio_id)
    except Exception as error:
        st.warning(f"The forecast is unavailable for this portfolio: {error}")

    theme = current_theme()

    show_kpis(analysis, risk)
    show_allocation(analysis, theme)
    show_trend(analysis, theme)
    if forecast is not None:
        show_forecast(forecast, theme)
    show_insights(analysis, risk, forecast)

    st.caption(
        "Prices come from Yahoo Finance and may be delayed. Forecasts are estimates from past price "
        "behaviour, not investment advice."
    )


main()
