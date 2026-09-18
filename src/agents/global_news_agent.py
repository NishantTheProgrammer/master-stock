"""
Global News Agent.
Analyzes overall market news to determine the general market sentiment.
Uses FinBERT for headline sentiment + Ollama for summarization.
"""

import logging
from datetime import date

from sqlalchemy.orm import Session

from src.agents.base_agent import AgentScore, BaseAgent
from src.agents.llm_provider import LLMProvider
from src.data.news_fetcher import NewsFetcher
from src.db.crud import upsert_global_news_score
from src.db.models import Stock

logger = logging.getLogger(__name__)

# FinBERT system prompt for JSON output
GLOBAL_NEWS_SYSTEM_PROMPT = """You are a financial market analyst AI. Your task is to analyze news headlines and their sentiment scores to determine the overall market outlook.

You MUST respond with valid JSON in this exact format:
{
    "score": <number from -100 to 100>,
    "confidence": <number from 0.0 to 1.0>,
    "summary": "<1-2 sentence market outlook summary>",
    "key_events": ["<event 1>", "<event 2>", ...],
    "reasoning": "<brief explanation of your score>"
}

Score guide:
- +80 to +100: Extremely bullish (strong positive catalysts)
- +40 to +79: Moderately bullish
- -39 to +39: Neutral/mixed
- -40 to -79: Moderately bearish
- -80 to -100: Extremely bearish (major negative events)
"""


class GlobalNewsAgent(BaseAgent):
    """
    Analyzes global/general market news to gauge overall sentiment.
    This produces ONE score per day for the entire market.
    """

    name = "global_news_agent"
    description = "Analyzes global market news for overall market sentiment"

    def __init__(self, db: Session, llm: LLMProvider | None = None):
        super().__init__(db)
        self.news_fetcher = NewsFetcher()
        self.llm = llm or LLMProvider()
        self._finbert_pipeline = None

    def _get_finbert(self):
        """Lazy-load FinBERT pipeline (heavy model, load once)."""
        if self._finbert_pipeline is None:
            try:
                from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
                model_name = "ProsusAI/finbert"
                tokenizer = AutoTokenizer.from_pretrained(model_name)
                model = AutoModelForSequenceClassification.from_pretrained(model_name)
                self._finbert_pipeline = pipeline(
                    "sentiment-analysis", model=model, tokenizer=tokenizer
                )
                self.logger.info("FinBERT loaded successfully.")
            except Exception as e:
                self.logger.warning(f"Failed to load FinBERT: {e}. Using LLM-only mode.")
        return self._finbert_pipeline

    def analyze_market(self, target_date: date) -> AgentScore:
        """
        Analyze global news and produce a market-wide sentiment score.
        This is called once per day, not per stock.
        """
        # Step 1: Fetch general market news
        articles = self.news_fetcher.fetch_general_news("general")
        if not articles:
            return AgentScore(
                stock_id=0,
                stock_symbol="MARKET",
                date=target_date,
                score=0.0,
                confidence=0.0,
                reasoning="No news articles available.",
            )

        # Step 2: Run FinBERT sentiment on headlines
        headlines = [a.headline for a in articles if a.headline]
        headline_sentiments = self._analyze_sentiments(headlines)

        # Step 3: Build prompt for Ollama summarization
        news_text = self._format_news_for_prompt(articles, headline_sentiments)
        prompt = f"""Analyze these global market news headlines and their AI-calculated sentiment scores.
Determine the overall market outlook for today.

{news_text}

Provide your analysis as JSON with score (-100 to +100), confidence, summary, key_events, and reasoning."""

        # Step 4: Get LLM analysis
        result = self.llm.analyze(prompt, GLOBAL_NEWS_SYSTEM_PROMPT)

        score = float(result.get("score", 0))
        confidence = float(result.get("confidence", 0.5))

        agent_score = AgentScore(
            stock_id=0,
            stock_symbol="MARKET",
            date=target_date,
            score=self.clamp_score(score),
            confidence=self.clamp_confidence(confidence),
            reasoning=result.get("reasoning", ""),
            signals={
                "summary": result.get("summary", ""),
                "key_events": result.get("key_events", []),
                "headline_count": len(headlines),
                "avg_finbert_sentiment": (
                    sum(s.get("finbert_score", 0) for s in headline_sentiments) / len(headline_sentiments)
                    if headline_sentiments else 0
                ),
            },
        )

        # Persist to DB
        self._persist_global_score(agent_score, result)
        return agent_score

    def analyze_stock(self, stock: Stock, target_date: date) -> AgentScore:
        """
        Global news agent produces a market-level score, not per-stock.
        For the BaseAgent interface, just return the cached market score.
        """
        return self.analyze_market(target_date)

    def _analyze_sentiments(self, headlines: list[str]) -> list[dict]:
        """Run FinBERT sentiment analysis on headlines."""
        finbert = self._get_finbert()
        results = []

        for headline in headlines:
            if finbert:
                try:
                    sentiment = finbert(headline[:512])[0]  # FinBERT max 512 tokens
                    label = sentiment["label"]  # "positive", "negative", "neutral"
                    conf = sentiment["score"]

                    # Convert to numeric score
                    if label == "positive":
                        finbert_score = conf * 100
                    elif label == "negative":
                        finbert_score = -conf * 100
                    else:
                        finbert_score = 0

                    results.append({
                        "headline": headline,
                        "label": label,
                        "confidence": round(conf, 3),
                        "finbert_score": round(finbert_score, 1),
                    })
                except Exception as e:
                    results.append({
                        "headline": headline,
                        "label": "unknown",
                        "confidence": 0,
                        "finbert_score": 0,
                    })
            else:
                # No FinBERT — just pass headlines to LLM
                results.append({
                    "headline": headline,
                    "label": "unknown",
                    "confidence": 0,
                    "finbert_score": 0,
                })

        return results

    def _format_news_for_prompt(
        self, articles: list, sentiments: list[dict]
    ) -> str:
        """Format news articles for the LLM prompt."""
        lines = []
        for i, (article, sent) in enumerate(zip(articles, sentiments), 1):
            sentiment_label = sent.get("label", "unknown")
            finbert_score = sent.get("finbert_score", 0)
            lines.append(
                f"{i}. [{sentiment_label.upper()} ({finbert_score:+.0f})] "
                f"{article.headline} — {article.source}"
            )
        return "\n".join(lines)

    def _persist_global_score(self, score: AgentScore, raw_result: dict) -> None:
        """Persist global news score to database."""
        upsert_global_news_score(self.db, {
            "date": score.date,
            "score": score.score,
            "confidence": score.confidence,
            "summary": raw_result.get("summary", ""),
            "key_events_json": raw_result.get("key_events", []),
            "reasoning": score.reasoning,
        })

    def _persist_score(self, score: AgentScore) -> None:
        """Required by BaseAgent — delegates to _persist_global_score."""
        self._persist_global_score(score, {"summary": "", "key_events": []})
