"""
database.py - SQLite database for tracking trades, positions, and P&L.
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "momentum.db"


def get_db():
    """Get database connection with WAL mode."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS rebalances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            regime TEXT NOT NULL,          -- 'bullish' or 'bearish'
            num_stocks INTEGER NOT NULL,
            status TEXT NOT NULL,          -- 'invested' or 'cash'
            nifty_value REAL,
            nifty_ma REAL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            entry_date TEXT NOT NULL,
            entry_price REAL NOT NULL,
            qty INTEGER NOT NULL,
            capital REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',  -- 'open' or 'closed'
            exit_date TEXT,
            exit_price REAL,
            profit_pct REAL,
            profit_amount REAL,
            exit_reason TEXT,             -- 'rebalance', 'regime_exit', 'manual'
            rebalance_id INTEGER,
            FOREIGN KEY (rebalance_id) REFERENCES rebalances(id)
        );

        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            action TEXT NOT NULL,         -- 'BUY' or 'SELL'
            price REAL NOT NULL,
            qty INTEGER NOT NULL,
            amount REAL NOT NULL,
            rebalance_id INTEGER,
            kite_order_id TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (rebalance_id) REFERENCES rebalances(id)
        );

        CREATE TABLE IF NOT EXISTS daily_snapshots (
            date TEXT PRIMARY KEY,
            portfolio_value REAL,
            cash_value REAL,
            invested_value REAL,
            num_positions INTEGER,
            benchmark_value REAL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
        CREATE INDEX IF NOT EXISTS idx_positions_ticker ON positions(ticker);
        CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(created_at);
    """)
    conn.commit()
    conn.close()


# ── Rebalances ─────────────────────────────────────────────────

def log_rebalance(date, regime, num_stocks, status, nifty_value=None, nifty_ma=None):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO rebalances (date, regime, num_stocks, status, nifty_value, nifty_ma) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (str(date), regime, num_stocks, status, nifty_value, nifty_ma),
    )
    rebalance_id = cur.lastrowid
    conn.commit()
    conn.close()
    return rebalance_id


# ── Positions ──────────────────────────────────────────────────

def open_position(ticker, entry_date, entry_price, qty, capital, rebalance_id=None):
    conn = get_db()
    conn.execute(
        "INSERT INTO positions (ticker, entry_date, entry_price, qty, capital, status, rebalance_id) "
        "VALUES (?, ?, ?, ?, ?, 'open', ?)",
        (ticker, str(entry_date), entry_price, qty, capital, rebalance_id),
    )
    conn.commit()
    conn.close()


def close_position(ticker, exit_date, exit_price, exit_reason="rebalance"):
    conn = get_db()
    pos = conn.execute(
        "SELECT * FROM positions WHERE ticker=? AND status='open' ORDER BY id DESC LIMIT 1",
        (ticker,),
    ).fetchone()
    if pos:
        profit_pct = (exit_price / pos["entry_price"] - 1) * 100
        profit_amount = (exit_price - pos["entry_price"]) * pos["qty"]
        conn.execute(
            "UPDATE positions SET status='closed', exit_date=?, exit_price=?, "
            "profit_pct=?, profit_amount=?, exit_reason=? WHERE id=?",
            (str(exit_date), exit_price, round(profit_pct, 2),
             round(profit_amount, 2), exit_reason, pos["id"]),
        )
        conn.commit()
    conn.close()


def get_open_positions():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM positions WHERE status='open' ORDER BY entry_date DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_closed_positions(limit=100):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM positions WHERE status='closed' ORDER BY exit_date DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Trades ─────────────────────────────────────────────────────

def log_trade(ticker, action, price, qty, amount, rebalance_id=None, kite_order_id=None):
    conn = get_db()
    conn.execute(
        "INSERT INTO trades (ticker, action, price, qty, amount, rebalance_id, kite_order_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (ticker, action, price, qty, amount, rebalance_id, kite_order_id),
    )
    conn.commit()
    conn.close()


# ── Snapshots ──────────────────────────────────────────────────

def log_snapshot(date, portfolio_value, cash_value, invested_value, num_positions, benchmark_value=None):
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO daily_snapshots "
        "(date, portfolio_value, cash_value, invested_value, num_positions, benchmark_value) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (str(date), portfolio_value, cash_value, invested_value, num_positions, benchmark_value),
    )
    conn.commit()
    conn.close()


# ── Stats ──────────────────────────────────────────────────────

def get_trading_stats():
    conn = get_db()
    stats = {}

    # Total trades
    row = conn.execute("SELECT COUNT(*) as cnt FROM trades").fetchone()
    stats["total_trades"] = row["cnt"]

    # Open positions
    row = conn.execute("SELECT COUNT(*) as cnt FROM positions WHERE status='open'").fetchone()
    stats["open_positions"] = row["cnt"]

    # Closed positions
    row = conn.execute("SELECT COUNT(*) as cnt FROM positions WHERE status='closed'").fetchone()
    stats["closed_positions"] = row["cnt"]

    # Win rate
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM positions WHERE status='closed' AND profit_pct > 0"
    ).fetchone()
    wins = row["cnt"]
    stats["win_rate"] = round(wins / stats["closed_positions"] * 100, 1) if stats["closed_positions"] > 0 else 0

    # Total P&L
    row = conn.execute(
        "SELECT COALESCE(SUM(profit_amount), 0) as total FROM positions WHERE status='closed'"
    ).fetchone()
    stats["total_pnl"] = round(row["total"], 2)

    # Average P&L per trade
    stats["avg_pnl"] = round(stats["total_pnl"] / stats["closed_positions"], 2) if stats["closed_positions"] > 0 else 0

    # Last rebalance
    row = conn.execute("SELECT * FROM rebalances ORDER BY id DESC LIMIT 1").fetchone()
    stats["last_rebalance"] = dict(row) if row else None

    # Rebalance count
    row = conn.execute("SELECT COUNT(*) as cnt FROM rebalances").fetchone()
    stats["total_rebalances"] = row["cnt"]

    conn.close()
    return stats


def get_portfolio_value(initial_capital):
    """Compute current portfolio value: initial capital + realized P&L."""
    conn = get_db()
    # Total realized P&L from closed positions
    row = conn.execute(
        "SELECT COALESCE(SUM(profit_amount), 0) as total FROM positions WHERE status='closed'"
    ).fetchone()
    realized_pnl = row["total"]

    # Capital currently in open positions
    row = conn.execute(
        "SELECT COALESCE(SUM(capital), 0) as total FROM positions WHERE status='open'"
    ).fetchone()
    invested = row["total"]

    conn.close()
    total = initial_capital + realized_pnl
    available = total - invested
    return {"total": total, "available": available, "invested": invested, "realized_pnl": realized_pnl}


def get_recent_trades(limit=50):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM trades ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_rebalance_history(limit=20):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM rebalances ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_monthly_pnl():
    conn = get_db()
    rows = conn.execute("""
        SELECT
            strftime('%Y-%m', exit_date) as month,
            COUNT(*) as trades,
            SUM(CASE WHEN profit_pct > 0 THEN 1 ELSE 0 END) as wins,
            ROUND(SUM(profit_amount), 2) as pnl,
            ROUND(AVG(profit_pct), 2) as avg_pct
        FROM positions
        WHERE status='closed' AND exit_date IS NOT NULL
        GROUP BY month
        ORDER BY month DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Initialize on import
init_db()
