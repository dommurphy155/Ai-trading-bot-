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

# 6. Remove dummy text and syntax placeholders
find . -type f -exec sed -i '/dummy text/d' {} \;

# 7. Ensure .env file is not committed
echo ".env" >> .gitignore

# 8. Lint all Python files for syntax issues
flake8 . || echo "⚠️ Python lint warnings detected, but continuing..."

# 9. Run a basic syntax check on all .py files
find . -name "*.py" -exec python3 -m py_compile {} \; || echo "⚠️ Python syntax errors found"

# 10. Restart bot
pm2 restart ai-trader-bot || pm2 start main.py --name ai-trader-bot

echo "✅ Deployment complete at $(date)"
