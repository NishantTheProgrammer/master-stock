"""
Momentum Trading Strategy.
Buys stocks with strong positive scores, sells when momentum weakens.
Aggressive approach — rides trends hard.
"""

from datetime import date

from src.prediction.engine import PredictionResult
from src.sandbox.exchange import VirtualExchange
from src.sandbox.strategies.base_strategy import BaseStrategy, TradeDecision


class MomentumStrategy(BaseStrategy):
    """
    Aggressive momentum trader.
    - Buys when composite score > +60 (strong bullish)
    - Sells when score drops below -20 (momentum lost)
    - Max 15% portfolio per stock
    """

    name = "momentum"
    description = "Aggressive momentum rider — buys strong trends"

    BUY_THRESHOLD = 60
    SELL_THRESHOLD = -20
    MAX_POSITION_PCT = 15

    def decide(
        self,
        predictions: list[PredictionResult],
        current_prices: dict[str, float],
        current_date: date,
    ) -> list[TradeDecision]:
        decisions = []

        for pred in predictions:
            price = current_prices.get(pred.stock_symbol, 0)
            if price <= 0:
                continue

            holding_qty = self._get_holding_quantity(pred.stock_symbol)
            composite = sum(pred.component_scores.values())

            # SELL: momentum lost
            if holding_qty > 0 and composite < self.SELL_THRESHOLD:
                decisions.append(TradeDecision(
                    symbol=pred.stock_symbol,
                    stock_id=pred.stock_id,
                    action="SELL",
                    quantity=holding_qty,  # Sell all
                    reason=f"Momentum lost (score={composite:+.0f} < {self.SELL_THRESHOLD})",
                ))

            # BUY: strong momentum
            elif holding_qty == 0 and composite > self.BUY_THRESHOLD and pred.confidence > 0.4:
                qty = self._calculate_buy_quantity(price, self.MAX_POSITION_PCT)
                if qty > 0:
                    decisions.append(TradeDecision(
                        symbol=pred.stock_symbol,
                        stock_id=pred.stock_id,
                        action="BUY",
                        quantity=qty,
                        reason=f"Strong momentum (score={composite:+.0f} > {self.BUY_THRESHOLD})",
                    ))

        return decisions
