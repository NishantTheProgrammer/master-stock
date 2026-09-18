"""
Stock universe management.
Fetches and manages the list of stocks we track.
"""

import logging
from typing import Sequence

import pandas as pd
from sqlalchemy.orm import Session

from src.config import DEFAULT_STOCKS
from src.db.crud import get_all_stocks, upsert_stock
from src.db.models import Stock

logger = logging.getLogger(__name__)


def seed_default_stocks(db: Session) -> list[Stock]:
    """
    Seed the database with the default stock universe (top 20 Nifty stocks).
    Uses upsert to safely re-run without duplicates.
    """
    stocks = []
    for stock_data in DEFAULT_STOCKS:
        stock = upsert_stock(
            db,
            symbol=stock_data["symbol"],
            name=stock_data["name"],
            sector=stock_data["sector"],
            exchange="NSE",
        )
        stocks.append(stock)
        logger.info(f"Seeded stock: {stock.symbol} ({stock.name})")

    logger.info(f"Seeded {len(stocks)} stocks into the database.")
    return stocks


def fetch_nifty50_list() -> pd.DataFrame:
    """
    Fetch the current Nifty 50 constituent list from NSE.
    Falls back to defaults if the fetch fails.

    Returns:
        DataFrame with columns: Symbol, Company Name, Industry
    """
    try:
        url = "https://www1.nseindia.com/content/indices/ind_nifty50list.csv"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        }
        df = pd.read_csv(url, storage_options={"headers": headers})
        logger.info(f"Fetched {len(df)} stocks from Nifty 50 list.")
        return df
    except Exception as e:
        logger.warning(f"Failed to fetch Nifty 50 list from NSE: {e}. Using defaults.")
        return pd.DataFrame(DEFAULT_STOCKS)


def get_stock_symbols(db: Session) -> list[str]:
    """Get list of all active stock symbols."""
    stocks = get_all_stocks(db, active_only=True)
    return [s.symbol for s in stocks]


def get_sectors(db: Session) -> list[str]:
    """Get unique list of sectors from active stocks."""
    stocks = get_all_stocks(db, active_only=True)
    return sorted(set(s.sector for s in stocks))


def get_stocks_grouped_by_sector(db: Session) -> dict[str, Sequence[Stock]]:
    """Get stocks grouped by sector."""
    stocks = get_all_stocks(db, active_only=True)
    groups: dict[str, list[Stock]] = {}
    for stock in stocks:
        groups.setdefault(stock.sector, []).append(stock)
    return groups
