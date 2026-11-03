#!/bin/sh
# Install the sar_sequencer design into an ORFS tree. Idempotent.
#   sh install_design.sh [/OpenROAD-flow-scripts]
set -e
ORFS=${1:-/OpenROAD-flow-scripts}
HERE=$(cd "$(dirname "$0")" && pwd)
D="$ORFS/flow/designs/sky130hd/sar_sequencer"
S="$ORFS/flow/designs/src/sar_sequencer"
mkdir -p "$D" "$S"
cp "$HERE/config.mk" "$HERE/constraint.sdc" "$D"/
cp "$HERE/../sar_sequencer.v" "$S"/
for f in "$D/config.mk" "$D/constraint.sdc" "$S/sar_sequencer.v"; do
  [ -f "$f" ] || { echo "MISSING: $f"; exit 1; }
done
echo "installed -> $D"
echo "            $S"
