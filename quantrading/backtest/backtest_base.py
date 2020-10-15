from abc import ABCMeta, abstractmethod
from .simulation_result_utils import save_simulation_result_to_excel_file
from .. import utils
import plotly.graph_objects as go
from .trading_day import TradingDay
from .simulation_result_utils import calc_performance_from_value_history
import pandas as pd
from .portfolio import Portfolio


class BackTestBase(metaclass=ABCMeta):
    def __init__(self, **kwargs):
        self.name = kwargs.get("name")
        self.name_for_result_column = kwargs.get('name_for_result_column', 'port_value')
        self.start_date = kwargs.get("start_date")
        self.end_date = kwargs.get("end_date")
        self.date = self.start_date
        self.rebalancing_periodic = kwargs.get("rebalancing_periodic", 'monthly')
        self.rebalancing_moment = kwargs.get("rebalancing_moment", 'first')
        self.close_day_policy = kwargs.get("close_day_policy", "after")

        self.market_close_df = kwargs.get("market_close_df")
        self.benchmark_ticker = kwargs.get("benchmark_ticker", None)

        self.portfolio = Portfolio(**kwargs)
        self.portfolio_log = pd.DataFrame(columns=['port_value', 'cash'])

        self.rebalancing_mp_weight = pd.DataFrame()
        self._order_weight_df = pd.DataFrame()
        self._turnover_weight_series = pd.Series()
        self.port_weight_series_list = []
        self.port_weight_df = None
        self.event_log = pd.DataFrame(columns=["datetime", "log"])

        # set trading days & rebalancing days
        trading_day = TradingDay(self.market_close_df.index.to_series().reset_index(drop=True),
                                 close_day_policy=self.close_day_policy)
        self.trading_days = trading_day.get_trading_day_list(self.start_date, self.end_date).to_list()
        self.rebalancing_days = trading_day.get_rebalancing_days(
            self.start_date,
            self.end_date,
            self.rebalancing_periodic,
            self.rebalancing_moment
        )

        self.portfolio_rebalancing_factor_history_list = []

        if self.benchmark_ticker is not None:
            masking = (self.market_close_df.index >= self.start_date) & (self.market_close_df.index <= self.end_date)
            self.benchmark_value_series = self.market_close_df.pct_change()[masking][self.benchmark_ticker].add(
                1).cumprod() * 100
            self.benchmark_value_series.name = self.benchmark_ticker
        else:
            self.benchmark_value_series = None

    def get_result(self):
        portfolio_log = self.portfolio_log
        event_log = self.event_log
        result = self.get_result_from_portfolio_log(portfolio_log)

        if len(self.portfolio_rebalancing_factor_history_list) > 0:
            rebalancing_factor_history_df = pd.concat(self.portfolio_rebalancing_factor_history_list, axis=1)
        else:
            rebalancing_factor_history_df = pd.DataFrame()

        result['rebalancing_factor_history'] = rebalancing_factor_history_df
        result['event_log'] = event_log
        return result

    def _log_port_weight(self):
        port_weight_series = self.portfolio.get_allocations()
        port_weight_row = port_weight_series.to_frame(self.date).T
        self.port_weight_series_list.append(port_weight_row)

    def _is_trading_day(self):
        today = self.date
        if today in self.trading_days:
            return True
        else:
            return False

    def add_to_rebalancing_factor_history(self, data: pd.Series or pd.DataFrame):
        self.portfolio_rebalancing_factor_history_list.append(data)

    @abstractmethod
    def get_result_from_portfolio_log(self, portfolio_log) -> dict:
        pass

    def print_result_log(self, display_image=False):
        result: dict = self.get_result()

        performance: dict = result.get('performance', None)
        if performance is not None:
            annual_summary = performance.get("annual_summary", None)
            portfolio_log = performance.get("portfolio_log", None)

            if self.benchmark_ticker is not None and portfolio_log is not None:
                print(portfolio_log)
                benchmark_performance = calc_performance_from_value_history(portfolio_log[self.benchmark_ticker])
            else:
                benchmark_performance = None

            if annual_summary is not None:
                if benchmark_performance is not None:
                    benchmark_annual_summary = benchmark_performance['annual_summary']
                    benchmark_annual_summary.name = self.benchmark_ticker

                    multi_index = pd.MultiIndex.from_product(
                        [[self.benchmark_ticker], benchmark_annual_summary.columns])
                    benchmark_annual_summary = pd.DataFrame(benchmark_annual_summary.values, columns=multi_index,
                                                            index=benchmark_annual_summary.index.tolist())

                    print(
                        pd.concat([annual_summary, benchmark_annual_summary], axis=1).apply(lambda x: x.round(4) * 100))
                else:
                    print(annual_summary)

            performance_summary = performance.get("performance_summary", None)
            if performance_summary is not None:
                if benchmark_performance is not None:
                    benchmark_performance_summary = benchmark_performance['performance_summary']
                    benchmark_performance_summary.name = self.benchmark_ticker
                    print(pd.concat([performance_summary, benchmark_performance_summary], axis=1))
                else:
                    print(performance_summary)

            if performance is not None:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=portfolio_log.index,
                    y=portfolio_log[self.name_for_result_column],
                    name=self.name_for_result_column
                ))

                if self.benchmark_ticker is not None:
                    fig.add_trace(go.Scatter(
                        x=portfolio_log.index,
                        y=portfolio_log[self.benchmark_ticker],
                        name=self.benchmark_ticker
                    ))

                if display_image:
                    fig.show()

        asset_weight = result.get("asset_weight", None)
        if asset_weight is not None:
            x = asset_weight.index
            fig = go.Figure()
            for i, ticker in enumerate(asset_weight.columns):
                if i == 0:
                    fig.add_trace(go.Scatter(
                        x=x,
                        y=asset_weight[ticker],
                        mode='lines',
                        stackgroup='one',
                        name=ticker,
                        groupnorm='percent'
                    ))
                else:
                    fig.add_trace(go.Scatter(
                        x=x,
                        y=asset_weight[ticker],
                        mode='lines',
                        stackgroup='one',
                        name=ticker,
                    ))

            fig.update_layout(
                showlegend=True,
                yaxis=dict(
                    type='linear',
                    range=[1, 100],
                    ticksuffix='%'))
            if display_image:
                fig.show()

    def result_to_excel(self, file_name=None, folder_path=None):
        if file_name is None:
            file_name = self.name

        if folder_path is None:
            path = f"./{file_name}.xlsx"
        else:
            utils.make_folder(f'./{folder_path}')
            path = f"./{folder_path}/{file_name}.xlsx"

        result = self.get_result()
        save_simulation_result_to_excel_file(result, path)

    def port_value_to_csv(self, file_name=None, folder_path=None):
        if file_name is None:
            file_name = self.name

        if folder_path is None:
            path = f"./{file_name}.csv"
        else:
            path = f"./{folder_path}/{file_name}.csv"

        result = self.get_result()
        performance = result['performance']
        portfolio_log = performance["portfolio_log"]
        port_value = portfolio_log['port_value']
        port_value.to_csv(path, encoding='cp949')
