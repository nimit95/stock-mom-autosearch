#!/bin/bash
# deploy.sh - Deploy to server via Docker.
# Usage: bash deploy.sh

set -e

SERVER="nimit@100.86.165.31"
REMOTE_DIR="/home/nimit/Documents/stock-mom-autosearch"

echo "Pushing to GitHub..."
git push origin autoresearch/mar25

echo "Deploying to ${SERVER}:${REMOTE_DIR}..."

ssh $SERVER << EOF
    mkdir -p ~/Documents
    cd ~/Documents

    # Clone if first time
    if [ ! -d "stock-mom-autosearch" ]; then
        git clone https://github.com/nimit95/stock-mom-autosearch.git
        cd stock-mom-autosearch
        git checkout autoresearch/mar25
    else
        cd stock-mom-autosearch
        git pull
    fi

    # Copy .env if missing
    if [ ! -f .env ]; then
        echo "WARNING: .env missing on server. Copy it manually:"
        echo "  scp .env ${SERVER}:${REMOTE_DIR}/.env"
    fi

    # Build and start
    docker compose up -d --build dashboard
    echo "Dashboard running on port 8765"

    # Fetch data if not cached
    docker compose run --rm rebalance python3 prepare.py

    echo "Deploy complete!"
EOF

echo "Done."
