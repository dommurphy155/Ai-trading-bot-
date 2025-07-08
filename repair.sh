#!/bin/bash

set -e

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
pip install --quiet autopep8
find . -name "*.py" -exec autopep8 --in-place --aggressive --aggressive --indent-size=4 {} +

# 4. Fix all shell scripts to Unix format (remove CRLF)
find . -name "*.sh" -exec dos2unix {} \; 2>/dev/null || true

# 5. Remove dummy text or placeholder lines from all files
find . -type f -exec sed -i '/dummy text/d' {} \;

# 6. Ensure .env file is in .gitignore
grep -qxF '.env' .gitignore || echo '.env' >> .gitignore

# 7. Install/update Python dependencies
pip install -r requirements.txt || { echo "❌ Dependency install failed"; exit 1; }

# 8. Lint all Python files (warnings don’t stop deploy)
flake8 . || echo "⚠️ Python lint warnings detected, continuing..."

# 9. Syntax check all Python files (errors don’t stop deploy)
find . -name "*.py" -exec python3 -m py_compile {} \; || echo "⚠️ Python syntax errors detected, continuing..."

# 10. Run repair script before pm2 restart
if [ -f ./repair.sh ]; then
    echo "🔄 Running repair.sh before pm2 restart..."
    bash ./repair.sh || echo "❌ repair.sh failed, continuing with pm2 restart"
fi

# 11. Restart or start pm2 bot with python3 interpreter explicitly
pm2 restart ai-trader-bot --interpreter python3 || pm2 start main.py --name ai-trader-bot --interpreter python3

# 12. Push local commits to remote repo (if any)
git push origin main || echo "❌ Git push failed; check authentication and network"

echo "✅ Deploy & Repair complete at $(date)"
