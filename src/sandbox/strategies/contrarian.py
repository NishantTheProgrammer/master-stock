"""
Contrarian Trading Strategy.
Buys oversold stocks (negative sentiment), sells when sentiment recovers.
Bets on mean reversion.
"""

from datetime import date

from src.prediction.engine import PredictionResult
from src.sandbox.exchange import VirtualExchange
from src.sandbox.strategies.base_strategy import BaseStrategy, TradeDecision


class ContrarianStrategy(BaseStrategy):
    """
    Contrarian trader — bets against the crowd.
    - Buys when composite score < -40 (oversold, crowd is fearful)
    - Sells when score rises above +40 (sentiment recovered)
    - Max 12% portfolio per stock
    """

    name = "contrarian"
    description = "Mean reversion — buys fear, sells greed"

    BUY_THRESHOLD = -40
    SELL_THRESHOLD = 40
    MAX_POSITION_PCT = 12

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

            # SELL: sentiment recovered (take profit)
            if holding_qty > 0 and composite > self.SELL_THRESHOLD:
                decisions.append(TradeDecision(
                    symbol=pred.stock_symbol,
                    stock_id=pred.stock_id,
                    action="SELL",
                    quantity=holding_qty,
                    reason=f"Sentiment recovered (score={composite:+.0f} > {self.SELL_THRESHOLD})",
                ))

            # BUY: oversold / extreme fear
            elif holding_qty == 0 and composite < self.BUY_THRESHOLD:
                qty = self._calculate_buy_quantity(price, self.MAX_POSITION_PCT)
                if qty > 0:
                    decisions.append(TradeDecision(
                        symbol=pred.stock_symbol,
                        stock_id=pred.stock_id,
                        action="BUY",
                        quantity=qty,
                        reason=f"Oversold — contrarian buy (score={composite:+.0f} < {self.BUY_THRESHOLD})",
                    ))

        return decisions
