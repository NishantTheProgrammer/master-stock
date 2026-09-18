"""
Technical Analysis Agent.
Analyzes price patterns and indicators — NO LLM required, pure computation.
Uses the `ta` library for indicator calculations.
"""

import logging
from datetime import date

import pandas as pd
import ta
from sqlalchemy.orm import Session

from src.agents.base_agent import AgentScore, BaseAgent
from src.data.price_fetcher import get_price_dataframe
from src.db.crud import upsert_technical_score
from src.db.models import Stock

logger = logging.getLogger(__name__)


class TechnicalAgent(BaseAgent):
    """
    Analyzes stocks using technical indicators.
    No LLM needed — pure math on price/volume data.

    Indicators used:
    - RSI (Relative Strength Index)
    - MACD (Moving Average Convergence Divergence)
    - Bollinger Bands
    - SMA crossovers (20/50)
    - EMA crossovers (12/26)
    - Volume trend
    - ATR (Average True Range) for volatility
    """

    name = "technical_agent"
    description = "Analyzes price patterns and technical indicators"

    def __init__(self, db: Session, lookback_days: int = 120):
        super().__init__(db)
        self.lookback_days = lookback_days

    def analyze_stock(self, stock: Stock, target_date: date) -> AgentScore:
        """Analyze a stock using technical indicators."""
        df = get_price_dataframe(self.db, stock, days=self.lookback_days)

        if df.empty or len(df) < 30:
            return AgentScore(
                stock_id=stock.id,
                stock_symbol=stock.symbol,
                date=target_date,
                score=0.0,
                confidence=0.0,
                reasoning="Insufficient price data for technical analysis.",
            )

        signals = self._compute_signals(df)
        score, confidence = self._aggregate_signals(signals)

        return AgentScore(
            stock_id=stock.id,
            stock_symbol=stock.symbol,
            date=target_date,
            score=self.clamp_score(score),
            confidence=self.clamp_confidence(confidence),
            reasoning=self._generate_reasoning(signals, score),
            signals=signals,
        )

    def _compute_signals(self, df: pd.DataFrame) -> dict:
        """Compute all technical indicator signals."""
        signals = {}

        # --- RSI ---
        rsi = ta.momentum.RSIIndicator(close=df["Close"], window=14)
        rsi_value = rsi.rsi().iloc[-1]
        signals["rsi"] = {
            "value": round(rsi_value, 2),
            "signal": self._rsi_signal(rsi_value),
            "weight": 20,
        }

        # --- MACD ---
        macd = ta.trend.MACD(close=df["Close"])
        macd_line = macd.macd().iloc[-1]
        signal_line = macd.macd_signal().iloc[-1]
        macd_hist = macd.macd_diff().iloc[-1]
        signals["macd"] = {
            "macd": round(macd_line, 4),
            "signal": round(signal_line, 4),
            "histogram": round(macd_hist, 4),
            "signal": self._macd_signal(macd_line, signal_line, macd_hist),
            "weight": 20,
        }

        # --- Bollinger Bands ---
        bb = ta.volatility.BollingerBands(close=df["Close"], window=20, window_dev=2)
        current_price = df["Close"].iloc[-1]
        bb_high = bb.bollinger_hband().iloc[-1]
        bb_low = bb.bollinger_lband().iloc[-1]
        bb_mid = bb.bollinger_mavg().iloc[-1]
        bb_pct = (current_price - bb_low) / (bb_high - bb_low) if (bb_high - bb_low) > 0 else 0.5
        signals["bollinger"] = {
            "price": round(current_price, 2),
            "upper": round(bb_high, 2),
            "lower": round(bb_low, 2),
            "pct_b": round(bb_pct, 4),
            "signal": self._bollinger_signal(bb_pct),
            "weight": 15,
        }

        # --- SMA Crossover (20/50) ---
        sma_20 = ta.trend.SMAIndicator(close=df["Close"], window=20).sma_indicator().iloc[-1]
        sma_50 = ta.trend.SMAIndicator(close=df["Close"], window=50).sma_indicator().iloc[-1]
        signals["sma_crossover"] = {
            "sma_20": round(sma_20, 2),
            "sma_50": round(sma_50, 2),
            "signal": self._crossover_signal(sma_20, sma_50, current_price),
            "weight": 15,
        }

        # --- EMA Crossover (12/26) ---
        ema_12 = ta.trend.EMAIndicator(close=df["Close"], window=12).ema_indicator().iloc[-1]
        ema_26 = ta.trend.EMAIndicator(close=df["Close"], window=26).ema_indicator().iloc[-1]
        signals["ema_crossover"] = {
            "ema_12": round(ema_12, 2),
            "ema_26": round(ema_26, 2),
            "signal": self._crossover_signal(ema_12, ema_26, current_price),
            "weight": 10,
        }

        # --- Volume Trend ---
        vol_sma_20 = df["Volume"].rolling(20).mean().iloc[-1]
        current_vol = df["Volume"].iloc[-1]
        vol_ratio = current_vol / vol_sma_20 if vol_sma_20 > 0 else 1.0
        price_change = (df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2]
        signals["volume"] = {
            "current": int(current_vol),
            "avg_20": int(vol_sma_20),
            "ratio": round(vol_ratio, 2),
            "signal": self._volume_signal(vol_ratio, price_change),
            "weight": 10,
        }

        # --- ATR (Volatility) ---
        atr = ta.volatility.AverageTrueRange(
            high=df["High"], low=df["Low"], close=df["Close"], window=14
        )
        atr_value = atr.average_true_range().iloc[-1]
        atr_pct = (atr_value / current_price) * 100
        signals["atr"] = {
            "value": round(atr_value, 2),
            "pct": round(atr_pct, 2),
            "signal": 0,  # ATR is used for confidence, not direction
            "weight": 10,
        }

        return signals

    def _aggregate_signals(self, signals: dict) -> tuple[float, float]:
        """
        Aggregate individual signals into a composite score and confidence.

        Returns:
            (score: -100..+100, confidence: 0..1)
        """
        total_weight = 0
        weighted_score = 0
        agreement_count = 0
        total_signals = 0

        for key, sig in signals.items():
            signal_val = sig.get("signal", 0)
            weight = sig.get("weight", 10)

            if isinstance(signal_val, (int, float)):
                weighted_score += signal_val * weight
                total_weight += weight
                if signal_val != 0:
                    total_signals += 1
                    if signal_val > 0:
                        agreement_count += 1

        score = weighted_score / total_weight if total_weight > 0 else 0

        # Confidence based on signal agreement + volatility
        if total_signals > 0:
            bullish_pct = agreement_count / total_signals
            # Confidence is high when most signals agree (either all bullish or all bearish)
            agreement = max(bullish_pct, 1 - bullish_pct)
            confidence = 0.3 + (agreement * 0.7)  # Scale 0.3..1.0
        else:
            confidence = 0.3

        return score, confidence

    # --- Signal computation helpers ---

    @staticmethod
    def _rsi_signal(rsi: float) -> float:
        """RSI signal: oversold (bullish) → overbought (bearish)."""
        if rsi < 30:
            return 100  # Strongly oversold → bullish
        elif rsi < 40:
            return 50
        elif rsi > 70:
            return -100  # Strongly overbought → bearish
        elif rsi > 60:
            return -50
        else:
            return 0  # Neutral

    @staticmethod
    def _macd_signal(macd_line: float, signal_line: float, histogram: float) -> float:
        """MACD signal based on crossover and histogram direction."""
        if macd_line > signal_line and histogram > 0:
            return 80  # Bullish crossover + momentum
        elif macd_line > signal_line:
            return 40  # Above signal but momentum weakening
        elif macd_line < signal_line and histogram < 0:
            return -80  # Bearish crossover + momentum
        elif macd_line < signal_line:
            return -40
        return 0

    @staticmethod
    def _bollinger_signal(pct_b: float) -> float:
        """Bollinger Band %B signal."""
        if pct_b < 0.05:
            return 80  # Below lower band → oversold
        elif pct_b < 0.2:
            return 40
        elif pct_b > 0.95:
            return -80  # Above upper band → overbought
        elif pct_b > 0.8:
            return -40
        return 0

    @staticmethod
    def _crossover_signal(fast: float, slow: float, price: float) -> float:
        """Moving average crossover signal."""
        if fast > slow and price > fast:
            return 70  # Bullish: price above both, fast above slow
        elif fast > slow:
            return 30  # Mild bullish
        elif fast < slow and price < fast:
            return -70  # Bearish: price below both
        elif fast < slow:
            return -30
        return 0

    @staticmethod
    def _volume_signal(vol_ratio: float, price_change: float) -> float:
        """Volume signal combined with price direction."""
        if vol_ratio > 1.5 and price_change > 0:
            return 60  # High volume + price up = bullish conviction
        elif vol_ratio > 1.5 and price_change < 0:
            return -60  # High volume + price down = bearish conviction
        elif vol_ratio < 0.5:
            return 0  # Low volume = uncertain
        return 0

    @staticmethod
    def _generate_reasoning(signals: dict, score: float) -> str:
        """Generate a human-readable summary of the technical analysis."""
        parts = []
        direction = "BULLISH" if score > 20 else ("BEARISH" if score < -20 else "NEUTRAL")
        parts.append(f"Overall technical outlook: {direction} (score: {score:+.1f})")

        rsi = signals.get("rsi", {})
        if rsi.get("value"):
            parts.append(f"RSI: {rsi['value']:.1f}")

        macd = signals.get("macd", {})
        if "histogram" in macd:
            parts.append(f"MACD histogram: {macd['histogram']:+.4f}")

        bb = signals.get("bollinger", {})
        if "pct_b" in bb:
            parts.append(f"Bollinger %B: {bb['pct_b']:.2f}")

        sma = signals.get("sma_crossover", {})
        if sma.get("sma_20") and sma.get("sma_50"):
            cross = "above" if sma["sma_20"] > sma["sma_50"] else "below"
            parts.append(f"SMA20 {cross} SMA50")

        vol = signals.get("volume", {})
        if vol.get("ratio"):
            parts.append(f"Volume ratio: {vol['ratio']:.2f}x avg")

        return " | ".join(parts)

    def _persist_score(self, score: AgentScore) -> None:
        """Save technical score to database."""
        import math
        def sanitize_dict(d):
            if isinstance(d, dict):
                return {k: sanitize_dict(v) for k, v in d.items()}
            elif isinstance(d, list):
                return [sanitize_dict(v) for v in d]
            elif isinstance(d, float):
                if math.isnan(d) or math.isinf(d):
                    return None
                return d
            return d

        sanitized_signals = sanitize_dict(score.signals)

        upsert_technical_score(self.db, {
            "stock_id": score.stock_id,
            "date": score.date,
            "score": score.score,
            "confidence": score.confidence,
            "signals_json": sanitized_signals,
            "reasoning": score.reasoning,
        })
