#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

LOGFILE="deploy.log"
trap 'echo "[ERROR] Deployment failed at line $LINENO. See $LOGFILE for details." >&2; exit 1' ERR
exec > >(tee -a "$LOGFILE") 2>&1

echo "==== Deployment started at $(date --iso-8601=seconds) ===="

# 1. Env check
for v in OPENAI_API_KEY TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID MT5_LOGIN MT5_PASSWORD MT5_SERVER; do
  [ ! -z "${!v-}" ] || { echo "[ERROR] $v not set"; exit 1; }
done

# 2. Dependencies
command -v python3 >/dev/null || sudo apt-get update && sudo apt-get install -y python3
command -v pip3   >/dev/null || sudo apt-get install -y python3-pip
command -v pm2    >/dev/null && echo "PM2 OK" || sudo npm install -g pm2

# 3. venv + pip
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip show MetaTrader5 >/dev/null || pip install MetaTrader5

# 4. PM2 restart
pm2 delete ai-trader-bot || true
pm2 start pm2.config.js
sleep 2

pm2 describe ai-trader-bot | grep -q "online" \
  && echo "Bot is online" \
  || { echo "PM2 failed to start bot"; exit 1; }

pm2 save
pm2 startup systemd -u "$USER" --hp "$HOME"

echo "==== Deployment completed at $(date --iso-8601=seconds) ===="
echo "Logs: $PWD/$LOGFILE"
