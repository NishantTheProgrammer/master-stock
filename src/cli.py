"""
CLI entry point for the Master Stock system.
Provides commands to run agents, predictions, sandbox, and serve the API.
"""

import logging
import sys
from argparse import ArgumentParser
from datetime import date, timedelta

from rich.console import Console

console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)


def cmd_seed(args):
    """Seed the database with default stocks."""
    from scripts.seed_stocks import main as seed_main
    seed_main()


def cmd_fetch_prices(args):
    """Fetch price data for all stocks."""
    from src.db.engine import get_session
    from src.db.crud import get_all_stocks
    from src.data.price_fetcher import fetch_prices_for_all

    console.print("\n[bold cyan]📈 Fetching price data...[/bold cyan]\n")
    db = get_session()
    try:
        stocks = list(get_all_stocks(db))
        results = fetch_prices_for_all(
            db, stocks,
            lookback_days=args.days,
            force_full=args.full,
        )
        for symbol, count in results.items():
            status = f"[green]{count} rows[/green]" if count > 0 else "[dim]up to date[/dim]"
            console.print(f"  {symbol}: {status}")
        console.print(f"\n[green]✓ Done.[/green]\n")
    finally:
        db.close()


def cmd_run_agents(args):
    """Run all AI agents."""
    from scripts.run_agents import main as agents_main
    agents_main()


def cmd_predict(args):
    """Run the prediction engine."""
    from src.db.engine import get_session
    from src.prediction.engine import PredictionEngine

    console.print("\n[bold cyan]🎯 Running prediction engine...[/bold cyan]\n")
    db = get_session()
    try:
        engine = PredictionEngine(db)
        predictions = engine.predict_all(date.today())
        console.print(f"[green]✓ Generated {len(predictions)} predictions.[/green]\n")
    finally:
        db.close()


def cmd_sandbox(args):
    """Run the paper trading sandbox."""
    from scripts.run_sandbox import main as sandbox_main
    sandbox_main()


def cmd_serve(args):
    """Start the FastAPI server."""
    import uvicorn
    from src.config import settings

    console.print(f"\n[bold cyan]🚀 Starting API server on {settings.api_host}:{settings.api_port}[/bold cyan]\n")
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )


def main():
    parser = ArgumentParser(
        prog="master-stock",
        description="Agentic AI Stock Market Prediction System",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # seed
    subparsers.add_parser("seed", help="Seed database with default stocks")

    # fetch-prices
    fetch_parser = subparsers.add_parser("fetch-prices", help="Fetch price data")
    fetch_parser.add_argument("--days", type=int, default=365, help="Lookback days (default: 365)")
    fetch_parser.add_argument("--full", action="store_true", help="Force full re-fetch")

    # run-agents
    subparsers.add_parser("run-agents", help="Run all AI agents")

    # predict
    subparsers.add_parser("predict", help="Run the prediction engine")

    # sandbox
    subparsers.add_parser("sandbox", help="Run paper trading sandbox")

    # serve
    subparsers.add_parser("serve", help="Start the API server")

    args = parser.parse_args()

    commands = {
        "seed": cmd_seed,
        "fetch-prices": cmd_fetch_prices,
        "run-agents": cmd_run_agents,
        "predict": cmd_predict,
        "sandbox": cmd_sandbox,
        "serve": cmd_serve,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
