#!/usr/bin/env bash
# Verify CACL library packaging
# Usage: docker compose exec web bash scripts/verify_packaging.sh

set -e

echo "=== CACL Packaging Verification ==="

# Clean previous builds
echo "[1/6] Cleaning previous builds..."
rm -rf /app/cacl/dist /app/cacl/build /app/cacl/*.egg-info

# Build sdist + wheel
echo "[2/6] Building sdist and wheel..."
cd /app/cacl
python -m build --quiet

# Verify artifacts exist
echo "[3/6] Verifying build artifacts..."
ls -la dist/
test -f dist/cacl-*.whl || { echo "ERROR: wheel not found"; exit 1; }
test -f dist/cacl-*.tar.gz || { echo "ERROR: sdist not found"; exit 1; }

# Create clean venv and install
echo "[4/6] Installing in clean venv..."
rm -rf /tmp/verify_venv
python -m venv /tmp/verify_venv
/tmp/verify_venv/bin/pip install --quiet dist/cacl-*.whl

# Verify import works (from non-source directory)
echo "[5/6] Verifying import..."
cd /tmp
IMPORT_PATH=$(/tmp/verify_venv/bin/python -c "import cacl; print(cacl.__file__)")
echo "Imported from: $IMPORT_PATH"
if [[ "$IMPORT_PATH" != *"verify_venv"* ]]; then
    echo "ERROR: Import not from venv site-packages"
    exit 1
fi

# Run tests (uses main environment with DB drivers)
echo "[6/6] Running library tests..."
cd /app
python -m pytest tests/ -v --tb=short

echo ""
echo "=== All packaging checks passed ==="
