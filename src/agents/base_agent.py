"""
Abstract base class for all AI agents.
Each agent analyzes a specific data source and produces scores for stocks.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from src.db.models import Stock

logger = logging.getLogger(__name__)


@dataclass
class AgentScore:
    """
    Standard score output from any agent.
    All agents must produce this format.
    """
    stock_id: int
    stock_symbol: str
    date: date
    score: float  # -100 (extremely bearish) to +100 (extremely bullish)
    confidence: float  # 0.0 to 1.0
    reasoning: str = ""
    signals: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Base class for all AI agents.
    Subclasses must implement `analyze_stock()` and optionally `analyze_market()`.
    """

    name: str = "base_agent"
    description: str = "Base agent"

    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(f"agent.{self.name}")

    @abstractmethod
    def analyze_stock(self, stock: Stock, target_date: date) -> AgentScore:
        """
        Analyze a single stock and return a score.

        Args:
            stock: The Stock ORM object to analyze
            target_date: The date to analyze for

        Returns:
            AgentScore with the analysis result
        """
        ...

    def analyze_all(self, stocks: list[Stock], target_date: date) -> list[AgentScore]:
        """
        Analyze all stocks in the universe. Default implementation loops
        over each stock; override for batch optimization.
        """
        scores = []
        for stock in stocks:
            try:
                self.logger.info(f"Analyzing {stock.symbol}...")
                score = self.analyze_stock(stock, target_date)
                self._persist_score(score)
                scores.append(score)
                self.logger.info(
                    f"  {stock.symbol}: score={score.score:+.1f} "
                    f"confidence={score.confidence:.2f}"
                )
            except Exception as e:
                self.logger.error(f"  {stock.symbol}: Failed — {e}")
                self.db.rollback()
                # Create a neutral fallback score
                scores.append(AgentScore(
                    stock_id=stock.id,
                    stock_symbol=stock.symbol,
                    date=target_date,
                    score=0.0,
                    confidence=0.0,
                    reasoning=f"Analysis failed: {e}",
                ))
        return scores

    @abstractmethod
    def _persist_score(self, score: AgentScore) -> None:
        """Persist the score to the appropriate database table."""
        ...

    @staticmethod
    def clamp_score(value: float) -> float:
        """Clamp a score to the -100 to +100 range."""
        return max(-100.0, min(100.0, value))

    @staticmethod
    def clamp_confidence(value: float) -> float:
        """Clamp confidence to the 0.0 to 1.0 range."""
        return max(0.0, min(1.0, value))
