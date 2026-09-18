"""
Sandbox Simulator.
Runs multiple trading agents over historical data and tracks performance.
"""

import logging
from datetime import date, timedelta
from typing import Type

import pandas as pd
from sqlalchemy.orm import Session

from src.config import settings
from src.db.crud import (
    get_all_stocks,
    get_latest_predictions,
    get_prices,
    save_sandbox_performance,
    save_sandbox_portfolio,
    save_sandbox_trade,
)
from src.db.models import Stock
from src.sandbox.exchange import VirtualExchange
from src.sandbox.strategies.balanced import BalancedStrategy
from src.sandbox.strategies.base_strategy import BaseStrategy
from src.sandbox.strategies.conservative import ConservativeStrategy
from src.sandbox.strategies.contrarian import ContrarianStrategy
from src.sandbox.strategies.momentum import MomentumStrategy

logger = logging.getLogger(__name__)


class SandboxSimulator:
    """
    Runs a multi-day paper trading simulation with multiple strategy agents.
    Each agent starts with the same capital and trades independently.
    Performance is compared against a benchmark (Nifty 50).
    """

    STRATEGIES: list[Type[BaseStrategy]] = [
        MomentumStrategy,
        ContrarianStrategy,
        BalancedStrategy,
        ConservativeStrategy,
    ]

    def __init__(
        self,
        db: Session,
        initial_capital: float | None = None,
    ):
        self.db = db
        self.initial_capital = initial_capital or settings.sandbox_initial_capital

    def run(
        self,
        start_date: date,
        end_date: date,
    ) -> dict:
        """
        Run the full simulation from start_date to end_date.

        Args:
            start_date: First trading day
            end_date: Last trading day

        Returns:
            Summary dict with performance metrics for each agent
        """
        logger.info(
            f"Starting sandbox simulation: {start_date} → {end_date} "
            f"with ₹{self.initial_capital:,.0f} per agent"
        )

        stocks = list(get_all_stocks(self.db, active_only=True))
        stock_map = {s.symbol: s for s in stocks}

        # Initialize an exchange (portfolio) for each strategy
        agents: dict[str, tuple[BaseStrategy, VirtualExchange]] = {}
        for StrategyClass in self.STRATEGIES:
            exchange = VirtualExchange(
                agent_name=StrategyClass.name,
                initial_capital=self.initial_capital,
            )
            strategy = StrategyClass(exchange)
            agents[strategy.name] = (strategy, exchange)
            logger.info(f"Initialized agent: {strategy.name} — {strategy.description}")

        # Get trading days in range
        trading_days = self._get_trading_days(stocks, start_date, end_date)
        if not trading_days:
            logger.error("No trading days found in the specified range.")
            return {"error": "No trading days found"}

        logger.info(f"Simulating {len(trading_days)} trading days...")

        # Run simulation day by day
        for day_idx, current_day in enumerate(trading_days):
            logger.info(f"\n--- Day {day_idx + 1}/{len(trading_days)}: {current_day} ---")

            # Get prices for this day
            day_prices = self._get_day_prices(stocks, current_day)
            if not day_prices:
                logger.warning(f"No price data for {current_day}, skipping.")
                continue

            # Get predictions for this day
            predictions = list(get_latest_predictions(self.db, current_day))

            # Each agent makes decisions and executes trades
            for agent_name, (strategy, exchange) in agents.items():
                # Update portfolio with current prices
                exchange.update_prices(day_prices)

                if predictions:
                    # Strategy decides trades
                    decisions = strategy.decide(predictions, day_prices, current_day)

                    # Execute trades
                    trades_done = strategy.execute_decisions(
                        decisions, day_prices, current_day
                    )

                    # Record trades in DB
                    for trade in exchange.trade_history[-trades_done:] if trades_done else []:
                        save_sandbox_trade(self.db, {
                            "agent_name": trade.agent_name,
                            "stock_id": trade.stock_id,
                            "date": trade.date,
                            "action": trade.action,
                            "quantity": trade.quantity,
                            "price": trade.price,
                            "fee": trade.fee,
                            "total_cost": trade.total_cost,
                        })

                # Take daily snapshot
                snapshot = exchange.take_snapshot(current_day)

                # Save portfolio snapshot
                save_sandbox_portfolio(self.db, {
                    "agent_name": agent_name,
                    "date": current_day,
                    "cash": snapshot["cash"],
                    "holdings_json": snapshot["holdings"],
                    "total_value": snapshot["total_value"],
                })

                # Calculate and save daily performance
                prev_value = self.initial_capital
                if len(exchange.daily_snapshots) >= 2:
                    prev_value = exchange.daily_snapshots[-2]["total_value"]

                daily_return = (
                    (snapshot["total_value"] - prev_value) / prev_value * 100
                    if prev_value > 0 else 0
                )
                cumulative_return = snapshot["return_pct"]

                # Max drawdown
                peak = max(s["total_value"] for s in exchange.daily_snapshots)
                max_drawdown = ((peak - snapshot["total_value"]) / peak * 100) if peak > 0 else 0

                save_sandbox_performance(self.db, {
                    "agent_name": agent_name,
                    "date": current_day,
                    "daily_return_pct": round(daily_return, 4),
                    "cumulative_return_pct": round(cumulative_return, 4),
                    "portfolio_value": round(snapshot["total_value"], 2),
                    "max_drawdown_pct": round(max_drawdown, 4),
                })

                logger.info(
                    f"  {agent_name}: ₹{snapshot['total_value']:,.0f} "
                    f"(day: {daily_return:+.2f}%, total: {cumulative_return:+.2f}%) "
                    f"positions: {snapshot['num_positions']}"
                )

        # Generate summary
        summary = self._generate_summary(agents, trading_days)
        return summary

    def _get_trading_days(
        self, stocks: list[Stock], start_date: date, end_date: date
    ) -> list[date]:
        """Get actual trading days (days where we have price data)."""
        if not stocks:
            return []

        # Use the first stock to determine trading days
        prices = get_prices(self.db, stocks[0].id, start_date, end_date)
        return sorted(set(p.date for p in prices))

    def _get_day_prices(
        self, stocks: list[Stock], target_date: date
    ) -> dict[str, float]:
        """Get closing prices for all stocks on a given date."""
        prices = {}
        for stock in stocks:
            day_prices = get_prices(self.db, stock.id, target_date, target_date)
            if day_prices:
                prices[stock.symbol] = day_prices[0].close
        return prices

    def _generate_summary(
        self,
        agents: dict[str, tuple[BaseStrategy, VirtualExchange]],
        trading_days: list[date],
    ) -> dict:
        """Generate final simulation summary."""
        summary = {
            "simulation_days": len(trading_days),
            "start_date": str(trading_days[0]) if trading_days else None,
            "end_date": str(trading_days[-1]) if trading_days else None,
            "initial_capital": self.initial_capital,
            "agents": {},
        }

        best_agent = None
        best_return = float("-inf")

        for agent_name, (strategy, exchange) in agents.items():
            total_value = exchange.total_portfolio_value
            total_return = exchange.total_return_pct
            num_trades = len(exchange.trade_history)

            # Calculate Sharpe ratio (simplified)
            if exchange.daily_snapshots:
                daily_returns = []
                for i in range(1, len(exchange.daily_snapshots)):
                    prev = exchange.daily_snapshots[i - 1]["total_value"]
                    curr = exchange.daily_snapshots[i]["total_value"]
                    daily_returns.append((curr - prev) / prev if prev > 0 else 0)

                if daily_returns:
                    import numpy as np
                    avg_return = np.mean(daily_returns)
                    std_return = np.std(daily_returns)
                    sharpe = (avg_return / std_return * (252 ** 0.5)) if std_return > 0 else 0
                else:
                    sharpe = 0
            else:
                sharpe = 0

            # Max drawdown
            peak = self.initial_capital
            max_dd = 0
            for snap in exchange.daily_snapshots:
                peak = max(peak, snap["total_value"])
                dd = (peak - snap["total_value"]) / peak * 100
                max_dd = max(max_dd, dd)

            agent_summary = {
                "strategy": strategy.description,
                "final_value": round(total_value, 2),
                "total_return_pct": round(total_return, 2),
                "total_trades": num_trades,
                "num_positions": len(exchange.holdings),
                "cash_remaining": round(exchange.cash, 2),
                "sharpe_ratio": round(sharpe, 4),
                "max_drawdown_pct": round(max_dd, 2),
            }
            summary["agents"][agent_name] = agent_summary

            if total_return > best_return:
                best_return = total_return
                best_agent = agent_name

        summary["best_agent"] = best_agent
        summary["best_return_pct"] = round(best_return, 2)

        logger.info(f"\n{'='*60}")
        logger.info(f"SIMULATION COMPLETE — Best agent: {best_agent} ({best_return:+.2f}%)")
        logger.info(f"{'='*60}")

        return summary
