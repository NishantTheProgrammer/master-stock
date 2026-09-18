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

from fastapi.responses import StreamingResponse
import subprocess

def run_script_stream(cmd: list[str]):
    """Run a script and yield its output as Server-Sent Events."""
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,  # Line buffered
    )
    
    try:
        for line in iter(process.stdout.readline, ""):
            if line:
                # SSE format
                yield f"data: {line.strip()}\n\n"
                
        process.stdout.close()
        process.wait()
        yield "data: [DONE]\n\n"
    except GeneratorExit:
        # Client disconnected, kill the process!
        process.kill()
        raise

@router.get("/fetch-prices/stream")
def fetch_prices_stream(days: int = 365):
    """Stream logs of fetching prices."""
    cmd = ["python", "-u", "-m", "src.cli", "fetch-prices", "--days", str(days)]
    return StreamingResponse(run_script_stream(cmd), media_type="text/event-stream")

@router.get("/run-agents/stream")
def run_agents_stream():
    """Stream logs of AI agents running."""
    cmd = ["python", "-u", "-m", "scripts.run_agents"]
    return StreamingResponse(run_script_stream(cmd), media_type="text/event-stream")

@router.get("/sandbox/stream")
def run_sandbox_stream(days: int = 10, capital: float = 1000000.0):
    """Stream logs of the paper trading sandbox."""
    cmd = ["python", "-u", "-m", "scripts.run_sandbox", "--days", str(days), "--capital", str(capital)]
    return StreamingResponse(run_script_stream(cmd), media_type="text/event-stream")
