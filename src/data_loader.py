import pandas as pd

def load_portfolio(file_path="data/portfolios.csv"):
    """
    Load Portfolio
    """
    portfolios = pd.read_csv(file_path)

    portfolio_summary = portfolios.groupby(
        ["Portfolio_ID", "Portfolio_Name"]
    )["Shares"].sum()

    portfolio_id = "P001"
    
    selected_portfolio = portfolios[
        portfolios["Portfolio_ID"] == portfolio_id
    ]

    return portfolios


if __name__ == "__main__":
    portfolios = load_portfolio()