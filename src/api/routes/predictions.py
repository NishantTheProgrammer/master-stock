"""
Prediction API routes.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.engine import get_db
from src.db.models import Prediction, Stock

router = APIRouter()


@router.get("/latest")
def get_latest_predictions(
    target_date: date = Query(default=None),
    db: Session = Depends(get_db),
):
    """Get the latest predictions for all stocks."""
    if not target_date:
        latest = db.scalars(
            select(Prediction.date).order_by(Prediction.date.desc()).limit(1)
        ).first()
        target_date = latest or date.today()

    predictions = db.scalars(
        select(Prediction)
        .where(Prediction.date == target_date)
        .order_by(Prediction.up_probability.desc())
    ).all()

    results = []
    for p in predictions:
        stock = db.scalars(select(Stock).where(Stock.id == p.stock_id)).first()
        results.append({
            "symbol": stock.symbol if stock else "?",
            "name": stock.name if stock else "?",
            "sector": stock.sector if stock else "?",
            "date": str(p.date),
            "up_probability": p.up_probability,
            "down_probability": p.down_probability,
            "expected_move_pct": p.expected_move_pct,
            "confidence": p.confidence,
            "suggested_action": p.suggested_action,
            "suggested_position_pct": p.suggested_position_pct,
            "component_scores": p.component_scores_json,
            "reasoning": p.reasoning,
        })

    return results


@router.get("/{symbol}")
def get_prediction_history(
    symbol: str,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get prediction history for a specific stock."""
    stock = db.scalars(select(Stock).where(Stock.symbol == symbol.upper())).first()
    if not stock:
        return {"error": f"Stock {symbol} not found"}

    from datetime import timedelta
    start_date = date.today() - timedelta(days=days)

    predictions = db.scalars(
        select(Prediction)
        .where(Prediction.stock_id == stock.id, Prediction.date >= start_date)
        .order_by(Prediction.date)
    ).all()

    return {
        "symbol": stock.symbol,
        "predictions": [
            {
                "date": str(p.date),
                "up_probability": p.up_probability,
                "down_probability": p.down_probability,
                "expected_move_pct": p.expected_move_pct,
                "confidence": p.confidence,
                "suggested_action": p.suggested_action,
            }
            for p in predictions
        ],
    }
