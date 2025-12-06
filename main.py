from __future__ import annotations

import argparse
import asyncio
import logging
from getpass import getpass
from pathlib import Path

from src.solcodex.clients.pumpfun_client import PumpfunClient
from src.solcodex.clients.solana_client import SolanaClient
from src.solcodex.clients.price_oracle import PriceOracle
from src.solcodex.config import Config
from src.solcodex.logger import configure_logging
from src.solcodex.seed_vault import SeedVault
from src.solcodex.trading.bot import TradingBot
from src.solcodex.trading.risk import RiskAssessor
from src.solcodex.trading.strategy import SnipingStrategy
from src.solcodex.ui import BotUI


async def main() -> None:
    parser = argparse.ArgumentParser(description="Real-time Solana sniping bot")
    parser.add_argument("--config", type=Path, default=Path("config.toml"), help="Path to config TOML file")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    args = parser.parse_args()

    configure_logging(args.log_level)
    logging.getLogger(__name__).info("Starting SolCodex bot")

    config = Config.load(args.config)
    ui = BotUI()
    print(ui.banner())

    pump_client = PumpfunClient(
        url=config.websocket.url,
        reconnect_seconds=config.websocket.reconnect_seconds,
        max_queue=config.websocket.max_queue,
    )
    solana_client = SolanaClient(endpoint=config.wallet.rpc_endpoint, commitment=config.wallet.commitment)
    price_oracle = PriceOracle()
    risk_assessor = RiskAssessor(
        min_description_chars=config.trading.min_description_chars,
        suspicious_creator_limit=config.trading.suspicious_creator_limit,
        max_symbol_length=config.trading.max_symbol_length,
    )
    strategy = SnipingStrategy(
        min_liquidity_sol=config.trading.min_liquidity_sol,
        stop_loss=config.trading.stop_loss,
        take_profit=config.trading.take_profit,
        max_risk_score=config.trading.max_risk_score,
        risk_assessor=risk_assessor,
    )

    bot = TradingBot(
        pump_client=pump_client,
        solana_client=solana_client,
        price_oracle=price_oracle,
        strategy=strategy,
        max_open_positions=config.trading.max_open_positions,
        max_position_sol=config.trading.max_position_sol,
        price_check_seconds=config.trading.price_check_seconds,
    )
    print(
        ui.render_config(
            rpc=config.wallet.rpc_endpoint,
            max_positions=config.trading.max_open_positions,
            max_sol=config.trading.max_position_sol,
            tp=config.trading.take_profit,
            sl=config.trading.stop_loss,
        )
    )

    vault = SeedVault.default(config.wallet.vault_path)
    wallet_key = config.wallet.private_key
    if not wallet_key:
        if vault.exists():
            passphrase = getpass("Vault passphrase: ")
            try:
                wallet_key = vault.load(passphrase)
                logging.getLogger(__name__).info("Loaded key from vault %s", vault.path)
            except Exception as exc:  # pragma: no cover - runtime prompt
                logging.getLogger(__name__).error("Failed to unlock vault: %s", exc)
        if not wallet_key:
            wallet_key = getpass("Enter your private key / seed phrase: ")
            save_pass = getpass("Create a vault passphrase to store it (leave blank to skip): ")
            if save_pass:
                vault.save(wallet_key, save_pass)
                logging.getLogger(__name__).info("Stored encrypted key at %s", vault.path)

    bot.load_wallet(wallet_key)

    try:
        await bot.run()
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Shutting down bot")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
