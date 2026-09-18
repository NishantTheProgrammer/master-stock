"""
SQLAlchemy ORM models for the Master Stock system.

Tables:
- stocks:              Stock universe (symbols, sectors)
- price_data:          Daily OHLCV price history
- technical_scores:    Technical analysis agent output
- global_news_scores:  Global market sentiment
- sector_scores:       Sector-level news sentiment
- stock_news_scores:   Company-specific news sentiment
- social_scores:       Social media sentiment
- predictions:         Final aggregated predictions
- sandbox_portfolios:  Sandbox agent portfolio snapshots
- sandbox_trades:      Sandbox trade log
- sandbox_performance: Sandbox daily performance metrics
"""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# ──────────────────────────────────────────────
# Stock Universe
# ──────────────────────────────────────────────

class Stock(Base):
    """A stock in our tracking universe."""
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sector: Mapped[str] = mapped_column(String(100), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), default="NSE")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    prices: Mapped[list["PriceData"]] = relationship(back_populates="stock", cascade="all, delete-orphan")
    technical_scores: Mapped[list["TechnicalScore"]] = relationship(back_populates="stock", cascade="all, delete-orphan")
    stock_news_scores: Mapped[list["StockNewsScore"]] = relationship(back_populates="stock", cascade="all, delete-orphan")
    social_scores: Mapped[list["SocialScore"]] = relationship(back_populates="stock", cascade="all, delete-orphan")
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="stock", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Stock {self.symbol} ({self.name})>"


# ──────────────────────────────────────────────
# Price Data
# ──────────────────────────────────────────────

class PriceData(Base):
    """Daily OHLCV price data for a stock."""
    __tablename__ = "price_data"
    __table_args__ = (
        UniqueConstraint("stock_id", "date", name="uq_price_stock_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(Integer, ForeignKey("stocks.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)
    adj_close: Mapped[float | None] = mapped_column(Float, nullable=True)

    stock: Mapped["Stock"] = relationship(back_populates="prices")

    def __repr__(self) -> str:
        return f"<PriceData {self.stock_id} {self.date} C={self.close}>"


# ──────────────────────────────────────────────
# Agent Scores
# ──────────────────────────────────────────────

class TechnicalScore(Base):
    """Score from the Technical Analysis agent."""
    __tablename__ = "technical_scores"
    __table_args__ = (
        UniqueConstraint("stock_id", "date", name="uq_tech_stock_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(Integer, ForeignKey("stocks.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)  # -100 to +100
    confidence: Mapped[float] = mapped_column(Float, default=0.5)  # 0.0 to 1.0
    signals_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Individual indicator signals
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    stock: Mapped["Stock"] = relationship(back_populates="technical_scores")

    def __repr__(self) -> str:
        return f"<TechnicalScore {self.stock_id} {self.date} score={self.score}>"


class GlobalNewsScore(Base):
    """Score from the Global News agent — one per day for the whole market."""
    __tablename__ = "global_news_scores"
    __table_args__ = (
        UniqueConstraint("date", name="uq_global_news_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)  # -100 to +100
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_events_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<GlobalNewsScore {self.date} score={self.score}>"


class SectorScore(Base):
    """Score from the Sector News agent — one per sector per day."""
    __tablename__ = "sector_scores"
    __table_args__ = (
        UniqueConstraint("sector", "date", name="uq_sector_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sector: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)  # -100 to +100
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_news_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<SectorScore {self.sector} {self.date} score={self.score}>"


class StockNewsScore(Base):
    """Score from the Stock News agent — one per stock per day."""
    __tablename__ = "stock_news_scores"
    __table_args__ = (
        UniqueConstraint("stock_id", "date", name="uq_stock_news_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(Integer, ForeignKey("stocks.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)  # -100 to +100
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    headlines_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    stock: Mapped["Stock"] = relationship(back_populates="stock_news_scores")

    def __repr__(self) -> str:
        return f"<StockNewsScore {self.stock_id} {self.date} score={self.score}>"


class SocialScore(Base):
    """Score from the Social agent — one per stock per day."""
    __tablename__ = "social_scores"
    __table_args__ = (
        UniqueConstraint("stock_id", "date", name="uq_social_stock_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(Integer, ForeignKey("stocks.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)  # -100 to +100
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    post_count: Mapped[int] = mapped_column(Integer, default=0)
    key_posts_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    stock: Mapped["Stock"] = relationship(back_populates="social_scores")

    def __repr__(self) -> str:
        return f"<SocialScore {self.stock_id} {self.date} score={self.score}>"


# ──────────────────────────────────────────────
# Predictions
# ──────────────────────────────────────────────

class Prediction(Base):
    """Final aggregated prediction for a stock on a given day."""
    __tablename__ = "predictions"
    __table_args__ = (
        UniqueConstraint("stock_id", "date", name="uq_prediction_stock_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(Integer, ForeignKey("stocks.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    up_probability: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 to 1.0
    down_probability: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 to 1.0
    expected_move_pct: Mapped[float] = mapped_column(Float, nullable=False)  # e.g., +2.5 or -1.3
    confidence: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 to 1.0
    suggested_action: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY / SELL / HOLD
    suggested_position_pct: Mapped[float | None] = mapped_column(Float, nullable=True)  # % of portfolio
    component_scores_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    stock: Mapped["Stock"] = relationship(back_populates="predictions")

    def __repr__(self) -> str:
        return f"<Prediction {self.stock_id} {self.date} {self.suggested_action} P(up)={self.up_probability:.0%}>"


# ──────────────────────────────────────────────
# Sandbox / Paper Trading
# ──────────────────────────────────────────────

class SandboxPortfolio(Base):
    """Daily snapshot of a sandbox agent's portfolio."""
    __tablename__ = "sandbox_portfolios"
    __table_args__ = (
        UniqueConstraint("agent_name", "date", name="uq_sandbox_portfolio_agent_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    cash: Mapped[float] = mapped_column(Float, nullable=False)
    holdings_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {"RELIANCE": {"qty": 10, "avg_price": 2500}}
    total_value: Mapped[float] = mapped_column(Float, nullable=False)

    def __repr__(self) -> str:
        return f"<SandboxPortfolio {self.agent_name} {self.date} ₹{self.total_value:,.0f}>"


class SandboxTrade(Base):
    """A trade executed by a sandbox agent."""
    __tablename__ = "sandbox_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    stock_id: Mapped[int] = mapped_column(Integer, ForeignKey("stocks.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY / SELL
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    fee: Mapped[float] = mapped_column(Float, default=0.0)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False)  # price * qty + fee
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<SandboxTrade {self.agent_name} {self.action} {self.quantity}x @ ₹{self.price}>"


class SandboxPerformance(Base):
    """Daily performance metrics for a sandbox agent."""
    __tablename__ = "sandbox_performance"
    __table_args__ = (
        UniqueConstraint("agent_name", "date", name="uq_sandbox_perf_agent_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    daily_return_pct: Mapped[float] = mapped_column(Float, nullable=False)
    cumulative_return_pct: Mapped[float] = mapped_column(Float, nullable=False)
    portfolio_value: Mapped[float] = mapped_column(Float, nullable=False)
    benchmark_value: Mapped[float | None] = mapped_column(Float, nullable=True)  # Nifty 50 value for comparison
    max_drawdown_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    sharpe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:
        return f"<SandboxPerformance {self.agent_name} {self.date} cum={self.cumulative_return_pct:.2f}%>"
