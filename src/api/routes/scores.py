"""
Agent scores API routes.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.engine import get_db
from src.db.models import (
    GlobalNewsScore,
    SectorScore,
    SocialScore,
    StockNewsScore,
    TechnicalScore,
    Stock,
)
from src.db.crud import get_latest_scores_for_stock

router = APIRouter()


@router.get("/latest")
def get_latest_scores(
    target_date: date = Query(default=None),
    db: Session = Depends(get_db),
):
    """Get the latest scores from all agents for all stocks."""
    if not target_date:
        # Find the most recent date with scores
        latest = db.scalars(
            select(TechnicalScore.date)
            .order_by(TechnicalScore.date.desc())
            .limit(1)
        ).first()
        target_date = latest or date.today()

    stocks = db.scalars(
        select(Stock).where(Stock.is_active.is_(True)).order_by(Stock.symbol)
    ).all()

    results = []
    for stock in stocks:
        scores = get_latest_scores_for_stock(db, stock.id, target_date)
        results.append({
            "symbol": stock.symbol,
            "name": stock.name,
            "sector": stock.sector,
            "date": str(target_date),
            "technical": _score_dict(scores["technical"]),
            "global_news": _score_dict(scores["global_news"]),
            "sector_news": _score_dict(scores["sector"]),
            "stock_news": _score_dict(scores["stock_news"]),
            "social": _score_dict(scores["social"]),
        })

    return results


@router.get("/history/{symbol}")
def get_score_history(
    symbol: str,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get score history for a specific stock."""
    stock = db.scalars(select(Stock).where(Stock.symbol == symbol.upper())).first()
    if not stock:
        return {"error": f"Stock {symbol} not found"}

    from datetime import timedelta
    start_date = date.today() - timedelta(days=days)

    technical = db.scalars(
        select(TechnicalScore)
        .where(TechnicalScore.stock_id == stock.id, TechnicalScore.date >= start_date)
        .order_by(TechnicalScore.date)
    ).all()

    stock_news = db.scalars(
        select(StockNewsScore)
        .where(StockNewsScore.stock_id == stock.id, StockNewsScore.date >= start_date)
        .order_by(StockNewsScore.date)
    ).all()

    social = db.scalars(
        select(SocialScore)
        .where(SocialScore.stock_id == stock.id, SocialScore.date >= start_date)
        .order_by(SocialScore.date)
    ).all()

    return {
        "symbol": stock.symbol,
        "technical": [{"date": str(s.date), "score": s.score, "confidence": s.confidence} for s in technical],
        "stock_news": [{"date": str(s.date), "score": s.score, "confidence": s.confidence} for s in stock_news],
        "social": [{"date": str(s.date), "score": s.score, "confidence": s.confidence} for s in social],
    }


def _score_dict(obj) -> dict | None:
    """Convert a score ORM object to a dict."""
    if not obj:
        return None
    return {
        "score": obj.score,
        "confidence": obj.confidence,
        "reasoning": getattr(obj, "reasoning", ""),
    }
