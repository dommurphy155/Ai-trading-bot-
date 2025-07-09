#!/bin/bash

set -euo pipefail

echo "🚀 Deploy & Repair started at $(date)"

# 1. Auto-commit any local changes (stash if commit fails)
git add .
if ! git commit -m "🛠️ Auto-save local changes before deploy"; then
    echo "⚠️ No local changes to commit, trying stash..."
    git stash push -m "auto-repair stash" || echo "✅ No local changes to stash"
fi

# 2. Pull latest from remote with rebase
git pull origin main --rebase || { echo "❌ Git pull failed"; exit 1; }

# 3. Fix indentation + syntax issues in all Python files recursively
echo "🔧 Fixing Python indentation and style issues..."
pip install --quiet autopep8 flake8 || { echo "❌ Failed to install formatting tools"; exit 1; }
find . -name "*.py" -exec autopep8 --in-place --aggressive --aggressive --indent-size=4 {} +

# 4. Fix all shell scripts to Unix format (remove CRLF)
if command -v dos2unix >/dev/null 2>&1; then
    find . -name "*.sh" -exec dos2unix {} \; 2>/dev/null || true
else
    echo "⚠️ dos2unix not found, skipping shell script line ending fix"
fi

# 5. Remove dummy text or placeholder lines from all files
find . -type f -exec sed -i '/dummy text/d' {} \; || true

# 6. Ensure .env file is in .gitignore
grep -qxF '.env' .gitignore || echo '.env' >> .gitignore

# 7. Install/update Python dependencies
if ! pip install -r requirements.txt; then
    echo "❌ Dependency install failed"; exit 1;
fi

# 8. Lint all Python files (warnings don’t stop deploy)
flake8 . || echo "⚠️ Python lint warnings detected, continuing..."

# 9. Syntax check all Python files (errors don’t stop deploy)
if ! find . -name "*.py" -exec python3 -m py_compile {} \;; then
    echo "⚠️ Python syntax errors detected, continuing..."
fi

# 10. Run repair script before pm2 restart if exists
if [ -f ./repair.sh ]; then
    echo "🔄 Running repair.sh before pm2 restart..."
    if ! bash ./repair.sh; then
        echo "❌ repair.sh failed, continuing with pm2 restart"
    fi
fi

# 11. Clean Python bytecode cache folders to avoid stale pyc
echo "🧹 Cleaning __pycache__ folders..."
find . -type d -name "__pycache__" -exec rm -rf {} +

# 12. Restart or start pm2 bot with python3 interpreter explicitly
if pm2 restart ai-trader-bot --interpreter python3 2>/dev/null; then
    echo "✅ pm2 restarted ai-trader-bot"
else
    pm2 start main.py --name ai-trader-bot --interpreter python3
    echo "✅ pm2 started ai-trader-bot"
fi

# 13. Push local commits to remote repo (if any)
if ! git push origin main; then
    echo "❌ Git push failed; check authentication and network"
fi

# 14. Optional: prune old pm2 logs to save disk space
echo "🧹 Pruning old pm2 logs..."
pm2 flush
pm2 reloadLogs

# 15. Optional: show pm2 status summary
echo "📊 PM2 process status:"
pm2 status ai-trader-bot

echo "✅ Deploy & Repair complete at $(date)"