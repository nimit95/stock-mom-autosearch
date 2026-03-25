# CLAUDE.md

## Project
Indian stock momentum strategy — weekly rebalance, Kite Connect API, Telegram alerts.

## Key Rules
- **Never sell personal holdings** — only manage positions tracked in our SQLite DB (`data/momentum.db`). The `positions` table is the source of truth for what this system owns.
- **Always use venv** — `source .venv/bin/activate` before any pip install or python run.
- **prepare.py is read-only** — never modify it during experiments. Only strategy.py is tunable.
- **Backtest honesty** — all signals must have 1-day execution delay. Never compute return and stop-loss on the same day's close.
- **.env has secrets** — never commit. Contains Kite API key/secret, Telegram bot token/chat ID.

## Server
- SSH: `ssh nimit@100.86.165.31` (Tailscale, password: 0424)
- Deploy path: `~/Documents/stock-mom-autosearch`
- Runs in Docker: `docker compose up -d dashboard` (port 8765)
- Dashboard URL: `trading.nimitaggarwal.com/india`
- Weekly rebalance: `docker compose run --rm rebalance python3 rebalance.py --dry-run`

## Current Best Strategy (Config D)
- ROC periods: 1m/3m/6m/12m, weights: 0.05/0.15/0.3/0.5
- MA 50/200 trend filter
- RSI(14) 30-70
- Dual momentum (stock 6m ROC > Nifty 6m ROC)
- Top 3 sectors, top 15 stocks
- MIN_STOCKS=7 (fewer → cash)
- Regime filter: Nifty < 150 DMA → cash
- Weekly rebalance, 1-day execution delay
- Sharpe 2.45, max DD 11.4% (2023-2026 honest backtest)

## Telegram
- Bot: @Stock_momentum_india_bot
- Token in .env
- Sends weekly rebalance alerts (stocks to buy/sell or cash signal)

## GitHub
- Repo: https://github.com/nimit95/stock-mom-autosearch
- Branch: autoresearch/mar25
