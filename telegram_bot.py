"""
telegram_bot.py - Send momentum strategy alerts to Telegram.

Setup:
  1. Create a new Telegram bot via @BotFather → get bot token
  2. Create a Telegram group, add the bot
  3. Get chat ID (send a message in group, then check:
     https://api.telegram.org/bot<TOKEN>/getUpdates)
  4. Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to .env
"""

import os
import requests
from pathlib import Path


def _load_config():
    env_file = Path(__file__).parent / ".env"
    env = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


_env = _load_config()
BOT_TOKEN = _env.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = _env.get("TELEGRAM_CHAT_ID", "")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


def send_message(text, parse_mode="HTML"):
    """Send a message to the configured Telegram chat."""
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram not configured (missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env)")
        return False
    try:
        resp = requests.post(API_URL, json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": parse_mode,
        }, timeout=10)
        return resp.ok
    except Exception as e:
        print(f"Telegram send failed: {e}")
        return False


def send_rebalance_alert(date, regime_ok, picks, indicators, get_sector_fn):
    """Send weekly rebalance notification."""
    lines = [f"<b>MOMENTUM REBALANCE — {date}</b>"]
    lines.append("")

    if not regime_ok:
        lines.append("Regime: BEARISH (Nifty below 150 DMA)")
        lines.append("")
        lines.append("Action: <b>100% CASH</b>")
        lines.append("Sell all holdings.")
    elif not picks:
        lines.append("Regime: BULLISH")
        lines.append("But fewer than 7 stocks qualify.")
        lines.append("")
        lines.append("Action: <b>100% CASH</b>")
    else:
        lines.append(f"Regime: BULLISH")
        lines.append(f"Action: <b>BUY {len(picks)} stocks</b> (equal weight)")
        lines.append("")

        for i, t in enumerate(picks, 1):
            sym = t.replace(".NS", "")
            sec = get_sector_fn(t)
            if t in indicators and date in indicators[t].index:
                row = indicators[t].loc[date]
                price = row["close"]
                score = row["mom_score"]
                rsi = row["rsi"]
                lines.append(
                    f"{i:2d}. <b>{sym}</b>  {sec}"
                    f"\n    ₹{price:.0f}  score={score:.3f}  RSI={rsi:.0f}"
                )
            else:
                lines.append(f"{i:2d}. <b>{sym}</b>  {sec}")

    send_message("\n".join(lines))


def send_cash_alert(reason):
    """Send alert when going to cash."""
    send_message(f"<b>MOMENTUM ALERT</b>\n\nGoing to CASH.\nReason: {reason}")


def send_error(error, context=""):
    """Send error notification."""
    text = f"<b>MOMENTUM ERROR</b>\n\n{context}\n<code>{error}</code>"
    send_message(text)


def send_test():
    """Send a test message to verify setup."""
    ok = send_message("Momentum bot connected.")
    if ok:
        print("Test message sent successfully.")
    else:
        print("Failed to send test message.")
    return ok


if __name__ == "__main__":
    send_test()
