from datetime import datetime
import pandas as pd
import calendar

DEFAULT_DATE_FORMAT = "%Y-%m-%d"


class TradingDay:
    def __init__(self, trading_days: list):
        self.all_trading_days = pd.Series(trading_days).sort_values().reset_index(drop=True)
        self.first_date = self.all_trading_days.iloc[0]
        self.last_date = self.all_trading_days.iloc[-1]

    def get_trading_day_list(self, start_date: datetime, end_date: datetime) -> pd.Series:
        trading_days = self.all_trading_days
        trading_days = trading_days[trading_days >= start_date]
        trading_days = trading_days[trading_days <= end_date]
        return trading_days

    def get_rebalancing_days(self,
                             start_date: datetime,
                             end_date: datetime,
                             rebalancing_periodic: str,
                             rebalancing_moment: str) -> list:
        if rebalancing_periodic == 'daily':
            rebalancing_days = self.get_trading_day_list(start_date, end_date).to_list()
        elif rebalancing_periodic == 'weekly':
            rebalancing_days = self.get_first_day_of_every_week(start_date, end_date)
        elif rebalancing_periodic == 'monthly':
            start_month = start_date.strftime("%Y-%m")
            end_month = end_date.strftime("%Y-%m")
            if rebalancing_moment == 'first':
                rebalancing_days = self.get_first_day_of_every_month(start_month, end_month)
            elif rebalancing_moment == 'last':
                rebalancing_days = self.get_last_day_of_every_month(start_month, end_month)
            else:
                raise ValueError("Invalid rebalancing_moment type : ", rebalancing_moment)
        elif rebalancing_periodic == 'quarterly':
            start_quarter = f"{start_date.year}-{(start_date.month - 1) // 3 + 1}"
            end_quarter = f"{end_date.year}-{(end_date.month - 1) // 3 + 1}"
            rebalancing_days = self.get_first_day_of_report_month(start_quarter, end_quarter)
        elif rebalancing_periodic == 'yearly':
            if rebalancing_moment == 'first':
                rebalancing_days = self.get_first_day_of_every_year(start_date.year, end_date.year)
            elif rebalancing_moment == 'last':
                rebalancing_days = self.get_last_day_of_every_year(start_date.year, end_date.year)
            else:
                raise ValueError("Invalid rebalancing_moment type : ", rebalancing_moment)
        else:
            raise ValueError("Invalid rebalancing_periodic type : ", rebalancing_periodic)
        return rebalancing_days

    def get_first_day_of_every_month(self, start_date: str, end_date: str):
        """
        ex) 2002Y,2M -> "2002-2"
        ex) 2015Y,12M -> "2015-12"
        """
        year_n_month_combination = generate_year_n_month(start_date, end_date)
        days = []
        for year, month in year_n_month_combination:
            first_date = f"{year}-{month}-1"
            temp_date = self.magnet(first_date, 1)
            days.append(temp_date)
        return days

    def get_last_day_of_every_month(self, start_date: str, end_date: str):
        """
        example
        date: 2019-12
        """
        year_n_month_combination = generate_year_n_month(start_date, end_date)
        days = []
        for year, month in year_n_month_combination:
            temp_trading_days = self.get_trading_days_by_year_n_month(year, month)
            last_date = temp_trading_days.tolist()[-1]
            days.append(last_date)
        return days

    def magnet(self, date, flag):
        """
        flag: before:0, after:1
        """
        if flag == 1:
            trading_days = self.get_trading_day_list(date, self.last_date)
            near_date = trading_days.iloc[0]
        elif flag == 0:
            trading_days = self.get_trading_day_list(self.first_date, date)
            near_date = trading_days.iloc[-1]
        else:
            raise ValueError(f"Invalid flag : {flag}")
        return near_date

    def get_trading_days_by_year_n_month(self, year, month):
        end_month_last_day = calendar.monthrange(year, month)[1]
        start_date = f"{year}-{month}-01"
        end_date = f"{year}-{month}-{end_month_last_day}"
        start_date = datetime.strptime(start_date, DEFAULT_DATE_FORMAT)
        end_date = datetime.strptime(end_date, DEFAULT_DATE_FORMAT)

        trading_date_series = self.get_trading_day_list(start_date, end_date)
        return trading_date_series

    def get_first_day_of_report_month(self, start_date: str, end_date: str):
        year_n_month_combination = generate_year_n_month(start_date, end_date)
        days = []
        for year, month in year_n_month_combination:
            if month not in [4, 6, 9, 12]:
                continue
            first_date = f"{year}-{month}-1"
            temp_date = self.magnet(first_date, 1)
            days.append(temp_date)
        return days

    def get_first_day_of_every_week(self, start_date: datetime, end_date: datetime) -> list:
        every_monday_list = generate_every_monday(start_date, end_date)
        days = []
        for date in every_monday_list:
            temp_date = self.magnet(date, 1)
            days.append(temp_date)
        return days

    def get_first_day_of_every_year(self, start_year: int, end_year: int) -> list:
        days = []
        for year in range(start_year, end_year + 1):
            temp_date = self.get_trading_days_by_year(year).to_list()[0]
            days.append(temp_date)
        return days

    def get_last_day_of_every_year(self, start_year: int, end_year: int) -> list:
        days = []
        for year in range(start_year, end_year + 1):
            temp_date = self.get_trading_days_by_year(year).to_list()[-1]
            days.append(temp_date)
        return days

    def get_trading_days_by_year(self, year):
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31)
        trading_date_series = self.get_trading_day_list(start_date, end_date)
        return trading_date_series


def generate_year_n_month(start_date: str, end_date: str):
    start_year, start_month = start_date.split("-")
    end_year, end_month = end_date.split("-")
    start_year = int(start_year)
    start_month = int(start_month)
    end_year = int(end_year)
    end_month = int(end_month)

    combinations = []

    if start_year == end_year:
        return [(start_year, month) for month in range(start_month, end_month + 1)]

    # start year
    combinations += [(start_year, month) for month in range(start_month, 13)]

    # middle years
    if start_year < (end_year - 1):
        combinations += [(year, month) for year in range(start_year + 1, end_year) for month in range(1, 13)]

    # end year
    if start_year != end_year:
        combinations += [(end_year, month) for month in range(1, end_month + 1)]

    return combinations


def generate_year_n_quarter(start_quarter: str, end_quarter: str):
    start_year, start_quarter = start_quarter.split("-")
    end_year, end_quarter = end_quarter.split("-")
    start_year = int(start_year)
    start_quarter = int(start_quarter)
    end_year = int(end_year)
    end_quarter = int(end_quarter)

    combinations = []
    # start year
    combinations += [(start_year, quarter) for quarter in range(start_quarter, 5)]

    # middle years
    if start_year < (end_year - 1):
        combinations += [(year, quarter) for year in range(start_year + 1, end_year) for quarter in range(1, 5)]

    # end year
    if start_year != end_year:
        combinations += [(end_year, quarter) for quarter in range(1, end_quarter + 1)]

    return combinations


def generate_every_monday(start_date: datetime, end_date: datetime):
    every_monday_list = pd.date_range(start_date, end_date, freq="W-MON")
    return every_monday_list
