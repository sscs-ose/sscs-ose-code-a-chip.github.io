#!/usr/bin/env bash
# Sensitivity of one design point's place-and-route result to a small change of the clock target: run the same
# ORFS flow as run_orfs.sh at <clock ns> and keep only the finish metrics (a one-line json) under <out dir>.
# usage: pnr_perturb.sh <variant> <clock_ns> <out dir>      e.g.  pnr_perturb.sh ntt_sp 20.2 /root/cac_noise
# The work directory is <out dir>/<variant>_<clock>ns; nothing is written to the repository.
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
V=$1; T=$2; OUT=$3
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ORFS="${ORFS_ROOT:-/opt/eda/orfs-6101364b}"
export PATH="$ORFS/tools/install/OpenROAD/bin:$ORFS/tools/install/yosys/bin:$PATH"
export NUM_CORES="${CAC_NUM_CORES:-2}"     # threads per flow: several flows share the machine
export YOSYS_EXE="${YOSYS_EXE:-$ORFS/tools/install/yosys/bin/yosys}" OPENROAD_EXE="${OPENROAD_EXE:-$ORFS/tools/install/OpenROAD/bin/openroad}"
TAG="${V}_${T/./p}ns"; WORK="$OUT/$TAG"; mkdir -p "$WORK"
start=$(date +%s)
set +e
make -C "$ORFS/flow" DESIGN_CONFIG="$ROOT/flow/config.mk" CAC_ROOT="$ROOT" CAC_VARIANT="$V" CAC_CLK_NS="$T" \
     WORK_HOME="$WORK" finish > "$WORK/make.log" 2>&1
rc=$?
if [ "$rc" != 0 ]; then       # an occasional OpenROAD start-up failure when many flows start together: make resumes
  make -C "$ORFS/flow" DESIGN_CONFIG="$ROOT/flow/config.mk" CAC_ROOT="$ROOT" CAC_VARIANT="$V" CAC_CLK_NS="$T" \
       WORK_HOME="$WORK" finish >> "$WORK/make.log" 2>&1; rc=$?
fi
set -e
R=$(find "$WORK/logs" -name 6_report.json | head -1)
python3 - "$R" "$V" "$T" "$rc" "$(( $(date +%s) - start ))" "$OUT/$TAG.json" <<'PY'
import json, sys
r, v, t, rc, secs, out = sys.argv[1:]
d = json.load(open(r)) if r else {}
keep = {k: d[k] for k in d if k.startswith("finish__") and isinstance(d[k], (int, float)) and "warnings" not in k}
json.dump({"variant": v, "clock_ns": float(t), "rc": int(rc), "seconds": int(secs), "finish": keep}, open(out, "w"))
print(v, t, "rc", rc, "ws", keep.get("finish__timing__setup__ws"), "area", keep.get("finish__design__instance__area"))
PY
rm -rf "$WORK/objects"      # intermediate databases are not needed
