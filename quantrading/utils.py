import pandas as pd


def generate_leverage_index(index_series: pd.Series, leverage: int, start_value=100) -> pd.Series:
    pct_change = index_series.pct_change().mul(leverage)
    new_index = (1 + pct_change).cumprod()
    new_index.iloc[0] = 1
    new_index = new_index * start_value
    return new_index
