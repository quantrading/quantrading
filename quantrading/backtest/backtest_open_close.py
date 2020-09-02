import pandas as pd
from datetime import timedelta
from .portfolio import Portfolio
from .simulation_result_utils import calc_performance_from_value_history
from .trading_day import TradingDay
from datetime import datetime
import numpy as np
from .backtest_base import BackTestBase


class OpenCloseStrategy(BackTestBase):
    """
    기존 Strategy Class 에 open price 고려 로직을 추가하여, 시가, 종가 데이터로 시뮬레이션
    거래는 시가 데이터 기준, 가격 평가는 종가 데이터 기준.
    보유자산은 quantity 가 아닌, amount 로 가정
    """

    def __init__(self, **kwargs):
        self.name = kwargs.get("name")
        self.start_date = kwargs.get("start_date")
        self.end_date = kwargs.get("end_date")
        self.market_open_price_df = kwargs.get("market_open_price_df")
        self.market_close_df = kwargs.get("market_close_df")
        self.rebalancing_periodic = kwargs.get("rebalancing_periodic", 'monthly')
        self.rebalancing_moment = kwargs.get("rebalancing_moment", 'first')
        self.close_day_policy = kwargs.get("close_day_policy", "after")
        self.name_for_result_column = kwargs.get('name_for_result_column', '전략')
        self.buy_delay = kwargs.get("buy_delay", 0)
        self.sell_delay = kwargs.get("sell_delay", 0)
        self.default_irregular_cool_time = kwargs.get("default_irregular_cool_time", 7)

        # set trading days & rebalancing days
        trading_day = TradingDay(self.market_close_df.index.to_series().reset_index(drop=True),
                                 close_day_policy=self.close_day_policy)
        self.trading_days = trading_day.get_trading_day_list(self.start_date, self.end_date).to_list()
        self.rebalancing_days = trading_day.get_rebalancing_days(self.start_date, self.end_date,
                                                                 self.rebalancing_periodic, self.rebalancing_moment)
        self.date = self.start_date
        # 당일 시가와 당일 종가 비교
        self.market_intraday_pct_change = self.market_close_df.divide(self.market_open_price_df) - 1

        # 시가는 전일 종가와 비교
        self.market_open_df_pct_change = self.market_open_price_df.divide(self.market_close_df.shift(1)) - 1
        self.portfolio = Portfolio()
        self.portfolio_log = pd.DataFrame()
        self.rebalancing_mp_weight = pd.DataFrame()
        self.order_weight_df = pd.DataFrame()
        self.event_log = pd.DataFrame(columns=["datetime", "log"])
        self.reservation_order = {}
        self.selected_asset_counts = pd.Series()
        self.irregular_rebalancing = False
        self.irregular_cool_time = 0
        self.portfolio_log_series_df = pd.DataFrame()

    def initialize(self):
        pass

    def on_data(self):
        pass

    def run(self):
        """
        1. 시작

        2. 거래일?
            2-1. on_start_of_day()

            2-2. 예약 주문 있나?
                2-2-1. execute_reservation_order()

            2-3. 오늘 리밸런싱 날인가?
                2-3-1. on_d
                ata()

            2-4. on_end_of_day()

        3. on_end_of_algorithm()
        """
        self.initialize()
        end_date = self.end_date
        while self.date <= end_date:
            if self.is_trading_day():

                self.on_start_of_day()

                if self.is_rebalancing_day():
                    self.on_data()

                self.update_portfolio_value('open')

                if self.date in self.reservation_order.keys():
                    self.execute_reservation_order()

                self.on_end_of_day()
            self.date += timedelta(days=1)
        self.on_end_of_algorithm()

    def execute_reservation_order(self):
        today_reserved_order: pd.Series = self.reservation_order.get(self.date)

        downsize_ratio = self.evaluate_buy_ability(today_reserved_order)

        for ticker, amount_delta in today_reserved_order.iteritems():
            if np.isneginf(amount_delta):
                amount_delta = -self.portfolio.security_holding.get(ticker, 0)
                today_reserved_order[ticker] = amount_delta

            if amount_delta == 0:
                continue

            if amount_delta > 0:
                if downsize_ratio < 1:
                    amount_delta *= downsize_ratio
                self.portfolio.buy(ticker, amount_delta)
            else:
                if self.portfolio.security_holding.get(ticker, 0) == 0:
                    continue

                self.portfolio.sell(ticker, -amount_delta)

        port_value = self.portfolio.get_total_portfolio_value()
        reservation_order_series = today_reserved_order / port_value
        reservation_order_series.name = self.date
        self.order_weight_df = pd.concat([self.order_weight_df, reservation_order_series.to_frame().T], axis=0)

    def reserve_order(self, amount_series: pd.Series, order_type: str):
        assert order_type in ["buy", "sell"]

        if order_type == "buy":
            date = self.get_date(delta=self.buy_delay)
        else:
            date = self.get_date(delta=self.sell_delay)

        if date in self.reservation_order.keys():
            prev_amount_series = self.reservation_order[date]
            self.reservation_order[date] = prev_amount_series.add(amount_series, fill_value=0)
        else:
            self.reservation_order[date] = amount_series

    def evaluate_buy_ability(self, order_series: pd.Series) -> float:
        cash = self.portfolio.cash
        accumulated_amount = 0
        for ticker, amount_delta in order_series.iteritems():
            if amount_delta > 0:
                accumulated_amount += amount_delta
        if accumulated_amount == 0:
            return 1
        return cash / accumulated_amount

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

        if self.irregular_rebalancing:
            self.irregular_cool_time -= 1
            if self.irregular_cool_time <= 0:
                self.irregular_cool_time = self.default_irregular_cool_time
                self.irregular_rebalancing = False
                return True
            else:
                return False

        if today in self.rebalancing_days:
            return True
        else:
            return False

    def on_start_of_day(self):
        pass

    def on_end_of_day(self):
        self.update_portfolio_value('close')
        self.log_portfolio_value()

    def on_end_of_algorithm(self):
        pass

    def get_date(self, delta=0):
        cur_date_idx = self.trading_days.index(self.date)

        new_date_idx = cur_date_idx + delta
        if new_date_idx >= len(self.trading_days):
            return self.trading_days[-1]
        else:
            return self.trading_days[cur_date_idx + delta]

    def log_portfolio_value(self):
        port_value = self.portfolio.get_total_portfolio_value()
        cash = self.portfolio.cash

        self.portfolio_log.loc[self.date, "port_value"] = port_value
        self.portfolio_log.loc[self.date, "cash"] = cash

        for ticker, amount in self.portfolio.security_holding.items():
            self.portfolio_log.loc[self.date, ticker + "_amount"] = amount

    def update_portfolio_value(self, price_type):
        assert price_type in ['open', 'close']
        if price_type == 'open':
            self.portfolio.update_holdings_value(self.date, self.market_open_df_pct_change)
        else:
            self.portfolio.update_holdings_value(self.date, self.market_intraday_pct_change)

    def get_daily_return(self):
        return self.portfolio_log['port_value'].pct_change()

    def add_series_to_portfolio_log(self, series: pd.Series):
        self.portfolio_log_series_df = pd.concat([self.portfolio_log_series_df, series], axis=1)

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

        port_drawdown = performance.get("drawdown")
        if len(self.portfolio_log_series_df) > 0:
            portfolio_index = portfolio_log.index
            portfolio_log = pd.concat([portfolio_log, port_drawdown, self.portfolio_log_series_df], axis=1)
            portfolio_log = portfolio_log.reindex(portfolio_index)
        else:
            portfolio_log = pd.concat([portfolio_log, port_drawdown], axis=1)
        performance["portfolio_log"] = portfolio_log

        result = dict()
        result['performance'] = performance
        result['rebalancing_weight'] = self.rebalancing_mp_weight
        result['order_weight'] = self.order_weight_df
        return result
