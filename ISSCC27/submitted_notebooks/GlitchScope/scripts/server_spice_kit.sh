#!/bin/bash
# Transistor-level (ngspice, SKY130, parasitic-extracted cells) confirmation of GlitchScope's
# automatic fix on the 16x16 multiplier -- the long runs, for a multi-core server.
#
#   bash scripts/server_spice_kit.sh setup          # check / install ngspice + SKY130 (micromamba, no root)
#   bash scripts/server_spice_kit.sh run [JOBS]     # start in the background (resumable; safe to re-run)
#   bash scripts/server_spice_kit.sh status         # progress
#   bash scripts/server_spice_kit.sh postlayout [JOBS]   # the routed layouts (clock tree + wire caps), 30 jobs
#   bash scripts/server_spice_kit.sh pack           # -> spice_results.zip (results only, a few kB) to send back
#   bash scripts/server_spice_kit.sh c6288 [JOBS]           # c6288 SPICE (round 7)
#   GLOW_PY=<python> bash scripts/server_spice_kit.sh glow7 <GLOW>   # GLOW warm starts; then status7, pack7
#
# Work, in this order (all resumable):
#   1. mul8:  original, timing-driven and GlitchScope's two candidate placements (arrival cuts, MILP), 48 cycles,
#             48 jobs of ~0.5 h each
#   2. mul16: the same four designs, 40 cycles, 40 jobs of ~4-9 h of one core and ~0.8 GB each
# JOBS defaults to the number of cores minus 2.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd); cd "$ROOT"
ENV=$ROOT/conda-env
LOG=$ROOT/spice_kit.log
[ -f "$ROOT/server.env" ] && set -a && . "$ROOT/server.env" && set +a

find_tools() {
  NG=${GS_NGSPICE:-$(command -v ngspice || true)}
  [ -z "$NG" ] && [ -x "$ENV/bin/ngspice" ] && NG=$ENV/bin/ngspice
  PDK=${GS_PDK_ROOT:-}
  for p in "$PDK" "$ENV/share/pdk/sky130A" "${PDK_ROOT:-/nonexistent}/sky130A" /usr/local/share/pdk/sky130A; do
    if [ -n "$p" ] && [ -f "$p/libs.tech/ngspice/sky130.lib.spice" ]; then PDK=$p; break; fi
  done
}

case "${1:-}" in
setup)
  find_tools
  if [ -z "$NG" ] || [ ! -f "${PDK:-/x}/libs.tech/ngspice/sky130.lib.spice" ]; then
    echo "installing ngspice + SKY130 into $ENV (micromamba, ~5-10 min) ..."
    [ -x bin/micromamba ] || curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba
    bin/micromamba create --yes --prefix "$ENV" --channel litex-hub --channel conda-forge ngspice open_pdks.sky130a python=3.11 numpy
    find_tools
  fi
  PY=$( [ -x "$ENV/bin/python" ] && echo "$ENV/bin/python" || command -v python3 )
  LIB=$PDK/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
  cat > "$ROOT/server.env" <<EOF
GS_NGSPICE=$NG
GS_PDK_ROOT=$PDK
GS_LIB=$LIB
GS_PY=$PY
EOF
  "$PY" -c "import numpy" && echo "numpy ok"
  "$NG" -v 2>/dev/null | head -2 || true
  ls "$LIB" && echo "setup ok -> server.env written"
  ;;
run)
  [ -f "$ROOT/server.env" ] || { echo "run 'setup' first"; exit 1; }
  JOBS=${2:-$(( $(nproc) > 3 ? $(nproc) - 2 : 1 ))}
  TAGS=original,timing_driven,best_cuts,best_milp
  nohup bash -c "
    '$GS_PY' scripts/spice_confirm_parallel.py run '$GS_LIB' mul8_r --cells pex --cycles 48 --chunk 4 --jobs $JOBS --tags $TAGS
    '$GS_PY' scripts/spice_confirm_parallel.py run '$GS_LIB' mul16_r --cells pex --cycles 40 --chunk 4 --jobs $JOBS --tags $TAGS
    echo ALL_DONE" >> "$LOG" 2>&1 &
  echo "started with $JOBS parallel jobs (pid $!); log: $LOG"
  ;;
postlayout)
  [ -f "$ROOT/server.env" ] || { echo "run 'setup' first"; exit 1; }
  JOBS=${2:-30}
  nohup "$GS_PY" scripts/spice_confirm_postlayout.py run "$GS_LIB" --cycles 40 --chunk 4 --jobs "$JOBS" \
      >> "$ROOT/spice_postlayout.log" 2>&1 &
  echo "started post-layout SPICE with $JOBS parallel jobs (pid $!); log: $ROOT/spice_postlayout.log"
  ;;
