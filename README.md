# SolCodex

Bot de trading asynchrone en Python pour surveiller les lancements de tokens sur la blockchain Solana (via le flux Pump.fun) et appliquer une stratégie de sniping configurable.

## Fonctionnalités

- Connexion websocket en temps réel au flux public Pump.fun pour détecter les nouveaux tokens.
- Stratégie de filtrage simple configurable (liquidité minimale, mots clés bloquants) pour décider des snipes.
- Analyse de risque (rug/honeypot) basée sur plusieurs facteurs : mots-clés suspects, spam créateur, longueur du symbole, présence d'une description.
- Surveillance continue du prix (DexScreener) pour couper automatiquement en take-profit/stop-loss.
- Orchestrateur `TradingBot` qui enchaîne découverte, décision, exécution (simulée) et sorties sécurisées.
- Interface console légère affichant la configuration active et l'état des positions au lancement.
- Configuration via fichier TOML ou variables d'environnement `SOLCODEX_*`.
- Coffre local chiffré (passphrase) pour mémoriser votre seed phrase/clé privée en dehors du fichier de config.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration rapide

Créez un fichier `config.toml` (ou utilisez la variable d'environnement `SOLCODEX_CONFIG` pour pointer vers un autre chemin) avec vos paramètres :

```toml
[wallet]
# Clé privée en base58 ou base64
private_key = "..."
rpc_endpoint = "https://api.mainnet-beta.solana.com"
commitment = "processed"
# Emplacement du coffre chiffré pour conserver la clé (optionnel)
vault_path = "~/.solcodex/seed_vault.json"

[websocket]
url = "wss://pumpportal.fun/api/v1"
reconnect_seconds = 5
max_queue = 1000

[trading]
max_open_positions = 3
max_position_sol = 0.5
# Ratio de prise de profit / stop (0.3 = +30%, 0.15 = -15%)
take_profit = 0.3
stop_loss = 0.15
# Slippage maximum en basis points
slippage_bps = 50
min_liquidity_sol = 5.0
# Score de risque maximum autorisé (0 = très strict, 1 = permissif)
max_risk_score = 0.5
# Longueur minimale de description exigée pour limiter les fiches vides
min_description_chars = 20
# Nombre de tokens émis par le même créateur avant de le marquer comme spam
suspicious_creator_limit = 3
# Longueur maximale du symbole pour filtrer les tickers peu sérieux
max_symbol_length = 10
# Fréquence de vérification des positions ouvertes (en secondes)
price_check_seconds = 10
```

## Lancement

```bash
python main.py --config config.toml --log-level INFO
```

Au démarrage, un bandeau CLI affiche le résumé des paramètres de trading et l'état des positions. Si `wallet.private_key` est
vide, le bot tentera de déverrouiller votre clé depuis le coffre local (passphrase demandée). À défaut, il vous demandera une
clé privée/seed phrase puis proposera d'enregistrer une passphrase pour la stocker de manière chiffrée.

La section d'exécution d'ordres est volontairement simulée pour éviter l'envoi de transactions réelles. Branchez votre logique de swap Solana (par ex. Jupiter, Raydium) dans `TradingBot._attempt_snipe` dès que vous êtes prêt à trader sur mainnet.

## Architecture

- `src/solcodex/clients/pumpfun_client.py` : client websocket Pump.fun avec reconnexion automatique.
- `src/solcodex/clients/price_oracle.py` : récupération des prix (DexScreener) pour surveiller les positions.
- `src/solcodex/clients/solana_client.py` : envoi de transactions et lecture d'état via `solana-py`.
- `src/solcodex/trading/strategy.py` : stratégie de sniping basique.
- `src/solcodex/trading/risk.py` : heuristiques de défense (rug/honeypot) et scoring de risque.
- `src/solcodex/trading/bot.py` : orchestrateur principal des flux et décisions.
- `src/solcodex/config.py` : chargement des paramètres TOML + overrides d'environnement.
- `main.py` : point d'entrée CLI.

## Avertissement

Ce dépôt est fourni à titre éducatif. Vérifiez la conformité légale et les risques financiers avant tout usage en production. Toute transaction sur Solana est définitive et peut engendrer des pertes. 
