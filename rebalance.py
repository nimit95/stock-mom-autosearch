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
INITIAL_CAPITAL = 500_000  # 5 lakh

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


def get_strategy_picks(send_telegram=True, portfolio_value=None):
    """Run momentum strategy, return list of NSE symbols or empty (cash)."""
    import pandas as pd
    import numpy as np
    import telegram_bot

    pv = portfolio_value or INITIAL_CAPITAL

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

    import database as db

    if not regime_ok:
        print("REGIME FILTER: Go to cash")
        db.log_rebalance(latest.date(), "bearish", 0, "cash",
                         float(bench_cum.loc[latest]), float(bench_ma.loc[latest]))
        if send_telegram:
            telegram_bot.send_rebalance_alert(
                latest, False, [], indicators, get_sector, portfolio_value=pv)
        return []

    picks = screen_stocks(indicators, latest)

    # Send Telegram alert
    if send_telegram:
        telegram_bot.send_rebalance_alert(
            latest, True, picks, indicators, get_sector, portfolio_value=pv)

    if len(picks) < MIN_STOCKS:
        print(f"Only {len(picks)} stocks qualify (need {MIN_STOCKS}). Go to cash.")
        db.log_rebalance(latest.date(), "bullish", len(picks), "cash",
                         float(bench_cum.loc[latest]), float(bench_ma.loc[latest]))
        return []

    db.log_rebalance(latest.date(), "bullish", len(picks), "invested",
                     float(bench_cum.loc[latest]), float(bench_ma.loc[latest]))

    # Convert to Kite symbols (remove .NS suffix)
    return [t.replace(".NS", "") for t in picks]


def compute_trades(current_holdings, target_symbols, portfolio_value, kite):
    """
    Compute BUY/SELL orders to rebalance from current to target.
    Only manages positions tracked in our DB — never touches personal holdings.
    Returns list of order dicts.
    """
    import database as db

    orders = []

    # Get OUR open positions from DB (not all Kite holdings)
    our_positions = {p["ticker"]: p for p in db.get_open_positions()}

    # Stocks to sell: in our DB but not in target picks
    for sym, pos in our_positions.items():
        if sym not in target_symbols:
            orders.append({
                "action": "SELL",
                "symbol": sym,
                "qty": pos["qty"],
                "price": pos.get("entry_price", 0),
                "reason": "not in target",
            })

    if not target_symbols:
        return orders

    # Target allocation: equal weight
    per_stock = portfolio_value / len(target_symbols)

    # Get current prices via LTP
    all_syms = set(target_symbols) | set(our_positions.keys())
    instruments = [f"{EXCHANGE}:{sym}" for sym in all_syms]
    try:
        ltps = kite.ltp(instruments)
    except Exception as e:
        print(f"Error fetching LTP: {e}")
        return orders

    # Update sell prices with live LTP
    for o in orders:
        key = f"{EXCHANGE}:{o['symbol']}"
        if key in ltps:
            o["price"] = ltps[key]["last_price"]
            o["amount"] = o["qty"] * o["price"]

    for sym in target_symbols:
        key = f"{EXCHANGE}:{sym}"
        if key not in ltps:
            print(f"  Warning: no LTP for {sym}, skipping")
            continue

        price = ltps[key]["last_price"]
        target_qty = int(per_stock / price)

        # Only consider qty from our positions, not personal holdings
        current_qty = our_positions[sym]["qty"] if sym in our_positions else 0
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
    """Place orders via Kite Connect and log to database."""
    import database as db
    from datetime import date

    if not orders:
        print("No trades needed.")
        return

    print(f"\n{'=' * 60}")
    print(f"  {'DRY RUN - ' if dry_run else ''}TRADES TO EXECUTE")
    print(f"{'=' * 60}")

    sells = [o for o in orders if o["action"] == "SELL"]
    buys = [o for o in orders if o["action"] == "BUY"]
    today = str(date.today())

    # Sell first (free up capital)
    for o in sells:
        print(f"  SELL  {o['symbol']:<15s}  qty={o['qty']:>4d}  ({o['reason']})")
        order_id = None
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

        price = o.get("price", 0)
        amount = o.get("amount", o["qty"] * price)

        # Log trade to DB
        db.log_trade(o["symbol"], "SELL", price, o["qty"], amount,
                      kite_order_id=str(order_id) if order_id else None)

        # Close position in DB
        db.close_position(o["symbol"], today, price,
                          exit_reason=o.get("reason", "rebalance"))

    for o in buys:
        price = o.get("price", 0)
        amount = o.get("amount", o["qty"] * price)
        amt_str = f"  ~Rs {amount:,.0f}" if amount else ""
        print(f"  BUY   {o['symbol']:<15s}  qty={o['qty']:>4d}  @ {price:>8.1f}{amt_str}")
        order_id = None
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

        # Log trade to DB
        db.log_trade(o["symbol"], "BUY", price, o["qty"], amount,
                      kite_order_id=str(order_id) if order_id else None)

        # Open position in DB
        db.open_position(o["symbol"], today, price, o["qty"], amount)

    print(f"{'=' * 60}")
    total_sell = sum(o.get("amount", 0) for o in sells)
    total_buy = sum(o.get("amount", 0) for o in buys)
    print(f"  Total sell: Rs {total_sell:,.0f}")
    print(f"  Total buy:  Rs {total_buy:,.0f}")


