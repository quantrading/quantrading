import quantrading as qt
from datetime import datetime
import pandas as pd


class MyStrategy(qt.Strategy):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_data(self):
        today_date = self.date

        allocation = {
            'MSCI_WORLD_ACWI': 0.8,
            'IEF_BOND_7_10_INDEX': 0.2
        }

        print(today_date, allocation)

        allocation_series = pd.Series(allocation)
        self.reserve_order(allocation_series)


if __name__ == "__main__":
    market_df = pd.read_csv("./stock_bond_data.csv", index_col=0, parse_dates=True)
    market_df = market_df.ffill()

    simulation_args = {
        "market_df": market_df,
        "name": "주식8 채권2 전략",
        "start_date": datetime(2005, 1, 1),
        "end_date": datetime(2020, 7, 31),
        "rebalancing_periodic": "monthly",
        "rebalancing_moment": "first",
    }

    strategy = MyStrategy(**simulation_args)
    strategy.run()
    strategy.result_to_excel(folder_path="simulation_result")
