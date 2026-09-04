#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install nbmake pytest jupyter
echo "[setup_env] done. PDK_ROOT=${PDK_ROOT:-<unset — will use analytical oracle>}"
