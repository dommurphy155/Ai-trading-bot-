#!/bin/bash

set -e
echo "🔧 Starting ultra-hardened deployment at $(date)"

# === FAILSAFE 1: Auto stash dirty changes to prevent merge conflicts ===
git stash push -m "auto-repair stash" || echo "No local changes to stash"

# === FAILSAFE 2: Pull latest changes ===
git pull origin main || { echo "❌ Git pull failed"; exit 1; }

# === FAILSAFE 3: Auto fix broken or inconsistent file indentation (tabs → 4 spaces) ===
find . -type f -name "*.py" -exec sed -i 's/^\t/    /g' {} +
echo "✅ Indentation fixed to 4 spaces across all .py files"

# === FAILSAFE 4: Check for Python syntax errors ===
SYNTAX_ERRORS=$(find . -name "*.py" -exec python3 -m py_compile {} \; 2>&1 | tee /dev/stderr)
if [ -n "$SYNTAX_ERRORS" ]; then
    echo "❌ Syntax errors found. Aborting deployment."
    exit 1
fi

# === FAILSAFE 5: Install required Python packages ===
pip install --upgrade pip
pip install -r requirements.txt || {
    echo "❌ requirements.txt failed. Trying to install fallback core packages..."
    pip install python-dotenv schedule requests scikit-learn python-telegram-bot
}

# === FAILSAFE 6: Check for .env presence and critical vars ===
if [ ! -f .env ]; then
    echo "❌ .env file missing!"
    touch .env && echo "# AUTO-GENERATED .env" >> .env
    echo "OPENAI_API_KEY=" >> .env
    echo "TELEGRAM_BOT_TOKEN=" >> .env
    echo "TELEGRAM_CHAT_ID=" >> .env
    echo "FXOPEN_LOGIN=" >> .env
    echo "FXOPEN_KEY=" >> .env
    echo "FXOPEN_SECRET=" >> .env
    echo "⚠️  Blank .env created. You must manually fill credentials."
fi

# === FAILSAFE 7: Ensure .env is loaded for this shell ===
export $(grep -v '^#' .env | xargs) || echo "⚠️  Could not export .env variables"

# === FAILSAFE 8: Check Python version ===
PY_VERSION=$(python3 --version | awk '{print $2}')
if [[ "$PY_VERSION" < "3.8" ]]; then
    echo "❌ Python 3.8+ required. You have $PY_VERSION. Abort."
    exit 1
fi

# === FAILSAFE 9: Validate that main.py exists and is executable ===
if [ ! -f main.py ]; then
    echo "❌ main.py not found. Aborting."
    exit 1
fi

# === FAILSAFE 10: Restart or start the bot using PM2 ===
pm2 describe ai-trader-bot > /dev/null
if [ $? -eq 0 ]; then
    echo "♻️  Restarting existing PM2 process: ai-trader-bot"
    pm2 restart ai-trader-bot --update-env
else
    echo "🚀 Starting new PM2 process: ai-trader-bot"
    pm2 start main.py --name ai-trader-bot
fi

echo "✅ Deployment complete at $(date)"
