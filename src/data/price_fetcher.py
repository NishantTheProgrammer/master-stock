"""
Price data fetcher using yfinance.
Fetches historical OHLCV data for NSE stocks and stores in the database.
"""

import logging
from datetime import date, timedelta

import pandas as pd
import yfinance as yf
from sqlalchemy.orm import Session

from src.db.crud import bulk_insert_prices, get_latest_price_date
from src.db.models import Stock

logger = logging.getLogger(__name__)


def _to_nse_ticker(symbol: str) -> str:
    """Convert an NSE symbol to yfinance ticker format (append .NS)."""
    return f"{symbol}.NS"


def fetch_prices_for_stock(
    db: Session,
    stock: Stock,
    lookback_days: int = 365,
    force_full: bool = False,
) -> int:
    """
    Fetch historical price data for a single stock and store in DB.
    Supports incremental fetching — only downloads new data since last stored date.

    Args:
        db: Database session
        stock: Stock ORM object
        lookback_days: How many days of history to fetch on first run
        force_full: If True, re-fetch full history ignoring existing data

    Returns:
        Number of new rows inserted
    """
    ticker = _to_nse_ticker(stock.symbol)

    # Determine start date — incremental or full
    if not force_full:
        latest_date = get_latest_price_date(db, stock.id)
        if latest_date:
            # Fetch from next day after the latest stored date
            start_date = latest_date + timedelta(days=1)
            if start_date > date.today():
                logger.info(f"{stock.symbol}: Already up to date (latest={latest_date})")
                return 0
        else:
            start_date = date.today() - timedelta(days=lookback_days)
    else:
        start_date = date.today() - timedelta(days=lookback_days)

    end_date = date.today()
    logger.info(f"{stock.symbol}: Fetching prices from {start_date} to {end_date}")

    try:
        df = yf.download(
            ticker,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            progress=False,
            auto_adjust=True,
        )

        if df.empty:
            logger.warning(f"{stock.symbol}: No price data returned from yfinance.")
            return 0

        # Flatten multi-level columns if present (yfinance sometimes returns MultiIndex)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Prepare rows for bulk insert
        rows = []
        for idx, row in df.iterrows():
            price_date = idx.date() if hasattr(idx, "date") else idx
            rows.append({
                "stock_id": stock.id,
                "date": price_date,
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
                "adj_close": round(float(row["Close"]), 2),  # auto_adjust=True means Close IS adjusted
            })

        inserted = bulk_insert_prices(db, rows)
        logger.info(f"{stock.symbol}: Inserted {inserted} new price rows.")
        return inserted

    except Exception as e:
        logger.error(f"{stock.symbol}: Failed to fetch prices: {e}")
        return 0


def fetch_prices_for_all(
    db: Session,
    stocks: list[Stock],
    lookback_days: int = 365,
    force_full: bool = False,
) -> dict[str, int]:
    """
    Fetch prices for all stocks in the universe.

    Returns:
        Dict mapping symbol → number of rows inserted
    """
    results = {}
    for stock in stocks:
        count = fetch_prices_for_stock(db, stock, lookback_days, force_full)
        results[stock.symbol] = count

    total = sum(results.values())
    logger.info(f"Total: Fetched {total} new price rows across {len(stocks)} stocks.")
    return results


def get_price_dataframe(db: Session, stock: Stock, days: int = 90) -> pd.DataFrame:
    """
    Get price data for a stock as a pandas DataFrame (for technical analysis).

    Returns:
        DataFrame with columns: Date, Open, High, Low, Close, Volume (indexed by Date)
    """
    from src.db.crud import get_prices

    start_date = date.today() - timedelta(days=days)
    prices = get_prices(db, stock.id, start_date=start_date)

    if not prices:
        return pd.DataFrame()

    data = [{
        "Date": p.date,
        "Open": p.open,
        "High": p.high,
        "Low": p.low,
        "Close": p.close,
        "Volume": p.volume,
    } for p in prices]

    df = pd.DataFrame(data)
    df.set_index("Date", inplace=True)
    df.index = pd.DatetimeIndex(df.index)
    return df
