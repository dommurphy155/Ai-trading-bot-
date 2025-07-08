#!/bin/bash

set -e

echo "🚀 Starting full bot deployment at $(date)"

# 1. Auto stash any local changes
git stash push -m "auto-deploy stash" || echo "No local changes to stash"

# 2. Pull latest from GitHub main branch
git pull origin main || { echo "❌ Git pull failed"; exit 1; }

# 3. Fix indentation across all files (force 4 spaces)
find . -type f -not -path '*/\.*' -exec sed -i 's/^\t/    /g' {} + && echo "✅ Indentation standardized"

# 4. Install updated Python dependencies
pip install -r requirements.txt || { echo "❌ Dependency install failed"; exit 1; }

# 5. Restart bot process using PM2
pm2 restart ai-trader-bot || pm2 start main.py --name ai-trader-bot

echo "✅ Bot deployed and restarted successfully at $(date)"
