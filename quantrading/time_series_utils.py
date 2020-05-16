import pandas as pd


def add_future_price(price_series: pd.Series, shift_list: list) -> pd.DataFrame:
    df = pd.DataFrame(price_series)

    temp_series_dict = dict()
    for shift in shift_list:
        name = f"D+{-shift}"
        temp_series = price_series.shift(shift)
        temp_series.name = name
        temp_series_dict[name] = temp_series

    df = pd.concat([df, *temp_series_dict.values()], axis=1)
    return df


def get_rolling_returns(price_series: pd.Series, window_list=None) -> pd.DataFrame:
    if window_list is None:
        window_list = [21, 63, 126, 252]

    df = pd.DataFrame()
    for window in window_list:
        name = f"Rolling{window}Returns"
        rolling_returns = price_series.pct_change().add(1).rolling(window=window).agg(lambda x: x.prod()) - 1
        rolling_returns.name = name
        df = pd.concat([df, rolling_returns], axis=1)
    return df


def get_future_returns(price_series: pd.Series, shift_list=None) -> pd.DataFrame:
    if shift_list is None:
        shift_list = [-21, -63]

    price_df = add_future_price(price_series, shift_list)

    name = price_series.name
    base_price_series = price_df[name]
    del price_df[name]

    future_returns_df = price_df.sub(base_price_series, axis='index').divide(base_price_series, axis='index')
    return future_returns_df


def add_past_price(price_series: pd.Series, shift_list: list) -> pd.DataFrame:
    df = pd.DataFrame(price_series)

    for shift in shift_list:
        name = f"D-{shift}"
        temp_series = price_series.shift(shift)
        temp_series.name = name
        df = pd.concat([df, temp_series], axis=1)
    return df


def get_past_returns(price_series: pd.Series, shift_list=None) -> pd.DataFrame:
    if shift_list is None:
        shift_list = [21, 63, 126, 252]

    price_df = add_past_price(price_series, shift_list)

    past_returns_df = pd.DataFrame()
    final_price_series = price_df.iloc[:, 0]

    for col_name in price_df.columns[1:]:
        base_price_series = price_df.loc[:, col_name]
        target_returns_series = (final_price_series - base_price_series) / base_price_series
        target_returns_series.name = col_name
        past_returns_df = pd.concat([past_returns_df, target_returns_series], axis=1)

    return past_returns_df


def add_both_side_returns(price_series: pd.Series, remove_base=True) -> pd.DataFrame:
    past_returns = get_past_returns(price_series)
    future_returns = get_future_returns(price_series)

    if remove_base:
        df = pd.concat([past_returns, future_returns], axis=1)
    else:
        df = pd.concat([past_returns, price_series, future_returns], axis=1)
    return df


def add_ma_price(price_series: pd.Series, ma_list: list) -> pd.DataFrame:
    df = pd.DataFrame(price_series)
    for ma in ma_list:
        temp_ma = price_series.rolling(ma).mean()
        df = pd.concat([df, temp_ma], axis=1)
    df.columns = [price_series.name] + [f"{ma}MA" for ma in ma_list]
    return df


def get_ma(price_series: pd.Series, ma_list=None) -> pd.DataFrame:
    if ma_list is None:
        ma_list = [21, 63, 126, 252]
    ma_price_df = add_ma_price(price_series, ma_list)
    ma_price_df = ma_price_df.dropna()

    new_ma_price_df = pd.DataFrame()
    for col_name in ma_price_df.columns[1:]:
        ma_price = ma_price_df.loc[:, col_name]
        ma_price.name = col_name
        new_ma_price_df = pd.concat([new_ma_price_df, ma_price], axis=1)
    return new_ma_price_df


def get_pct_change(price_series: pd.Series) -> pd.Series:
    pct_change = price_series.pct_change().dropna()
    pct_change.name = "PCT_CHANGE"
    return pct_change


def get_vol(price_series: pd.Series, window_list) -> pd.DataFrame:
    df = pd.DataFrame()
    for window in window_list:
        temp_ma = price_series.pct_change().rolling(window).std()
        df = pd.concat([df, temp_ma], axis=1)
    df.columns = [f"{window}VOL" for window in window_list]
    return df
