"""
Social Media Sentiment Agent.
Analyzes social media posts (Stocktwits) about stocks for sentiment signals.
"""

import logging
from datetime import date

from sqlalchemy.orm import Session

from src.agents.base_agent import AgentScore, BaseAgent
from src.agents.llm_provider import LLMProvider
from src.data.social_fetcher import SocialFetcher
from src.db.crud import upsert_social_score
from src.db.models import Stock

logger = logging.getLogger(__name__)

SOCIAL_SYSTEM_PROMPT = """You are a social media sentiment analyst specializing in stock markets. Analyze social media posts about a stock to gauge crowd sentiment and identify notable signals.

You MUST respond with valid JSON in this exact format:
{
    "score": <number from -100 to 100>,
    "confidence": <number from 0.0 to 1.0>,
    "summary": "<1-2 sentence sentiment summary>",
    "notable_signals": ["<signal 1>", "<signal 2>", ...],
    "reasoning": "<explanation of your score>"
}

Consider:
- Ratio of bullish vs bearish posts
- Posts from users with large followings carry more weight
- Volume of discussion (high buzz can indicate momentum)
- Specific claims or insider knowledge mentions
- Unusual activity patterns (sudden spike in posts)

Be cautious: social media is noisy. Low post counts = low confidence.
"""


class SocialAgent(BaseAgent):
    """
    Analyzes social media sentiment for each stock.
    Uses Stocktwits data + optional LLM for deeper analysis.
    """

    name = "social_agent"
    description = "Analyzes social media sentiment from Stocktwits"

    def __init__(self, db: Session, llm: LLMProvider | None = None):
        super().__init__(db)
        self.social_fetcher = SocialFetcher()
        self.llm = llm or LLMProvider()

    def analyze_stock(self, stock: Stock, target_date: date) -> AgentScore:
        """Analyze social media sentiment for a stock."""
        posts = self.social_fetcher.fetch_stock_posts(stock.symbol)

        if not posts:
            return AgentScore(
                stock_id=stock.id,
                stock_symbol=stock.symbol,
                date=target_date,
                score=0.0,
                confidence=0.1,
                reasoning=f"No social media posts found for {stock.symbol}.",
            )

        # Calculate basic sentiment stats from Stocktwits native sentiment tags
        sentiment_summary = self.social_fetcher.calculate_sentiment_summary(posts)

        # If we have enough posts, use LLM for deeper analysis
        if len(posts) >= 5:
            score = self._llm_analysis(stock, posts, sentiment_summary, target_date)
        else:
            # Few posts — just use the weighted sentiment score directly
            score = AgentScore(
                stock_id=stock.id,
                stock_symbol=stock.symbol,
                date=target_date,
                score=self.clamp_score(sentiment_summary["weighted_score"]),
                confidence=self.clamp_confidence(min(0.3, len(posts) / 20)),
                reasoning=(
                    f"Low social activity ({len(posts)} posts). "
                    f"Bullish: {sentiment_summary['bullish_pct']:.0f}%, "
                    f"Bearish: {sentiment_summary['bearish_pct']:.0f}%"
                ),
                signals=sentiment_summary,
            )

        return score

    def _llm_analysis(
        self,
        stock: Stock,
        posts: list,
        sentiment_summary: dict,
        target_date: date,
    ) -> AgentScore:
        """Use LLM for deeper sentiment analysis when enough posts exist."""
        # Format posts for the prompt (top posts by follower count)
        sorted_posts = sorted(posts, key=lambda p: p.followers_count, reverse=True)
        post_lines = []
        for i, post in enumerate(sorted_posts[:15], 1):  # Top 15 posts
            post_lines.append(
                f"  {i}. @{post.username} (followers: {post.followers_count:,}) "
                f"[{post.sentiment}]: {post.message[:200]}"
            )

        posts_text = "\n".join(post_lines)

        prompt = f"""Analyze these social media posts about {stock.name} ({stock.symbol}) from Stocktwits.

Posts (sorted by influence):
{posts_text}

Aggregate stats:
- Total posts: {sentiment_summary['post_count']}
- Bullish: {sentiment_summary['bullish_pct']:.1f}%
- Bearish: {sentiment_summary['bearish_pct']:.1f}%
- Neutral: {sentiment_summary['neutral_pct']:.1f}%
- Influence-weighted score: {sentiment_summary['weighted_score']:+.1f}

Provide your social sentiment analysis as JSON with score, confidence, summary, notable_signals, and reasoning."""

        result = self.llm.analyze(prompt, SOCIAL_SYSTEM_PROMPT)

        return AgentScore(
            stock_id=stock.id,
            stock_symbol=stock.symbol,
            date=target_date,
            score=self.clamp_score(float(result.get("score", sentiment_summary["weighted_score"]))),
            confidence=self.clamp_confidence(float(result.get("confidence", 0.4))),
            reasoning=result.get("reasoning", ""),
            signals={
                **sentiment_summary,
                "summary": result.get("summary", ""),
                "notable_signals": result.get("notable_signals", []),
            },
        )

    def _persist_score(self, score: AgentScore) -> None:
        """Save social score to database."""
        upsert_social_score(self.db, {
            "stock_id": score.stock_id,
            "date": score.date,
            "score": score.score,
            "confidence": score.confidence,
            "post_count": score.signals.get("post_count", 0),
            "key_posts_json": score.signals.get("notable_signals", []),
            "reasoning": score.reasoning,
        })
