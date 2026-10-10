import pandas as pd
from data_loader import load_sec_allocation, portfolio_w_prices


def largest_and_smallest_holdings(data):
    largest = data[
        data["Allocation_Percentage"] == data["Allocation_Percentage"].max()
    ]

    smallest = data[
        data["Allocation_Percentage"] == data["Allocation_Percentage"].min()
    ]

    return pd.concat([largest, smallest], ignore_index=True)

def sector_allocation(data):
    sector_data = load_sec_allocation.merge(
        data,
        on="Ticker",
        how="inner"
    )

    return sector_data

def sector_allocation_summary(data):
    sector_summary = data.groupby("Sector")[["Allocation_Percentage"]].sum()

    return sector_summary

def sector_diversification_score(data):
    sector_diversification = data.copy()
    sector_diversification["Diversified_Allocation"] = sector_diversification["Allocation_Percentage"]/100
    sector_diversification["Square_Diversification"] = sector_diversification["Diversified_Allocation"] ** 2

    hhi = sector_diversification["Square_Diversification"].sum()
    num_of_sectors = len(sector_diversification)

    if num_of_sectors == 1:
        return 0.0

    minimum_hhi = 1/num_of_sectors
    normalized_hhi = (hhi - minimum_hhi) / (1-minimum_hhi)
    diversification_score = (1 - normalized_hhi) * 100

    return diversification_score

holdings = largest_and_smallest_holdings(portfolio_w_prices)
sector = sector_allocation(portfolio_w_prices)
sector_summary = sector_allocation_summary(sector)
sector_score = sector_diversification_score(sector_summary)

print(sector_score)
