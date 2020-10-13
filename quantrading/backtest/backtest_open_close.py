import pandas as pd
from datetime import timedelta
from .simulation_result_utils import calc_performance_from_value_history
import numpy as np
from .backtest_base import BackTestBase


class OpenCloseStrategy(BackTestBase):
    """
    시가, 종가 데이터로 시뮬레이션
    거래는 시가 데이터 기준, 가격 평가는 종가 데이터 기준.
    보유자산은 quantity 가 아닌, amount 로 가정

    API list
    initialize()
    on_start_of_day()
    on_data()
    on_irregular_rebalacning()
    get_available_data()
    on_end_of_day()
    on_end_of_algorithm()
    get_base_weight()
    set_allocation()
    log_event()
    add_series_to_portfolio_log()
    get_result_from_portfolio_log()
    run()
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__market_open_price_df = kwargs.get("market_open_price_df")
        self.__index_df = kwargs.get("index_df", pd.DataFrame())
        self.__buy_delay = kwargs.get("buy_delay", 0)
        self.__sell_delay = kwargs.get("sell_delay", 0)
        self.__default_irregular_cool_time = kwargs.get("default_irregular_cool_time", 7)

        self.__custom_mp_option = kwargs.get("custom_mp_option", False)
        if self.__custom_mp_option:
            self.__custom_mp_start_date = kwargs.get("custom_mp_start_date")
            self.__custom_mp = kwargs.get("custom_mp")
            self.__custom_mp_sell_delay = kwargs.get("custom_mp_sell_delay", 0)
            self.__custom_mp_buy_delay = kwargs.get("custom_mp_buy_delay", 1)
            self.__custom_liquidate_date = kwargs.get("custom_liquidate_date")
        else:
            self.__custom_mp_start_date = None
            self.__custom_mp = None

        # 당일 시가와 당일 종가 비교
        self.__market_intraday_pct_change = self.market_close_df.divide(self.__market_open_price_df) - 1

        # 시가는 전일 종가와 비교
        self.__market_open_df_pct_change = self.__market_open_price_df.divide(self.market_close_df.shift(1)) - 1

        self.__reservation_order = {}
        self.__irregular_rebalancing = False
        self.__irregular_cool_time = 0
        self.portfolio_log_series_df = pd.DataFrame()

        self.__temp_allocation_series = pd.Series()

        self.__simulation_info = {}
        self.__last_day_portfolio_value = 100

    def initialize(self):
        pass

    def on_data(self):
        pass

    def on_irregular_rebalacning(self):
        pass

    def irregular_rebalacning_trigger(self):
        self.__irregular_rebalancing = True

    def run(self):
        self.initialize()
        end_date = self.end_date
        while self.date <= end_date:
            if self._is_trading_day():
                self.__run_at_start_of_day()
                if self.__is_custom_rebalancing_day():
                    if self.__is_custom_liquidate_date():
                        self.__run_at_custom_liquidate_date()
                    else:
                        self.__custom_mp_rebalancing()
                else:
                    if self.__is_rebalancing_day():
                        self.on_data()
                    if self.__is_irregular_rebalancing_day():
                        self.on_irregular_rebalacning()
                self.__reserve_allocation_order()
                self.__update_portfolio_value('open')
                if self.date in self.__reservation_order.keys():
                    self.__execute_reservation_order()

                self.__run_at_end_of_day()
            self.date += timedelta(days=1)
        self.__run_at_end_of_algorithm()

    def on_start_of_day(self):
        pass

    def on_end_of_day(self):
        pass

    def on_end_of_algorithm(self):
        pass

    def get_base_weight(self) -> pd.Series:
        if self.__is_rebalancing_day():
            return self.__temp_allocation_series
        else:
            return self.portfolio.get_allocations()

    def set_allocation(self, allocation_dict: dict, sum_should_one=True):
        allocation_series = pd.Series(allocation_dict)
        allocation_series.name = self.date
        self.__temp_allocation_series = allocation_series

        if sum_should_one:
            assert self.__temp_allocation_series.sum() == 1, "비중의 합이 1이 되어야 합니다. 비중이 남으면 'cash' 값 명시"

    def log_event(self, msg: str):
        self.event_log.loc[len(self.event_log)] = [self.date, msg]

    def get_date(self, delta=0):
        cur_date_idx = self.trading_days.index(self.date)

        new_date_idx = cur_date_idx + delta
        if new_date_idx >= len(self.trading_days):
            return self.trading_days[-1]
        else:
            return self.trading_days[cur_date_idx + delta]

    def get_available_data(self, exclude_today_data=True) -> dict:
        today_date = self.date

        if exclude_today_data:
            sliced_market_close_df = self.market_close_df.loc[self.market_close_df.index < today_date]
            sliced_market_open_price_df = self.__market_open_price_df.loc[
                self.__market_open_price_df.index < today_date]
            sliced_index_df = self.__index_df.loc[self.__index_df.index < today_date]
        else:
            sliced_market_close_df = self.market_close_df.loc[self.market_close_df.index <= today_date]
            sliced_market_open_price_df = self.__market_open_price_df.loc[
                self.__market_open_price_df.index <= today_date]
            sliced_index_df = self.__index_df.loc[self.__index_df.index <= today_date]

        data_store = {
            "market_close_df": sliced_market_close_df,
            "market_open_price_df": sliced_market_open_price_df,
            "index_df": sliced_index_df
        }

        return data_store

    def __run_at_end_of_day(self):
        self.__update_portfolio_value('close')
        self.__log_portfolio_value()
        self._log_port_weight()
        self.__last_day_portfolio_value = self.portfolio.get_total_portfolio_value()
        self.on_end_of_day()

    def __run_at_end_of_algorithm(self):
        self.port_weight_df = pd.concat(self.port_weight_series_list, axis=0)

        simulation_range_time_delta = self.end_date - self.start_date
        years_delta = simulation_range_time_delta.days / 365.25
        self.__simulation_info['years_delta'] = years_delta

        self.on_end_of_algorithm()

    def __run_at_start_of_day(self):
        self.on_start_of_day()

    def __is_irregular_rebalancing_day(self) -> bool:
        return self.__irregular_rebalancing

    def __is_custom_liquidate_date(self) -> bool:
        return self.__custom_liquidate_date == self.date

    def __run_at_custom_liquidate_date(self):
        self.__sell_delay = 0
        self.__buy_delay = 0
        allocation = {
            'cash': 1
        }
        self.set_allocation(allocation)

    def __is_custom_rebalancing_day(self) -> bool:
        return self.__custom_mp_option and self.__custom_mp_start_date <= self.date

    def __custom_mp_rebalancing(self):
        """
        custom_mp_rebalancing 시작시, 
        sell delay, buy delay 수정
        :return: 
        """
        self.__sell_delay = self.__custom_mp_sell_delay
        self.__buy_delay = self.__custom_mp_buy_delay

        today_date = self.date

        if today_date in self.__custom_mp.index:
            allocation = self.__custom_mp.loc[today_date].to_dict()
            print(today_date, allocation)
        else:
            return
        self.set_allocation(allocation)

    def __reserve_allocation_order(self):
        if len(self.__temp_allocation_series) == 0:
            return

        allocation_series = self.__temp_allocation_series
        self.rebalancing_mp_weight = pd.concat([self.rebalancing_mp_weight, allocation_series.to_frame().T], axis=0)
        amount_delta_series = self.portfolio.get_amount_delta(allocation_series)
        amount_delta_series.pop('cash')
        sell_amount_series = amount_delta_series[amount_delta_series < 0]
        buy_amount_series = amount_delta_series[amount_delta_series > 0]

        self.__reserve_order(sell_amount_series, "sell")
        self.__reserve_order(buy_amount_series, "buy")
        self.__temp_allocation_series = pd.Series()

    def __execute_reservation_order(self):
        today_reserved_order: pd.Series = self.__reservation_order.get(self.date)

        buy_series = pd.Series()
        sell_series = pd.Series()
        for ticker, amount_delta in today_reserved_order.iteritems():
            if np.isneginf(amount_delta):
                amount_delta = -self.portfolio.security_holding.get(ticker, 0)
                today_reserved_order[ticker] = amount_delta

            if amount_delta == 0:
                continue

            if amount_delta > 0:
                buy_series.loc[ticker] = amount_delta
            else:
                if self.portfolio.security_holding.get(ticker, 0) == 0:
                    continue
                sell_series.loc[ticker] = -amount_delta

        for ticker, amount in sell_series.iteritems():
            self.portfolio.sell(ticker, amount)

        downsize_ratio = self.__evaluate_buy_ability(buy_series)

        for ticker, amount in buy_series.iteritems():
            if downsize_ratio < 1:
                amount *= downsize_ratio
            self.portfolio.buy(ticker, amount)

        port_value = self.__last_day_portfolio_value
        reservation_order_series = today_reserved_order / port_value
        reservation_order_series.name = self.date
        turnover_weight = reservation_order_series.abs().sum()
        self._order_weight_df = pd.concat([self._order_weight_df, reservation_order_series.to_frame().T], axis=0)
        self._turnover_weight_series.loc[self.date] = turnover_weight

    def __reserve_order(self, amount_series: pd.Series, order_type: str):
        assert order_type in ["buy", "sell"]

        if order_type == "buy":
            date = self.get_date(delta=self.__buy_delay)
        else:
            date = self.get_date(delta=self.__sell_delay)

        if date in self.__reservation_order.keys():
            prev_amount_series = self.__reservation_order[date]
            self.__reservation_order[date] = prev_amount_series.add(amount_series, fill_value=0)
        else:
            self.__reservation_order[date] = amount_series

    def __evaluate_buy_ability(self, order_series: pd.Series) -> float:
        cash = self.portfolio.cash
        accumulated_amount = 0
        for ticker, amount_delta in order_series.iteritems():
            if amount_delta > 0:
                accumulated_amount += amount_delta
        if accumulated_amount == 0:
            return 1
        return cash / accumulated_amount

    def __is_rebalancing_day(self):
        today = self.date

        if self.__irregular_rebalancing:
            self.__irregular_cool_time -= 1
            if self.__irregular_cool_time <= 0:
                self.__irregular_cool_time = self.__default_irregular_cool_time
                self.__irregular_rebalancing = False
                return True
            else:
                return False

        if today in self.rebalancing_days:
            return True
        else:
            return False

    def __log_portfolio_value(self):
        port_value = self.portfolio.get_total_portfolio_value()
        cash = self.portfolio.cash

        self.portfolio_log.loc[self.date, "port_value"] = port_value
        self.portfolio_log.loc[self.date, "cash"] = cash

        for ticker, amount in self.portfolio.security_holding.items():
            self.portfolio_log.loc[self.date, ticker + "_amount"] = amount

    def __update_portfolio_value(self, price_type):
        assert price_type in ['open', 'close']
        if price_type == 'open':
            self.portfolio.update_holdings_value(self.date, self.__market_open_df_pct_change)
        else:
            self.portfolio.update_holdings_value(self.date, self.__market_intraday_pct_change)

    def get_daily_return(self):
        return self.portfolio_log['port_value'].pct_change()

    def add_series_to_portfolio_log(self, series: pd.Series):
        self.portfolio_log_series_df = pd.concat([self.portfolio_log_series_df, series], axis=1)

    def get_result_from_portfolio_log(self, portfolio_log):
        port_col_name = self.name_for_result_column
        portfolio_log = portfolio_log.rename(columns={'port_value': port_col_name})

        performance = calc_performance_from_value_history(portfolio_log[port_col_name])
        performance_summary = performance.get('performance_summary')
        performance_summary.name = port_col_name
        performance_summary.loc["연회전율"] = (self._turnover_weight_series.sum() - 1) / self.__simulation_info[
            'years_delta']

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

        if self.benchmark_value_series is not None:
            portfolio_log = pd.concat([portfolio_log, self.benchmark_value_series], axis=1)

        performance["portfolio_log"] = portfolio_log

        asset_list = []
        for column in portfolio_log.columns:
            if column == "cash" or '_amount' in column:
                asset_list.append(column)
        asset_weight_df = self.portfolio_log[asset_list]

        result = dict()
        result['performance'] = performance
        result['rebalancing_weight'] = self.rebalancing_mp_weight
        result['order_weight'] = self._order_weight_df
        result['turnover_weight'] = self._turnover_weight_series
        result['asset_weight'] = asset_weight_df
        result['portfolio_weight_history'] = self.port_weight_df.fillna(0)
        return result
