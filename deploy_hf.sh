#!/bin/bash

# Hugging Face FXOpen AI Trading Bot - Full Auto Deployment Script

set -euo pipefail

echo "🔁 Starting full Hugging Face AI Trading Bot deployment..."

# Install system dependencies (Playwright etc.)
sudo apt update && sudo apt install -y \
  git curl unzip software-properties-common \
  python3 python3-pip python3-dev \
  libatk1.0-0 libatk-bridge2.0-0 libcups2 libxkbcommon0 \
  libxdamage1 libgbm1 libpango-1.0-0 libcairo2 libatspi2.0-0 \
  nodejs npm

# Install PM2 globally
sudo npm install -g pm2

# Clone or pull repo
REPO_NAME="Ai-trading-bot-"
if [ -d "$REPO_NAME" ]; then
  echo "📁 Repo exists. Pulling latest..."
  cd "$REPO_NAME"
  git pull origin main
else
  echo "📥 Cloning fresh repo..."
  git clone https://github.com/dommurphy155/Ai-trading-bot-.git
  cd "$REPO_NAME"
fi

# Install Python deps globally (skip venv)
echo "📦 Installing Python dependencies..."
pip3 install --upgrade pip
pip3 install -r requirements.txt httpx autopep8

# Install Playwright browser
echo "🌐 Installing Playwright Chromium..."
playwright install chromium || true
sudo playwright install-deps || true

# Format working files only (skip venv/system)
echo "🧹 Auto-formatting working Python files..."
find . -name "*.py" ! -path "./venv/*" ! -path "./.*" -print0 | xargs -0 autopep8 --in-place --aggressive --aggressive || true

# Export environment variables
echo "🔐 Exporting environment variables..."
export HF_TOKEN="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"
export HF_MODEL="mistralai/Mixtral-8x7B-Instruct-v0.1"
export TELEGRAM_BOT_TOKEN="7970729024:AAFIFzpY8-m2OLY07chzcYWJevgXXcTbZUs"
export TELEGRAM_CHAT_ID="7108900627"
export FXOPEN_LOGIN="5012716"
export FXOPEN_API_KEY="fEYWr5E9BmgrC76k"
export FXOPEN_API_SECRET="ab6WXCsQfYn88YPn4Gq2gXDwPqzd9fWn7tcydNnwNfa9wBdsfxGfyT3mFHfFcnR9"
export FXOPEN_SERVER="ttdemomarginal.fxopen.net"

# Launch via PM2
echo "🚀 Launching bot with PM2..."
pm2 delete ai-trader-bot || true
pm2 start main.py --name ai-trader-bot --interpreter python3
pm2 save

# Enable PM2 on boot
pm2 startup systemd -u $USER --hp $HOME | tee /dev/null
sudo env PATH=$PATH:/usr/bin pm2 startup systemd -u $USER --hp $HOME | tee /dev/null

# Check logs
echo "📄 Last 20 lines of PM2 error log:"
pm2 logs ai-trader-bot --lines 20 --err

echo "✅ Deployment complete. Bot is live and running on Hugging Face."