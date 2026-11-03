#!/bin/bash
# KLayout DRC of the routed layouts with the sky130hd deck of OpenROAD-flow-scripts (what `make drc` runs):
# each 6_final.def is streamed to GDS with the standard-cell GDS (ORFS def2stream.py), then checked.
#
#   bash scripts/klayout_drc.sh [data/layout/<name> ...]     (default: every layout with a 6_final.def.gz)
#
# Needs klayout (installed into ./conda-env with bin/micromamba if not found) and bench/external/drc_kit
# (ORFS platform files: tech LEF, merged cell LEF, cell GDS, sky130hd.lyt, sky130hd.lydrc, def2stream.py,
# generate_klayout_tech.py).  Writes data/layout/<name>/drc_klayout.json; work files in drc_work/.
set -uo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd); cd "$ROOT"
K=$ROOT/bench/external/drc_kit
W=$ROOT/drc_work; mkdir -p "$W"
KL=$(command -v klayout || true)
[ -z "$KL" ] && [ -x "$ROOT/conda-env/bin/klayout" ] && KL=$ROOT/conda-env/bin/klayout
if [ -z "$KL" ]; then
  if [ ! -x bin/micromamba ]; then
    mkdir -p bin
    curl -Lso bin/micromamba https://github.com/mamba-org/micromamba-releases/releases/download/1.5.10-0/micromamba-linux-64
    chmod +x bin/micromamba
  fi
  MAMBA_ROOT_PREFIX=$ROOT/.mamba bin/micromamba install -y -p "$ROOT/conda-env" -c conda-forge "klayout=0.30" || exit 1
  KL=$ROOT/conda-env/bin/klayout
fi
"$KL" -v
PY=$( [ -x "$ROOT/conda-env/bin/python" ] && echo "$ROOT/conda-env/bin/python" || command -v python3 )
"$PY" "$K/generate_klayout_tech.py" --template "$K/sky130hd.lyt" --output "$W/klayout.lyt" \
    --lef-files "$K/sky130_fd_sc_hd.tlef" "$K/sky130_fd_sc_hd_merged.lef" || exit 1
DIRS=("$@"); [ ${#DIRS[@]} -eq 0 ] && DIRS=($(ls -d data/layout/*/ 2>/dev/null))
for d in "${DIRS[@]}"; do
  d=${d%/}; n=$(basename "$d")
  [ -f "$d/6_final.def.gz" ] || continue
  zcat "$d/6_final.def.gz" > "$W/$n.def"
  top=$(grep -m1 '^DESIGN' "$W/$n.def" | awk '{print $2}')
  echo "== $n ($top) $(date +%H:%M)"
  if ! "$KL" -zz -rd design_name="$top" -rd in_def="$W/$n.def" -rd in_files="$K/sky130_fd_sc_hd.gds" \
        -rd seal_file="" -rd out_file="$W/$n.gds" -rd tech_file="$W/klayout.lyt" -rd layer_map="" \
        -r "$K/def2stream.py" > "$W/$n.merge.log" 2>&1; then
    echo "   stream-out FAILED:"; tail -5 "$W/$n.merge.log"; continue
  fi
  if ! "$KL" -zz -rd in_gds="$W/$n.gds" -rd report_file="$W/$n.lyrdb" -r "$K/sky130hd.lydrc" > "$W/$n.drc.log" 2>&1; then
    echo "   DRC FAILED:"; tail -5 "$W/$n.drc.log"; continue
  fi
  "$PY" scripts/drc_summary.py "$W/$n.lyrdb" "$d/drc_klayout.json"
done
echo DRC_DONE
