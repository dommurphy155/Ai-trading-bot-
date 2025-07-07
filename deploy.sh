#!/bin/bash
set -e
echo "==== Deployment started at $(date -Iseconds) ===="

sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

# Export envs
export $(grep -v '^#' .env | xargs)

# PM2 (only if installed already)
if ! command -v pm2 &> /dev/null; then
  echo "⚠️ PM2 not installed. Install with: sudo npm install -g pm2"
  exit 1
fi

pm2 start main.py --name ai-trader-bot
pm2 save
echo "✅ Deployment complete"
