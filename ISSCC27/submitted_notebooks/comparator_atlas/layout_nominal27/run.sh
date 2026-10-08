#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFLIGHT="$(realpath "$HERE/../layout_preflight")"
WORK="$(realpath -m "${NOMINAL27_WORK:-$HERE/.work}")"
OUT="$(realpath -m "${NOMINAL27_OUT:-$HERE/out}")"
if [[ "$(uname -s)" != Linux ]]; then
    echo "Run on a disposable Linux runner, not the shared Windows machine." >&2
    exit 1
fi
if [[ -e "$WORK" || -e "$OUT" ]]; then
    echo "Refusing to overwrite/reuse source, build, layout, or simulation evidence." >&2
    exit 1
fi
mkdir -p "$OUT"
export NOMINAL27_STOP_EPOCH="$(($(date +%s) + 1380))"
stage=initialization
finish() {
    result=$?
    trap - EXIT
    python3 - "$HERE" "$OUT" "$stage" "$result" <<'PY'
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, sys.argv[1])
from contract import sha256, write_json
out = Path(sys.argv[2])
write_json(out / "execution.json", {
    "last_stage": sys.argv[3], "exit_code": int(sys.argv[4]),
    "repository": os.environ.get("GITHUB_REPOSITORY"),
    "commit": os.environ.get("GITHUB_SHA"),
    "run_id": os.environ.get("GITHUB_RUN_ID"),
    "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
    "run_url": "https://github.com/{}/actions/runs/{}".format(
        os.environ.get("GITHUB_REPOSITORY", ""), os.environ.get("GITHUB_RUN_ID", "")),
})
paths = sorted(p for p in out.rglob("*") if p.is_file() and p.name != "manifest.sha256")
(out / "manifest.sha256").write_text("".join(
    f"{sha256(p)}  {p.relative_to(out).as_posix()}\n" for p in paths))
print(f"Final evidence manifest: {len(paths)} files; exit={sys.argv[4]}, stage={sys.argv[3]}")
PY
    exit "$result"
}
trap finish EXIT
trap 'exit 124' TERM
cp "$HERE/protocol.json" "$HERE/devices.json" "$OUT/"
stage=toolchain
bash "$PREFLIGHT/build_toolchain.sh" "$WORK" "$OUT"
export PATH="$WORK/install/bin:$PATH"
export PDK_ROOT="$WORK/src/open_pdks/sky130"
stage=structural
python3 "$HERE/layout.py" "$OUT"
stage=native-parasitic-analysis
python3 "$HERE/analyze.py" "$OUT"
stage=private-models
python3 "$HERE/setup_models.py" "$WORK/models" "$OUT/model-evidence"
stage=private-simulation-environment
python3 -m venv "$WORK/venv"
"$WORK/venv/bin/python" -m pip install --disable-pip-version-check \
    --requirement "$HERE/requirements.txt" > "$OUT/logs/python-install.log" 2>&1
"$WORK/venv/bin/python" -m pip freeze > "$OUT/simulation-python-packages.txt"
dpkg-query -W -f='${binary:Package}\t${Version}\n' ngspice python3 python3-venv \
    > "$OUT/simulation-system-packages.tsv"
stage=matched-simulations
"$WORK/venv/bin/python" "$HERE/simulate.py" "$OUT" "$WORK/models"
stage=complete
