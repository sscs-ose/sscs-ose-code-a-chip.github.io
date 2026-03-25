#!/usr/bin/env bash
# NeuroSAR — package submission artefacts
# Usage: bash scripts/package_submission.sh

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "============================================="
echo "  NeuroSAR Submission Packaging"
echo "============================================="

# Run tests
echo "[1/4] Running tests ..."
python -m pytest tests/ -v --tb=short || echo "WARNING: Some tests failed"

# Verify notebooks compile (syntax check)
echo "[2/4] Checking notebook syntax ..."
for nb in notebooks/*.ipynb; do
    python -c "import json; json.load(open('$nb'))" && echo "  OK: $nb" || echo "  FAIL: $nb"
done

# Compile all source files
echo "[3/4] Compiling source ..."
for py in src/*.py; do
    python -m py_compile "$py" && echo "  OK: $py" || echo "  FAIL: $py"
done

# Package
echo "[4/4] Collecting artefacts ..."
python -c "
import sys; sys.path.insert(0, '.')
from src.export_results import package_submission
package_submission()
"

echo ""
echo "============================================="
echo "  Packaging complete!"
echo "  Output: submission_package/"
echo "============================================="
echo ""
echo "Checklist:"
echo "  - [ ] Review submission_package/"
echo "  - [ ] Record video (see docs/video_script.md)"
echo "  - [ ] Upload to submission portal"
