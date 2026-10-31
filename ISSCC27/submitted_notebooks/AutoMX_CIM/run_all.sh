#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
mkdir -p tmp
export AUTOMX_BUNDLE_DIR="$PWD"
export PYTHONPATH="$PWD/tools/python_guard:$PWD"
export TMPDIR="$PWD/tmp"
automx_python="${AUTOMX_PYTHON:-/home/nam/anaconda3/envs/env_mamba/bin/python}"
if [[ ! -x "$automx_python" ]]; then automx_python="$(command -v python)"; fi
export PATH="$(dirname -- "$automx_python"):$PATH"
exec "$automx_python" -u execute_standalone.py
