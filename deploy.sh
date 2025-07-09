#!/bin/bash

# FXOpen AI Trading Bot - Full Auto Deployment Script
# Usage: bash deploy.sh

set -euo pipefail

echo "🛠️  Starting deployment..."

# Check Python version (>=3.8)
if ! python3 -c "import sys; exit(sys.version_info >= (3,8) or 1)"; then
  echo "❌ Python 3.8+ is required. Please install it."
  exit 1
fi

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

# Recreate clean virtual environment
echo "🐍 Setting up virtual environment..."
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# Ensure autopep8 is installed for formatting
if ! command -v autopep8 &> /dev/null; then
  echo "📦 Installing autopep8..."
  pip install autopep8
fi

# Install all dependencies
echo "📦 Installing Python requirements..."
pip install -r requirements.txt

# Install Playwright browsers
echo "🌐 Installing Playwright Chromium browser..."
playwright install chromium

# Auto-format Python files for clean code
echo "🧹 Auto-formatting Python files..."
find . -name "*.py" -not -path "./venv/*" -print0 | xargs -0 -n1 ./venv/bin/autopep8 --in-place --aggressive --aggressive

# Export environment variables to .env file for persistent use
echo "🔐 Creating .env file with secrets..."
cat > .env <<EOF
OPENAI_API_KEY="sk-proj-0c1KcQnF-IFdfx8_..."
TELEGRAM_BOT_TOKEN="7970729024:AAFIFzpY8-m2OLY07chzcYWJevgXXcTbZUs"
TELEGRAM_CHAT_ID="7108900627"
FXOPEN_LOGIN="5012716"
FXOPEN_API_KEY="fEYWr5E9BmgrC76k"
FXOPEN_API_SECRET="ab6WXCsQfYn88YPn4Gq2gXDwPqzd9fWn7tcydNnwNfa9wBdsfxGfyT3mFHfFcnR9"
EOF

# Load .env variables for this session
set -a
source .env
set +a

# PM2 process management
echo "🚀 Starting bot with PM2..."
pm2 delete ai-trader-bot || true
pm2 start main.py --name ai-trader-bot --interpreter ./venv/bin/python
pm2 save

# Enable PM2 startup on system reboot
echo "⚙️ Configuring PM2 to start on system boot..."
pm2 startup systemd -u $(whoami) --hp $HOME
sudo env PATH=$PATH:/usr/bin pm2 startup systemd -u $(whoami) --hp $HOME

# Show last 50 lines of PM2 logs
echo "📄 Bot deployed. Last 50 lines of logs:"
pm2 logs ai-trader-bot --lines 50

echo "✅ Deployment complete. Bot is running."