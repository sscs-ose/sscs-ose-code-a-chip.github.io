#!/usr/bin/env bash
# FEOL DRC of a GDS with the SKY130 KLayout deck that ORFS ships (platforms/sky130hd/drc/sky130hd.lydrc).
# ORFS runs that deck with its FEOL section disabled, so the flow's own DRC covers only the BEOL and
# off-grid rules; this script runs the FEOL section on its own.
# Rule vpp.5 is left out: it merges poly, li, met1 and met2 of the whole layout before it looks at the
# vpp layer, and in KLayout 0.30 it does not finish within hours even on a small block. The rule can
# only fire where the vpp layer (82/64) has shapes, so the script counts that layer first and stops if
# it is not empty.
# usage: scripts/feol_drc.sh <in.gds> <report.lyrdb>
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
GDS=${1:?gds}; RPT=${2:?report}
ORFS="${ORFS_ROOT:-/opt/eda/orfs-6101364b}"
DECK="$(mktemp --suffix=.lydrc)"; trap 'rm -f "$DECK" "$DECK.py" "$DECK.src"' EXIT
SRC="$ORFS/flow/platforms/sky130hd/drc/sky130hd.lydrc"
if [ ! -f "$SRC" ]; then      # no local ORFS (e.g. Colab): the same deck from ORFS at the pinned commit
  curl -sfL "https://raw.githubusercontent.com/The-OpenROAD-Project/OpenROAD-flow-scripts/6101364b2d7909dd797e1e3e7f80695401cfa4e4/flow/platforms/sky130hd/drc/sky130hd.lydrc" -o "$DECK.src"
  SRC="$DECK.src"
fi
sed -e 's/^FEOL    = false/FEOL    = true/' -e 's/^BEOL    = true/BEOL    = false/' \
    -e 's/^OFFGRID = true/OFFGRID = false/' -e '/output("vpp\.5"/s/^/# (vpp.5 left out, see feol_drc.sh) /' \
    "$SRC" > "$DECK"
grep -q '^FEOL    = true' "$DECK" && grep -q '^# (vpp.5 left out' "$DECK" || { echo "deck edit failed"; exit 1; }
cat > "$DECK.py" <<'PY'
import pya
ly = pya.Layout(); ly.read(gds)
li = ly.find_layer(82, 64); n = 0
if li is not None:
    it = ly.top_cell().begin_shapes_rec(li)
    while not it.at_end():
        n += 1; it.next()
print(n)
PY
NVPP=$(klayout -b -rd gds="$GDS" -r "$DECK.py" | tail -1)
[ "$NVPP" = 0 ] || { echo "the vpp layer holds $NVPP shapes: vpp.5 would have to be checked"; exit 1; }
klayout -b -rd in_gds="$GDS" -rd report_file="$RPT" -r "$DECK"
echo "FEOL markers: $(grep -c '<item>' "$RPT")   (vpp layer empty, vpp.5 not needed)"
