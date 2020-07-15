import pandas as pd


def divide_code_list_by_quantiles(asset_series: pd.Series, quantiles: int, target_tile: int) -> tuple:
    counts_per_division = len(asset_series) / quantiles
    counts_per_division = int(counts_per_division)

    tile = target_tile

    reversed_asset_series = asset_series.sort_values(ascending=False)

    first_quantile = asset_series.index.to_list()[counts_per_division * tile: counts_per_division * (tile + 1)]
    last_quantile = reversed_asset_series.index.to_list()[counts_per_division * tile: counts_per_division * (tile + 1)]
    return first_quantile, last_quantile


def apply_equal_weights(code_list: list, for_short=False, exposure=1) -> dict:
    total_weight = -exposure if for_short else exposure
    if len(code_list) == 0:
        weights = {}
    else:
        weights = {}
        weight_per_stock = total_weight / len(code_list)
        for ticker in code_list:
            weights[ticker] = weight_per_stock
    return weights


def get_intersect_code_list(one: list, another: list) -> list:
    return list(set(one).intersection(set(another)))


def get_no_rebalancing_port_daily_value_df(weight_series: pd.Series, daily_return_df: pd.DataFrame) -> pd.DataFrame:
    """
    리밸런싱이 없는 포트폴리오 자산 value
    시작 value 는 합산 1
    """
    assert weight_series.sum() == 1
    initial_value_series = weight_series
    daily_value_df = daily_return_df.add(1).cumprod().multiply(initial_value_series)
    return daily_value_df


def get_static_weight_rebalancing_port_daily_value_df(weight_series: pd.Series,
                                                      daily_return_df: pd.DataFrame,
                                                      rebalancing_date_list: list) -> pd.DataFrame:
    """
    리밸런싱이 반영된 포트폴리오 자산 value
    weight_series 의 index 와 daily_return_df column 이 일치해야함.
    for 문 없앨수 없나??..
    리밸런싱 날의 종가에 매도, 매수 모두 이루어진다고 가정.
    """

    port_value_df = pd.DataFrame()

    new_rebalancing_date_list = [*rebalancing_date_list]
    if new_rebalancing_date_list[-1] != daily_return_df.index[-1].strftime("%Y-%m-%d"):
        new_rebalancing_date_list.append(daily_return_df.index[-1].strftime("%Y-%m-%d"))

    for i, date in enumerate(new_rebalancing_date_list):
        if i == 0:
            start_date = daily_return_df.index[0].strftime("%Y-%m-%d")
            end_date = date
            previous_value_series = weight_series
            date_range = (daily_return_df.index >= start_date) & (daily_return_df.index <= end_date)
        else:
            start_date = new_rebalancing_date_list[i - 1]
            end_date = date
            previous_value_series = weight_series * port_value_df.iloc[-1].sum()
            date_range = (daily_return_df.index > start_date) & (daily_return_df.index <= end_date)
        sliced_daily_return_df = daily_return_df.loc[date_range]
        sliced_value_df = sliced_daily_return_df.add(1).cumprod().multiply(previous_value_series)
        port_value_df = pd.concat([port_value_df, sliced_value_df], axis=0)
    return port_value_df


def get_dynamic_weight_rebalancing_port_daily_value_df(weight_series_list: list,
                                                       daily_return_df: pd.DataFrame,
                                                       rebalancing_date_list: list) -> pd.DataFrame:
    """
    weight_eries_list 의 첫 항목은 최조 비중
    리밸런싱 날의 종가에 매도, 매수 모두 이루어진다고 가정.
    """
    assert len(weight_series_list) == len(rebalancing_date_list) + 1

    port_value_df = pd.DataFrame()

    new_rebalancing_date_list = [*rebalancing_date_list]
    if new_rebalancing_date_list[-1] != daily_return_df.index[-1].strftime("%Y-%m-%d"):
        new_rebalancing_date_list.append(daily_return_df.index[-1].strftime("%Y-%m-%d"))

    sliced_value_df_list = []
    for i, date in enumerate(new_rebalancing_date_list):
        print(date)
        if i == 0:
            start_date = daily_return_df.index[0].strftime("%Y-%m-%d")
            end_date = date
            previous_value_series = weight_series_list[i]
            date_range = (daily_return_df.index >= start_date) & (daily_return_df.index <= end_date)
        else:
            start_date = rebalancing_date_list[i - 1]
            end_date = date
            # previous_value_series = weight_series_list[i] * port_value_df.iloc[-1].sum()
            previous_value_series = weight_series_list[i] * sliced_value_df_list[-1].iloc[-1].sum()
            date_range = (daily_return_df.index > start_date) & (daily_return_df.index <= end_date)
        sliced_daily_return_df = daily_return_df.loc[date_range]
        sliced_value_df = sliced_daily_return_df.add(1).cumprod().multiply(previous_value_series)
        sliced_value_df_list.append(sliced_value_df)
    port_value_df = pd.concat([*sliced_value_df_list], axis=0)
    return port_value_df
