import pandas as pd
from .trading_day import TradingDay
from .utils import get_dynamic_weight_rebalancing_port_daily_value_df
from .simulation_result_utils import calc_performance_from_value_history


class LightStrategy:
    def __init__(self, **kwargs):
        self.name = kwargs.get("name")
        self.start_date = kwargs.get("start_date")
        self.end_date = kwargs.get("end_date")
        self.date = self.start_date

        # 전 기간 동안의 유니버스를 받아옴.
        self.daily_price_df: pd.DataFrame = kwargs.get("daily_price_df")
        self.daily_return_df: pd.DataFrame = self.daily_price_df.pct_change()
        self.daily_return_df = self.daily_return_df.loc[self.daily_return_df.index >= self.start_date]

        self.tickers = self.daily_return_df.columns.to_list()

        # set trading days & rebalancing days
        trading_day = TradingDay(self.daily_price_df.index.to_series().reset_index(drop=True))
        self.trading_days = trading_day.get_trading_day_list(self.start_date, self.end_date).to_list()
        self.rebalancing_periodic = kwargs.get("rebalancing_periodic")
        self.rebalancing_moment = kwargs.get("rebalancing_moment")
        self.rebalancing_days = trading_day.get_rebalancing_days(self.start_date, self.end_date,
                                                                 self.rebalancing_periodic,
                                                                 self.rebalancing_moment)
        self.initial_order = False
        self.weight_dict_list = []
        self.result = None

    def initialize(self):
        """
        상속하여 초기 포트 비중 설정시, self.initial_order = True 로 설정해줘야함.
        """
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
        allocation['date'] = self.date
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

        if self.trading_days[0] in self.rebalancing_days:
            rebalacing_date_list = self.rebalancing_days[1:]
            if self.initial_order:
                weight_dict_list = weight_dict_list[1:]
        else:
            rebalacing_date_list = self.rebalancing_days

        ticker_set = set()
        for weight_dict in weight_dict_list:
            tickers = list(weight_dict.keys())
            ticker_set = ticker_set.union(set(tickers))
        ticker_set.remove('date')

        traded_tickers = list(ticker_set)

        daily_return_df = daily_return_df.loc[:, traded_tickers]

        empty_weight_series = pd.Series(0, index=traded_tickers)
        weight_series_list = []
        for weight_dict in weight_dict_list:
            date = weight_dict.pop('date')
            weight_series = empty_weight_series.add(pd.Series(weight_dict)).fillna(0)
            weight_series.name = date
            weight_series_list.append(weight_series)

        port_value_df = get_dynamic_weight_rebalancing_port_daily_value_df(
            weight_series_list,
            daily_return_df,
            rebalacing_date_list
        )
        port_value_series = port_value_df.sum(axis=1)
        port_value_series = port_value_series * 100
        port_value_series.name = self.name

        result = dict()
        performance = calc_performance_from_value_history(port_value_series)
        performance['port_value'] = port_value_series
        result['performance'] = performance

        weight_df = pd.DataFrame(weight_series_list)
        result['rebalacing_history'] = weight_df
        self.result = result

    def result_value_to_excel_file(self, path):
        result = self.result

        performance = result['performance']
        rebalacing_history = result['rebalacing_history']

        portfolio_log = pd.concat([performance["port_value"], performance['drawdown']], axis=1)
        monthly_returns = performance["monthly_returns"]
        annual_summary = performance["annual_summary"]
        performance_summary = performance["performance_summary"]
        with pd.ExcelWriter(path, datetime_format="yyyy-mm-dd") as writer:
            portfolio_log.to_excel(writer, sheet_name="portfolio log")
            performance_summary.to_excel(writer, sheet_name="요약")
            rebalacing_history.to_excel(writer, sheet_name="리밸런싱 비중")
            monthly_returns.to_excel(writer, sheet_name="월별수익률")
            annual_summary.to_excel(writer, sheet_name="연도별 요약")

