import pandas as pd
from .trading_day import TradingDay
from .utils import get_dynamic_weight_rebalancing_port_daily_value_df


class LightStrategy:
    def __init__(self, **kwargs):
        self.name = kwargs.get("name")
        self.start_date = kwargs.get("start_date")
        self.end_date = kwargs.get("end_date")
        self.date = self.start_date

        # 전 기간 동안의 유니버스를 받아옴.
        self.daily_price_df: pd.DataFrame = kwargs.get("daily_price_df")
        self.daily_return_df: pd.DataFrame = self.daily_price_df.pct_change()

        self.tickers = self.daily_return_df.columns.to_list()

        # set trading days & rebalancing days
        trading_day = TradingDay(self.daily_price_df.index.to_series().reset_index(drop=True))
        self.trading_days = trading_day.get_trading_day_list(self.start_date, self.end_date).to_list()
        self.rebalancing_periodic = kwargs.get("rebalancing_periodic")
        self.rebalancing_moment = kwargs.get("rebalancing_moment")
        self.rebalancing_days = trading_day.get_rebalancing_days(self.start_date, self.end_date,
                                                                 self.rebalancing_periodic,
                                                                 self.rebalancing_moment)

        self.weight_dict_list = []

    def initialize(self):
        pass

    def on_data(self):
        pass

    def run(self):
        self.initialize()
        for date in self.rebalancing_days:
            self.date = date
            self.on_data()
        self.on_end_of_algorithm()

    def reserve_order(self, allocation: dict):
        self.weight_dict_list.append(allocation)

    def is_trading_day(self):
        today = self.date
        if today in self.trading_days:
            return True
        else:
            return False

    def is_rebalancing_day(self):
        today = self.date
        if today in self.rebalancing_days:
            return True
        else:
            return False

    def on_end_of_algorithm(self):
        weight_dict_list = self.weight_dict_list
        daily_return_df = self.daily_return_df
        rebalacing_date_list = self.rebalancing_days

        ticker_set = set()
        for weight_dict in weight_dict_list:
            tickers = list(weight_dict.keys())
            ticker_set = ticker_set.union(set(tickers))

        traded_tickers = list(ticker_set)

        daily_return_df = daily_return_df.loc[:, traded_tickers]

        empty_weight_series = pd.Series(0, index=traded_tickers)
        weight_series_list = []
        for weight_dict in weight_dict_list:
            weight_series = empty_weight_series.add(pd.Series(weight_dict)).fillna(0)
            weight_series_list.append(weight_series)

        port_value_df = get_dynamic_weight_rebalancing_port_daily_value_df(
            weight_series_list,
            daily_return_df,
            rebalacing_date_list
        )
        print(port_value_df.sum(axis=1))
