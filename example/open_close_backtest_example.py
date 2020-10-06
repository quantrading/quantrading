import quantrading as qt
from datetime import datetime
import pandas as pd


class MyStrategy(qt.OpenCloseStrategy):
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

        allocation_series.name = self.date
        self.rebalancing_mp_weight = pd.concat([self.rebalancing_mp_weight, allocation_series.to_frame().T], axis=0)

        amount_delta_series = self.portfolio.get_amount_delta(allocation_series)

        amount_delta_series.pop('cash')
        sell_amount_series = amount_delta_series[amount_delta_series < 0]
        buy_amount_series = amount_delta_series[amount_delta_series > 0]

        self.reserve_order(sell_amount_series, "sell")
        self.reserve_order(buy_amount_series, "buy")


if __name__ == "__main__":
    market_df = pd.read_csv("./stock_bond_data.csv", index_col=0, parse_dates=True)
    market_df = market_df.ffill()

    custom_mp_df = pd.DataFrame(data=[[0.5, 0.5]], index=[datetime(2020, 1, 6)], columns=[
        'MSCI_WORLD_ACWI',
        'IEF_BOND_7_10_INDEX',
    ])

    print(custom_mp_df)

    simulation_args = {
        "market_close_df": market_df,
        "market_open_price_df": market_df,
        "name": "OpenCloseStrategy 주식8 채권2 전략",
        "start_date": datetime(2005, 1, 1),
        "end_date": datetime(2020, 7, 31),
        "rebalancing_periodic": "quarterly",
        "rebalancing_moment": "first",
        "benchmark_ticker": "MSCI_WORLD_ACWI",
        "sell_delay": 1,
        "buy_delay": 2,

        "custom_mp_option": True,
        "custom_mp_start_date": datetime(2020, 1, 1),
        "custom_mp": custom_mp_df,
        "custom_mp_sell_delay": 0,
        "custom_mp_buy_delay": 1,
    }

    strategy = MyStrategy(**simulation_args)
    strategy.run()
    strategy.print_result_log(display_image=True)
    strategy.result_to_excel(folder_path="simulation_result")
