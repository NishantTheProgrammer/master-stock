#!/usr/bin/env python3
"""
Run all AI agents to generate scores for the current day.
Usage: python -m scripts.run_agents
"""

import logging
import sys
from datetime import date

from rich.console import Console
from rich.table import Table

sys.path.insert(0, ".")

from src.db.engine import get_session
from src.db.crud import get_all_stocks
from src.agents.llm_provider import LLMProvider
from src.agents.technical_agent import TechnicalAgent
from src.agents.global_news_agent import GlobalNewsAgent
from src.agents.sector_news_agent import SectorNewsAgent
from src.agents.stock_news_agent import StockNewsAgent
from src.agents.social_agent import SocialAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s", datefmt="%H:%M:%S")
console = Console()


def main():
    today = date.today()
    console.print(f"\n[bold cyan]🤖 Running all AI agents for {today}[/bold cyan]\n")

    db = get_session()
    try:
        stocks = list(get_all_stocks(db))
        if not stocks:
            console.print("[red]No stocks in database. Run 'python -m scripts.seed_stocks' first.[/red]")
            return

        console.print(f"[dim]Analyzing {len(stocks)} stocks...[/dim]\n")

        # 1. Technical Agent (no LLM needed)
        console.print("[bold yellow]📊 Running Technical Agent...[/bold yellow]")
        tech_agent = TechnicalAgent(db)
        tech_scores = tech_agent.analyze_all(stocks, today)
        console.print(f"[green]✓ Technical Agent: {len(tech_scores)} scores generated.[/green]\n")

        # Initialize shared LLM provider
        llm = LLMProvider()
        if not llm.is_available():
            console.print("[bold red]⚠️  Ollama is not running! Start it with 'ollama serve'[/bold red]")
            console.print("[yellow]Skipping LLM-based agents. Only technical scores available.[/yellow]\n")
            return

        # 2. Global News Agent
        console.print("[bold yellow]🌍 Running Global News Agent...[/bold yellow]")
        global_agent = GlobalNewsAgent(db, llm)
        global_score = global_agent.analyze_market(today)
        console.print(f"[green]✓ Global News: score={global_score.score:+.1f}[/green]\n")

        # 3. Sector News Agent
        console.print("[bold yellow]🏭 Running Sector News Agent...[/bold yellow]")
        sector_agent = SectorNewsAgent(db, llm)
        sector_scores = sector_agent.analyze_all_sectors(today)
        console.print(f"[green]✓ Sector News: {len(sector_scores)} sectors scored.[/green]\n")

        # 4. Stock News Agent
        console.print("[bold yellow]📰 Running Stock News Agent...[/bold yellow]")
        stock_agent = StockNewsAgent(db, llm)
        stock_scores = stock_agent.analyze_all(stocks, today)
        console.print(f"[green]✓ Stock News: {len(stock_scores)} scores generated.[/green]\n")

        # 5. Social Agent
        console.print("[bold yellow]💬 Running Social Agent...[/bold yellow]")
        social_agent = SocialAgent(db, llm)
        social_scores = social_agent.analyze_all(stocks, today)
        console.print(f"[green]✓ Social Agent: {len(social_scores)} scores generated.[/green]\n")

        # Run prediction engine
        console.print("[bold yellow]🎯 Running Prediction Engine...[/bold yellow]")
        from src.prediction.engine import PredictionEngine
        engine = PredictionEngine(db)
        predictions = engine.predict_all(today)

        # Display results
        table = Table(title=f"Predictions for {today}", show_lines=True)
        table.add_column("Symbol", style="bold cyan", width=12)
        table.add_column("Action", justify="center", width=8)
        table.add_column("P(Up)", justify="right", width=8)
        table.add_column("Move %", justify="right", width=8)
        table.add_column("Conf", justify="right", width=8)
        table.add_column("Reasoning", width=40)

        for pred in predictions[:20]:  # Top 20
            action_color = {"BUY": "green", "SELL": "red", "HOLD": "yellow"}.get(
                pred.suggested_action, "white"
            )
            table.add_row(
                pred.stock_symbol,
                f"[{action_color}]{pred.suggested_action}[/{action_color}]",
                f"{pred.up_probability:.0%}",
                f"{pred.expected_move_pct:+.1f}%",
                f"{pred.confidence:.0%}",
                pred.reasoning[:40],
            )

        console.print(table)
        console.print(f"\n[green]✓ All agents and predictions complete![/green]\n")

    finally:
        db.close()


if __name__ == "__main__":
    main()
