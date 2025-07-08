#!/bin/bash
set -e

echo "🚨 Repair started at $(date)"

# 1. Stash local changes safely (in case of conflicts)
git stash push -m "auto-repair stash" || echo "No local changes to stash"

# 2. Pull latest code from main branch
git pull origin main || { echo "Git pull failed"; exit 1; }

# 3. Auto-commit any remaining local changes (if any)
git add .
git commit -m "Auto-commit before deploy $(date)" || echo "No changes to commit"

# 4. Fix indentation + style issues in all Python files recursively
echo "🔧 Fixing Python indentation and style issues..."
pip install --quiet autopep8
find . -name "*.py" -exec autopep8 --in-place --aggressive --aggressive {} +

# 5. Install Python dependencies
pip install -r requirements.txt

# 6. Restart pm2 bot process explicitly with python3 interpreter
pm2 restart ai-trader-bot --interpreter python3 || pm2 start main.py --name ai-trader-bot --interpreter python3

echo "✅ Repair complete at $(date)"
