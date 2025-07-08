#!/bin/bash

set -e

echo "🚀 Deploy script started at $(date)"

# 1. Auto-commit any local changes
git add . && \
git commit -m "🛠️ Auto-save local changes before deploy" || echo "✅ No local changes to commit"

# 2. Pull latest from remote with rebase
git pull origin main --rebase || { echo "❌ Git pull failed"; exit 1; }

# 3. Install dependencies
pip install -r requirements.txt || { echo "❌ Dependency install failed"; exit 1; }

# 4. Auto-fix Python file indentation to 4 spaces (entire repo)
find . -name "*.py" -exec autopep8 --in-place --aggressive --aggressive --indent-size=4 {} \;

# 5. Fix all shell scripts to Unix format
find . -name "*.sh" -exec dos2unix {} \; 2>/dev/null || true

# 6. Remove dummy text and syntax placeholders from all files
find . -type f -exec sed -i '/dummy text/d' {} \;

# 7. Ensure .env file is not committed (add to gitignore if missing)
grep -qxF '.env' .gitignore || echo '.env' >> .gitignore

# 8. Lint all Python files (errors don’t stop deploy)
flake8 . || echo "⚠️ Python lint warnings detected, continuing..."

# 9. Syntax check all Python files (errors don’t stop deploy)
find . -name "*.py" -exec python3 -m py_compile {} \; || echo "⚠️ Python syntax errors detected, continuing..."

# 10. Restart or start pm2 bot
pm2 restart ai-trader-bot || pm2 start main.py --name ai-trader-bot

# 11. Push local commits to remote repo
git push origin main || echo "❌ Git push failed; check authentication and network"

echo "✅ Deployment complete at $(date)"
