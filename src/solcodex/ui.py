from __future__ import annotations

import shutil
from dataclasses import dataclass
from typing import Iterable

from .trading.models import Position


@dataclass
class BotUI:
    """Lightweight console UI to greet the operator and show state."""

    line_width: int = 72

    def banner(self) -> str:
        term_width = shutil.get_terminal_size(fallback=(self.line_width, 20)).columns
        width = min(term_width, self.line_width)
        border = "═" * width
        title = " SOLCODEX – SOLANA SNIPING BOT "
        padded_title = title.center(width, "═")
        return f"{border}\n{padded_title}\n{border}"

    def render_config(self, *, rpc: str, max_positions: int, max_sol: float, tp: float, sl: float) -> str:
        return (
            "Runtime setup:\n"
            f"- RPC endpoint       : {rpc}\n"
            f"- Max open positions : {max_positions}\n"
            f"- Max SOL per entry  : {max_sol:.3f} SOL\n"
            f"- Take profit        : {tp * 100:.1f}%\n"
            f"- Stop loss          : {sl * 100:.1f}%"
        )

    def render_positions(self, positions: Iterable[Position]) -> str:
        rows = [
            f"{pos.symbol:<10} @ {pos.entry_price:.6f} SOL | size: {pos.amount:.3f} SOL"
            for pos in positions
        ]
        if not rows:
            rows.append("No open positions yet – waiting for opportunities.")
        return "Open positions:\n" + "\n".join(rows)


__all__ = ["BotUI"]
