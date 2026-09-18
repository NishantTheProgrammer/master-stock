"""
Virtual Exchange for the Paper Trading Sandbox.
Simulates buy/sell operations with virtual currency using real historical prices.
"""

import logging
from dataclasses import dataclass, field
from datetime import date

from src.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Holding:
    """A stock holding in the portfolio."""
    symbol: str
    stock_id: int
    quantity: int
    avg_price: float
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.avg_price

    @property
    def unrealized_pnl(self) -> float:
        return self.market_value - self.cost_basis

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.cost_basis == 0:
            return 0.0
        return (self.unrealized_pnl / self.cost_basis) * 100


@dataclass
class TradeRecord:
    """Record of a trade execution."""
    agent_name: str
    stock_id: int
    symbol: str
    date: date
    action: str  # BUY or SELL
    quantity: int
    price: float
    fee: float
    total_cost: float  # price * qty ± fee


class VirtualExchange:
    """
    Simulates a stock exchange with virtual money.
    Supports buy/sell operations at specified prices (no order book).
    """

    def __init__(
        self,
        agent_name: str,
        initial_capital: float | None = None,
        transaction_fee_pct: float | None = None,
    ):
        self.agent_name = agent_name
        self.cash = initial_capital or settings.sandbox_initial_capital
        self.initial_capital = self.cash
        self.fee_pct = transaction_fee_pct or settings.sandbox_transaction_fee_pct
        self.holdings: dict[str, Holding] = {}  # symbol → Holding
        self.trade_history: list[TradeRecord] = []
        self.daily_snapshots: list[dict] = []

    @property
    def total_holdings_value(self) -> float:
        """Total market value of all stock holdings."""
        return sum(h.market_value for h in self.holdings.values())

    @property
    def total_portfolio_value(self) -> float:
        """Total portfolio value = cash + holdings."""
        return self.cash + self.total_holdings_value

    @property
    def total_return_pct(self) -> float:
        """Total return percentage from initial capital."""
        if self.initial_capital == 0:
            return 0.0
        return ((self.total_portfolio_value - self.initial_capital) / self.initial_capital) * 100

    def buy(
        self, stock_id: int, symbol: str, quantity: int, price: float, trade_date: date
    ) -> TradeRecord | None:
        """
        Buy shares of a stock.

        Args:
            stock_id: Database stock ID
            symbol: Stock symbol
            quantity: Number of shares to buy
            price: Price per share
            trade_date: Date of the trade

        Returns:
            TradeRecord if successful, None if insufficient funds
        """
        if quantity <= 0 or price <= 0:
            logger.warning(f"{self.agent_name}: Invalid buy — qty={quantity}, price={price}")
            return None

        gross_cost = quantity * price
        fee = gross_cost * self.fee_pct
        total_cost = gross_cost + fee

        if total_cost > self.cash:
            # Try buying fewer shares
            max_affordable = int(self.cash / (price * (1 + self.fee_pct)))
            if max_affordable <= 0:
                logger.warning(
                    f"{self.agent_name}: Cannot afford {quantity}x {symbol} @ ₹{price:.2f} "
                    f"(need ₹{total_cost:,.0f}, have ₹{self.cash:,.0f})"
                )
                return None
            quantity = max_affordable
            gross_cost = quantity * price
            fee = gross_cost * self.fee_pct
            total_cost = gross_cost + fee

        # Deduct cash
        self.cash -= total_cost

        # Update holdings
        if symbol in self.holdings:
            existing = self.holdings[symbol]
            new_total_qty = existing.quantity + quantity
            new_avg_price = (
                (existing.avg_price * existing.quantity + price * quantity) / new_total_qty
            )
            existing.quantity = new_total_qty
            existing.avg_price = new_avg_price
            existing.current_price = price
        else:
            self.holdings[symbol] = Holding(
                symbol=symbol,
                stock_id=stock_id,
                quantity=quantity,
                avg_price=price,
                current_price=price,
            )

        # Record trade
        trade = TradeRecord(
            agent_name=self.agent_name,
            stock_id=stock_id,
            symbol=symbol,
            date=trade_date,
            action="BUY",
            quantity=quantity,
            price=price,
            fee=round(fee, 2),
            total_cost=round(total_cost, 2),
        )
        self.trade_history.append(trade)

        logger.info(
            f"{self.agent_name}: BUY {quantity}x {symbol} @ ₹{price:.2f} "
            f"(cost: ₹{total_cost:,.0f}, fee: ₹{fee:.0f}) — "
            f"Cash: ₹{self.cash:,.0f}"
        )
        return trade

    def sell(
        self, stock_id: int, symbol: str, quantity: int, price: float, trade_date: date
    ) -> TradeRecord | None:
        """
        Sell shares of a stock.

        Returns:
            TradeRecord if successful, None if insufficient holdings
        """
        if quantity <= 0 or price <= 0:
            logger.warning(f"{self.agent_name}: Invalid sell — qty={quantity}, price={price}")
            return None

        if symbol not in self.holdings:
            logger.warning(f"{self.agent_name}: No holdings of {symbol} to sell.")
            return None

        holding = self.holdings[symbol]
        if quantity > holding.quantity:
            logger.warning(
                f"{self.agent_name}: Trying to sell {quantity}x {symbol} "
                f"but only hold {holding.quantity}. Selling all."
            )
            quantity = holding.quantity

        gross_proceeds = quantity * price
        fee = gross_proceeds * self.fee_pct
        net_proceeds = gross_proceeds - fee

        # Add cash
        self.cash += net_proceeds

        # Update holdings
        holding.quantity -= quantity
        holding.current_price = price
        if holding.quantity <= 0:
            del self.holdings[symbol]

        # Record trade
        trade = TradeRecord(
            agent_name=self.agent_name,
            stock_id=stock_id,
            symbol=symbol,
            date=trade_date,
            action="SELL",
            quantity=quantity,
            price=price,
            fee=round(fee, 2),
            total_cost=round(net_proceeds, 2),
        )
        self.trade_history.append(trade)

        logger.info(
            f"{self.agent_name}: SELL {quantity}x {symbol} @ ₹{price:.2f} "
            f"(proceeds: ₹{net_proceeds:,.0f}, fee: ₹{fee:.0f}) — "
            f"Cash: ₹{self.cash:,.0f}"
        )
        return trade

    def update_prices(self, prices: dict[str, float]) -> None:
        """
        Update current prices for all holdings.

        Args:
            prices: Dict mapping symbol → current price
        """
        for symbol, holding in self.holdings.items():
            if symbol in prices:
                holding.current_price = prices[symbol]

    def take_snapshot(self, snapshot_date: date) -> dict:
        """Take a portfolio snapshot for the given date."""
        snapshot = {
            "date": snapshot_date,
            "cash": round(self.cash, 2),
            "holdings_value": round(self.total_holdings_value, 2),
            "total_value": round(self.total_portfolio_value, 2),
            "return_pct": round(self.total_return_pct, 4),
            "holdings": {
                sym: {
                    "qty": h.quantity,
                    "avg_price": round(h.avg_price, 2),
                    "current_price": round(h.current_price, 2),
                    "pnl": round(h.unrealized_pnl, 2),
                    "pnl_pct": round(h.unrealized_pnl_pct, 2),
                }
                for sym, h in self.holdings.items()
            },
            "num_positions": len(self.holdings),
        }
        self.daily_snapshots.append(snapshot)
        return snapshot

    def get_holdings_json(self) -> dict:
        """Get holdings as a JSON-serializable dict."""
        return {
            sym: {
                "qty": h.quantity,
                "avg_price": round(h.avg_price, 2),
            }
            for sym, h in self.holdings.items()
        }
