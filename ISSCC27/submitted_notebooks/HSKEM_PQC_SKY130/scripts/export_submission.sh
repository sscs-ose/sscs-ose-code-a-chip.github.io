#!/usr/bin/env bash
# Stage the Code-a-Chip submission folder: everything needed to read and rerun
# the notebook, without files that are regenerated (vectors, netlists, traces,
# the downloaded liberty, the routed netlists of supplementary clock-sweep
# points) or too large for a pull request (GDS; the GDS files
# are published separately as gzip assets, see README).
# usage: export_submission.sh <dest_dir>
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; DST=${1:?destination}
mkdir -p "$DST"
rsync -a --delete --delete-excluded \
  --exclude 'pdk/' --exclude 'vectors*/' --exclude 'results/sim_notebook/' --exclude 'results/gls_notebook/' \
  --exclude '*.gds' --exclude '*.vvp' --exclude '__pycache__/' \
  --exclude 'results/synth/*/netlist.v' --exclude 'results/synth/*/yosys.log' \
  --exclude 'results/leakage*/leak_traces.txt' --exclude 'results/leakage*/leak_in.hex' \
  --exclude 'BOARD_SESSION_PLAN.md' --exclude 'HEAVY_RUNS_PLAN.md' --exclude 'REVIEW_CRITERIA.md' --exclude 'PR_DESCRIPTION_DRAFT.md' --exclude 'BOARD_KEY_ROTATION_PLAN.md' --exclude 'PENDING_REVIEW_*.md' --exclude 'board/*.log' --exclude 'board/*.csv' \
  --exclude 'board/__pycache__/' --exclude '*_ant10/' --exclude '*_superseded/' --exclude '*_udocker/' --exclude '*_bundle*/' --exclude '*_hm[0-9]*/' \
  --exclude 'results/asic/*/images/' --exclude 'results/asic/*/layout.png' \
  --exclude 'results/fullchip/fullchip_layout.png' --exclude '*.vcd' --exclude '*.vcd.gz' \
  --exclude 'results/asic/ntt_dp_15ns/6_final.v' --exclude 'results/asic/ntt_dp_30ns/6_final.v' \
  --exclude 'results/asic/ntt_sp_1[25]ns/6_final.v' --exclude 'results/asic/ntt_sp_30ns/6_final.v' \
  --exclude 'results/asic/keccak_*_7ns/6_final.v' --exclude 'results/asic/keccak_*_10ns/6_final.v' \
  "$ROOT/" "$DST/"
du -sh "$DST"
find "$DST" -type f -size +2M -exec ls -la {} \;
