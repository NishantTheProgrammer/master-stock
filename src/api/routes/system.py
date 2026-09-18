from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import logging

from src.db.engine import get_session
from src.db.crud import get_all_stocks
from src.data.price_fetcher import fetch_prices_for_all

logger = logging.getLogger(__name__)

router = APIRouter()

class FetchPricesRequest(BaseModel):
    days: int = 365
    full: bool = False

class SandboxRequest(BaseModel):
    days: int = 10
    capital: float = 1000000.0

class DummyArgs:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

@router.post("/seed")
def seed_database():
    """Seed the database with default stocks."""
    try:
        from scripts.seed_stocks import main as seed_main
        seed_main()
        return {"status": "success", "message": "Database seeded successfully."}
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fetch-prices")
def fetch_prices(req: FetchPricesRequest):
    """Fetch price data for all stocks."""
    db = get_session()
    try:
        stocks = list(get_all_stocks(db))
        results = fetch_prices_for_all(
            db, stocks,
            lookback_days=req.days,
            force_full=req.full,
        )
        total = sum(results.values())
        return {"status": "success", "message": f"Fetched {total} new price rows across {len(stocks)} stocks.", "details": results}
    except Exception as e:
        logger.error(f"Error fetching prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.post("/run-agents")
def run_agents():
    """Run all AI agents and generate predictions."""
    try:
        from scripts.run_agents import main as agents_main
        agents_main()
        return {"status": "success", "message": "AI Agents finished running and predictions generated."}
    except Exception as e:
        logger.error(f"Error running agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sandbox")
def run_sandbox(req: SandboxRequest):
    """Run the paper trading sandbox."""
    try:
        from scripts.run_sandbox import main as sandbox_main
        args = DummyArgs(days=req.days, capital=req.capital)
        sandbox_main(args)
        return {"status": "success", "message": f"Sandbox simulation completed for {req.days} days."}
    except Exception as e:
        logger.error(f"Error running sandbox: {e}")
        raise HTTPException(status_code=500, detail=str(e))
