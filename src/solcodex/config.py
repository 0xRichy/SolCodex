from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import tomllib


@dataclass
class WebsocketConfig:
    url: str = "wss://pumpportal.fun/api/v1"
    reconnect_seconds: int = 5
    max_queue: int = 1000


@dataclass
class TradingConfig:
    max_open_positions: int = 3
    max_position_sol: float = 0.5
    take_profit: float = 0.3
    stop_loss: float = 0.15
    slippage_bps: int = 50
    min_liquidity_sol: float = 5.0
    max_risk_score: float = 0.5
    min_description_chars: int = 20
    suspicious_creator_limit: int = 3
    max_symbol_length: int = 10
    price_check_seconds: int = 10


@dataclass
class WalletConfig:
    private_key: str = ""
    rpc_endpoint: str = "https://api.mainnet-beta.solana.com"
    commitment: str = "processed"
    vault_path: str = "~/.solcodex/seed_vault.json"


@dataclass
class Config:
    """Runtime configuration for the trading bot.

    Values can be provided through a TOML file or environment variables prefixed with
    ``SOLCODEX_``. The environment variables override values found in the config file.
    """

    websocket: WebsocketConfig = field(default_factory=WebsocketConfig)
    trading: TradingConfig = field(default_factory=TradingConfig)
    wallet: WalletConfig = field(default_factory=WalletConfig)

    @staticmethod
    def _load_from_toml(path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        with path.open("rb") as handle:
            return tomllib.load(handle)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Config":
        path = path or Path(os.environ.get("SOLCODEX_CONFIG", "config.toml"))
        raw = cls._load_from_toml(path)

        # Environment overrides
        env_overrides: Dict[str, Any] = {}
        for key, value in os.environ.items():
            if not key.startswith("SOLCODEX_"):
                continue
            _, *parts = key.split("_", maxsplit=1)
            if not parts:
                continue
            env_overrides[parts[0].lower()] = value

        def merge_section(section_name: str, section_cls: Any) -> Any:
            data: Dict[str, Any] = raw.get(section_name, {}).copy()
            data.update(json.loads(env_overrides.get(section_name, "{}")) if section_name in env_overrides else {})
            return section_cls(**data)

        return cls(
            websocket=merge_section("websocket", WebsocketConfig),
            trading=merge_section("trading", TradingConfig),
            wallet=merge_section("wallet", WalletConfig),
        )


__all__ = [
    "Config",
    "WebsocketConfig",
    "TradingConfig",
    "WalletConfig",
]
