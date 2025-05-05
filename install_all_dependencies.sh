#!/bin/bash

echo "Activating virtual environment..."
source venv/bin/activate || { echo "Failed to activate venv. Exiting."; exit 1; }

echo "Installing required packages from requirements.txt..."
pip install -r requirements.txt || { echo "Failed to install packages from requirements.txt. Exiting."; exit 1; }

echo "Checking for directly-imported but unlisted dependencies..."
# Grep all imported modules in your src/ and tests/ dirs
missing_modules=$(grep -r '^import\|^from' src/ tests/ \
    | awk '{print $2}' \
    | cut -d. -f1 \
    | sort -u \
    | grep -vE 'src|tests|from|import|__future__' \
    | while read module; do
        python -c "import $module" 2>/dev/null || echo "$module"
      done)

if [ -n "$missing_modules" ]; then
    echo "Missing modules detected:"
    echo "$missing_modules"
    echo "Installing them..."
    for pkg in $missing_modules; do
        pip install "$pkg" && echo "$pkg installed successfully."
    done
    echo "Freezing updated requirements.txt..."
    pip freeze > requirements.txt
else
    echo "✅ All necessary modules are installed."
fi