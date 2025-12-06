from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Position:
    mint: str
    symbol: str
    entry_price: float
    amount: float
    take_profit: float
    stop_loss: float
    signature: Optional[str] = None

    @property
    def invested_sol(self) -> float:
        return self.entry_price * self.amount


__all__ = ["Position"]
