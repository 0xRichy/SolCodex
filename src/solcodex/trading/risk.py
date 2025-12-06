from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Iterable, List

from ..clients.pumpfun_client import NewTokenEvent
from .models import Position

_LOGGER = logging.getLogger(__name__)


@dataclass
class RiskReport:
    score: float
    reasons: List[str] = field(default_factory=list)

    def summary(self) -> str:
        if not self.reasons:
            return "No risk factors triggered"
        return "; ".join(self.reasons)


class RiskAssessor:
    """Evaluate new token metadata for rug/honeypot risk signals.

    The heuristic intentionally errs on the side of caution to avoid
    entering illiquid or obviously malicious launches.
    """

    def __init__(
        self,
        *,
        min_description_chars: int,
        suspicious_creator_limit: int,
        max_symbol_length: int,
        suspicious_keywords: Iterable[str] | None = None,
    ) -> None:
        self.min_description_chars = min_description_chars
        self.suspicious_creator_limit = suspicious_creator_limit
        self.max_symbol_length = max_symbol_length
        self.suspicious_keywords = [
            "rug",
            "honeypot",
            "scam",
            "pump",
            "dump",
            "exit",
            "rekt",
        ]
        if suspicious_keywords:
            self.suspicious_keywords.extend(keyword.lower() for keyword in suspicious_keywords)
        self._creator_issuance: Dict[str, int] = {}

    def assess(self, event: NewTokenEvent, open_positions: Iterable[Position]) -> RiskReport:
        score = 0.0
        reasons: List[str] = []

        creator_count = self._creator_issuance.get(event.creator, 0) + 1
        self._creator_issuance[event.creator] = creator_count
        if creator_count > self.suspicious_creator_limit:
            score += 0.35
            reasons.append(f"Creator {event.creator[:8]} issued {creator_count} tokens this session")

        description = event.description or ""
        if len(description) < self.min_description_chars:
            score += 0.1
            reasons.append("Description too short/missing")

        lower_fields = f"{event.name} {event.symbol} {description}".lower()
        matched_keywords = [word for word in self.suspicious_keywords if word in lower_fields]
        if matched_keywords:
            score += 0.25
            reasons.append(f"Suspicious keywords detected: {', '.join(sorted(set(matched_keywords)))}")

        if len(event.symbol) > self.max_symbol_length or not event.symbol.isascii():
            score += 0.1
            reasons.append("Symbol length/charset looks spammy")

        open_symbols = {position.symbol for position in open_positions}
        if event.symbol in open_symbols:
            score += 0.2
            reasons.append("Already exposed to this symbol")

        capped_score = min(score, 1.0)
        if capped_score > 0:
            _LOGGER.debug("Risk score %.2f for %s: %s", capped_score, event.symbol, "; ".join(reasons))
        return RiskReport(score=capped_score, reasons=reasons)


__all__ = ["RiskAssessor", "RiskReport"]
