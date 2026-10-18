#!/usr/bin/env bash
# Evidence for the Magic DRC of HSKEM-2 revision B (magic_drc.json): the stand-alone Magic DRC of
#  (1) the two standard cells under the 349 markers outside the macros, from the GDS that ORFS 6101364b streams in and
#      from the current SKY130 PDK, and
#  (2) one OpenRAM macro (24 x 128) read alone from a routed block's GDS,
# written to <out.json>. Stand-alone cells always show the context rules (taps, latch-up) that the rows satisfy.
# usage: magic_cell_check.sh <block gds with the 24x128 macro> <out.json>
set -euo pipefail
MAGIC=/opt/eda/magic-8.3.629/install/bin/magic
P=$(ls -d /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A | head -1); export PDK_ROOT=$(dirname $P)
ORFS_GDS=/opt/eda/orfs-6101364b/flow/platforms/sky130hd/gds/sky130_fd_sc_hd.gds
PDK_GDS=$P/libs.ref/sky130_fd_sc_hd/gds/sky130_fd_sc_hd.gds
BLOCK="${1:?block gds}"; OUT="${2:?out.json}"; W=$(mktemp -d); trap 'rm -rf $W' EXIT
run() {   # tag gds cells...
  local tag=$1 gds=$2; shift 2
  { echo "drc off"; echo "gds readonly true"; echo "gds read $gds"
    for c in "$@"; do
      echo "load $c"; echo "select top cell"; echo "drc euclidean on"; echo "drc style drc(full)"; echo "drc on"
      echo "drc check"; echo "drc catchup"
      echo "foreach {why boxes} [drc listall why] { puts \"RES\t$tag\t$c\t[llength \$boxes]\t\$why\" }"
    done; echo "quit -noprompt"; } > $W/$tag.tcl
  $MAGIC -dnull -noconsole -rcfile $P/libs.tech/magic/sky130A.magicrc $W/$tag.tcl 2>/dev/null | grep "^RES" || true
}
{ run orfs_gds "$ORFS_GDS" sky130_fd_sc_hd__a2111oi_0 sky130_fd_sc_hd__buf_16
  run pdk_gds "$PDK_GDS" sky130_fd_sc_hd__a2111oi_0 sky130_fd_sc_hd__buf_16
  run macro_alone "$BLOCK" sky130_sram_1rw_24x128; } > $W/res.tsv
python3 - $W/res.tsv "$OUT" "$ORFS_GDS" "$PDK_GDS" <<'PY'
import collections, hashlib, json, sys
res = collections.defaultdict(lambda: collections.defaultdict(dict))
for l in open(sys.argv[1]):
    _, tag, cell, n, why = l.rstrip("\n").split("\t")
    res[tag][cell][why] = int(n)
out = {"method": "Magic 8.3.629, SKY130 drc(full), euclidean, each cell loaded alone",
       "orfs_cell_gds_sha256": hashlib.sha256(open(sys.argv[3], "rb").read()).hexdigest(),
       "pdk_cell_gds_sha256": hashlib.sha256(open(sys.argv[4], "rb").read()).hexdigest(),
       "results": res}
open(sys.argv[2], "w").write(json.dumps(out, indent=1) + "\n"); print(json.dumps(out["results"], indent=1))
PY
