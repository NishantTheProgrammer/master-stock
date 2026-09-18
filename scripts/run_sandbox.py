#!/usr/bin/env python3
"""
Run the paper trading sandbox simulation.
Usage: python -m scripts.run_sandbox [--days 10]
"""

import logging
import sys
from argparse import ArgumentParser
from datetime import date, timedelta

from rich.console import Console
from rich.table import Table

sys.path.insert(0, ".")

from src.db.engine import get_session
from src.sandbox.simulator import SandboxSimulator

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s", datefmt="%H:%M:%S")
console = Console()


def main(args=None):
    if args is None:
        parser = ArgumentParser(description="Run paper trading sandbox")
        parser.add_argument("--days", type=int, default=10, help="Number of days to simulate")
        parser.add_argument("--capital", type=float, default=1_000_000, help="Initial capital per agent")
        args = parser.parse_args()

    end_date = date.today()
    start_date = end_date - timedelta(days=args.days + 5)  # Extra buffer for weekends

    console.print(f"\n[bold cyan]🏦 Paper Trading Sandbox[/bold cyan]")
    console.print(f"Period: {start_date} → {end_date}")
    console.print(f"Capital: ₹{args.capital:,.0f} per agent\n")

    db = get_session()
    try:
        simulator = SandboxSimulator(db, initial_capital=args.capital)
        summary = simulator.run(start_date, end_date)

        if "error" in summary:
            console.print(f"[red]Error: {summary['error']}[/red]")
            return

        # Display results
        console.print(f"\n[bold green]{'='*60}[/bold green]")
        console.print(f"[bold green]  SIMULATION RESULTS[/bold green]")
        console.print(f"[bold green]{'='*60}[/bold green]\n")

        table = Table(title="Agent Performance Comparison", show_lines=True)
        table.add_column("Agent", style="bold", width=15)
        table.add_column("Strategy", width=30)
        table.add_column("Final Value", justify="right", width=15)
        table.add_column("Return %", justify="right", width=10)
        table.add_column("Trades", justify="right", width=8)
        table.add_column("Max DD %", justify="right", width=10)
        table.add_column("Sharpe", justify="right", width=8)

        for name, data in summary.get("agents", {}).items():
            return_color = "green" if data["total_return_pct"] >= 0 else "red"
            is_best = name == summary.get("best_agent")
            name_display = f"🏆 {name}" if is_best else name

            table.add_row(
                name_display,
                data["strategy"],
                f"₹{data['final_value']:,.0f}",
                f"[{return_color}]{data['total_return_pct']:+.2f}%[/{return_color}]",
                str(data["total_trades"]),
                f"{data['max_drawdown_pct']:.2f}%",
                f"{data['sharpe_ratio']:.2f}",
            )

        console.print(table)
        console.print(
            f"\n[bold green]🏆 Best Agent: {summary.get('best_agent')} "
            f"({summary.get('best_return_pct', 0):+.2f}% return)[/bold green]\n"
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()