def main():
    parser = argparse.ArgumentParser(description="Weekly momentum rebalance via Kite")
    parser.add_argument("--login", action="store_true", help="Login and get access token")
    parser.add_argument("--dry-run", action="store_true", help="Show trades without executing")
    parser.add_argument("--portfolio", type=float, default=None,
                        help="Override portfolio size in Rs (default: auto from DB)")
    args = parser.parse_args()

    if args.login:
        login()
        return

    import database as db_mod
    import telegram_bot

    # 1. Compute portfolio value (reinvest profits)
    pv = db_mod.get_portfolio_value(INITIAL_CAPITAL)
    portfolio_value = args.portfolio or pv["total"]
    print(f"Portfolio: ₹{portfolio_value:,.0f} (initial ₹{INITIAL_CAPITAL:,.0f} + P&L ₹{pv['realized_pnl']:+,.0f})")
    print(f"  Available: ₹{pv['available']:,.0f}  Invested: ₹{pv['invested']:,.0f}")

    # 2. Get strategy picks
    print("\nRunning momentum strategy...")
    target_symbols = get_strategy_picks(portfolio_value=portfolio_value)

    # 3. Connect to Kite (skip in dry-run if no token)
    kite = None
    current = {}
    if not args.dry_run:
        print("\nConnecting to Kite...")
        kite = get_kite()
        current = get_current_holdings(kite)
        print(f"Current holdings: {len(current)} stocks")
        if current:
            for sym, qty in sorted(current.items()):
                print(f"  {sym}: {qty}")
    else:
        # In dry-run, use DB positions as current holdings
        open_positions = db_mod.get_open_positions()
        current = {p["ticker"]: p["qty"] for p in open_positions}
        print(f"\nDry-run: {len(current)} open positions from DB")

    # 5. Compute trades
    print(f"\nTarget: {len(target_symbols)} stocks" if target_symbols else "\nTarget: CASH")
    orders = compute_trades(current, target_symbols, portfolio_value, kite)

    # 5. Execute
    execute_orders(kite, orders, dry_run=args.dry_run)

    # 6. Send status to Telegram
    stats = db_mod.get_trading_stats()
    open_pos = db_mod.get_open_positions()
    mode = "DRY RUN" if args.dry_run else "LIVE"

    status_lines = [f"<b>REBALANCE STATUS ({mode})</b>", ""]

    if open_pos:
        status_lines.append(f"Open positions: {len(open_pos)}")
        for p in open_pos:
            sym = p['ticker'].replace('.NS', '')
            status_lines.append(f"  {sym}  qty={p['qty']}  entry=₹{p['entry_price']:.0f}")
    else:
        status_lines.append("Open positions: 0 (CASH)")

    status_lines.append("")
    status_lines.append(f"Portfolio: ₹{portfolio_value:,.0f}")
    status_lines.append(f"Closed trades: {stats['closed_positions']}")
    status_lines.append(f"Win rate: {stats['win_rate']}%")
    status_lines.append(f"Total P&L: ₹{stats['total_pnl']:+,.0f}")
    status_lines.append(f"Rebalances: {stats['total_rebalances']}")

    telegram_bot.send_message("\n".join(status_lines))


if __name__ == "__main__":
    main()
