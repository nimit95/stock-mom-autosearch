"""
rebalance.py - Weekly rebalance via Kite Connect API.

Setup:
  1. Get free personal API key from https://developers.kite.trade
     (Execution APIs are free — no subscription needed)
  2. Copy .env.example to .env and fill in credentials
  3. Run: python rebalance.py --login   (first time / daily)
  4. Run: python rebalance.py           (execute rebalance)

Usage:
  python rebalance.py --login          # Get access token (opens browser)
  python rebalance.py --dry-run        # Show trades without executing
  python rebalance.py                  # Execute trades
  python rebalance.py --portfolio 1500000  # Custom portfolio size (default 10L)
"""

import argparse
import json
import os
import sys
import webbrowser
from pathlib import Path

from kiteconnect import KiteConnect

from prepare import load_data, get_sector, RISK_FREE_RATE
from strategy import (
    precompute_indicators, screen_stocks,
    REGIME_MA, MIN_STOCKS, REBALANCE_EVERY,
)

# ── Config ─────────────────────────────────────────────────────
ENV_FILE = Path(__file__).parent / ".env"
TOKEN_FILE = Path(__file__).parent / ".kite_token"
DEFAULT_PORTFOLIO = 1_000_000  # 10 lakh

EXCHANGE = "NSE"
PRODUCT = "CNC"      # delivery
ORDER_TYPE = "MARKET"


def load_env():
    """Load API key/secret from .env file."""
    if not ENV_FILE.exists():
        print(f"Missing {ENV_FILE}. Copy .env.example to .env and fill credentials.")
        sys.exit(1)
    env = {}
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env


def login():
    """Open browser for Kite login, get access token."""
    env = load_env()
    kite = KiteConnect(api_key=env["KITE_API_KEY"])
    login_url = kite.login_url()
    print(f"Opening browser for login...")
    print(f"URL: {login_url}")
    webbrowser.open(login_url)

    request_token = input("\nPaste the request_token from redirect URL: ").strip()
    session = kite.generate_session(request_token, api_secret=env["KITE_API_SECRET"])
    access_token = session["access_token"]

    TOKEN_FILE.write_text(access_token)
    print(f"Access token saved to {TOKEN_FILE}")
    return access_token


def get_kite():
    """Get authenticated KiteConnect instance."""
    env = load_env()
    if not TOKEN_FILE.exists():
        print("No access token. Run: python rebalance.py --login")
        sys.exit(1)
    access_token = TOKEN_FILE.read_text().strip()
    kite = KiteConnect(api_key=env["KITE_API_KEY"])
    kite.set_access_token(access_token)
    return kite


def get_current_holdings(kite):
    """Get current stock holdings from Kite. Returns {symbol: qty}."""
    holdings = kite.holdings()
    current = {}
    for h in holdings:
        sym = h["tradingsymbol"]
        qty = h["quantity"]
        if qty > 0:
            current[sym] = qty
    return current


def get_strategy_picks():
    """Run momentum strategy, return list of NSE symbols or empty (cash)."""
    import pandas as pd
    import numpy as np

    data = load_data()
    indicators = precompute_indicators(data)

    bench_cum = (1 + data["benchmark_returns"]).cumprod()
    bench_ma = bench_cum.rolling(REGIME_MA).mean()
    latest = sorted(data["benchmark_returns"].index)[-1]

    # Regime check
    regime_ok = bench_cum.loc[latest] >= bench_ma.loc[latest]

    print(f"Date: {latest.date()}")
    print(f"Regime: {'BULLISH' if regime_ok else 'BEARISH'}")
    print(f"Nifty vs {REGIME_MA}DMA: {bench_cum.loc[latest]:.3f} vs {bench_ma.loc[latest]:.3f}")
    print()

    if not regime_ok:
        print("REGIME FILTER: Go to cash")
        return []

    picks = screen_stocks(indicators, latest)
    if len(picks) < MIN_STOCKS:
        print(f"Only {len(picks)} stocks qualify (need {MIN_STOCKS}). Go to cash.")
        return []

    # Convert to Kite symbols (remove .NS suffix)
    return [t.replace(".NS", "") for t in picks]


