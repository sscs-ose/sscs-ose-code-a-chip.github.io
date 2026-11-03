#!/bin/bash
# GlitchScope -> OpenSTA hand-off check on the MAC: OpenSTA power with its default activity and with GlitchScope's
# SAIF, next to GlitchScope's own Liberty-energy estimate of the same activity.
#   scripts/opensta_saif_check.sh        -> data/bench/opensta_saif_check_mac.log
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
[ -f "$ROOT/tools.env" ] && set -a && . "$ROOT/tools.env" && set +a
export LD_LIBRARY_PATH=$(dirname "$GS_STA")/../../sta_deps/lib:${LD_LIBRARY_PATH:-}
export TCL_LIBRARY=${TCL_LIBRARY:-$(dirname "$GS_STA")/../../sta_deps/lib/tcl8.6}
W=$(mktemp -d)
python3 -m glitchscope.flow --netlist "$ROOT/bench/netlists/mac.v" --vcd "$ROOT/bench/sim/mac.vcd" --lib "$GS_LIB" \
        --no-spice-scale --no-attribution --out "$W/gs" > /dev/null
cp "$ROOT/bench/netlists/mac.v" "$W/gs/glitch_activity.saif" "$W/"
REF=$(python3 - "$W/gs/summary.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); T, n = s["totals"], s["design"]["cycles"]; p = s["design"]["clock_period_ps"]
uw = lambda e: e / n / p * 1e3          # fJ per cycle / ps -> mW -> uW
print(f"combinational dynamic = {uw(T['E_total_fJ']):.1f} uW, of which glitch = {uw(T['E_glitch_fJ']):.1f} uW")
PY
)
sed "s|^puts \"\\\\nGlitchScope reference.*|puts \"\\\\nGlitchScope reference (Liberty energy, same activity): $REF\"|" \
    "$ROOT/scripts/opensta_power.tcl" > "$W/check.tcl"
(cd "$W" && "$GS_STA" -no_init -exit check.tcl) > "$ROOT/data/bench/opensta_saif_check_mac.log" 2>&1
grep -E "=====|Annotated|Combinational|GlitchScope" "$ROOT/data/bench/opensta_saif_check_mac.log"
rm -rf "$W"
