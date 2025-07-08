#!/bin/bash

# FXOpen AI Trading Bot - Full Auto Deployment Script
# Usage: bash deploy.sh

set -e

echo "🛠️  Starting deployment..."

# Git identity (set once per VPS)
git config --global user.name "Dom Murphy"
git config --global user.email "dommurphy155@gmail.com"

# SSH key already added to GitHub — clone or pull
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

# Recreate clean venv if broken
echo "🐍 Setting up virtual environment..."
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# Install all dependencies
echo "📦 Installing Python requirements..."
pip install -r requirements.txt

# Auto-fix Python formatting issues (indentation, style)
echo "🧹 Auto-formatting all Python files..."
find . -name "*.py" -not -path "./venv/*" -print0 | xargs -0 -n1 ./venv/bin/autopep8 --in-place --aggressive --aggressive

# Export all required credentials
export OPENAI_API_KEY="sk-proj-0c1KcQnF-IFdfx8_..."
export TELEGRAM_BOT_TOKEN="7970729024:AAFIFzpY8-m2OLY07chzcYWJevgXXcTbZUs"
export TELEGRAM_CHAT_ID="7108900627"
export FXOPEN_LOGIN="5012716"
export FXOPEN_KEY="fEYWr5E9BmgrC76k"
export FXOPEN_SECRET="ab6WXCsQfYn88YPn4Gq2gXDwPqzd9fWn7tcydNnwNfa9wBdsfxGfyT3mFHfFcnR9"

# Kill and restart bot with PM2
echo "🚀 Starting bot with PM2..."
pm2 delete ai-trader-bot || true
pm2 start main.py --name ai-trader-bot --interpreter ./venv/bin/python
pm2 save

# Tail logs for 50 lines
echo "📄 Bot deployed. Last 50 error logs:"
pm2 logs ai-trader-bot --lines 50
