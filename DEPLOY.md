# Deploy Guide

## Server: ssh nimit@100.86.165.31 (password: 0424)

### First-time setup

```bash
# 1. Clone repo
cd ~/Documents
git clone https://github.com/nimit95/stock-mom-autosearch.git
cd stock-mom-autosearch
git checkout autoresearch/mar25

# 2. Create .env with credentials
cat > .env << 'EOF'
KITE_API_KEY=mucrfgia4jjjtk44
KITE_API_SECRET=r570lf3out0okhsxj46me2olwm0s2dwc
TELEGRAM_BOT_TOKEN=8571513104:AAF2zPMaSel3GdBQte5b-F3be8aRclsMlNA
TELEGRAM_CHAT_ID=8294634281
EOF

# 3. Build and start dashboard
docker compose up -d --build dashboard

# 4. Fetch market data (first time only, takes ~5 min)
docker compose run --rm rebalance python3 prepare.py

# 5. Test Telegram
docker compose run --rm rebalance python3 telegram_bot.py

# 6. Verify dashboard
curl http://localhost:8765/india
```

### Cloudflare / Nginx

Point `trading.nimitaggarwal.com/india` → `127.0.0.1:8765`.

If using nginx, add to existing server block:
```nginx
location /india/ {
    proxy_pass http://127.0.0.1:8765/india/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

Then: `sudo nginx -t && sudo nginx -s reload`

### Weekly rebalance (Monday morning)

```bash
cd ~/Documents/stock-mom-autosearch

# Dry run first (shows trades + sends Telegram)
docker compose run --rm rebalance python3 rebalance.py --dry-run

# To execute real trades:
# 1. Login to Kite (opens browser — do this on local machine, copy token)
# docker compose run --rm rebalance python3 rebalance.py --login
# 2. Execute
# docker compose run --rm rebalance python3 rebalance.py --portfolio 1500000
```

### Cron (optional — auto dry-run every Monday)

```bash
crontab -e
# Add:
50 3 * * 1 cd ~/Documents/stock-mom-autosearch && docker compose run --rm rebalance python3 rebalance.py --dry-run >> rebalance.log 2>&1
```
(3:50 UTC = 9:20 AM IST)

### Update deployment

```bash
cd ~/Documents/stock-mom-autosearch
git pull
docker compose up -d --build dashboard
```

### Check status

```bash
docker compose ps                    # running containers
docker compose logs dashboard        # dashboard logs
curl http://localhost:8765/india      # test dashboard
```
