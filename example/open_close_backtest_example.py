import quantrading as qt
from datetime import datetime
import pandas as pd


class MyStrategy(qt.OpenCloseStrategy):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def initialize(self):
        initial_weight = {
            'MSCI_WORLD_ACWI': 0.8,
            'IEF_BOND_7_10_INDEX': 0.2
        }
        initial_weight_series = pd.Series(initial_weight)
        self.reserve_order(initial_weight_series, datetime(2005, 1, 3))

    def on_data(self):
        today_date = self.date

        allocation = {
            'MSCI_WORLD_ACWI': 0.8,
            'IEF_BOND_7_10_INDEX': 0.2
        }

        print(today_date, allocation)

        allocation_series = pd.Series(allocation)

        allocation_series.name = self.date
        self.rebalancing_mp_weight = pd.concat([self.rebalancing_mp_weight, allocation_series.to_frame().T], axis=0)

        amount_delta_series = self.portfolio.get_amount_delta(allocation_series)

        amount_delta_series.pop('cash')
        sell_amount_series = amount_delta_series[amount_delta_series < 0]
        buy_amount_series = amount_delta_series[amount_delta_series > 0]

        _1_day_after = self.get_date(delta=1)
        _2_day_after = self.get_date(delta=2)

        self.reserve_order(sell_amount_series, _1_day_after)
        self.reserve_order(buy_amount_series, _2_day_after)


if __name__ == "__main__":
    market_df = pd.read_csv("./stock_bond_data.csv", index_col=0, parse_dates=True)
    market_df = market_df.ffill()

    simulation_args = {
        "market_close_df": market_df,
        "market_open_price_df": market_df,
        "name": "OpenCloseStrategy 주식8 채권2 전략",
        "start_date": datetime(2005, 1, 1),
        "end_date": datetime(2020, 7, 31),
        "rebalancing_periodic": "monthly",
        "rebalancing_moment": "first",
    }

    strategy = MyStrategy(**simulation_args)
    strategy.run()
    strategy.result_to_excel(folder_path="simulation_result")
