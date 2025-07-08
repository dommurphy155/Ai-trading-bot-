#!/bin/bash
set -e

echo "🚨 Repair started at $(date)"

git stash push -m "auto-repair stash" || echo "No local changes to stash"

git pull origin main || { echo "Git pull failed"; exit 1; }

git add .
git commit -m "Auto-commit before deploy $(date)" || echo "No changes to commit"

echo "🧐 Checking Python syntax errors..."

fix_indentation() {
    local file="$1"
    echo "🔧 Attempting to fix indentation in $file"
    # Convert tabs to 4 spaces
    python3 -c "
with open('$file', 'r') as f:
    content = f.read()
fixed = content.replace('\t', '    ')
with open('$file', 'w') as f:
    f.write(fixed)
"
}

syntax_errors=0
while read -r pyfile; do
    if ! python3 -m py_compile "$pyfile"; then
        syntax_errors=$((syntax_errors + 1))
        echo "❌ Syntax error detected in $pyfile, trying to fix indentation..."
        fix_indentation "$pyfile"
        # Retry compile after fix
        if ! python3 -m py_compile "$pyfile"; then
            echo "⚠️ Still syntax errors in $pyfile after indentation fix."
        else
            echo "✅ Fixed indentation in $pyfile."
            syntax_errors=$((syntax_errors - 1))
        fi
    fi
done < <(find . -type f -name "*.py" ! -path "./.venv/*" ! -path "./venv/*" ! -path "*/__pycache__/*")

echo "🔍 Final syntax check..."
if ! python3 -c "
import os, sys
errors = 0
for root, dirs, files in os.walk('.'):
    if any(skip in root for skip in ['.venv', 'venv', '__pycache__']):
        continue
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            try:
                with open(path, 'r') as f:
                    source = f.read()
                compile(source, path, 'exec')
            except SyntaxError as e:
                errors += 1
                print(f'❌ Syntax error in {path}: {e.msg} at line {e.lineno}')
if errors:
    sys.exit(1)
"; then
    echo "❌ Syntax errors remain after attempted fixes. Deploying anyway."
else
    echo "✅ No syntax errors found."
fi

pip install -r requirements.txt

pm2 restart ai-trader-bot --interpreter python3 || pm2 start main.py --name ai-trader-bot --interpreter python3

echo "✅ Repair complete at $(date)"
