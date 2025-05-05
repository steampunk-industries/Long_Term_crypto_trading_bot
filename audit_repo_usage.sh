#!/bin/bash

echo "🔍 Running dead code and file audit..."

# 1. Check for 'simple_' legacy scripts
echo -e "\n🧹 Checking for legacy scripts (simple_*)..."
find . -type f -name "simple_*.py"

# 2. Check for test stubs with low content
echo -e "\n🧪 Scanning for test stubs with <5 lines..."
find tests -type f -name "*.py" -exec awk 'NF {count++} END {if (count < 5) print FILENAME}' {} \;

# 3. Check for orphan .py files not imported anywhere
echo -e "\n🕸️ Searching for .py files not referenced in other code..."
ALL_PY=$(find src -type f -name "*.py")
for f in $ALL_PY; do
    name=$(basename "$f" .py)
    refs=$(grep -r "$name" src --exclude-dir=__pycache__ | grep -v "$f")
    if [ -z "$refs" ]; then
        echo "Possibly unused: $f"
    fi
done

echo -e "\n✅ Audit complete. Manually review the output before deleting."
