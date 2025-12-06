from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import List

from ..clients.pumpfun_client import PumpfunClient
from ..clients.solana_client import SolanaClient, load_keypair
from ..clients.price_oracle import PriceOracle
from .models import Position
from .strategy import ExitDecision, SnipingStrategy

_LOGGER = logging.getLogger(__name__)


class TradingBot:
    """Async trading bot connecting Pump.fun feed to Solana execution."""

    def __init__(
        self,
        pump_client: PumpfunClient,
        solana_client: SolanaClient,
        price_oracle: PriceOracle,
        strategy: SnipingStrategy,
        max_open_positions: int,
        max_position_sol: float,
        price_check_seconds: int = 10,
    ) -> None:
        self.pump_client = pump_client
        self.solana_client = solana_client
        self.price_oracle = price_oracle
        self.strategy = strategy
        self.max_open_positions = max_open_positions
        self.max_position_sol = max_position_sol
        self.price_check_seconds = price_check_seconds
        self.positions: List[Position] = []
        self._wallet = None
        self._running = False

    def load_wallet(self, private_key: str) -> None:
        self._wallet = load_keypair(private_key)
        _LOGGER.info("Loaded wallet %s", self._wallet.public_key)

    async def run(self) -> None:
        if not self._wallet:
            raise RuntimeError("Wallet must be loaded before running the bot")

        self._running = True
        monitor_task = asyncio.create_task(self._monitor_positions())
        try:
            async for event in self.pump_client.listen_new_tokens():
                if len(self.positions) >= self.max_open_positions:
                    _LOGGER.debug("Position limit reached; skipping %s", event.symbol)
                    continue

                decision = self.strategy.evaluate(event, self.positions)
                if not decision.should_buy:
                    _LOGGER.debug("Skipping %s: %s", event.symbol, decision.reason)
                    continue

                await self._attempt_snipe(event)
        finally:
            self._running = False
            monitor_task.cancel()
            with suppress(asyncio.CancelledError):
                await monitor_task

    async def _attempt_snipe(self, event) -> None:
        # Placeholder: here you would craft and send the actual swap transaction
        # against the bonding curve. We record a simulated position instead.
        position = Position(
            mint=event.mint,
            symbol=event.symbol,
            entry_price=event.market_cap / 1_000_000_000,  # rough placeholder
            amount=self.max_position_sol,
            take_profit=self.strategy.take_profit,
            stop_loss=self.strategy.stop_loss,
            signature=None,
        )
        self.positions.append(position)
        _LOGGER.info("Opened simulated position on %s with %.2f SOL", event.symbol, position.amount)

    async def _monitor_positions(self) -> None:
        while self._running:
            await asyncio.sleep(self.price_check_seconds)
            if not self.positions:
                continue

            for position in list(self.positions):
                quote = await self.price_oracle.get_price(position.mint)
                if not quote:
                    _LOGGER.debug("No price quote for %s; skipping", position.symbol)
                    continue

                exit_decision = self.strategy.evaluate_exit(position, quote.price)
                if exit_decision.should_sell:
                    self._exit_position(position, exit_decision, quote.price)

    async def close(self) -> None:
        await self.pump_client.stop()
        await self.solana_client.aclose()
        await self.price_oracle.aclose()

    def _exit_position(self, position: Position, decision: ExitDecision, price: float) -> None:
        try:
            self.positions.remove(position)
        except ValueError:
            return
        pnl = (price - position.entry_price) * position.amount
        _LOGGER.info(
            "Closed %s at %.6f SOL (%+.4f SOL): %s",
            position.symbol,
            price,
            pnl,
            decision.reason,
        )


__all__ = ["TradingBot"]
