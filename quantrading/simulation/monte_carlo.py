import pandas as pd
import numpy as np


def generate_single_case(returns_df: pd.DataFrame, walk_length: int):
    assets_counts = len(returns_df.columns)
    cov = returns_df.cov()
    returns_mean = returns_df.mean()
    returns_std = returns_df.std()
    z_list = []

    for asset in returns_df.columns:
        mean = returns_mean[asset]
        std = returns_std[asset]
        standardized_returns = (returns_df[asset] - mean) / std
        z = np.random.choice(standardized_returns, walk_length)
        z_list.append([z])

    Z = np.concatenate(z_list)
    L = np.linalg.cholesky(cov)
    future_returns = np.full((walk_length, assets_counts), returns_mean).T + np.dot(L, Z)
    return pd.DataFrame(future_returns.T, columns=returns_df.columns)
