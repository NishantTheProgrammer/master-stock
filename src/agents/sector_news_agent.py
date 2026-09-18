"""
Sector News Agent.
Analyzes sector-specific news to determine sentiment for each industry sector.
"""

import logging
from datetime import date

from sqlalchemy.orm import Session

from src.agents.base_agent import AgentScore, BaseAgent
from src.agents.llm_provider import LLMProvider
from src.data.news_fetcher import NewsFetcher
from src.data.stocks import get_sectors, get_stocks_grouped_by_sector
from src.db.crud import upsert_sector_score
from src.db.models import Stock

logger = logging.getLogger(__name__)

SECTOR_NEWS_SYSTEM_PROMPT = """You are a financial sector analyst AI. Analyze news headlines related to a specific market sector and assess the sector's outlook.

You MUST respond with valid JSON in this exact format:
{
    "score": <number from -100 to 100>,
    "confidence": <number from 0.0 to 1.0>,
    "summary": "<1-2 sentence sector outlook>",
    "key_factors": ["<factor 1>", "<factor 2>", ...],
    "reasoning": "<explanation of your score>"
}
"""


class SectorNewsAgent(BaseAgent):
    """
    Analyzes sector-level news to produce one score per sector per day.
    Stocks inherit their sector's score.
    """

    name = "sector_news_agent"
    description = "Analyzes sector-specific news and trends"

    def __init__(self, db: Session, llm: LLMProvider | None = None):
        super().__init__(db)
        self.news_fetcher = NewsFetcher()
        self.llm = llm or LLMProvider()
        self._sector_scores_cache: dict[str, AgentScore] = {}
        self._finbert_pipeline = None

    def _get_finbert(self):
        """Lazy-load FinBERT."""
        if self._finbert_pipeline is None:
            try:
                from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
                model_name = "ProsusAI/finbert"
                tokenizer = AutoTokenizer.from_pretrained(model_name)
                model = AutoModelForSequenceClassification.from_pretrained(model_name)
                self._finbert_pipeline = pipeline(
                    "sentiment-analysis", model=model, tokenizer=tokenizer
                )
            except Exception as e:
                self.logger.warning(f"Failed to load FinBERT: {e}")
        return self._finbert_pipeline

    def analyze_all_sectors(self, target_date: date) -> dict[str, AgentScore]:
        """
        Analyze all sectors and cache results.
        Call this once before analyze_all() for efficiency.
        """
        sectors = get_sectors(self.db)
        self.logger.info(f"Analyzing {len(sectors)} sectors...")

        for sector in sectors:
            score = self._analyze_sector(sector, target_date)
            self._sector_scores_cache[sector] = score
            self._persist_sector_score(score, sector)
            self.logger.info(f"  {sector}: score={score.score:+.1f} conf={score.confidence:.2f}")

        return self._sector_scores_cache

    def _analyze_sector(self, sector: str, target_date: date) -> AgentScore:
        """Analyze a single sector."""
        # Fetch sector-relevant news
        articles = self.news_fetcher.fetch_sector_news(sector)

        if not articles:
            return AgentScore(
                stock_id=0,
                stock_symbol=f"SECTOR:{sector}",
                date=target_date,
                score=0.0,
                confidence=0.2,
                reasoning=f"No news articles found for {sector} sector.",
            )

        # FinBERT sentiment on headlines
        finbert = self._get_finbert()
        headline_data = []
        for article in articles:
            finbert_score = 0.0
            if finbert and article.headline:
                try:
                    result = finbert(article.headline[:512])[0]
                    if result["label"] == "positive":
                        finbert_score = result["score"] * 100
                    elif result["label"] == "negative":
                        finbert_score = -result["score"] * 100
                except Exception:
                    pass
            headline_data.append(f"[{finbert_score:+.0f}] {article.headline}")

        # LLM analysis
        news_text = "\n".join(headline_data[:15])  # Cap at 15 headlines
        prompt = f"""Analyze these news headlines related to the {sector} sector in India.
Each headline has an AI sentiment score in brackets.

{news_text}

Provide your assessment of the {sector} sector outlook as JSON with score, confidence, summary, key_factors, and reasoning."""

        result = self.llm.analyze(prompt, SECTOR_NEWS_SYSTEM_PROMPT)

        return AgentScore(
            stock_id=0,
            stock_symbol=f"SECTOR:{sector}",
            date=target_date,
            score=self.clamp_score(float(result.get("score", 0))),
            confidence=self.clamp_confidence(float(result.get("confidence", 0.5))),
            reasoning=result.get("reasoning", ""),
            signals={
                "summary": result.get("summary", ""),
                "key_factors": result.get("key_factors", []),
                "article_count": len(articles),
            },
        )

    def analyze_stock(self, stock: Stock, target_date: date) -> AgentScore:
        """
        Return the sector score for this stock's sector.
        If sector hasn't been analyzed yet, analyze it now.
        """
        sector = stock.sector
        if sector not in self._sector_scores_cache:
            self._sector_scores_cache[sector] = self._analyze_sector(sector, target_date)
            self._persist_sector_score(self._sector_scores_cache[sector], sector)

        sector_score = self._sector_scores_cache[sector]

        # Return a stock-specific version of the sector score
        return AgentScore(
            stock_id=stock.id,
            stock_symbol=stock.symbol,
            date=target_date,
            score=sector_score.score,
            confidence=sector_score.confidence,
            reasoning=f"[Sector: {sector}] {sector_score.reasoning}",
            signals=sector_score.signals,
        )

    def _persist_sector_score(self, score: AgentScore, sector: str) -> None:
        """Save sector score to database."""
        upsert_sector_score(self.db, {
            "sector": sector,
            "date": score.date,
            "score": score.score,
            "confidence": score.confidence,
            "summary": score.signals.get("summary", ""),
            "key_news_json": score.signals.get("key_factors", []),
            "reasoning": score.reasoning,
        })

    def _persist_score(self, score: AgentScore) -> None:
        """Required by BaseAgent interface."""
        # Extract sector from the symbol (SECTOR:Banking → Banking)
        parts = score.stock_symbol.split(":")
        sector = parts[1] if len(parts) > 1 else "Unknown"
        self._persist_sector_score(score, sector)
