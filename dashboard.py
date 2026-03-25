"""
dashboard.py - Web dashboard for momentum strategy.
Serves on port 8765. Host behind nginx for trading.nimitaggarwal.com.

Usage:
  python dashboard.py              # Serve dashboard
  python dashboard.py --port 9000  # Custom port
"""

import argparse
import json
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler

import database as db


class DashboardHandler(SimpleHTTPRequestHandler):
    PREFIX = "/india"

    def do_GET(self):
        path = self.path
        # Strip prefix for routing
        if path.startswith(self.PREFIX):
            path = path[len(self.PREFIX):] or "/"

        if path == "/" or path == "/dashboard":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(generate_html().encode())
        elif path == "/api/stats":
            self.send_json(db.get_trading_stats())
        elif path == "/api/positions/open":
            self.send_json(db.get_open_positions())
        elif path == "/api/positions/closed":
            self.send_json(db.get_closed_positions())
        elif path == "/api/trades":
            self.send_json(db.get_recent_trades())
        elif path == "/api/rebalances":
            self.send_json(db.get_rebalance_history())
        elif path == "/api/monthly":
            self.send_json(db.get_monthly_pnl())
        else:
            self.send_response(404)
            self.end_headers()

    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

    def log_message(self, format, *args):
        pass  # suppress access logs


