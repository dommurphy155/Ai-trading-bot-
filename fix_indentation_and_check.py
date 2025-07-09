#!/usr/bin/env python3
import os
import subprocess

# File extensions to fix
VALID_EXTENSIONS = ('.py', '.sh', '.txt', '.json', '.md', '.env')

# Directories to ignore
EXCLUDED_DIRS = {'.git', '__pycache__', 'venv', '.venv'}

def is_text_file(filename):
    return filename.endswith(VALID_EXTENSIONS)

def replace_tabs_in_file(filepath):
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
        with open(filepath, 'w') as f:
            for line in lines:
                f.write(line.replace('\t', '    '))
        print(f"✅ Fixed tabs: {filepath}")
    except Exception as e:
        print(f"❌ Failed to process {filepath}: {e}")

def find_all_files(root='.'):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        for file in filenames:
            full_path = os.path.join(dirpath, file)
            if is_text_file(full_path):
                yield full_path

def check_python_indentation(filepath):
    if not filepath.endswith('.py'):
        return
    result = subprocess.run(['python3', '-m', 'py_compile', filepath], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✅ Syntax OK: {filepath}")
    else:
        print(f"❌ Syntax ERROR in {filepath}:\n{result.stderr.strip()}")

def main():
    for file in find_all_files():
        replace_tabs_in_file(file)
        check_python_indentation(file)

if __name__ == "__main__":
    main()
