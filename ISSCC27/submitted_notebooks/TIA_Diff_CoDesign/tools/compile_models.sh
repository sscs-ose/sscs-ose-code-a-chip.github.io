#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$ROOT/tools/opt/bin:$PATH"
if command -v openvaf-r >/dev/null; then
    COMPILER=openvaf-r
elif command -v openvaf >/dev/null; then
    COMPILER=openvaf
else
    echo 'Install OpenVAF before compiling the external PDK model sources.' >&2; exit 2
fi
cd "${TIA_PDK_ROOT:?Install the PDK separately and set TIA_PDK_ROOT}/ihp-sg13g2/libs.tech/verilog-a"
mkdir -p ../ngspice/osdi
for model in psp103/psp103 psp103/psp103_nqs r3_cmc/r3_cmc mosvar/mosvar cap_cmomi/cap_cmomi cap_cmomf/cap_cmomf; do
    "$COMPILER" -D__NGSPICE__ -o "../ngspice/osdi/${model##*/}.osdi" "$model.va"
    test -s "../ngspice/osdi/${model##*/}.osdi"
done
