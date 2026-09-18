"""
Stock API routes.
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.crud import get_all_stocks, get_prices, get_stock_by_symbol
from src.db.engine import get_db

router = APIRouter()


@router.get("")
def list_stocks(db: Session = Depends(get_db)):
    """List all active stocks with basic info."""
    stocks = get_all_stocks(db, active_only=True)
    return [
        {
            "id": s.id,
            "symbol": s.symbol,
            "name": s.name,
            "sector": s.sector,
            "exchange": s.exchange,
        }
        for s in stocks
    ]


@router.get("/{symbol}")
def get_stock(symbol: str, db: Session = Depends(get_db)):
    """Get detailed info for a single stock."""
    stock = get_stock_by_symbol(db, symbol.upper())
    if not stock:
        return {"error": f"Stock {symbol} not found"}

    # Get recent prices
    recent_prices = get_prices(
        db, stock.id,
        start_date=date.today() - timedelta(days=30),
    )

    return {
        "id": stock.id,
        "symbol": stock.symbol,
        "name": stock.name,
        "sector": stock.sector,
        "exchange": stock.exchange,
        "recent_prices": [
            {
                "date": str(p.date),
                "open": p.open,
                "high": p.high,
                "low": p.low,
                "close": p.close,
                "volume": p.volume,
            }
            for p in recent_prices[-10:]  # Last 10 days
        ],
    }
