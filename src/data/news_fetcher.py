"""
News data fetcher using Finnhub API.
Fetches global market news, sector news, and company-specific news.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime

import finnhub
import httpx

from src.config import settings

logger = logging.getLogger(__name__)


@dataclass
class NewsArticle:
    """Structured news article."""
    headline: str
    summary: str
    source: str
    url: str
    published_at: datetime
    category: str = ""
    related_tickers: list[str] = field(default_factory=list)
    image_url: str = ""


class NewsFetcher:
    """Fetches financial news from Finnhub API."""

    def __init__(self):
        self.api_key = settings.finnhub_api_key
        if self.api_key:
            self.client = finnhub.Client(api_key=self.api_key)
        else:
            self.client = None
            logger.warning(
                "Finnhub API key not configured. News fetching will be limited. "
                "Set FINNHUB_API_KEY in your .env file."
            )

    def _ensure_client(self) -> bool:
        """Check if the Finnhub client is available."""
        if not self.client:
            logger.warning("Finnhub client not initialized — skipping news fetch.")
            return False
        return True

    def fetch_general_news(self, category: str = "general") -> list[NewsArticle]:
        """
        Fetch general market news.

        Args:
            category: "general", "forex", "crypto", or "merger"

        Returns:
            List of NewsArticle objects
        """
        if not self._ensure_client():
            return []

        try:
            raw_news = self.client.general_news(category, min_id=0)
            articles = []
            for item in raw_news[:20]:  # Limit to top 20
                articles.append(NewsArticle(
                    headline=item.get("headline", ""),
                    summary=item.get("summary", ""),
                    source=item.get("source", ""),
                    url=item.get("url", ""),
                    published_at=datetime.fromtimestamp(item.get("datetime", 0)),
                    category=item.get("category", category),
                    image_url=item.get("image", ""),
                ))
            logger.info(f"Fetched {len(articles)} general news articles (category={category}).")
            return articles

        except Exception as e:
            logger.error(f"Failed to fetch general news: {e}")
            return []

    def fetch_company_news(
        self,
        symbol: str,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[NewsArticle]:
        """
        Fetch news specific to a company.
        Note: Finnhub uses US tickers. For Indian stocks, we search by name as well.

        Args:
            symbol: Stock symbol (e.g., "RELIANCE")
            from_date: Start date in YYYY-MM-DD format
            to_date: End date in YYYY-MM-DD format

        Returns:
            List of NewsArticle objects
        """
        if not self._ensure_client():
            return []

        if not from_date:
            from datetime import timedelta, date
            from_date = (date.today() - timedelta(days=7)).isoformat()
        if not to_date:
            from datetime import date
            to_date = date.today().isoformat()

        try:
            # Try with .NS suffix for NSE stocks
            nse_symbol = f"{symbol}.NS"
            raw_news = self.client.company_news(nse_symbol, _from=from_date, to=to_date)

            # If no results with .NS, try with .BO (BSE) and plain symbol
            if not raw_news:
                raw_news = self.client.company_news(f"{symbol}.BO", _from=from_date, to=to_date)
            if not raw_news:
                raw_news = self.client.company_news(symbol, _from=from_date, to=to_date)

            articles = []
            for item in raw_news[:15]:  # Limit per stock
                articles.append(NewsArticle(
                    headline=item.get("headline", ""),
                    summary=item.get("summary", ""),
                    source=item.get("source", ""),
                    url=item.get("url", ""),
                    published_at=datetime.fromtimestamp(item.get("datetime", 0)),
                    category="company",
                    related_tickers=item.get("related", "").split(",") if item.get("related") else [symbol],
                    image_url=item.get("image", ""),
                ))

            logger.info(f"Fetched {len(articles)} news articles for {symbol}.")
            return articles

        except Exception as e:
            logger.error(f"Failed to fetch news for {symbol}: {e}")
            return []

    def fetch_sector_news(self, sector: str, keywords: list[str] | None = None) -> list[NewsArticle]:
        """
        Fetch news related to a sector by searching general news
        and filtering by sector-relevant keywords.

        Args:
            sector: Sector name (e.g., "Banking", "IT")
            keywords: Additional keywords to search for

        Returns:
            List of relevant NewsArticle objects
        """
        # Sector → search keywords mapping
        sector_keywords = {
            "IT": ["technology", "software", "IT services", "digital", "cloud computing"],
            "Banking": ["banking", "RBI", "interest rate", "NBFC", "credit", "loan"],
            "Finance": ["financial services", "insurance", "mutual fund", "fintech"],
            "Pharma": ["pharmaceutical", "drug", "FDA", "healthcare", "biotech"],
            "Auto": ["automobile", "EV", "electric vehicle", "car sales", "auto"],
            "FMCG": ["consumer goods", "FMCG", "retail", "consumption"],
            "Energy": ["oil", "gas", "energy", "petroleum", "renewable", "solar"],
            "Metals": ["steel", "metals", "mining", "aluminum", "copper"],
            "Realty": ["real estate", "property", "housing", "construction"],
            "Infrastructure": ["infrastructure", "roads", "railway", "ports"],
            "Telecom": ["telecom", "5G", "broadband", "spectrum"],
            "Media": ["media", "entertainment", "OTT", "broadcasting"],
            "Chemicals": ["chemicals", "specialty chemicals", "fertilizer"],
            "Cement": ["cement", "construction materials"],
            "Consumer Durables": ["consumer electronics", "appliances", "durables"],
        }

        search_terms = sector_keywords.get(sector, [sector.lower()])
        if keywords:
            search_terms.extend(keywords)

        # Get general news and filter by sector keywords
        all_news = self.fetch_general_news("general")
        sector_articles = []

        for article in all_news:
            text = f"{article.headline} {article.summary}".lower()
            if any(kw.lower() in text for kw in search_terms):
                article.category = f"sector:{sector}"
                sector_articles.append(article)

        logger.info(f"Found {len(sector_articles)} sector-relevant articles for {sector}.")
        return sector_articles


# Alternative: Fetch Indian financial news via web scraping (backup)
class IndianNewsSearcher:
    """
    Backup news fetcher that searches Indian financial news sites.
    Used when Finnhub doesn't return relevant Indian market news.
    """

    SEARCH_SOURCES = [
        "https://economictimes.indiatimes.com",
        "https://www.moneycontrol.com",
        "https://www.livemint.com",
    ]

    def __init__(self):
        self.http_client = httpx.Client(
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
        )

    def search_news(self, query: str, max_results: int = 10) -> list[dict]:
        """
        Search for Indian financial news using a query string.
        Returns raw search results as dicts.
        This is a placeholder — implement with a proper search API or scraper.
        """
        logger.info(f"IndianNewsSearcher: Searching for '{query}' (placeholder)")
        # TODO: Implement actual Indian news search
        # Options: Google News RSS, NewsAPI, or direct scraping
        return []
