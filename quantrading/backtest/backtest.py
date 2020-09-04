import pandas as pd
from datetime import timedelta
from .portfolio import Portfolio
from .simulation_result_utils import calc_performance_from_value_history
from .trading_day import TradingDay
from .backtest_base import BackTestBase


class Strategy(BackTestBase):
    def __init__(self, **kwargs):
        self.name = kwargs.get("name")
        self.start_date = kwargs.get("start_date")
        self.end_date = kwargs.get("end_date")
        self.market_df = kwargs.get("market_df")
        self.rebalancing_periodic = kwargs.get("rebalancing_periodic", 'monthly')
        self.rebalancing_moment = kwargs.get("rebalancing_moment", 'first')
        self.name_for_result_column = kwargs.get('name_for_result_column', '전략')

        self.on_data_before_n_days_of_rebalacing_days = kwargs.get('on_data_before_n_days_of_rebalacing_days', 1)

        # set trading days & rebalancing days
        trading_day = TradingDay(self.market_df.index.to_series().reset_index(drop=True))
        self.trading_days = trading_day.get_trading_day_list(self.start_date, self.end_date).to_list()
        self.rebalancing_days = trading_day.get_rebalancing_days(self.start_date, self.end_date,
                                                                 self.rebalancing_periodic, self.rebalancing_moment)
        self.date = self.start_date
        self.market_df_pct_change = self.market_df.pct_change()

        self.portfolio = Portfolio()
        self.portfolio_log = pd.DataFrame(columns=['port_value', 'cash'])
        self.order_weight_df = pd.DataFrame()
        self.simulation_status = {}
        self.simulation_result = {}
        self.event_log = pd.DataFrame(columns=["datetime", "log"])
        self.exist_reservation_order = False
        self.reservation_order = pd.Series()
        self.selected_asset_counts = pd.Series()
        self.daily_log_list = []

    def initialize(self):
        pass

    def on_data(self):
        pass

    def run(self):
        self.initialize()

        for date in self.trading_days:
            self.date = date
            self.on_start_of_day()
            if self.exist_reservation_order:
                self.execute_reservation_order()
            if self.is_rebalancing_day(self.on_data_before_n_days_of_rebalacing_days):
                self.on_data()
            self.on_end_of_day()
        self.on_end_of_algorithm()

    def execute_reservation_order(self):
        self.portfolio.set_allocations(self.reservation_order)
        reservation_order_series = self.reservation_order
        reservation_order_series.name = self.date
        self.order_weight_df = pd.concat([self.order_weight_df, reservation_order_series.to_frame().T], axis=0)
        self.selected_asset_counts.loc[self.date] = len(self.reservation_order)
        self.reservation_order = pd.Series()
        self.exist_reservation_order = False

    def reserve_order(self, allocation: pd.Series):
        self.reservation_order = allocation
        self.exist_reservation_order = True

    def log_event(self, msg: str):
        self.event_log.loc[len(self.event_log)] = [self.date, msg]

    def is_rebalancing_day(self, next_n_trading_days):
        today = self.date

        if today == self.start_date:
            if today in self.rebalancing_days:
                return True
            else:
                return False

        target_date_index = self.trading_days.index(today) + next_n_trading_days
        if target_date_index >= len(self.trading_days):
            return False

        target_date = self.trading_days[target_date_index]
        if target_date in self.rebalancing_days:
            return True
        else:
            return False

    def on_start_of_day(self):
        pass

    def on_end_of_day(self):
        self.update_portfolio_value()
        self.log_portfolio_value()

    def on_end_of_algorithm(self):
        self.portfolio_log = pd.concat(self.daily_log_list, axis=1).T

    def log_portfolio_value(self):
        port_value = self.portfolio.get_total_portfolio_value()
        cash = self.portfolio.cash
        series = pd.Series(self.portfolio.security_holding)
        series.index = [ticker + "_amount" for ticker in series.index]
        series.name = self.date

        series.loc["port_value"] = port_value
        series.loc["cash"] = cash
        self.daily_log_list.append(series)

    def update_portfolio_value(self):
        self.portfolio.update_holdings_value(self.date, self.market_df_pct_change)

    def get_daily_return(self):
        return self.portfolio_log['port_value'].pct_change()

    def get_result(self):
        portfolio_log = self.portfolio_log
        event_log = self.event_log
        result = self.get_result_from_portfolio_log(portfolio_log)
        result['event_log'] = event_log
        return result

    def get_result_from_portfolio_log(self, portfolio_log):
        port_col_name = self.name_for_result_column
        portfolio_log = portfolio_log.rename(columns={'port_value': port_col_name})

        performance = calc_performance_from_value_history(portfolio_log[port_col_name])
        performance_summary = performance.get('performance_summary')
        performance_summary.name = port_col_name

        annual_summary = performance.get('annual_summary')

        multi_index = pd.MultiIndex.from_product([[port_col_name], annual_summary.columns])
        annual_summary = pd.DataFrame(annual_summary.values, columns=multi_index, index=annual_summary.index.tolist())
        performance['annual_summary'] = annual_summary

        rebalancing_weight = self.order_weight_df

        port_drawdown = performance.get("drawdown")
        portfolio_log = pd.concat([portfolio_log, port_drawdown], axis=1)
        performance["portfolio_log"] = portfolio_log

        result = dict()
        result['performance'] = performance
        result['rebalancing_weight'] = rebalancing_weight
        return result

    def selected_asset_counts_to_csv(self, file_name=None, folder_path=None):
        if file_name is None:
            file_name = self.name

        if folder_path is None:
            path = f"./{file_name}.csv"
        else:
            path = f"./{folder_path}/{file_name}.csv"

        self.selected_asset_counts.to_csv(path, encoding='cp949')
