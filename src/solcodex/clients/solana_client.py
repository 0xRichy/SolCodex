from __future__ import annotations

import asyncio
import base64
import logging
from dataclasses import dataclass
from typing import Optional

from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TxOpts

_LOGGER = logging.getLogger(__name__)


@dataclass
class TransactionResult:
    signature: str
    slot: int


class SolanaClient:
    """Thin wrapper around solana-py for sending transactions and fetching state."""

    def __init__(self, endpoint: str, commitment: str = "processed") -> None:
        self._client = AsyncClient(endpoint, commitment=commitment)

    async def aclose(self) -> None:
        await self._client.close()

    async def get_balance(self, pubkey: PublicKey) -> float:
        response = await self._client.get_balance(pubkey)
        lamports = response.value
        return lamports / 1_000_000_000

    async def send_transaction(self, serialized_tx: bytes, opts: Optional[TxOpts] = None) -> TransactionResult:
        opts = opts or TxOpts(skip_preflight=True)
        encoded = base64.b64encode(serialized_tx).decode()
        response = await self._client.send_raw_transaction(encoded, opts=opts)
        signature = response.value
        confirmation = await self._wait_for_confirmation(signature)
        return TransactionResult(signature=signature, slot=confirmation)

    async def _wait_for_confirmation(self, signature: str) -> int:
        while True:
            result = await self._client.get_signature_statuses([signature])
            status = result.value[0]
            if status and status.slot is not None:
                _LOGGER.debug("Transaction %s confirmed at slot %s", signature, status.slot)
                return status.slot
            await asyncio.sleep(0.25)


def load_keypair(private_key: str) -> Keypair:
    """Load a keypair from a base58 or base64 encoded private key string."""
    try:
        return Keypair.from_base58_string(private_key)
    except ValueError:
        secret = base64.b64decode(private_key)
        return Keypair.from_secret_key(secret)


__all__ = ["SolanaClient", "TransactionResult", "load_keypair"]
