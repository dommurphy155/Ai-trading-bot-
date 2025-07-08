#!/bin/bash

set -e

echo "🚨 Repair started at $(date)"

# 1. Stash local changes safely (in case of conflicts)
git stash push -m "auto-repair stash" || echo "No local changes to stash"

# 2. Pull latest code from main branch
git pull origin main || { echo "Git pull failed"; exit 1; }

# 3. Install dependencies (adjust if using pipenv/poetry)
pip install -r requirements.txt

# 4. Restart pm2 bot process
pm2 restart ai-trader-bot || pm2 start main.py --name ai-trader-bot

echo "✅ Repair complete at $(date)"
