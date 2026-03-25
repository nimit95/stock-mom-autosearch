#!/bin/bash
# watchdog.sh - Monitor and restart momentum services.
# Add to crontab: */5 * * * * /path/to/stock-mom-autosearch/watchdog.sh >> /path/to/watchdog.log 2>&1

cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null

TELEGRAM_TOKEN=$(grep TELEGRAM_BOT_TOKEN .env | cut -d= -f2)
TELEGRAM_CHAT=$(grep TELEGRAM_CHAT_ID .env | cut -d= -f2)

send_telegram() {
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
        -d chat_id="${TELEGRAM_CHAT}" -d text="$1" > /dev/null 2>&1
}

echo "$(date): Watchdog check"

# Check dashboard
if ! screen -ls | grep -q "mom-dashboard"; then
    echo "Dashboard is DOWN. Restarting..."
    screen -dmS mom-dashboard python3 -u dashboard.py
    sleep 3
    if screen -ls | grep -q "mom-dashboard"; then
        echo "Dashboard restarted successfully."
        send_telegram "[MOMENTUM] Dashboard restarted"
    else
        echo "Dashboard FAILED to restart."
        send_telegram "[MOMENTUM] Dashboard FAILED to restart!"
    fi
else
    echo "Dashboard: OK"
fi

echo "$(date): Watchdog done"
