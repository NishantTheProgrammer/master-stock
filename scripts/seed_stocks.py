#!/usr/bin/env python3
"""
Seed the database with the default stock universe.
Usage: python -m scripts.seed_stocks
"""

import logging
import sys

from rich.console import Console
from rich.table import Table

# Ensure project root is in path
sys.path.insert(0, ".")

from src.db.engine import get_session
from src.db.models import Base
from src.db.engine import engine
from src.data.stocks import seed_default_stocks

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)
console = Console()


def main():
    console.print("\n[bold cyan]🏗️  Master Stock — Database Setup[/bold cyan]\n")

    # Create all tables
    console.print("[yellow]Creating database tables...[/yellow]")
    Base.metadata.create_all(engine)
    console.print("[green]✓ Tables created successfully.[/green]\n")

    # Seed stocks
    console.print("[yellow]Seeding default stocks (Nifty top 20)...[/yellow]")
    db = get_session()
    try:
        stocks = seed_default_stocks(db)

        # Display results
        table = Table(title="Seeded Stocks", show_lines=False)
        table.add_column("#", style="dim", width=4)
        table.add_column("Symbol", style="bold cyan")
        table.add_column("Name", style="white")
        table.add_column("Sector", style="magenta")
        table.add_column("Exchange", style="green")

        for i, stock in enumerate(stocks, 1):
            table.add_row(str(i), stock.symbol, stock.name, stock.sector, stock.exchange)

        console.print(table)
        console.print(f"\n[green]✓ Seeded {len(stocks)} stocks successfully.[/green]\n")

    finally:
        db.close()


if __name__ == "__main__":
    main()
