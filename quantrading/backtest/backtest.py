import pandas as pd
from .simulation_result_utils import calc_performance_from_value_history
from .backtest_base import BackTestBase
from datetime import timedelta


class Strategy(BackTestBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.market_df_pct_change = self.market_close_df.pct_change()

        self.simulation_status = {}
        self.simulation_result = {}
        self.exist_reservation_order = False
        self.reservation_order = pd.Series()
        self.selected_asset_counts = pd.Series()
        self.daily_log_list = []
        self.returns_until_next_rebal_series = None

    def initialize(self):
        pass

    def on_data(self):
        pass

    def run(self):
        self.initialize()
        end_date = self.end_date
        while self.date <= end_date:
            if self._is_trading_day():
                self.on_start_of_day()
                if self.exist_reservation_order:
                    self.execute_reservation_order()
                if self.is_rebalancing_day():
                    self.on_data()
                self.on_end_of_day()
            self.date += timedelta(days=1)
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

    def is_rebalancing_day(self):
        today = self.date
        if today in self.rebalancing_days:
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
        returns_until_next_rebal = (
            self.portfolio_log["port_value"]
                .reindex(self.rebalancing_days)
                .pct_change()
                .shift(-1)
                .dropna()
        )
        returns_until_next_rebal.name = self.name_for_result_column
        self.returns_until_next_rebal_series = returns_until_next_rebal

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

        port_drawdown = performance.get("drawdown")
        portfolio_log = pd.concat([portfolio_log, port_drawdown], axis=1)

        if self.benchmark_value_series is not None:
            portfolio_log = pd.concat([portfolio_log, self.benchmark_value_series], axis=1)

        performance["portfolio_log"] = portfolio_log
        performance["returns_until_next_rebal"] = self.returns_until_next_rebal_series

        rebalancing_weight = self.order_weight_df

        asset_list = []
        for column in portfolio_log.columns:
            if column == "cash" or '_amount' in column:
                asset_list.append(column)
        asset_weight_df = self.portfolio_log[asset_list]

        result = dict()
        result['performance'] = performance
        result['rebalancing_weight'] = rebalancing_weight
        result['asset_weight'] = asset_weight_df
        return result

    def selected_asset_counts_to_csv(self, file_name=None, folder_path=None):
        if file_name is None:
            file_name = self.name

        if folder_path is None:
            path = f"./{file_name}.csv"
        else:
            path = f"./{folder_path}/{file_name}.csv"

        self.selected_asset_counts.to_csv(path, encoding='cp949')
