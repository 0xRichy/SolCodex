from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

_LOGGER = logging.getLogger(__name__)


@dataclass
class PriceQuote:
    price: float
    liquidity_usd: Optional[float] = None


class PriceOracle:
    """Fetch token prices from public aggregators for exit decisions."""

    def __init__(self, timeout: float = 5.0) -> None:
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_price(self, mint: str) -> Optional[PriceQuote]:
        """Return the latest price for a token mint via DexScreener."""

        url = f"https://api.dexscreener.com/latest/dex/tokens/{mint}"
        try:
            response = await self._client.get(url)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:  # pragma: no cover - network dependent
            _LOGGER.debug("Price fetch failed for %s: %s", mint, exc)
            return None

        if not isinstance(payload, dict):
            return None

        pairs = payload.get("pairs", [])
        if not pairs:
            return None

        first_pair = pairs[0]
        try:
            price = float(first_pair.get("priceUsd"))
        except (TypeError, ValueError):
            return None

        liquidity = first_pair.get("liquidity", {}) if isinstance(first_pair, dict) else {}
        liquidity_usd = None
        if isinstance(liquidity, dict) and "usd" in liquidity:
            try:
                liquidity_usd = float(liquidity.get("usd"))
            except (TypeError, ValueError):
                liquidity_usd = None

        return PriceQuote(price=price, liquidity_usd=liquidity_usd)


__all__ = ["PriceOracle", "PriceQuote"]
