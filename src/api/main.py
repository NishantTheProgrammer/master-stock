"""
FastAPI application — REST API for the Master Stock dashboard.
"""

import logging
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import predictions, sandbox, scores, stocks, system
from src.config import settings

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown logic."""
    logger.info("🚀 Master Stock API starting up...")
    yield
    logger.info("Master Stock API shutting down.")

app = FastAPI(
    title="Master Stock API",
    description="Agentic AI Stock Market Prediction System",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for Next.js dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.dashboard_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(system.router, prefix="/api/system", tags=["System"])
app.include_router(stocks.router, prefix="/api/stocks", tags=["Stocks"])
app.include_router(scores.router, prefix="/api/scores", tags=["Scores"])
app.include_router(predictions.router, prefix="/api/predictions", tags=["Predictions"])
app.include_router(sandbox.router, prefix="/api/sandbox", tags=["Sandbox"])


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "master-stock-api"}
