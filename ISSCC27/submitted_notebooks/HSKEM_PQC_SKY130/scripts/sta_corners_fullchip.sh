#!/usr/bin/env bash
# Three-corner STA of the routed full HSKEM core (OpenROAD's STA on the routed database with the
# extracted SPEF; flow/sta_corner.tcl explains why the database rather than 6_final.v is read).
# The layout database is not published (see README), so this script needs the private
# run directory; only the summary it writes, results/fullchip/sta_corners.json, is published.
# The OpenRAM macros are characterized at the typical corner only, so their TT views are
# used at every corner; the standard cells use their ss / tt / ff libraries.
# usage: FULLCHIP_DIR=<ORFS results dir with 6_final.{odb,sdc,spef}> MACRO_LIB_DIR=<dir of the
#        eight *.physical.lib views> scripts/sta_corners_fullchip.sh
# SPDX-License-Identifier: Apache-2.0
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ORFS="${ORFS_ROOT:-/opt/eda/orfs-6101364b}"; OPENROAD="$ORFS/tools/install/OpenROAD/bin/openroad"
PDK="${SKY130_LIBS:-$(ls -d /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A/libs.ref/sky130_fd_sc_hd/lib | head -1)}"
B="${FULLCHIP_DIR:?FULLCHIP_DIR}"; M="${MACRO_LIB_DIR:?MACRO_LIB_DIR}"
LOGS="${FULLCHIP_STA_LOGS:-$HOME/fullchip_sta}"; mkdir -p "$LOGS"     # detailed logs stay private
MACROS=$(ls "$M"/*.physical.lib | tr '\n' ' ')
[ "$(echo $MACROS | wc -w)" -eq 8 ] || { echo "expected eight macro views in $M"; exit 1; }
CLK_NS=$(grep -m1 -oE "create_clock.*-period [0-9.]+" "$B/6_final.sdc" | grep -oE "[0-9.]+$")
for corner in ss_100C_1v60 tt_025C_1v80 ff_n40C_1v95; do
  LIB="$PDK/sky130_fd_sc_hd__$corner.lib" EXTRA_LIBS="$MACROS" ODB="$B/6_final.odb" SDC="$B/6_final.sdc" \
  SPEF="$B/6_final.spef" "$OPENROAD" -no_splash -exit "$ROOT/flow/sta_corner.tcl" \
    > "$LOGS/fullchip_$corner.log" 2>&1
  echo "$corner $(grep RESULT "$LOGS/fullchip_$corner.log" | tr '\n' ' ')"
done
python3 - "$LOGS" "$CLK_NS" "$ROOT/results/fullchip/sta_corners.json" <<'PY'
import json, re, sys, pathlib
logs, clk, out = pathlib.Path(sys.argv[1]), float(sys.argv[2]), pathlib.Path(sys.argv[3])
SLACK = re.compile(r"^\S+\s+\(\S+\)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+\((?:MET|VIOLATED)\)", re.M)
res = {"clock_period_ns": clk, "macro_views": "OpenRAM TT_1p8V_25C at every corner (no other corner characterized)",
       "corners": {}}
for c in ("ss_100C_1v60", "tt_025C_1v80", "ff_n40C_1v95"):
    t = (logs / f"fullchip_{c}.log").read_text(errors="replace")
    r = {k: float(v) for k, v in re.findall(r"RESULT (\w+) (-?[\d.]+)", t)}
    r2r = float(SLACK.search(t.split("max_delay/setup", 1)[1].split("min_delay/hold", 1)[0])[3])
    r["reg2reg_setup_slack_ns"] = r2r
    r["reg2reg_fmax_mhz"] = round(1e3 / (clk - r2r), 2)
    r["reg2reg_hold_slack_ns"] = float(SLACK.search(t.split("min_delay/hold", 1)[1])[3])
    res["corners"][c] = r
out.write_text(json.dumps(res, indent=2) + "\n"); print(json.dumps(res, indent=2))
PY
