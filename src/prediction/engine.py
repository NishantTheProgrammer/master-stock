"""
Prediction Engine.
Combines scores from all 5 agents to produce final buy/sell/hold predictions.
"""

import logging
import math
from dataclasses import dataclass
from datetime import date
from typing import Sequence

from sqlalchemy.orm import Session

from src.config import settings
from src.db.crud import (
    get_all_stocks,
    get_latest_scores_for_stock,
    upsert_prediction,
)
from src.db.models import Stock

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """Final prediction for a stock."""
    stock_id: int
    stock_symbol: str
    date: date
    up_probability: float  # 0.0 to 1.0
    down_probability: float  # 0.0 to 1.0
    expected_move_pct: float  # e.g., +2.5 or -1.3
    confidence: float  # 0.0 to 1.0
    suggested_action: str  # BUY / SELL / HOLD
    suggested_position_pct: float  # Suggested % of portfolio
    component_scores: dict
    reasoning: str


class PredictionEngine:
    """
    Aggregates scores from all agents using configurable weights
    to produce probabilistic buy/sell predictions.
    """

    def __init__(
        self,
        db: Session,
        weights: dict[str, float] | None = None,
    ):
        self.db = db

        # Default weights from config, overridable
        self.weights = weights or {
            "technical": settings.weight_technical,
            "global_news": settings.weight_global_news,
            "sector_news": settings.weight_sector_news,
            "stock_news": settings.weight_stock_news,
            "social": settings.weight_social,
        }

        # Validate weights sum to ~1.0
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.01:
            logger.warning(f"Prediction weights sum to {total:.3f}, expected ~1.0. Normalizing.")
            self.weights = {k: v / total for k, v in self.weights.items()}

    def predict_all(self, target_date: date) -> list[PredictionResult]:
        """Generate predictions for all active stocks."""
        stocks = get_all_stocks(self.db, active_only=True)
        results = []

        for stock in stocks:
            try:
                result = self.predict_stock(stock, target_date)
                self._persist(result)
                results.append(result)
                logger.info(
                    f"{stock.symbol}: {result.suggested_action} "
                    f"P(up)={result.up_probability:.0%} "
                    f"Move={result.expected_move_pct:+.1f}% "
                    f"Conf={result.confidence:.0%}"
                )
            except Exception as e:
                logger.error(f"Prediction failed for {stock.symbol}: {e}")

        # Sort by conviction: highest absolute expected move * confidence
        results.sort(
            key=lambda r: abs(r.expected_move_pct) * r.confidence,
            reverse=True,
        )
        return results

    def predict_stock(self, stock: Stock, target_date: date) -> PredictionResult:
        """Generate prediction for a single stock."""
        scores = get_latest_scores_for_stock(self.db, stock.id, target_date)

        # Extract score values (default to 0 if missing)
        component_scores = {
            "technical": self._extract_score(scores.get("technical")),
            "global_news": self._extract_score(scores.get("global_news")),
            "sector_news": self._extract_score(scores.get("sector")),
            "stock_news": self._extract_score(scores.get("stock_news")),
            "social": self._extract_score(scores.get("social")),
        }

        component_confidences = {
            "technical": self._extract_confidence(scores.get("technical")),
            "global_news": self._extract_confidence(scores.get("global_news")),
            "sector_news": self._extract_confidence(scores.get("sector")),
            "stock_news": self._extract_confidence(scores.get("stock_news")),
            "social": self._extract_confidence(scores.get("social")),
        }

        # Weighted composite score (-100 to +100)
        composite_score = sum(
            self.weights[key] * component_scores[key]
            for key in self.weights
        )

        # Weighted confidence (0 to 1)
        composite_confidence = sum(
            self.weights[key] * component_confidences[key]
            for key in self.weights
        )

        # Signal agreement bonus: boost confidence when signals agree
        agreement = self._calculate_agreement(component_scores)
        composite_confidence = min(1.0, composite_confidence * (0.7 + 0.3 * agreement))

        # Convert composite score to probabilities using sigmoid
        up_prob, down_prob = self._score_to_probabilities(composite_score)

        # Estimate expected move magnitude
        expected_move = self._estimate_move(composite_score, composite_confidence)

        # Determine action
        action = self._determine_action(up_prob, down_prob, composite_confidence)

        # Position sizing based on confidence and conviction
        position_pct = self._calculate_position_size(
            up_prob, down_prob, composite_confidence
        )

        # Generate reasoning
        reasoning = self._generate_reasoning(
            stock.symbol, component_scores, composite_score, action
        )

        return PredictionResult(
            stock_id=stock.id,
            stock_symbol=stock.symbol,
            date=target_date,
            up_probability=round(up_prob, 4),
            down_probability=round(down_prob, 4),
            expected_move_pct=round(expected_move, 2),
            confidence=round(composite_confidence, 4),
            suggested_action=action,
            suggested_position_pct=round(position_pct, 2),
            component_scores=component_scores,
            reasoning=reasoning,
        )

    # ── Score extraction helpers ──

    @staticmethod
    def _extract_score(obj) -> float:
        """Extract the score value from an ORM object, defaulting to 0."""
        if obj is None:
            return 0.0
        return float(getattr(obj, "score", 0.0))

    @staticmethod
    def _extract_confidence(obj) -> float:
        """Extract confidence from an ORM object, defaulting to 0."""
        if obj is None:
            return 0.0
        return float(getattr(obj, "confidence", 0.0))

    # ── Math helpers ──

    @staticmethod
    def _score_to_probabilities(score: float) -> tuple[float, float]:
        """
        Convert a -100..+100 score to P(up) and P(down) using a sigmoid function.
        Score of 0 → 50%/50%, +100 → ~97%/3%, -100 → ~3%/97%
        """
        # Sigmoid: P(up) = 1 / (1 + e^(-score/25))
        # Scaling factor of 25 gives good spread
        x = score / 25.0
        p_up = 1.0 / (1.0 + math.exp(-x))
        p_down = 1.0 - p_up
        return p_up, p_down

    @staticmethod
    def _estimate_move(score: float, confidence: float) -> float:
        """
        Estimate expected price move percentage.
        Moderate scores (~50) with high confidence → ~2-3% expected move.
        """
        # Base move is proportional to score magnitude
        base_move = score / 20.0  # ±5% at max score

        # Scale by confidence (low confidence = smaller expected move)
        adjusted_move = base_move * confidence

        # Cap at ±10%
        return max(-10.0, min(10.0, adjusted_move))

    @staticmethod
    def _calculate_agreement(component_scores: dict) -> float:
        """
        Calculate how much agents agree with each other.
        Returns 0..1 where 1 = perfect agreement.
        """
        active_scores = [v for v in component_scores.values() if v != 0]
        if len(active_scores) < 2:
            return 0.5

        # Check if all scores have the same sign
        positive = sum(1 for s in active_scores if s > 0)
        negative = sum(1 for s in active_scores if s < 0)
        total = len(active_scores)

        # Agreement = max(positive, negative) / total
        return max(positive, negative) / total

    @staticmethod
    def _determine_action(
        up_prob: float, down_prob: float, confidence: float
    ) -> str:
        """Determine BUY/SELL/HOLD based on probabilities and confidence."""
        # Need at least 30% confidence to act
        if confidence < 0.3:
            return "HOLD"

        # Strong buy: >65% up probability with decent confidence
        if up_prob > 0.65 and confidence > 0.4:
            return "BUY"

        # Strong sell: >65% down probability with decent confidence
        if down_prob > 0.65 and confidence > 0.4:
            return "SELL"

        # Moderate buy: >55% up with high confidence
        if up_prob > 0.55 and confidence > 0.6:
            return "BUY"

        # Moderate sell: >55% down with high confidence
        if down_prob > 0.55 and confidence > 0.6:
            return "SELL"

        return "HOLD"

    @staticmethod
    def _calculate_position_size(
        up_prob: float, down_prob: float, confidence: float
    ) -> float:
        """
        Calculate suggested position size as % of portfolio.
        Uses Kelly Criterion-inspired sizing.
        Max position: 10% of portfolio.
        """
        # Edge = expected value per unit bet
        edge = abs(up_prob - down_prob)

        # Position = edge * confidence * max_position
        max_position = 10.0
        position = edge * confidence * max_position

        # Minimum position of 1% if we're suggesting any action
        if position > 0 and position < 1.0:
            position = 1.0

        return min(max_position, position)

    @staticmethod
    def _generate_reasoning(
        symbol: str,
        component_scores: dict,
        composite: float,
        action: str,
    ) -> str:
        """Generate a human-readable reasoning string."""
        parts = [f"{symbol} — {action}"]
        parts.append(f"Composite: {composite:+.1f}")

        for key, score in component_scores.items():
            if score != 0:
                direction = "+" if score > 0 else ""
                parts.append(f"{key}: {direction}{score:.0f}")

        # Count agreement
        active = [v for v in component_scores.values() if v != 0]
        if active:
            bullish = sum(1 for v in active if v > 0)
            parts.append(f"Agreement: {bullish}/{len(active)} bullish")

        return " | ".join(parts)

    def _persist(self, result: PredictionResult) -> None:
        """Save prediction to database."""
        upsert_prediction(self.db, {
            "stock_id": result.stock_id,
            "date": result.date,
            "up_probability": result.up_probability,
            "down_probability": result.down_probability,
            "expected_move_pct": result.expected_move_pct,
            "confidence": result.confidence,
            "suggested_action": result.suggested_action,
            "suggested_position_pct": result.suggested_position_pct,
            "component_scores_json": result.component_scores,
            "reasoning": result.reasoning,
        })
