"""
Stock News Agent.
Analyzes company-specific news for each individual stock.
"""

import logging
from datetime import date

from sqlalchemy.orm import Session

from src.agents.base_agent import AgentScore, BaseAgent
from src.agents.llm_provider import LLMProvider
from src.data.news_fetcher import NewsFetcher
from src.db.crud import upsert_stock_news_score
from src.db.models import Stock

logger = logging.getLogger(__name__)

STOCK_NEWS_SYSTEM_PROMPT = """You are a financial analyst AI specializing in individual stock analysis. Analyze company-specific news headlines and assess their impact on the stock price.

You MUST respond with valid JSON in this exact format:
{
    "score": <number from -100 to 100>,
    "confidence": <number from 0.0 to 1.0>,
    "summary": "<1-2 sentence impact assessment>",
    "catalysts": ["<catalyst 1>", "<catalyst 2>", ...],
    "risks": ["<risk 1>", "<risk 2>", ...],
    "reasoning": "<explanation of your score>"
}

Consider:
- Earnings reports, revenue growth, profit margins
- Management changes, strategy shifts
- Product launches, partnerships, acquisitions
- Regulatory actions, lawsuits, compliance issues
- Market share changes, competitive dynamics
"""


class StockNewsAgent(BaseAgent):
    """
    Analyzes company-specific news for each stock.
    Produces one score per stock per day.
    """

    name = "stock_news_agent"
    description = "Analyzes company-specific news and events"

    def __init__(self, db: Session, llm: LLMProvider | None = None):
        super().__init__(db)
        self.news_fetcher = NewsFetcher()
        self.llm = llm or LLMProvider()
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

    def analyze_stock(self, stock: Stock, target_date: date) -> AgentScore:
        """Analyze company-specific news for a stock."""
        articles = self.news_fetcher.fetch_company_news(stock.symbol)

        if not articles:
            return AgentScore(
                stock_id=stock.id,
                stock_symbol=stock.symbol,
                date=target_date,
                score=0.0,
                confidence=0.1,
                reasoning=f"No recent news found for {stock.name} ({stock.symbol}).",
            )

        # FinBERT sentiment analysis on each headline
        finbert = self._get_finbert()
        scored_headlines = []

        for article in articles:
            finbert_score = 0.0
            finbert_label = "neutral"
            if finbert and article.headline:
                try:
                    result = finbert(article.headline[:512])[0]
                    finbert_label = result["label"]
                    if result["label"] == "positive":
                        finbert_score = result["score"] * 100
                    elif result["label"] == "negative":
                        finbert_score = -result["score"] * 100
                except Exception:
                    pass

            scored_headlines.append({
                "headline": article.headline,
                "source": article.source,
                "sentiment": finbert_label,
                "finbert_score": round(finbert_score, 1),
            })

        # Build prompt for LLM
        headlines_text = "\n".join(
            f"  {i}. [{h['sentiment'].upper()} ({h['finbert_score']:+.0f})] "
            f"{h['headline']} — {h['source']}"
            for i, h in enumerate(scored_headlines, 1)
        )

        prompt = f"""Analyze these recent news headlines for {stock.name} ({stock.symbol}), a company in the {stock.sector} sector listed on NSE India.

Each headline has an AI-calculated sentiment score in brackets.

{headlines_text}

Based on these headlines, assess the short-term (1-5 day) impact on {stock.symbol}'s stock price.
Provide your analysis as JSON with score, confidence, summary, catalysts, risks, and reasoning."""

        result = self.llm.analyze(prompt, STOCK_NEWS_SYSTEM_PROMPT)

        score = AgentScore(
            stock_id=stock.id,
            stock_symbol=stock.symbol,
            date=target_date,
            score=self.clamp_score(float(result.get("score", 0))),
            confidence=self.clamp_confidence(float(result.get("confidence", 0.5))),
            reasoning=result.get("reasoning", ""),
            signals={
                "summary": result.get("summary", ""),
                "catalysts": result.get("catalysts", []),
                "risks": result.get("risks", []),
                "headline_count": len(articles),
                "headlines": scored_headlines[:5],  # Store top 5 for reference
            },
        )

        return score

    def _persist_score(self, score: AgentScore) -> None:
        """Save stock news score to database."""
        upsert_stock_news_score(self.db, {
            "stock_id": score.stock_id,
            "date": score.date,
            "score": score.score,
            "confidence": score.confidence,
            "headlines_json": score.signals.get("headlines", []),
            "summary": score.signals.get("summary", ""),
            "reasoning": score.reasoning,
        })
