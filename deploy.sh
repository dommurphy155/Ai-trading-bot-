#!/bin/bash

# FXOpen AI Trading Bot - Production Auto Deployment Script
# Usage: bash deploy.sh

set -euo pipefail

# ==== CONFIGURE YOUR ENVIRONMENT VARIABLES HERE OR LOAD FROM EXTERNAL SECURE LOCATION ====
# Recommended: export these in your ~/.bashrc or VPS secrets manager
# Example:
# export HF_TOKEN="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"
# export TELEGRAM_BOT_TOKEN="your_telegram_token"
# export TELEGRAM_CHAT_ID="your_chat_id"
# export FXOPEN_LOGIN="your_fxopen_login"
# export FXOPEN_API_KEY="your_fxopen_api_key"
# export FXOPEN_API_SECRET="your_fxopen_api_secret"

# ---- Required Environment Variables (must be set externally) ----
REQUIRED_VARS=(
  "HF_TOKEN"
  "TELEGRAM_BOT_TOKEN"
  "TELEGRAM_CHAT_ID"
  "FXOPEN_LOGIN"
  "FXOPEN_API_KEY"
  "FXOPEN_API_SECRET"
)

echo "🛠️  Starting deployment..."

# --- Utility functions ---
function check_env_vars() {
  local missing=()
  for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
      missing+=("$var")
    fi
  done
  if [ ${#missing[@]} -ne 0 ]; then
    echo "❌ Missing required environment variables: ${missing[*]}"
    echo "Please export them before running this script."
    exit 1
  fi
}

function check_command() {
  command -v "$1" >/dev/null 2>&1
}

function install_node() {
  echo "📦 Installing Node.js v18.x ..."
  curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
  sudo apt-get install -y nodejs
}

function install_python() {
  echo "📦 Installing Python 3.8+ and essentials ..."
  sudo apt-get update
  sudo apt-get install -y python3 python3-venv python3-pip build-essential libssl-dev libffi-dev
}

function version_compare() {
  # Returns 0 if $1 >= $2 else 1
  [ "$(printf '%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]
}

function check_python_version() {
  PYTHON_VER=$(python3 --version 2>&1 | awk '{print $2}')
  if ! version_compare "$PYTHON_VER" "3.8"; then
    echo "❌ Python 3.8 or higher required. Current: $PYTHON_VER"
    install_python
  else
    echo "✅ Python version $PYTHON_VER OK"
  fi
}

function check_node_version() {
  NODE_VER=$(node --version 2>&1 | sed 's/v//')
  if ! version_compare "$NODE_VER" "18.0.0"; then
    echo "❌ Node.js v18 or higher required. Current: $NODE_VER"
    install_node
  else
    echo "✅ Node.js version $NODE_VER OK"
  fi
}

function install_pm2() {
  if ! check_command pm2; then
    echo "📦 Installing PM2 globally ..."
    sudo npm install -g pm2
  else
    echo "✅ PM2 already installed."
  fi
}

function playwright_install() {
  echo "🌐 Installing Playwright and Chromium dependencies ..."
  # Install system dependencies for Playwright (Debian/Ubuntu)
  sudo apt-get install -y libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxss1 libxcomposite1 libxdamage1 libgbm1 libasound2 libpangocairo-1.0-0 libgtk-3-0 libxrandr2 libpango1.0-0 libcurl4
  ./venv/bin/python -m pip install --upgrade playwright
  npx playwright install --with-deps chromium
}

function setup_virtualenv() {
  echo "🐍 Setting up clean Python virtual environment..."
  rm -rf venv
  python3 -m venv venv
  source venv/bin/activate
  pip install --upgrade pip setuptools wheel
}

function install_python_dependencies() {
  echo "📦 Installing Python requirements..."
  pip install -r requirements.txt
}

function auto_format_code() {
  echo "🧹 Auto-formatting Python files with autopep8..."
  if ! check_command autopep8; then
    pip install autopep8
  fi
  find . -name "*.py" -not -path "./venv/*" -print0 | xargs -0 -n1 ./venv/bin/autopep8 --in-place --aggressive --aggressive
}

function clear_pm2_logs() {
  echo "🧹 Cleaning PM2 logs to save disk space..."
  pm2 flush
  pm2 delete ai-trader-bot || true
}

function pm2_start_bot() {
  echo "🚀 Starting bot with PM2..."
  pm2 start main.py --name ai-trader-bot --interpreter ./venv/bin/python --watch --max-restarts=10 --restart-delay=5000
  pm2 save
}

function pm2_setup_startup() {
  echo "⚙️ Configuring PM2 to start on system boot..."
  pm2 startup systemd -u "$(whoami)" --hp "$HOME" | tee /dev/null
  sudo env PATH=$PATH:/usr/bin pm2 startup systemd -u "$(whoami)" --hp "$HOME" | tee /dev/null
}

function hug_face_health_check() {
  echo "🔎 Checking Hugging Face API token validity..."
  RETRIES=3
  DELAY=3
  for i in $(seq 1 $RETRIES); do
    RESPONSE=$(curl -sS -H "Authorization: Bearer $HF_TOKEN" https://api-inference.huggingface.co/models/gpt2)
    if echo "$RESPONSE" | grep -q "error"; then
      echo "❌ Hugging Face API token invalid or request failed. Retrying ($i/$RETRIES)..."
      sleep $DELAY
      DELAY=$((DELAY * 2))
    else
      echo "✅ Hugging Face API token valid."
      return 0
    fi
  done
  echo "❌ Hugging Face API token check failed after $RETRIES retries. Exiting."
  exit 1
}

function validate_all() {
  check_env_vars
  check_python_version
  check_node_version
  install_pm2
  setup_virtualenv
  install_python_dependencies
  playwright_install
  auto_format_code
  hug_face_health_check
}

# --- Main Execution ---

validate_all

clear_pm2_logs

pm2_start_bot

pm2_setup_startup

echo "✅ Deployment complete. Bot is running under PM2 with auto-restart and log management."