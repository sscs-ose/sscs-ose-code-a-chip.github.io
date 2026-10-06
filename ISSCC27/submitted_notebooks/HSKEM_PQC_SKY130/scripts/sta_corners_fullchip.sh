#!/usr/bin/env bash
# Three-corner STA of the routed full HSKEM core (OpenROAD's STA on the routed database with the
# extracted SPEF; flow/sta_corner.tcl explains why the database rather than 6_final.v is read, and
# flow/sta_corner_fullchip.tcl adds the reports that this summary reads).
# The layout database is not published (see README), so this script needs the private
# run directory; only the summary it writes, results/fullchip/sta_corners.json, is published.
# The OpenRAM macros are characterized at the typical corner only, so their TT views are
# used at every corner; the standard cells use their ss / tt / ff libraries. For that reason the
# summary keeps the flip-flop-to-flip-flop paths (macros excluded at both ends) apart from the paths
# that start or end at a macro, and it reads the core_clk group by name: report_checks prints the
# asynchronous (reset recovery/removal) group first, and an earlier version of this script took that
# group's slack as the register-to-register slack.
# usage: FULLCHIP_DIR=<ORFS results dir with 6_final.{odb,sdc,spef}> MACRO_LIB_DIR=<dir of the
#        *.physical.lib macro views> [FULLCHIP_STA_OUT=<summary json>] scripts/sta_corners_fullchip.sh
# SPDX-License-Identifier: Apache-2.0
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ORFS="${ORFS_ROOT:-/opt/eda/orfs-6101364b}"; OPENROAD="$ORFS/tools/install/OpenROAD/bin/openroad"
PDK="${SKY130_LIBS:-$(ls -d /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A/libs.ref/sky130_fd_sc_hd/lib | head -1)}"
B="${FULLCHIP_DIR:?FULLCHIP_DIR}"; M="${MACRO_LIB_DIR:?MACRO_LIB_DIR}"
OUT="${FULLCHIP_STA_OUT:-$ROOT/results/fullchip/sta_corners.json}"
LOGS="${FULLCHIP_STA_LOGS:-$HOME/fullchip_sta}"; mkdir -p "$LOGS"     # detailed logs stay private
MACROS=$(ls "$M"/*.physical.lib | tr '\n' ' ')
[ -n "$MACROS" ] || { echo "no macro views in $M"; exit 1; }
CLK_NS=$(grep -m1 -oE "create_clock.*-period [0-9.]+" "$B/6_final.sdc" | grep -oE "[0-9.]+$")
for corner in ss_100C_1v60 tt_025C_1v80 ff_n40C_1v95; do
  LIB="$PDK/sky130_fd_sc_hd__$corner.lib" EXTRA_LIBS="$MACROS" ODB="$B/6_final.odb" SDC="$B/6_final.sdc" \
  SPEF="$B/6_final.spef" "$OPENROAD" -no_splash -exit "$ROOT/flow/sta_corner_fullchip.tcl" \
    > "$LOGS/fullchip_$corner.log" 2>&1
  echo "$corner $(grep RESULT "$LOGS/fullchip_$corner.log" | tr '\n' ' ')"
done
python3 - "$LOGS" "$CLK_NS" "$OUT" <<'PY'
import json, re, sys, pathlib
logs, clk, out = pathlib.Path(sys.argv[1]), float(sys.argv[2]), pathlib.Path(sys.argv[3])
SLACK = re.compile(r"^\S+\s+\(\S+\)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+\((?:MET|VIOLATED)\)", re.M)

def section(text, name):
    return text.split(f"SECTION {name}\n", 1)[1].split("SECTION ", 1)[0]

def group_slack(text, check, group="core_clk"):
    """worst endpoint slack of <check> (max_delay/setup or min_delay/hold) in <group>"""
    parts = text.split(f"{check} group {group}", 1)
    if len(parts) < 2:
        return None
    body = re.split(r"\n(?:max_delay/setup|min_delay/hold) group ", parts[1], maxsplit=1)[0]
    m = SLACK.search(body)
    return float(m[3]) if m else None

res = {"clock_period_ns": clk,
       "macro_views": "OpenRAM TT_1p8V_25C at every corner (no other corner characterized)",
       "method": "OpenROAD STA on the routed database + extracted SPEF; core_clk group; flip-flop-to-flip-flop "
                 "paths exclude the SRAM macros at both ends", "corners": {}}
for c in ("ss_100C_1v60", "tt_025C_1v80", "ff_n40C_1v95"):
    t = (logs / f"fullchip_{c}.log").read_text(errors="replace")
    r = {k: float(v) for k, v in re.findall(r"RESULT (\w+) (-?[\d.]+)", t)}
    rm = section(t, "reg2reg_with_macros")
    r["reg2reg_incl_macros_setup_slack_ns"] = group_slack(rm, "max_delay/setup")
    r["reg2reg_incl_macros_hold_slack_ns"] = group_slack(rm, "min_delay/hold")
    s = group_slack(section(t, "ff2ff_setup"), "max_delay/setup")
    r["ff2ff_setup_slack_ns"] = s
    r["ff2ff_fmax_mhz"] = round(1e3 / (clk - s), 2) if s is not None else None
    r["ff2ff_hold_slack_ns"] = group_slack(section(t, "ff2ff_hold"), "min_delay/hold")
    hv = []
    for line in section(t, "hold_violators").splitlines():
        f = line.split()
        if len(f) >= 3 and re.fullmatch(r"-?[\d.]+", f[-1]) and float(f[-1]) < 0:
            hv.append({"startpoint": f[0], "endpoint": f[-3] if f[-2].startswith("(") else f[-2],
                       "slack_ns": float(f[-1])})
    r["hold_violators"] = hv
    res["corners"][c] = r
out.write_text(json.dumps(res, indent=2) + "\n"); print(json.dumps(res, indent=2))
PY
