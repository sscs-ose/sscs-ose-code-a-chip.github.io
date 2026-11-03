#!/usr/bin/env bash
# (28/10) Pack the HSKEM-2 rev C release assets (tag hskem2-rev-c; uploaded only with the author's OK), as
# release_revb_pack.sh: gzip -9 -n of the parked final ga1 database and the implant-fixed GDS, their SHA-256 into
# hskem_revc/results/release_sha256.txt (copied to codeachip/results/fullchip/rev_c/ by the integration).
set -euo pipefail
F=/root/t3/revc_final_ga1/results O=/root/release_revc R=/mnt/d/TKVM_ATTT_2026_test/hskem_revc/results
mkdir -p $O
sha256sum -c /root/t3/revc_final_ga1.sha256 | grep -v ": OK" || true
pack() { gzip -9 -n -c "$1" > "$O/hskem2_rev_c_$2.gz"; }
export -f pack; export O F
printf '%s\n' "$F/6_final.v 6_final.v" "$F/6_final.def 6_final.def" "$F/6_final.odb 6_final.odb" "$F/6_final.spef 6_final.spef" \
  "$F/6_final.sdc 6_final.sdc" "$F/6_final.gds 6_final.gds" "/root/t3/feol_revc_ga1/chip_v2_final7_implantfix.gds implant_fixed.gds" \
  | xargs -P 2 -L 1 bash -c 'pack $0 $1'
(cd $O && sha256sum hskem2_rev_c_*.gz) > $R/release_sha256.txt
ls -la $O; cat $R/release_sha256.txt
