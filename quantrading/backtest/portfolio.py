import pandas as pd
from datetime import datetime
import numpy as np

INITIAL_MONEY = "INITIAL_MONEY"
SECURITY_HOLDING = "SECURITY_HOLDING"
DEFAULT_SEED_MONEY = 100


class Portfolio:
    def __init__(self, **kwargs):
        self.cash = kwargs.get(INITIAL_MONEY, DEFAULT_SEED_MONEY)
        self.security_holding = kwargs.get(SECURITY_HOLDING, {})

    def buy(self, ticker, amount):
        new_amount = self.security_holding.get(ticker, 0) + amount
        self.security_holding[ticker] = new_amount
        self.cash -= amount

    def sell(self, ticker, amount):
        prev_amount = self.security_holding.get(ticker, 0)
        self.security_holding[ticker] = prev_amount - amount
        self.cash += amount

        if self.security_holding[ticker] == 0:
            del self.security_holding[ticker]

    def get_allocations(self) -> pd.Series:
        allocations = pd.Series()
        for ticker in self.security_holding.keys():
            allocations.loc[ticker] = self.get_weight(ticker)

        allocations.loc["cash"] = 1 - allocations.sum()
        return allocations

    def set_allocations(self, new_allocations: pd.Series):
        current_allocations = self.get_allocations()
        allocations_df = pd.concat([current_allocations, new_allocations], axis=1, sort=False)
        allocations_df.columns = ["current", "next"]
        allocations_df = allocations_df.fillna(0)
        allocations_df["weight_delta"] = allocations_df["next"] - allocations_df["current"]
        allocations_df = allocations_df.sort_values("weight_delta", ascending=True)

        for ticker, weight in allocations_df["next"].items():
            if ticker == "cash":
                continue
            self.set_weight(ticker, weight)

    def set_weight(self, ticker, weight):
        current_weight = self.get_weight(ticker)
        weight_delta = weight - current_weight
        port_value = self.get_total_portfolio_value()
        if weight_delta > 0:
            # buy
            amount = port_value * weight_delta
            self.buy(ticker, amount)
        elif weight_delta < 0:
            # sell
            amount = port_value * -weight_delta
            self.sell(ticker, amount)
        else:
            # nothing
            pass

    def update_holdings_value(self, today_date: datetime, market_df_pct_change: pd.DataFrame):
        prev_holdings = self.security_holding.items()
        for ticker, amount in prev_holdings:
            daily_returns = market_df_pct_change.loc[today_date, ticker]
            if np.isnan(daily_returns):
                continue
            new_amount = amount * (1 + daily_returns)
            self.security_holding[ticker] = new_amount

    def get_weight(self, ticker):
        amount = self.security_holding.get(ticker, 0)
        port_value = self.get_total_portfolio_value()
        return amount / port_value

    def get_total_portfolio_value(self):
        holdings_value = self.get_total_holdings_value()
        cash = self.cash
        return holdings_value + cash

    def get_total_holdings_value(self):
        return sum(self.security_holding.values())
