"""
Base trading strategy for sandbox agents.
All trading strategies inherit from this.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from src.prediction.engine import PredictionResult
from src.sandbox.exchange import VirtualExchange


@dataclass
class TradeDecision:
    """A trade decision made by a strategy."""
    symbol: str
    stock_id: int
    action: str  # BUY, SELL, or HOLD
    quantity: int
    reason: str


class BaseStrategy(ABC):
    """
    Abstract base strategy for sandbox trading agents.
    Each strategy implements different risk/reward profiles.
    """

    name: str = "base_strategy"
    description: str = "Base trading strategy"

    def __init__(self, exchange: VirtualExchange):
        self.exchange = exchange

    @abstractmethod
    def decide(
        self,
        predictions: list[PredictionResult],
        current_prices: dict[str, float],
        current_date: date,
    ) -> list[TradeDecision]:
        """
        Given today's predictions and prices, decide what trades to make.

        Args:
            predictions: List of PredictionResult for all stocks
            current_prices: Dict mapping symbol → current price
            current_date: Today's date

        Returns:
            List of TradeDecision objects
        """
        ...

    def execute_decisions(
        self,
        decisions: list[TradeDecision],
        current_prices: dict[str, float],
        current_date: date,
    ) -> int:
        """Execute trade decisions on the exchange."""
        trades_executed = 0
        for decision in decisions:
            if decision.action == "HOLD" or decision.quantity <= 0:
                continue

            price = current_prices.get(decision.symbol, 0)
            if price <= 0:
                continue

            if decision.action == "BUY":
                trade = self.exchange.buy(
                    decision.stock_id, decision.symbol,
                    decision.quantity, price, current_date
                )
            elif decision.action == "SELL":
                trade = self.exchange.sell(
                    decision.stock_id, decision.symbol,
                    decision.quantity, price, current_date
                )
            else:
                continue

            if trade:
                trades_executed += 1

        return trades_executed

    def _calculate_buy_quantity(
        self, price: float, portfolio_pct: float
    ) -> int:
        """Calculate how many shares to buy given a portfolio % allocation."""
        max_spend = self.exchange.total_portfolio_value * (portfolio_pct / 100)
        max_spend = min(max_spend, self.exchange.cash * 0.95)  # Keep 5% cash buffer
        if price <= 0 or max_spend <= 0:
            return 0
        return int(max_spend / price)

    def _get_holding_quantity(self, symbol: str) -> int:
        """Get current holding quantity for a symbol."""
        holding = self.exchange.holdings.get(symbol)
        return holding.quantity if holding else 0
