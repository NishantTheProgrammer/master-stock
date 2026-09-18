"""
Sandbox / Paper Trading API routes.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from src.db.engine import get_db
from src.db.models import SandboxPerformance, SandboxPortfolio, SandboxTrade

router = APIRouter()


@router.get("/results")
def get_sandbox_results(db: Session = Depends(get_db)):
    """Get sandbox performance data for all agents."""
    performance = db.scalars(
        select(SandboxPerformance).order_by(SandboxPerformance.date)
    ).all()

    # Group by agent
    agents: dict[str, list] = {}
    for p in performance:
        agents.setdefault(p.agent_name, []).append({
            "date": str(p.date),
            "daily_return_pct": p.daily_return_pct,
            "cumulative_return_pct": p.cumulative_return_pct,
            "portfolio_value": p.portfolio_value,
            "max_drawdown_pct": p.max_drawdown_pct,
        })

    return agents


@router.get("/agents")
def get_sandbox_agents(db: Session = Depends(get_db)):
    """Get summary stats for each sandbox agent."""
    # Get distinct agent names
    agent_names = db.scalars(
        select(SandboxPerformance.agent_name).distinct()
    ).all()

    summaries = []
    for name in agent_names:
        # Get latest performance
        latest = db.scalars(
            select(SandboxPerformance)
            .where(SandboxPerformance.agent_name == name)
            .order_by(SandboxPerformance.date.desc())
            .limit(1)
        ).first()

        # Count trades
        trade_count = db.scalar(
            select(func.count(SandboxTrade.id))
            .where(SandboxTrade.agent_name == name)
        )

        if latest:
            summaries.append({
                "agent_name": name,
                "latest_date": str(latest.date),
                "portfolio_value": latest.portfolio_value,
                "cumulative_return_pct": latest.cumulative_return_pct,
                "max_drawdown_pct": latest.max_drawdown_pct,
                "total_trades": trade_count or 0,
            })

    # Sort by return
    summaries.sort(key=lambda s: s["cumulative_return_pct"], reverse=True)
    return summaries


@router.get("/trades")
def get_sandbox_trades(
    agent_name: str = Query(default=None),
    db: Session = Depends(get_db),
):
    """Get trade log, optionally filtered by agent."""
    stmt = select(SandboxTrade).order_by(SandboxTrade.date.desc())
    if agent_name:
        stmt = stmt.where(SandboxTrade.agent_name == agent_name)

    trades = db.scalars(stmt.limit(100)).all()

    return [
        {
            "agent_name": t.agent_name,
            "stock_id": t.stock_id,
            "date": str(t.date),
            "action": t.action,
            "quantity": t.quantity,
            "price": t.price,
            "fee": t.fee,
            "total_cost": t.total_cost,
        }
        for t in trades
    ]
