"""
Balanced Trading Strategy.
Moderate approach — buys good signals, diversifies, uses stop-losses.
"""

from datetime import date

from src.prediction.engine import PredictionResult
from src.sandbox.exchange import VirtualExchange
from src.sandbox.strategies.base_strategy import BaseStrategy, TradeDecision


class BalancedStrategy(BaseStrategy):
    """
    Balanced, diversified trader.
    - Buys when composite score > +30 with confidence > 0.5
    - Sells when score drops below -30
    - Max 10% portfolio per stock (diversified)
    - Keeps at least 20% cash reserve
    """

    name = "balanced"
    description = "Diversified moderate approach with cash reserves"

    BUY_THRESHOLD = 30
    SELL_THRESHOLD = -30
    MAX_POSITION_PCT = 10
    CASH_RESERVE_PCT = 20

    def decide(
        self,
        predictions: list[PredictionResult],
        current_prices: dict[str, float],
        current_date: date,
    ) -> list[TradeDecision]:
        decisions = []

        # Sort by conviction (best opportunities first)
        sorted_preds = sorted(
            predictions,
            key=lambda p: abs(p.expected_move_pct) * p.confidence,
            reverse=True,
        )

        for pred in sorted_preds:
            price = current_prices.get(pred.stock_symbol, 0)
            if price <= 0:
                continue

            holding_qty = self._get_holding_quantity(pred.stock_symbol)
            composite = sum(pred.component_scores.values())

            # SELL: negative outlook
            if holding_qty > 0 and composite < self.SELL_THRESHOLD:
                decisions.append(TradeDecision(
                    symbol=pred.stock_symbol,
                    stock_id=pred.stock_id,
                    action="SELL",
                    quantity=holding_qty,
                    reason=f"Negative outlook (score={composite:+.0f} < {self.SELL_THRESHOLD})",
                ))

            # BUY: moderate conviction with quality filter
            elif (
                holding_qty == 0
                and composite > self.BUY_THRESHOLD
                and pred.confidence > 0.5
                and self._has_sufficient_cash()
            ):
                qty = self._calculate_buy_quantity(price, self.MAX_POSITION_PCT)
                if qty > 0:
                    decisions.append(TradeDecision(
                        symbol=pred.stock_symbol,
                        stock_id=pred.stock_id,
                        action="BUY",
                        quantity=qty,
                        reason=(
                            f"Balanced buy (score={composite:+.0f}, "
                            f"conf={pred.confidence:.0%})"
                        ),
                    ))

        return decisions

    def _has_sufficient_cash(self) -> bool:
        """Check if we still have enough cash (maintain reserve)."""
        min_cash = self.exchange.initial_capital * (self.CASH_RESERVE_PCT / 100)
        return self.exchange.cash > min_cash