def compute_trades(current_holdings, target_symbols, portfolio_value, kite):
    """
    Compute BUY/SELL orders to rebalance from current to target.
    Returns list of order dicts.
    """
    orders = []

    # Stocks to sell (in current but not in target)
    for sym, qty in current_holdings.items():
        if sym not in target_symbols:
            orders.append({
                "action": "SELL",
                "symbol": sym,
                "qty": qty,
                "reason": "not in target",
            })

    if not target_symbols:
        return orders

    # Target allocation: equal weight
    per_stock = portfolio_value / len(target_symbols)

    # Get current prices via LTP
    instruments = [f"{EXCHANGE}:{sym}" for sym in target_symbols]
    try:
        ltps = kite.ltp(instruments)
    except Exception as e:
        print(f"Error fetching LTP: {e}")
        # Fallback: skip buy orders
        return orders

    for sym in target_symbols:
        key = f"{EXCHANGE}:{sym}"
        if key not in ltps:
            print(f"  Warning: no LTP for {sym}, skipping")
            continue

        price = ltps[key]["last_price"]
        target_qty = int(per_stock / price)
        current_qty = current_holdings.get(sym, 0)
        diff = target_qty - current_qty

        if diff > 0:
            orders.append({
                "action": "BUY",
                "symbol": sym,
                "qty": diff,
                "price": price,
                "amount": diff * price,
                "reason": "new" if current_qty == 0 else "add",
            })
        elif diff < 0:
            orders.append({
                "action": "SELL",
                "symbol": sym,
                "qty": abs(diff),
                "price": price,
                "amount": abs(diff) * price,
                "reason": "reduce to target weight",
            })
        # else: already at target, no action

    return orders


def execute_orders(kite, orders, dry_run=False):
    """Place orders via Kite Connect."""
    if not orders:
        print("No trades needed.")
        return

    print(f"\n{'=' * 60}")
    print(f"  {'DRY RUN - ' if dry_run else ''}TRADES TO EXECUTE")
    print(f"{'=' * 60}")

    sells = [o for o in orders if o["action"] == "SELL"]
    buys = [o for o in orders if o["action"] == "BUY"]

    # Sell first (free up capital)
    for o in sells:
        print(f"  SELL  {o['symbol']:<15s}  qty={o['qty']:>4d}  ({o['reason']})")
        if not dry_run:
            try:
                order_id = kite.place_order(
                    variety=kite.VARIETY_REGULAR,
                    exchange=EXCHANGE,
                    tradingsymbol=o["symbol"],
                    transaction_type=kite.TRANSACTION_TYPE_SELL,
                    quantity=o["qty"],
                    product=PRODUCT,
                    order_type=ORDER_TYPE,
                )
                print(f"         -> Order ID: {order_id}")
            except Exception as e:
                print(f"         -> FAILED: {e}")

    for o in buys:
        amt_str = f"  ~Rs {o.get('amount', 0):,.0f}" if "amount" in o else ""
        print(f"  BUY   {o['symbol']:<15s}  qty={o['qty']:>4d}  @ {o.get('price', 0):>8.1f}{amt_str}")
        if not dry_run:
            try:
                order_id = kite.place_order(
                    variety=kite.VARIETY_REGULAR,
                    exchange=EXCHANGE,
                    tradingsymbol=o["symbol"],
                    transaction_type=kite.TRANSACTION_TYPE_BUY,
                    quantity=o["qty"],
                    product=PRODUCT,
                    order_type=ORDER_TYPE,
                )
                print(f"         -> Order ID: {order_id}")
            except Exception as e:
                print(f"         -> FAILED: {e}")

    print(f"{'=' * 60}")
    total_sell = sum(o.get("amount", 0) for o in sells)
    total_buy = sum(o.get("amount", 0) for o in buys)
    print(f"  Total sell: Rs {total_sell:,.0f}")
    print(f"  Total buy:  Rs {total_buy:,.0f}")


def main():
    parser = argparse.ArgumentParser(description="Weekly momentum rebalance via Kite")
    parser.add_argument("--login", action="store_true", help="Login and get access token")
    parser.add_argument("--dry-run", action="store_true", help="Show trades without executing")
    parser.add_argument("--portfolio", type=float, default=DEFAULT_PORTFOLIO,
                        help="Portfolio size in Rs (default: 10,00,000)")
    args = parser.parse_args()

    if args.login:
        login()
        return

    # 1. Get strategy picks
    print("Running momentum strategy...")
    target_symbols = get_strategy_picks()

    # 2. Connect to Kite
    print("\nConnecting to Kite...")
    kite = get_kite()

    # 3. Get current holdings
    current = get_current_holdings(kite)
    print(f"Current holdings: {len(current)} stocks")
    if current:
        for sym, qty in sorted(current.items()):
            print(f"  {sym}: {qty}")

    # 4. Compute trades
    print(f"\nTarget: {len(target_symbols)} stocks" if target_symbols else "\nTarget: CASH")
    orders = compute_trades(current, target_symbols, args.portfolio, kite)

    # 5. Execute
    execute_orders(kite, orders, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
