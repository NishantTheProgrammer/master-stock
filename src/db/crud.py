"""
CRUD (Create, Read, Update, Delete) helper functions for database operations.
"""

from datetime import date
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from src.db.models import (
    GlobalNewsScore,
    PriceData,
    Prediction,
    SandboxPerformance,
    SandboxPortfolio,
    SandboxTrade,
    SectorScore,
    SocialScore,
    Stock,
    StockNewsScore,
    TechnicalScore,
)


# ──────────────────────────────────────────────
# Stocks
# ──────────────────────────────────────────────

def get_all_stocks(db: Session, active_only: bool = True) -> Sequence[Stock]:
    """Get all stocks, optionally filtered to active only."""
    stmt = select(Stock)
    if active_only:
        stmt = stmt.where(Stock.is_active.is_(True))
    return db.scalars(stmt.order_by(Stock.symbol)).all()


def get_stock_by_symbol(db: Session, symbol: str) -> Stock | None:
    """Get a single stock by its NSE symbol."""
    return db.scalars(select(Stock).where(Stock.symbol == symbol)).first()


def get_stocks_by_sector(db: Session, sector: str) -> Sequence[Stock]:
    """Get all active stocks in a sector."""
    return db.scalars(
        select(Stock)
        .where(Stock.sector == sector, Stock.is_active.is_(True))
        .order_by(Stock.symbol)
    ).all()


def upsert_stock(db: Session, symbol: str, name: str, sector: str, exchange: str = "NSE") -> Stock:
    """Insert a stock or update it if it already exists."""
    stmt = pg_insert(Stock).values(
        symbol=symbol, name=name, sector=sector, exchange=exchange
    ).on_conflict_do_update(
        index_elements=["symbol"],
        set_={"name": name, "sector": sector, "exchange": exchange, "is_active": True},
    ).returning(Stock)
    result = db.execute(stmt)
    db.commit()
    return result.scalar_one()


# ──────────────────────────────────────────────
# Price Data
# ──────────────────────────────────────────────

def get_prices(
    db: Session, stock_id: int, start_date: date | None = None, end_date: date | None = None
) -> Sequence[PriceData]:
    """Get price history for a stock with optional date range."""
    stmt = select(PriceData).where(PriceData.stock_id == stock_id)
    if start_date:
        stmt = stmt.where(PriceData.date >= start_date)
    if end_date:
        stmt = stmt.where(PriceData.date <= end_date)
    return db.scalars(stmt.order_by(PriceData.date)).all()


def get_latest_price_date(db: Session, stock_id: int) -> date | None:
    """Get the most recent price date for a stock (for incremental fetching)."""
    result = db.scalars(
        select(PriceData.date)
        .where(PriceData.stock_id == stock_id)
        .order_by(PriceData.date.desc())
        .limit(1)
    ).first()
    return result


