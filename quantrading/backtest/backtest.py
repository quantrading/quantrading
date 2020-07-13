import pandas as pd
from datetime import datetime, timedelta
from .portfolio import Portfolio
from .trading_day import TradingDay
import empyrical
from .. import performance_utils


class Strategy:
    def __init__(self, **kwargs):
        self.name = kwargs.get("name")
        self.start_date = kwargs.get("start_date")
        self.end_date = kwargs.get("end_date")
        self.date = self.start_date

        self.market_df = kwargs.get("market_df")

        # set trading days & rebalancing days
        trading_day = TradingDay(self.market_df.index.to_series().reset_index(drop=True))
        self.trading_days = trading_day.get_trading_day_list(self.start_date, self.end_date).to_list()

        self.rebalancing_periodic = kwargs.get("rebalancing_periodic")
        self.rebalancing_moment = kwargs.get("rebalancing_moment")
        self.rebalancing_days = trading_day.get_rebalancing_days(self.start_date, self.end_date,
                                                                 self.rebalancing_periodic, self.rebalancing_moment)

        self.portfolio = Portfolio()
        self.portfolio_log = pd.DataFrame()
        self.simulation_status = {}
        self.simulation_result = {}
        self.event_log = pd.DataFrame(columns=["datetime", "log"])
        self.exist_reservation_order = False
        self.reservation_order = pd.Series()
        self.selected_asset_counts = pd.Series()

    def initialize(self):
        pass

    def on_data(self):
        pass

    def run(self):
        self.initialize()

        end_date = self.end_date
        while self.date <= end_date:
            if self.is_trading_day():
                if self.exist_reservation_order:
                    self.execute_reservation_order()
                if self.is_rebalancing_day():
                    self.on_data()
                self.on_end_of_day()
            self.date += timedelta(days=1)
        self.on_end_of_algorithm()

    def execute_reservation_order(self):
        self.portfolio.set_allocations(self.reservation_order)
        self.selected_asset_counts.loc[self.date] = len(self.reservation_order)
        self.reservation_order = pd.Series()
        self.exist_reservation_order = False

    def reserve_order(self, allocation: pd.Series):
        self.reservation_order = allocation
        self.exist_reservation_order = True

    def log_event(self, msg: str):
        self.event_log.loc[len(self.event_log)] = [self.date, msg]

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

    def on_start_of_day(self):
        pass

    def on_end_of_day(self):
        pass

    def on_end_of_algorithm(self):
        pass

    def log_portfolio_value(self):
        port_value = self.portfolio.get_total_portfolio_value()
        cash = self.portfolio.cash

        self.portfolio_log.loc[self.date, "port_value"] = port_value
        self.portfolio_log.loc[self.date, "cash"] = cash

        for ticker, amount in self.portfolio.security_holding.items():
            self.portfolio_log.loc[self.date, ticker + "_amount"] = amount

    def update_portfolio_value(self):
        self.portfolio.update_holdings_value(self.date, self.market_df_pct_change)

    def set_holdings(self, ticker: str, weight: float):
        self.portfolio.set_weight(ticker, weight)

    def set_start_date(self, year: int, month: int, day: int):
        self.start_date = datetime(year, month, day)

    def set_end_date(self, year: int, month: int, day: int):
        date = datetime(year, month, day)
        assert date >= self.start_date
        self.end_date = date

    def set_rebalancing_days(self, date_list: list):
        self.rebalancing_days = [*date_list]

    def liquidate(self, ticker: str):
        self.set_holdings(ticker, 0)

    def get_daily_return(self):
        return self.portfolio_log['port_value'].pct_change()

    def get_result(self):
        portfolio_log = self.portfolio_log
        event_log = self.event_log
        result = self.get_result_from_portfolio_log(portfolio_log)
        result['event_log'] = event_log
        return result

    def get_result_from_portfolio_log(self, portfolio_log):
        performance = calc_performance_from_value_history(portfolio_log["port_value"])
        portfolio_weight = portfolio_log.divide(portfolio_log['port_value'], axis=0)
        rebalancing_weight = portfolio_weight.loc[self.rebalancing_days]

        port_drawdown = performance.get("drawdown")
        portfolio_log = pd.concat([portfolio_log, port_drawdown], axis=1)
        performance["portfolio_log"] = portfolio_log

        result = dict()
        result['performance'] = performance
        result['rebalancing_weight'] = rebalancing_weight
        return result

    def result_to_excel(self, file_name=None, folder_path=None):
        if file_name is None:
            file_name = self.name

        if folder_path is None:
            path = f"./{file_name}.xlsx"
        else:
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

    def selected_asset_counts_to_csv(self, file_name=None, folder_path=None):
        if file_name is None:
            file_name = self.name

        if folder_path is None:
            path = f"./{file_name}.csv"
        else:
            path = f"./{folder_path}/{file_name}.csv"

        self.selected_asset_counts.to_csv(path, encoding='cp949')


def save_simulation_result_to_excel_file(result: dict, path: str) -> None:
    performance = result['performance']
    event_log = result['event_log']
    rebalancing_weight = result['rebalancing_weight']

    portfolio_log = performance["portfolio_log"]
    monthly_returns = performance["monthly_returns"]
    annual_summary = performance["annual_summary"]
    performance_summary = performance["performance_summary"]
    with pd.ExcelWriter(path, datetime_format="yyyy-mm-dd") as writer:
        portfolio_log.to_excel(writer, sheet_name="portfolio log")
        monthly_returns.to_excel(writer, sheet_name="월별수익률")
        annual_summary.to_excel(writer, sheet_name="연도별 요약")
        performance_summary.to_excel(writer, sheet_name="요약")
        event_log.to_excel(writer, sheet_name="event log")
        rebalancing_weight.to_excel(writer, sheet_name="리밸런싱 비중")


def calc_performance_from_value_history(daily_values: pd.Series) -> dict:
    daily_returns = daily_values.pct_change()
    final_returns = daily_values.iloc[-1] / 100 - 1

    monthly_returns = empyrical.aggregate_returns(daily_returns, "monthly")
    yearly_returns = empyrical.aggregate_returns(daily_returns, "yearly")
    performance_summary = performance_utils.get_performance_summary(daily_returns, final_returns)

    annual_std = performance_utils.get_annual_std(daily_returns)
    annual_summary = pd.concat([yearly_returns, annual_std], axis=1)
    annual_summary.columns = ["수익률", "변동성"]

    cumulative_returns = performance_utils.convert_values_to_cumulative_returns(daily_values)
    drawdown = performance_utils.get_draw_down(cumulative_returns)

    return {
        "monthly_returns": monthly_returns,
        "yearly_returns": yearly_returns,
        "performance_summary": performance_summary,
        "annual_summary": annual_summary,
        "drawdown": drawdown
    }
