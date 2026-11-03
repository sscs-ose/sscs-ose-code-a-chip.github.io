#!/bin/bash
# demo_antenna.sh - Magic antenna check on the layout, with a built-in positive control
cd "${GL12:-$HOME/glayout/vga12t}" || exit 1
export PDK_ROOT=${PDK_ROOT:-$HOME/.ciel/ciel/sky130/versions/0fe599b2afb6708d281543108caf8310912f54af}
RC=$PDK_ROOT/sky130A/libs.tech/magic/sky130A.magicrc
GDS=$(pwd)/layout/vga_core_12t.gds; OUT=verify_demo_antenna
rm -rf "$OUT"; mkdir -p "$OUT"; cd "$OUT"; SECONDS=0
echo "Antenna check on layout $(sha256sum $GDS | cut -c1-16)..."

echo "Running control cell (a gate wired to a huge metal plate: MUST be flagged)..."
magic -dnull -noconsole -rcfile $RC > control.log 2>&1 <<'CTRL'
cellname create antest
load antest
box 0 0 1um 1um
paint ndiff
box -1.5um 0.4um 1.3um 0.55um
paint poly
box -1.5um 0.3um -0.9um 0.7um
paint pcontact
box -1.5um 0.3um -0.9um 0.7um
paint viali
box -60um -60um -1um 60um
paint metal1
extract all
puts "BEFORE=[feedback count]"
antennacheck
puts "AFTER=[feedback count]"
quit -noprompt
CTRL

echo "Running the real layout (flattened)..."
magic -dnull -noconsole -rcfile $RC > layout.log 2>&1 <<LAYOUT
gds read $GDS
load vga_core_12t
flatten vga_core_12t_flat
load vga_core_12t_flat
select top cell
extract all
puts "BEFORE=[feedback count]"
antennacheck
puts "AFTER=[feedback count]"
quit -noprompt
LAYOUT

get() { grep -E "^$1=" "$2" | tail -1 | cut -d= -f2; }
cb=$(get BEFORE control.log); ca=$(get AFTER control.log); lb=$(get BEFORE layout.log); la=$(get AFTER layout.log)
echo "========================================================"
echo " ANTENNA CHECK  (Magic, SKY130 antenna rules, flattened layout)"
if [ -z "$cb" ] || [ -z "$ca" ] || [ -z "$lb" ] || [ -z "$la" ]; then
  echo "   CHECK DID NOT RUN - see $OUT/control.log and $OUT/layout.log"
else
  c=$((ca - cb)); l=$((la - lb))
  echo "   control cell (gate on a huge plate) : $c violations flagged   (must be above 0)"
  echo "   your layout                         : $l antenna violations"
  if [ "$c" -gt 0 ] && [ "$l" -eq 0 ]; then echo " RESULT: ANTENNA CLEAN   ($SECONDS s)"
  elif [ "$c" -le 0 ]; then echo " RESULT: INVALID - the control was not flagged, so the check cannot be trusted"
  else echo " RESULT: $l ANTENNA VIOLATIONS - see $OUT/"; fi
fi
echo "========================================================"
