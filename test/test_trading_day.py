import unittest
import quantrading as qt
from datetime import datetime
import pandas as pd


class MyTestCase(unittest.TestCase):
    def test_something(self):
        start_date = datetime(2020, 1, 1)
        end_date = datetime(2020, 10, 28)

        date_series = pd.date_range(start_date, end_date)

        td = qt.trading_day.TradingDay(date_series.tolist())

        rebalancing_periodic = 'quarterly'
        rebalancing_moment = 'last'

        a = td.get_rebalancing_days(start_date, end_date, rebalancing_periodic, rebalancing_moment)
        print(a)

        self.assertEqual(True, False)


if __name__ == '__main__':
    unittest.main()
