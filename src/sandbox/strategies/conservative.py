"""
Conservative Trading Strategy.
High-conviction only, small positions, tight risk management.
"""

from datetime import date

from src.prediction.engine import PredictionResult
from src.sandbox.exchange import VirtualExchange
from src.sandbox.strategies.base_strategy import BaseStrategy, TradeDecision


class ConservativeStrategy(BaseStrategy):
    """
    Conservative, risk-averse trader.
    - Buys ONLY when composite score > +70 with high confidence (> 0.6)
    - Sells quickly when score drops below -10
    - Max 5% portfolio per stock
    - Keeps at least 40% cash reserve
    - Maximum 6 positions at any time
    """

    name = "conservative"
    description = "High-conviction only, tight risk management"

    BUY_THRESHOLD = 70
    SELL_THRESHOLD = -10
    MAX_POSITION_PCT = 5
    CASH_RESERVE_PCT = 40
    MAX_POSITIONS = 6

    def decide(
        self,
        predictions: list[PredictionResult],
        current_prices: dict[str, float],
        current_date: date,
    ) -> list[TradeDecision]:
        decisions = []

        # Sort by confidence (highest first)
        sorted_preds = sorted(
            predictions, key=lambda p: p.confidence, reverse=True
        )

        for pred in sorted_preds:
            price = current_prices.get(pred.stock_symbol, 0)
            if price <= 0:
                continue

            holding_qty = self._get_holding_quantity(pred.stock_symbol)
            composite = sum(pred.component_scores.values())

            # SELL: tight stop-loss
            if holding_qty > 0 and composite < self.SELL_THRESHOLD:
                decisions.append(TradeDecision(
                    symbol=pred.stock_symbol,
                    stock_id=pred.stock_id,
                    action="SELL",
                    quantity=holding_qty,
                    reason=f"Stop-loss triggered (score={composite:+.0f} < {self.SELL_THRESHOLD})",
                ))

            # BUY: only the highest conviction opportunities
            elif (
                holding_qty == 0
                and composite > self.BUY_THRESHOLD
                and pred.confidence > 0.6
                and self._can_open_position()
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
                            f"High conviction (score={composite:+.0f}, "
                            f"conf={pred.confidence:.0%})"
                        ),
                    ))

        return decisions

    def _can_open_position(self) -> bool:
        """Check if we can open another position (max positions limit)."""
        return len(self.exchange.holdings) < self.MAX_POSITIONS

    def _has_sufficient_cash(self) -> bool:
        """Maintain high cash reserve."""
        min_cash = self.exchange.initial_capital * (self.CASH_RESERVE_PCT / 100)
        return self.exchange.cash > min_cash
