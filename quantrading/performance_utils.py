import pandas as pd
from datetime import datetime
import numpy as np
import empyrical


def get_returns(cur_price: float, base_price: float):
    return (cur_price - base_price) / base_price


def get_annualized_returns(start_date: datetime, end_date: datetime, returns: float):
    years = get_delta_year(start_date, end_date)
    if years == 0:
        return np.nan
    return (1 + returns) ** (1 / years) - 1


def get_delta_year(start_date: datetime, end_date: datetime):
    """
    1년 365일 기준
    4년(1460) 초과시마다 하루 씩 제외
    """
    time_delta = end_date - start_date

    leaps = int(time_delta.days / 1460)
    years = (time_delta.days - leaps) / 365
    return years


def convert_values_to_cumulative_returns(value_series: pd.Series) -> pd.Series:
    cumulative_returns = value_series.pct_change().add(1).cumprod() - 1
    return cumulative_returns


def get_annualized_std(std: float, returns_type="daily"):
    if returns_type == "daily":
        N = 252
    elif returns_type == "weekly":
        N = 52
    elif returns_type == "monthly":
        N = 12
    else:
        raise ValueError("Invalid returns type : ", returns_type)
    return std * N ** (1 / 2)


def get_returns_between_returns(returns_pairs: tuple):
    """
    :param returns_pairs: tuple(base, target)
    :return: -1 ~ Inf
    """
    base, target = returns_pairs
    return ((target + 1) / (base + 1)) - 1


def get_annual_std(daily_returns: pd.Series) -> pd.Series:
    return daily_returns.groupby(daily_returns.index.year).std().apply(get_annualized_std)


def get_performance_summary(daily_returns_series: pd.Series, final_returns: float):
    assert type(daily_returns_series) == pd.Series

    performance_summary = pd.Series()
    date_list = daily_returns_series.dropna().index.tolist()
    start_date = date_list[0]
    end_date = date_list[-1]
    cagr = get_annualized_returns(start_date, end_date, final_returns)
    annual_std = get_annualized_std(daily_returns_series.std(), "daily")
    mdd = empyrical.max_drawdown(daily_returns_series)

    performance_summary.loc["시작일"] = start_date
    performance_summary.loc["종료일"] = end_date
    performance_summary.loc["누적수익률"] = final_returns
    performance_summary.loc["CAGR"] = cagr
    performance_summary.loc["Ann.Std"] = annual_std
    performance_summary.loc["MDD"] = mdd
    performance_summary.loc["샤프지수"] = cagr / annual_std

    return performance_summary


def get_draw_down(returns: pd.Series):
    df = pd.DataFrame()
    df['cumulative_returns'] = returns
    df['historical_high'] = df['cumulative_returns'].cummax()
    df['drawdown'] = df.loc[:, ['historical_high', 'cumulative_returns']].apply(get_returns_between_returns, axis=1)
    return df['drawdown']