status)
  echo "post-layout chunks done: $(ls "$ROOT"/data/glitchfix/mul16_r/spice_parts_postlayout/*_*.json 2>/dev/null | wc -l)/30"
  for c in mul8_r:12 mul16_r:10; do
    D=$ROOT/data/glitchfix/${c%%:*}/spice_parts_pex
    for t in original timing_driven best_cuts best_milp; do
      printf "%-8s %-14s %s/%s chunks done\n" "${c%%:*}" "$t" "$(ls "$D"/${t}_*.json 2>/dev/null | wc -l)" "${c##*:}"
    done
  done
  echo "ngspice processes running: $(pgrep -c -x ngspice || true)"
  tail -3 "$LOG" 2>/dev/null || true
  ;;
c6288)
  # ngspice of c6288 (original, min-register, GlitchScope, GLOW cold), 40 cycles:  c6288 [JOBS]
  [ -f "$ROOT/server.env" ] || { echo "run 'setup' first"; exit 1; }
  JOBS=${2:-30}
  nohup bash -c "'$GS_PY' scripts/spice_confirm_parallel.py run '$GS_LIB' c6288_r --cells pex --cycles 40 --chunk 4 \
      --jobs $JOBS --tags original,min_register,glitchscope,glow_sim; echo SPICE_DONE" >> "$ROOT/round7_spice.log" 2>&1 &
  echo "started c6288 SPICE with $JOBS jobs (pid $!); log: $ROOT/round7_spice.log"
  ;;
glow7)
  # GLOW warm-started from minimum-register retiming, 4 cases / 5 runs of 1 h, as in the cold runs:
  #   GLOW_PY=<python with gurobipy> bash scripts/server_spice_kit.sh glow7 <GLOW checkout>
  G=${2:?path to the GLOW-ICCAD26 checkout}; G=$(cd "$G" && pwd)
  GPY=${GLOW_PY:-python3}
  "$GPY" -c "import gurobipy; print('gurobipy', gurobipy.gurobi.version())" || { echo "gurobipy not importable with $GPY (set GLOW_PY=...)"; exit 1; }
  "$GPY" scripts/glow_warmstart.py patch "$G"
  nohup env GLOW_PY="$GPY" bash -c "
    for c in 'c6288_r@0.0' 'b14@1.1' 'sin_r@0.0' 'mul16_v0@0.0'; do
      echo \"== GLOW warm \$c \$(date +%H:%M)\"
      bash data/glow/\$c/run_glow_warm.sh '$G' > data/glow/\$c/warm.out 2>&1 && echo '   done' || echo '   FAILED'
      grep -hiE 'MIP start|optimal|time limit|infeasible|Best objective' data/glow/\$c/glow_w*.log 2>/dev/null | tail -3
    done
    echo GLOW_DONE" >> "$ROOT/round7_glow.log" 2>&1 &
  echo "started GLOW warm starts (pid $!), ~5 h; log: $ROOT/round7_glow.log"
  ;;
status7)
  echo "--- GLOW"; tail -8 "$ROOT/round7_glow.log" 2>/dev/null || true
  echo "--- SPICE"; tail -2 "$ROOT/round7_spice.log" 2>/dev/null || true
  echo "c6288 SPICE chunks done: $(ls "$ROOT"/data/glitchfix/c6288_r/spice_parts_pex/*_*.json 2>/dev/null | wc -l)/40"
  echo "ngspice processes running: $(pgrep -c -x ngspice || true)"
  ;;
pack7)
  cd "$ROOT" && rm -f round7_results.zip && zip -qr round7_results.zip $(ls round7_*.log 2>/dev/null) \
      $(ls data/glow/*/glow_w*.dot data/glow/*/glow_w*.log data/glow/*/glow_w*.time data/glow/*/warm.out 2>/dev/null) \
      $(ls -d data/glitchfix/c6288_r/spice_parts_pex 2>/dev/null) && ls -la round7_results.zip
  ;;
pack)
  cd "$ROOT" && rm -f spice_results.zip && zip -qr spice_results.zip data/glitchfix/mul8_r/spice_parts_pex \
      data/glitchfix/mul16_r/spice_parts_pex $(ls -d data/glitchfix/mul16_r/spice_parts_postlayout 2>/dev/null) \
      $(ls spice_kit.log spice_postlayout.log 2>/dev/null) && ls -la spice_results.zip
  ;;
*)
  sed -n 2,13p "$0"
  ;;
esac
