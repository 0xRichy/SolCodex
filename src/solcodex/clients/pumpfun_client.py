from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import AsyncIterator, Dict, Optional

import websockets

_LOGGER = logging.getLogger(__name__)


@dataclass
class NewTokenEvent:
    mint: str
    symbol: str
    name: str
    market_cap: float
    creator: str
    description: Optional[str] = None


class PumpfunClient:
    """Lightweight wrapper around the public Pump.fun websocket feed.

    The feed provides newly created token metadata that can be consumed by a
    strategy to decide whether to snipe a launch.
    """

    def __init__(self, url: str, reconnect_seconds: int = 5, max_queue: int = 1000) -> None:
        self.url = url
        self.reconnect_seconds = reconnect_seconds
        self.max_queue = max_queue
        self._stop = asyncio.Event()

    async def stop(self) -> None:
        self._stop.set()

    async def listen_new_tokens(self) -> AsyncIterator[NewTokenEvent]:
        """Yield :class:`NewTokenEvent` values from the websocket stream.

        The generator will automatically reconnect on connection loss while the
        ``stop`` event is not set.
        """

        while not self._stop.is_set():
            try:
                async for event in self._connect():
                    yield event
            except websockets.WebSocketException as exc:  # pragma: no cover - network dependent
                _LOGGER.warning("Pump.fun stream error: %s", exc)
                await asyncio.sleep(self.reconnect_seconds)

    async def _connect(self) -> AsyncIterator[NewTokenEvent]:
        _LOGGER.info("Connecting to Pump.fun stream at %s", self.url)
        async with websockets.connect(self.url, max_queue=self.max_queue, ping_interval=20) as ws:
            await ws.send(json.dumps({"method": "subscribeNewTokens"}))
            async for message in ws:
                if self._stop.is_set():
                    break
                try:
                    yield self._parse_event(message)
                except ValueError as exc:
                    _LOGGER.debug("Discarded malformed event: %s", exc)

    @staticmethod
    def _parse_event(message: str) -> NewTokenEvent:
        payload: Dict[str, object] = json.loads(message)
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        if not isinstance(data, dict):
            raise ValueError("Missing data field in event")
        return NewTokenEvent(
            mint=str(data.get("mint", "")),
            symbol=str(data.get("symbol", "")),
            name=str(data.get("name", "")),
            market_cap=float(data.get("marketCap", 0) or 0),
            creator=str(data.get("creator", "")),
            description=str(data.get("description") or "") or None,
        )


__all__ = ["PumpfunClient", "NewTokenEvent"]
