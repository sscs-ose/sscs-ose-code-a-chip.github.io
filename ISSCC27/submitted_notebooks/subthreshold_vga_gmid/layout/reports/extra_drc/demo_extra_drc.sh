#!/bin/bash
# demo_extra_drc.sh - the official KLayout deck's off-by-default checks (off-grid, floating metal), with controls
cd "${GL12:-$HOME/glayout/vga12t}" || exit 1
[ -f ~/glayout/.venv/bin/activate ] && source ~/glayout/.venv/bin/activate
export PDK_ROOT=${PDK_ROOT:-$HOME/.ciel/ciel/sky130/versions/0fe599b2afb6708d281543108caf8310912f54af}
DECK=${KDECK:-$PDK_ROOT/sky130A/libs.tech/klayout/drc/sky130A_mr.drc}
GDS=$(pwd)/layout/vga_core_12t.gds; OUT=$(pwd)/verify_demo_extra_drc
rm -rf "$OUT"; mkdir -p "$OUT"; SECONDS=0
[ -f "$DECK" ] || { echo "deck not found: $DECK"; exit 1; }
echo "Extra deck checks on layout $(sha256sum $GDS | cut -c1-16) using $DECK"

# control file: one metal shape 1 nm off the 5 nm grid, and one metal shape connected to nothing
python - "$OUT/ctl.gds" <<'PY'
import sys, gdstk
lib = gdstk.Library(unit=1e-6, precision=1e-9); c = lib.new_cell("ctl")
c.add(gdstk.rectangle((0.001, 0.0), (1.001, 1.0), layer=68, datatype=20))
c.add(gdstk.rectangle((10.0, 10.0), (11.0, 11.0), layer=68, datatype=20))
lib.write_gds(sys.argv[1])
PY

count() { python -c "
import os, sys, xml.etree.ElementTree as ET
p = sys.argv[1]
print(len(ET.parse(p).getroot().findall('.//item')) if os.path.exists(p) else 'x')" "$1"; }
run() { rep="$OUT/$1.lyrdb"; shift; in="$1"; shift
        klayout -b -r "$DECK" -rd input="$in" -rd report="$rep" "$@" > "$rep.log" 2>&1; count "$rep"; }

c1=$(run ctl_offgrid "$OUT/ctl.gds" -rd offgrid=true)
c2=$(run ctl_floating "$OUT/ctl.gds" -rd beol=true -rd floating_met=true)
l=$(run layout "$GDS" -rd offgrid=true -rd beol=true -rd floating_met=true)

echo "========================================================"
echo " EXTRA OFFICIAL-DECK CHECKS  (KLayout; off by default, switched on here)"
if [ "$c1" = x ] || [ "$c2" = x ] || [ "$l" = x ]; then
  echo "   CHECK DID NOT RUN - see $OUT/*.log"
else
  echo "   control, off-grid shape       : $c1 flagged   (must be above 0)"
  echo "   control, floating metal       : $c2 flagged   (must be above 0)"
  echo "   your layout, both checks      : $l violations"
  if [ "$c1" -gt 0 ] && [ "$c2" -gt 0 ] && [ "$l" -eq 0 ]; then echo " RESULT: CLEAN   ($SECONDS s)"
  elif [ "$c1" -le 0 ] || [ "$c2" -le 0 ]; then echo " RESULT: INVALID - a control was not flagged, so the check cannot be trusted"
  else echo " RESULT: $l VIOLATIONS - see $OUT/"; fi
fi
echo "========================================================"
