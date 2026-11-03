#!/usr/bin/env bash
set -euo pipefail
CODE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export PDK_ROOT="${TIA_PDK_ROOT:?Install the PDK separately and set TIA_PDK_ROOT}"
export PDK=ihp-sg13g2
if [[ -n "${TIA_NGSPICE_BIN:-}" ]]; then
    exec "$TIA_NGSPICE_BIN" -b "$@"
elif [[ -x "$CODE_DIR/../tools/opt/bin/ngspice" ]]; then
    exec "$CODE_DIR/../tools/opt/bin/ngspice" -b "$@"
else
    exec ngspice -b "$@"
fi
