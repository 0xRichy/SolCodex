from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List

from ..clients.pumpfun_client import NewTokenEvent
from .models import Position
from .risk import RiskAssessor

_LOGGER = logging.getLogger(__name__)


@dataclass
class StrategyDecision:
    should_buy: bool
    reason: str


@dataclass
class ExitDecision:
    should_sell: bool
    reason: str


class SnipingStrategy:
    """Simple heuristic strategy for new Pump.fun listings.

    The strategy screens incoming tokens for minimum liquidity, quality, and
    rug/honeypot risk before recommending a buy.
    """

    def __init__(
        self,
        min_liquidity_sol: float,
        stop_loss: float,
        take_profit: float,
        max_risk_score: float = 0.5,
        risk_assessor: RiskAssessor | None = None,
    ) -> None:
        self.min_liquidity_sol = min_liquidity_sol
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.max_risk_score = max_risk_score
        self.risk_assessor = risk_assessor

    def evaluate(self, event: NewTokenEvent, open_positions: Iterable[Position]) -> StrategyDecision:
        open_symbols: List[str] = [p.symbol for p in open_positions]
        if event.symbol in open_symbols:
            return StrategyDecision(False, "Already holding symbol")

        assessor = self.risk_assessor
        if assessor:
            risk_report = assessor.assess(event, open_positions)
            if risk_report.score >= self.max_risk_score:
                return StrategyDecision(False, f"Risk score {risk_report.score:.2f} exceeded: {risk_report.summary()}")

        if event.market_cap < self.min_liquidity_sol:
            return StrategyDecision(False, f"Liquidity too low ({event.market_cap:.2f} < {self.min_liquidity_sol})")

        _LOGGER.info(
            "Approved snipe candidate %s (%s) with market cap %.2f SOL",
            event.name,
            event.symbol,
            event.market_cap,
        )
        return StrategyDecision(True, "Meets liquidity and risk gates")

    def evaluate_exit(self, position: Position, current_price: float) -> ExitDecision:
        """Decide whether to exit based on take-profit/stop-loss thresholds."""

        if position.entry_price <= 0:
            return ExitDecision(False, "Invalid entry price; cannot compute PnL")

        change = (current_price - position.entry_price) / position.entry_price
        if change >= self.take_profit:
            return ExitDecision(True, f"Take-profit reached at {change:.2%}")
        if change <= -self.stop_loss:
            return ExitDecision(True, f"Stop-loss hit at {change:.2%}")
        return ExitDecision(False, "Holding position")


__all__ = ["ExitDecision", "SnipingStrategy", "StrategyDecision"]
