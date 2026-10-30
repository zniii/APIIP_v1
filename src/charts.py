import numpy as np
import pandas as pd
import plotly.graph_objects as go

# One-hue palette (blue, slot 1 of the reference categorical palette) with recessive chrome.
# Text, grid and axis colors step with the theme; the data color stays the same hue.
THEMES = {
    "light": {
        "series": "#2a78d6",
        "text": "#52514e",
        "muted": "#898781",
        "grid": "#e1e0d9",
        "axis": "#c3c2b7",
        "surface": "#ffffff",
    },
    "dark": {
        "series": "#3987e5",
        "text": "#c3c2b7",
        "muted": "#898781",
        "grid": "#2c2c2a",
        "axis": "#383835",
        "surface": "#0e1117",
    },
}

# Bars are capped near 24px: each row gets ROW_HEIGHT and a BAR_GAP of it stays empty
ROW_HEIGHT = 40
BAR_GAP = 0.45
BAR_CORNER_RADIUS = 4
SMALL_HOLDING_PERCENTAGE = 3.0


def _rgba(hex_color, alpha):
    red, green, blue = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))

    return f"rgba({red},{green},{blue},{alpha})"

def _base_layout(colors, height, top=24):
    return dict(
        height=height,
        margin=dict(l=0, r=16, t=top, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=colors["text"], size=13),
        showlegend=False,
    )

def group_small_holdings(allocation, threshold=SMALL_HOLDING_PERCENTAGE):
    """
    Holdings under the threshold are folded into one "Other" row so large portfolios stay readable
    """
    data = allocation[["Ticker", "Allocation_Percentage"]].copy()
    small = data["Allocation_Percentage"] < threshold

    if small.sum() < 2:
        return data

    other = {"Ticker": f"Other ({small.sum()} holdings)", "Allocation_Percentage": data.loc[small, "Allocation_Percentage"].sum()}

    return pd.concat([data[~small], pd.DataFrame([other])], ignore_index=True)

def allocation_bars(data, label, value, limit=None, theme="light"):
    """
    Ranked horizontal bars (largest on top), with an optional limit marked as a hairline
    """
    colors = THEMES[theme]
    ranked = data.sort_values(value)

    figure = go.Figure(go.Bar(
        x=ranked[value],
        y=ranked[label],
        orientation="h",
        marker_color=colors["series"],
        text=[f"{share:.1f}%" for share in ranked[value]],
        textposition="outside",
        textfont=dict(color=colors["text"]),
        cliponaxis=False,
        hovertemplate="%{y}: <b>%{x:.1f}%</b><extra></extra>",
    ))

    longest = max(ranked[value].max(), limit or 0)

    figure.update_layout(
        **_base_layout(colors, ROW_HEIGHT * len(ranked) + 50, top=28),
        bargap=BAR_GAP,
        barcornerradius=BAR_CORNER_RADIUS,
    )
    figure.update_xaxes(
        range=[0, longest * 1.18],
        ticksuffix="%",
        gridcolor=colors["grid"],
        gridwidth=1,
        linecolor=colors["axis"],
        tickfont=dict(color=colors["muted"]),
        zeroline=False,
    )
    figure.update_yaxes(showgrid=False, linecolor=colors["axis"], automargin=True)

    if limit is not None:
        figure.add_vline(
            x=limit,
            line_width=1,
            line_color=colors["muted"],
            annotation_text=f"Limit {limit:.0f}%",
            annotation_position="top",
            annotation_font=dict(color=colors["text"], size=12),
        )

    return figure

def performance_line(history, theme="light", currency="$"):
    """
    Portfolio value over time: one 2px line, a crosshair, and the latest value labelled
    """
    colors = THEMES[theme]
    last_date, last_value = history.index[-1], history.iloc[-1]

    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=history.index,
        y=history.values,
        mode="lines",
        line=dict(color=colors["series"], width=2),
        hovertemplate=currency + "%{y:,.0f}<extra></extra>",
    ))
    figure.add_trace(go.Scatter(
        x=[last_date],
        y=[last_value],
        mode="markers+text",
        marker=dict(size=10, color=colors["series"], line=dict(color=colors["surface"], width=2)),
        text=[f"{currency}{last_value:,.0f}"],
        textposition="top left",
        textfont=dict(color=colors["text"]),
        cliponaxis=False,
        hoverinfo="skip",
    ))

    figure.update_layout(
        **_base_layout(colors, 340),
        hovermode="x unified",
    )
    figure.update_xaxes(
        showgrid=False,
        linecolor=colors["axis"],
        tickfont=dict(color=colors["muted"]),
        showspikes=True,
        spikemode="across",
        spikethickness=1,
        spikecolor=colors["muted"],
        spikedash="solid",
    )
    figure.update_yaxes(
        tickprefix=currency,
        tickformat=",.0f",
        gridcolor=colors["grid"],
        gridwidth=1,
        zeroline=False,
        tickfont=dict(color=colors["muted"]),
    )

    return figure

def forecast_ranges(stocks, theme="light"):
    """
    One row per stock: the worst-to-best case range as a bar, the expected return as a dot
    """
    colors = THEMES[theme]
    ranked = stocks.sort_values("Expected_Return_Pct")

    line_x, line_y = [], []
    for ticker, worst, best in zip(ranked["Ticker"], ranked["Worst_Case_Return_Pct"], ranked["Best_Case_Return_Pct"]):
        line_x += [worst, best, None]
        line_y += [ticker, ticker, None]

    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=line_x,
        y=line_y,
        mode="lines",
        line=dict(color=_rgba(colors["series"], 0.35), width=8),
        hoverinfo="skip",
    ))
    figure.add_trace(go.Scatter(
        x=ranked["Expected_Return_Pct"],
        y=ranked["Ticker"],
        mode="markers",
        marker=dict(size=12, color=colors["series"], line=dict(color=colors["surface"], width=2)),
        customdata=np.stack(
            [ranked["Worst_Case_Return_Pct"], ranked["Best_Case_Return_Pct"], ranked["Confidence_Score"]],
            axis=-1,
        ),
        hovertemplate=(
            "<b>%{y}</b><br>Expected %{x:+.1f}%"
            "<br>Worst case %{customdata[0]:+.1f}%, best case %{customdata[1]:+.1f}%"
            "<br>Confidence %{customdata[2]:.0f}/100<extra></extra>"
        ),
        hoverlabel=dict(namelength=0),
    ))

    figure.update_layout(
        **_base_layout(colors, ROW_HEIGHT * len(ranked) + 50),
        hovermode="closest",
        hoverdistance=40,
    )
    figure.update_xaxes(
        ticksuffix="%",
        gridcolor=colors["grid"],
        gridwidth=1,
        zeroline=False,
        tickfont=dict(color=colors["muted"]),
    )
    figure.update_yaxes(showgrid=False, linecolor=colors["axis"], automargin=True)
    figure.add_vline(x=0, line_width=1, line_color=colors["axis"])

    return figure
