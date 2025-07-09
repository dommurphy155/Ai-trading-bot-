#!/bin/bash

# FXOpen AI Trading Bot - Full Auto Deployment Script
# Usage: bash deploy.sh

set -euo pipefail

echo "🛠️  Starting deployment..."

# Git identity (set once per VPS)
git config --global user.name "Dom Murphy"
git config --global user.email "dommurphy155@gmail.com"

REPO_NAME="Ai-trading-bot-"
if [ -d "$REPO_NAME" ]; then
  echo "📁 Repo exists. Pulling latest changes..."
  cd "$REPO_NAME"
  git pull origin main
else
  echo "📥 Cloning fresh copy of bot repo..."
  git clone git@github.com:dommurphy155/Ai-trading-bot-.git
  cd "$REPO_NAME"
fi

echo "📂 Current directory: $(pwd)"

# Install Node.js and npm if not present (needed for pm2 and playwright)
if ! command -v node &> /dev/null; then
  echo "⬇️ Installing Node.js..."
  curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi

# Install PM2 globally if missing
if ! command -v pm2 &> /dev/null; then
  echo "⬇️ Installing PM2 globally..."
  sudo npm install -g pm2
fi

# Recreate clean virtual environment
echo "🐍 Setting up Python virtual environment..."
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel

# Ensure autopep8 is installed for formatting
if ! command -v autopep8 &> /dev/null; then
  echo "📦 Installing autopep8..."
  pip install autopep8
fi

# Install all Python dependencies
echo "📦 Installing Python requirements..."
pip install -r requirements.txt

# Install Playwright browsers
echo "🌐 Installing Playwright Chromium browser..."
playwright install chromium

# Auto-format Python files for clean code
echo "🧹 Auto-formatting Python files..."
find . -name "*.py" -not -path "./venv/*" -print0 | xargs -0 -n1 ./venv/bin/autopep8 --in-place --aggressive --aggressive

# Export environment variables directly (no .env file)
echo "🔐 Exporting environment variables..."
export HF_TOKEN="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"
export TELEGRAM_BOT_TOKEN="7970729024:AAFIFzpY8-m2OLY07chzcYWJevgXXcTbZUs"
export TELEGRAM_CHAT_ID="7108900627"
export FXOPEN_LOGIN="5012716"
export FXOPEN_API_KEY="fEYWr5E9BmgrC76k"
export FXOPEN_API_SECRET="ab6WXCsQfYn88YPn4Gq2gXDwPqzd9fWn7tcydNnwNfa9wBdsfxGfyT3mFHfFcnR9"
export FXOPEN_PASSWORD="PZXPJBFm"
export FXOPEN_SERVER="ttdemomarginal.fxopen.net"

# Start bot with PM2
echo "🚀 Starting bot with PM2..."
pm2 delete ai-trader-bot || true
pm2 start main.py --name ai-trader-bot --interpreter ./venv/bin/python
pm2 save

# Enable PM2 startup on system reboot
echo "⚙️ Configuring PM2 to start on system boot..."
sudo env PATH=$PATH:/usr/bin pm2 startup systemd -u $(whoami) --hp $HOME | tee /dev/null

# Show last 20 lines of PM2 error logs only
echo "📄 Bot deployed. Last 20 lines of error logs:"
pm2 logs ai-trader-bot --lines 20 --err

echo "✅ Deployment complete. Bot is running."