def bulk_insert_prices(db: Session, prices: list[dict]) -> int:
    """Bulk insert price data, skipping conflicts on (stock_id, date)."""
    if not prices:
        return 0
    stmt = pg_insert(PriceData).values(prices).on_conflict_do_nothing(
        constraint="uq_price_stock_date"
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount


# ──────────────────────────────────────────────
# Agent Scores — Upsert pattern (insert or update)
# ──────────────────────────────────────────────

def upsert_technical_score(db: Session, data: dict) -> None:
    """Upsert a technical score for a stock on a date."""
    stmt = pg_insert(TechnicalScore).values(**data).on_conflict_do_update(
        constraint="uq_tech_stock_date",
        set_={k: v for k, v in data.items() if k not in ("stock_id", "date")},
    )
    db.execute(stmt)
    db.commit()


def upsert_global_news_score(db: Session, data: dict) -> None:
    """Upsert the global news score for a date."""
    stmt = pg_insert(GlobalNewsScore).values(**data).on_conflict_do_update(
        constraint="uq_global_news_date",
        set_={k: v for k, v in data.items() if k != "date"},
    )
    db.execute(stmt)
    db.commit()


def upsert_sector_score(db: Session, data: dict) -> None:
    """Upsert a sector score."""
    stmt = pg_insert(SectorScore).values(**data).on_conflict_do_update(
        constraint="uq_sector_date",
        set_={k: v for k, v in data.items() if k not in ("sector", "date")},
    )
    db.execute(stmt)
    db.commit()


def upsert_stock_news_score(db: Session, data: dict) -> None:
    """Upsert a stock news score."""
    stmt = pg_insert(StockNewsScore).values(**data).on_conflict_do_update(
        constraint="uq_stock_news_date",
        set_={k: v for k, v in data.items() if k not in ("stock_id", "date")},
    )
    db.execute(stmt)
    db.commit()


def upsert_social_score(db: Session, data: dict) -> None:
    """Upsert a social score."""
    stmt = pg_insert(SocialScore).values(**data).on_conflict_do_update(
        constraint="uq_social_stock_date",
        set_={k: v for k, v in data.items() if k not in ("stock_id", "date")},
    )
    db.execute(stmt)
    db.commit()


# ──────────────────────────────────────────────
# Score Retrieval
# ──────────────────────────────────────────────

def get_latest_scores_for_stock(db: Session, stock_id: int, target_date: date) -> dict:
    """Get the latest scores from all agents for a stock on a given date."""
    technical = db.scalars(
        select(TechnicalScore)
        .where(TechnicalScore.stock_id == stock_id, TechnicalScore.date == target_date)
    ).first()

    global_news = db.scalars(
        select(GlobalNewsScore).where(GlobalNewsScore.date == target_date)
    ).first()

    # Find the stock's sector
    stock = db.scalars(select(Stock).where(Stock.id == stock_id)).first()
    sector = None
    if stock:
        sector = db.scalars(
            select(SectorScore)
            .where(SectorScore.sector == stock.sector, SectorScore.date == target_date)
        ).first()

    stock_news = db.scalars(
        select(StockNewsScore)
        .where(StockNewsScore.stock_id == stock_id, StockNewsScore.date == target_date)
    ).first()

    social = db.scalars(
        select(SocialScore)
        .where(SocialScore.stock_id == stock_id, SocialScore.date == target_date)
    ).first()

    return {
        "technical": technical,
        "global_news": global_news,
        "sector": sector,
        "stock_news": stock_news,
        "social": social,
    }


# ──────────────────────────────────────────────
# Predictions
# ──────────────────────────────────────────────

def upsert_prediction(db: Session, data: dict) -> None:
    """Upsert a prediction."""
    stmt = pg_insert(Prediction).values(**data).on_conflict_do_update(
        constraint="uq_prediction_stock_date",
        set_={k: v for k, v in data.items() if k not in ("stock_id", "date")},
    )
    db.execute(stmt)
    db.commit()


def get_latest_predictions(db: Session, target_date: date) -> Sequence[Prediction]:
    """Get all predictions for a given date."""
    return db.scalars(
        select(Prediction)
        .where(Prediction.date == target_date)
        .order_by(Prediction.up_probability.desc())
    ).all()


# ──────────────────────────────────────────────
# Sandbox
# ──────────────────────────────────────────────

def save_sandbox_portfolio(db: Session, data: dict) -> None:
    """Save a sandbox portfolio snapshot."""
    stmt = pg_insert(SandboxPortfolio).values(**data).on_conflict_do_update(
        constraint="uq_sandbox_portfolio_agent_date",
        set_={k: v for k, v in data.items() if k not in ("agent_name", "date")},
    )
    db.execute(stmt)
    db.commit()


def save_sandbox_trade(db: Session, data: dict) -> None:
    """Record a sandbox trade."""
    trade = SandboxTrade(**data)
    db.add(trade)
    db.commit()


def save_sandbox_performance(db: Session, data: dict) -> None:
    """Save sandbox daily performance."""
    stmt = pg_insert(SandboxPerformance).values(**data).on_conflict_do_update(
        constraint="uq_sandbox_perf_agent_date",
        set_={k: v for k, v in data.items() if k not in ("agent_name", "date")},
    )
    db.execute(stmt)
    db.commit()


def get_sandbox_performance(
    db: Session, agent_name: str | None = None
) -> Sequence[SandboxPerformance]:
    """Get sandbox performance data, optionally filtered by agent."""
    stmt = select(SandboxPerformance)
    if agent_name:
        stmt = stmt.where(SandboxPerformance.agent_name == agent_name)
    return db.scalars(stmt.order_by(SandboxPerformance.date)).all()


def get_sandbox_trades(
    db: Session, agent_name: str | None = None
) -> Sequence[SandboxTrade]:
    """Get sandbox trades, optionally filtered by agent."""
    stmt = select(SandboxTrade)
    if agent_name:
        stmt = stmt.where(SandboxTrade.agent_name == agent_name)
    return db.scalars(stmt.order_by(SandboxTrade.date, SandboxTrade.created_at)).all()