def generate_html():
    stats = db.get_trading_stats()
    open_pos = db.get_open_positions()
    closed_pos = db.get_closed_positions(50)
    recent_trades = db.get_recent_trades(30)
    rebalances = db.get_rebalance_history(10)
    monthly = db.get_monthly_pnl()

    last_reb = stats.get("last_rebalance") or {}

    # Open positions table
    open_rows = ""
    for p in open_pos:
        open_rows += f"""<tr>
            <td><b>{p['ticker'].replace('.NS','')}</b></td>
            <td>{p['entry_date'][:10]}</td>
            <td>₹{p['entry_price']:.1f}</td>
            <td>{p['qty']}</td>
            <td>₹{p['capital']:,.0f}</td>
        </tr>"""

    # Closed positions table
    closed_rows = ""
    for p in closed_pos:
        pnl_class = "profit" if (p.get("profit_pct") or 0) > 0 else "loss"
        closed_rows += f"""<tr>
            <td><b>{p['ticker'].replace('.NS','')}</b></td>
            <td>{(p.get('entry_date') or '')[:10]}</td>
            <td>{(p.get('exit_date') or '')[:10]}</td>
            <td>₹{p.get('entry_price', 0):.1f}</td>
            <td>₹{p.get('exit_price', 0):.1f}</td>
            <td class="{pnl_class}">{p.get('profit_pct', 0):+.1f}%</td>
            <td class="{pnl_class}">₹{p.get('profit_amount', 0):+,.0f}</td>
            <td>{p.get('exit_reason', '')}</td>
        </tr>"""

    # Recent trades table
    trade_rows = ""
    for t in recent_trades:
        action_class = "buy" if t["action"] == "BUY" else "sell"
        trade_rows += f"""<tr>
            <td class="{action_class}"><b>{t['action']}</b></td>
            <td>{t['ticker'].replace('.NS','')}</td>
            <td>₹{t['price']:.1f}</td>
            <td>{t['qty']}</td>
            <td>₹{t['amount']:,.0f}</td>
            <td>{(t.get('created_at') or '')[:16]}</td>
        </tr>"""

    # Rebalance history
    reb_rows = ""
    for r in rebalances:
        status_class = "invested" if r["status"] == "invested" else "cash-status"
        reb_rows += f"""<tr>
            <td>{r['date'][:10]}</td>
            <td>{r['regime']}</td>
            <td class="{status_class}"><b>{r['status'].upper()}</b></td>
            <td>{r['num_stocks']}</td>
        </tr>"""

    # Monthly P&L
    monthly_rows = ""
    for m in monthly:
        pnl_class = "profit" if (m.get("pnl") or 0) > 0 else "loss"
        wr = round(m["wins"] / m["trades"] * 100) if m["trades"] > 0 else 0
        monthly_rows += f"""<tr>
            <td>{m['month']}</td>
            <td>{m['trades']}</td>
            <td>{wr}%</td>
            <td class="{pnl_class}">₹{m.get('pnl', 0):+,.0f}</td>
            <td class="{pnl_class}">{m.get('avg_pct', 0):+.1f}%</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Momentum Dashboard</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
           background: #0d1117; color: #c9d1d9; padding: 20px; }}
    h1 {{ color: #58a6ff; margin-bottom: 8px; }}
    h2 {{ color: #8b949e; font-size: 16px; margin: 24px 0 12px; border-bottom: 1px solid #21262d; padding-bottom: 8px; }}
    .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
              gap: 12px; margin: 16px 0; }}
    .stat {{ background: #161b22; border: 1px solid #21262d; border-radius: 8px;
             padding: 16px; text-align: center; }}
    .stat .value {{ font-size: 28px; font-weight: bold; color: #58a6ff; }}
    .stat .label {{ font-size: 12px; color: #8b949e; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 14px; }}
    th {{ background: #161b22; color: #8b949e; text-align: left; padding: 8px 12px;
          border-bottom: 2px solid #21262d; font-weight: 600; }}
    td {{ padding: 8px 12px; border-bottom: 1px solid #21262d; }}
    tr:hover {{ background: #161b22; }}
    .profit {{ color: #3fb950; }}
    .loss {{ color: #f85149; }}
    .buy {{ color: #3fb950; }}
    .sell {{ color: #f85149; }}
    .invested {{ color: #3fb950; }}
    .cash-status {{ color: #d29922; }}
    .regime-badge {{ display: inline-block; padding: 4px 12px; border-radius: 12px;
                     font-weight: bold; font-size: 14px; }}
    .regime-bullish {{ background: #0d2818; color: #3fb950; }}
    .regime-bearish {{ background: #2d1013; color: #f85149; }}
    .updated {{ color: #484f58; font-size: 12px; margin-top: 16px; }}
    .section {{ background: #0d1117; margin-bottom: 24px; }}
</style>
</head><body>
<h1>Momentum Strategy Dashboard</h1>
<p>
    Last rebalance: <b>{last_reb.get('date', 'N/A')}</b> &nbsp;
    <span class="regime-badge regime-{last_reb.get('regime', 'bearish')}">
        {last_reb.get('regime', 'N/A').upper()}
    </span> &nbsp;
    <span class="regime-badge {'regime-bullish' if last_reb.get('status') == 'invested' else 'regime-bearish'}">
        {last_reb.get('status', 'N/A').upper()}
    </span>
</p>

<div class="stats">
    <div class="stat"><div class="value">{stats.get('open_positions', 0)}</div><div class="label">Open Positions</div></div>
    <div class="stat"><div class="value">{stats.get('closed_positions', 0)}</div><div class="label">Closed Trades</div></div>
    <div class="stat"><div class="value">{stats.get('win_rate', 0)}%</div><div class="label">Win Rate</div></div>
    <div class="stat"><div class="value {'profit' if stats.get('total_pnl', 0) >= 0 else 'loss'}">₹{stats.get('total_pnl', 0):+,.0f}</div><div class="label">Total P&L</div></div>
    <div class="stat"><div class="value">{stats.get('total_rebalances', 0)}</div><div class="label">Rebalances</div></div>
    <div class="stat"><div class="value">₹{stats.get('avg_pnl', 0):+,.0f}</div><div class="label">Avg P&L / Trade</div></div>
</div>

<h2>Open Positions</h2>
<table>
    <tr><th>Stock</th><th>Entry Date</th><th>Entry Price</th><th>Qty</th><th>Capital</th></tr>
    {open_rows if open_rows else '<tr><td colspan="5" style="text-align:center;color:#484f58">No open positions — in cash</td></tr>'}
</table>

<h2>Closed Positions</h2>
<table>
    <tr><th>Stock</th><th>Entry</th><th>Exit</th><th>Buy</th><th>Sell</th><th>P&L %</th><th>P&L ₹</th><th>Reason</th></tr>
    {closed_rows if closed_rows else '<tr><td colspan="8" style="text-align:center;color:#484f58">No closed positions yet</td></tr>'}
</table>

<h2>Monthly P&L</h2>
<table>
    <tr><th>Month</th><th>Trades</th><th>Win Rate</th><th>P&L ₹</th><th>Avg %</th></tr>
    {monthly_rows if monthly_rows else '<tr><td colspan="5" style="text-align:center;color:#484f58">No data yet</td></tr>'}
</table>

<h2>Recent Trades</h2>
<table>
    <tr><th>Action</th><th>Stock</th><th>Price</th><th>Qty</th><th>Amount</th><th>Time</th></tr>
    {trade_rows if trade_rows else '<tr><td colspan="6" style="text-align:center;color:#484f58">No trades yet</td></tr>'}
</table>

<h2>Rebalance History</h2>
<table>
    <tr><th>Date</th><th>Regime</th><th>Status</th><th>Stocks</th></tr>
    {reb_rows if reb_rows else '<tr><td colspan="4" style="text-align:center;color:#484f58">No rebalances yet</td></tr>'}
</table>

<p class="updated">Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</body></html>"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = HTTPServer(("0.0.0.0", args.port), DashboardHandler)
    print(f"Dashboard running on http://0.0.0.0:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
