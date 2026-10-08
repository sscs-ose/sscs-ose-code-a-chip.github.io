#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$(realpath -m "${LAYOUT_WORK:-$HERE/.work}")"
OUT="$(realpath -m "${LAYOUT_OUT:-$HERE/out}")"
if [[ "$(uname -s)" != Linux ]]; then
    echo "This toolchain runs on Linux, not the shared Windows host." >&2
    exit 1
fi
if [[ -e "$WORK" || -e "$OUT" ]]; then
    echo "Use fresh LAYOUT_WORK and LAYOUT_OUT paths; existing evidence is not overwritten." >&2
    exit 1
fi
mkdir -p "$OUT"
bash "$HERE/build_toolchain.sh" "$WORK" "$OUT"
export PATH="$WORK/install/bin:$PATH"
export PDK_ROOT="$WORK/src/open_pdks/sky130"
python3 "$HERE/preflight.py" "$OUT"
