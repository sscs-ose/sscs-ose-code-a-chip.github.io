#!/usr/bin/env bash
# Fresh-clone, fresh-venv, tier-1 run: exactly what a judge (or Vrinda) does, in one command.
#   tools/cleanroom.sh <git-url-or-path> [branch] [subdir]
set -euo pipefail
REPO=${1:?usage: cleanroom.sh <git-url-or-path> [branch] [subdir]}
BRANCH=${2:-main}
SUB=${3:-ISSCC27/submitted_notebooks/subthreshold_vga_gmid}
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
git clone -q --depth 1 --branch "$BRANCH" "$REPO" "$T/repo"
python3 -m venv "$T/venv"; . "$T/venv/bin/activate"
pip install -q numpy scipy pandas matplotlib nbformat nbclient ipykernel
echo "python $(python --version 2>&1 | cut -d' ' -f2) | $(pip list 2>/dev/null | grep -iE '^(numpy|scipy|pandas|matplotlib) ' | tr -s ' ' | tr '\n' ';')"
cd "$T/repo/$SUB"
start=$(date +%s)
python tools/run_nb.py --mode tier1 --no-save
echo "CLEAN-ROOM tier-1 finished in $(( $(date +%s) - start )) s"
python tools/check_notebook.py --final || true
