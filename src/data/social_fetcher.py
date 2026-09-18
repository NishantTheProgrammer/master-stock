"""
Social media sentiment fetcher using Stocktwits API.
Stocktwits is a free, finance-focused social platform — no API key needed for public data.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

STOCKTWITS_API_BASE = "https://api.stocktwits.com/api/2"


@dataclass
class SocialPost:
    """A social media post with sentiment information."""
    username: str
    message: str
    sentiment: str  # "Bullish", "Bearish", or "Neutral"
    timestamp: datetime
    followers_count: int = 0
    likes_count: int = 0
    post_id: str = ""
    source: str = "stocktwits"


class SocialFetcher:
    """Fetches social sentiment data from Stocktwits."""

    def __init__(self):
        self.http_client = httpx.Client(
            base_url=STOCKTWITS_API_BASE,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "Accept": "application/json",
            },
        )

    def fetch_stock_posts(self, symbol: str, limit: int = 30) -> list[SocialPost]:
        """
        Fetch recent posts about a stock from Stocktwits.

        Args:
            symbol: Stock symbol (e.g., "RELIANCE")
            limit: Max number of posts to fetch (API max is 30)

        Returns:
            List of SocialPost objects
        """
        # Stocktwits uses $ prefix tickers. Indian stocks may need .NS suffix
        # Try both formats: RELIANCE.NS and RELIANCE
        posts = self._try_fetch(f"{symbol}.NS", limit)
        if not posts:
            posts = self._try_fetch(symbol, limit)
        return posts

    def _try_fetch(self, ticker: str, limit: int) -> list[SocialPost]:
        """Attempt to fetch posts for a given ticker format."""
        try:
            response = self.http_client.get(
                f"/streams/symbol/{ticker}.json",
                params={"limit": min(limit, 30)},
            )

            if response.status_code == 404:
                logger.debug(f"Stocktwits: No stream found for {ticker}")
                return []

            if response.status_code == 429:
                logger.warning("Stocktwits: Rate limited. Backing off.")
                return []

            response.raise_for_status()
            data = response.json()

            messages = data.get("messages", [])
            posts = []

            for msg in messages:
                # Extract sentiment — Stocktwits users can tag posts as Bullish/Bearish
                sentiment_data = msg.get("entities", {}).get("sentiment")
                if sentiment_data:
                    sentiment = sentiment_data.get("basic", "Neutral")
                else:
                    sentiment = "Neutral"

                user = msg.get("user", {})

                posts.append(SocialPost(
                    username=user.get("username", "unknown"),
                    message=msg.get("body", ""),
                    sentiment=sentiment,
                    timestamp=datetime.strptime(
                        msg.get("created_at", "2024-01-01T00:00:00Z"),
                        "%Y-%m-%dT%H:%M:%SZ"
                    ) if msg.get("created_at") else datetime.utcnow(),
                    followers_count=user.get("followers", 0),
                    likes_count=msg.get("likes", {}).get("total", 0),
                    post_id=str(msg.get("id", "")),
                    source="stocktwits",
                ))

            logger.info(f"Stocktwits: Fetched {len(posts)} posts for {ticker}")
            return posts

        except httpx.HTTPStatusError as e:
            logger.error(f"Stocktwits HTTP error for {ticker}: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Stocktwits error for {ticker}: {e}")
            return []

    def fetch_trending(self) -> list[dict]:
        """
        Fetch currently trending stocks on Stocktwits.
        Useful for identifying market buzz.

        Returns:
            List of dicts with symbol, watchlist_count, title
        """
        try:
            response = self.http_client.get("/trending/symbols.json")
            response.raise_for_status()
            data = response.json()

            symbols = data.get("symbols", [])
            trending = []
            for sym in symbols[:20]:
                trending.append({
                    "symbol": sym.get("symbol", ""),
                    "title": sym.get("title", ""),
                    "watchlist_count": sym.get("watchlist_count", 0),
                })

            logger.info(f"Stocktwits: Fetched {len(trending)} trending symbols.")
            return trending

        except Exception as e:
            logger.error(f"Failed to fetch trending symbols: {e}")
            return []

    def calculate_sentiment_summary(self, posts: list[SocialPost]) -> dict:
        """
        Calculate aggregate sentiment from a list of posts.
        Weights posts by follower count for influence-adjusted scoring.

        Returns:
            Dict with bullish_pct, bearish_pct, neutral_pct, weighted_score, post_count
        """
        if not posts:
            return {
                "bullish_pct": 0.0,
                "bearish_pct": 0.0,
                "neutral_pct": 0.0,
                "weighted_score": 0.0,
                "post_count": 0,
            }

        total_weight = 0.0
        weighted_sentiment = 0.0
        bullish = 0
        bearish = 0
        neutral = 0

        for post in posts:
            # Weight by follower count (min 1 to avoid zero weight)
            weight = max(1, post.followers_count)
            total_weight += weight

            if post.sentiment == "Bullish":
                weighted_sentiment += weight * 1.0
                bullish += 1
            elif post.sentiment == "Bearish":
                weighted_sentiment -= weight * 1.0
                bearish += 1
            else:
                neutral += 1

        total_posts = len(posts)
        score = (weighted_sentiment / total_weight) * 100 if total_weight > 0 else 0.0

        return {
            "bullish_pct": round(bullish / total_posts * 100, 1) if total_posts else 0.0,
            "bearish_pct": round(bearish / total_posts * 100, 1) if total_posts else 0.0,
            "neutral_pct": round(neutral / total_posts * 100, 1) if total_posts else 0.0,
            "weighted_score": round(score, 2),  # -100 to +100
            "post_count": total_posts,
        }
