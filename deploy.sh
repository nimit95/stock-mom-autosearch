#!/bin/bash
# deploy.sh - Deploy to server.
# Usage: bash deploy.sh

set -e

SERVER="nimit@100.86.165.31"
REMOTE_DIR="/home/nimit/stock-mom-autosearch"

echo "Deploying to ${SERVER}:${REMOTE_DIR}..."

# Push latest to GitHub
git push origin autoresearch/mar25

# SSH and pull on server
ssh $SERVER << 'EOF'
    cd /home/nimit

    # Clone if first time
    if [ ! -d "stock-mom-autosearch" ]; then
        git clone https://github.com/nimit95/stock-mom-autosearch.git
        cd stock-mom-autosearch
        git checkout autoresearch/mar25
        python3 -m venv .venv
        source .venv/bin/activate
        pip install -q yfinance pandas numpy scipy kiteconnect requests
    else
        cd stock-mom-autosearch
        git pull
        source .venv/bin/activate
    fi

    # Fetch data if not cached
    if [ ! -f ~/.cache/mom-autosearch/market_data.pkl ]; then
        echo "Fetching market data..."
        python3 prepare.py
    fi

    # Copy .env if missing
    if [ ! -f .env ]; then
        echo "WARNING: .env missing on server. Copy manually."
    fi

    # Restart dashboard
    screen -X -S mom-dashboard quit 2>/dev/null || true
    screen -dmS mom-dashboard python3 -u dashboard.py
    echo "Dashboard started on port 8765"

    # Setup cron for watchdog (if not already set)
    if ! crontab -l 2>/dev/null | grep -q "mom-autosearch/watchdog.sh"; then
        (crontab -l 2>/dev/null; echo "*/5 * * * * /home/nimit/stock-mom-autosearch/watchdog.sh >> /home/nimit/stock-mom-autosearch/watchdog.log 2>&1") | crontab -
        echo "Watchdog cron added"
    fi

    # Setup cron for weekly rebalance (Monday 9:20 AM IST)
    if ! crontab -l 2>/dev/null | grep -q "mom-autosearch/rebalance.py"; then
        (crontab -l 2>/dev/null; echo "50 3 * * 1 cd /home/nimit/stock-mom-autosearch && source .venv/bin/activate && python3 rebalance.py --dry-run >> /home/nimit/stock-mom-autosearch/rebalance.log 2>&1") | crontab -
        echo "Weekly rebalance cron added (Monday 9:20 AM IST = 3:50 UTC)"
    fi

    echo "Deploy complete!"
EOF

echo "Done."
