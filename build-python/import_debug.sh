#!/bin/bash

SITE=$(python3 -c "import site; print(site.getsitepackages()[0])")
SO_FILE=$(find "$SITE/fourdst" -name "_phys.cpython-*-darwin.so")

echo "=== File Locations ==="
echo "Extension module: $SO_FILE"
echo "Libs directory: $SITE/.fourdst.mesonpy.libs/"
echo ""

echo "=== RPATH Entries ==="
otool -l "$SO_FILE" | grep -A 3 LC_RPATH
echo ""

echo "=== Library Dependencies ==="
otool -L "$SO_FILE"
echo ""

echo "=== Checking if dependencies exist ==="
for lib in $(otool -L "$SO_FILE" | grep -v ":" | awk '{print $1}' | grep -v "^/usr" | grep -v "^/System"); do
    echo "Checking: $lib"
    if [[ "$lib" == @* ]]; then
        resolved=$(echo "$lib" | sed "s|@loader_path|$SITE/fourdst|g")
        if [ -f "$resolved" ]; then
            echo "  Found: $resolved"
        else
            echo "  NOT FOUND: $resolved"
        fi
    fi
done
echo ""

echo "=== Attempting import with verbose error ==="
python3 -c "
import sys
sys.path.insert(0, '$SITE')
try:
    import fourdst._phys
    print('Import successful!')
except ImportError as e:
    print(f'Import failed: {e}')
    import traceback
    traceback.print_exc()
"
echo ""

echo "=== Contents of .fourdst.mesonpy.libs ==="
ls -lh "$SITE/.fourdst.mesonpy.libs/" 2>/dev/null || echo "Directory not found!"