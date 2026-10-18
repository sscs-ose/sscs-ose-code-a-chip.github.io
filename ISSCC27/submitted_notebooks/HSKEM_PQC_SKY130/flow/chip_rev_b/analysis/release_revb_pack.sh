#!/usr/bin/env bash
# (18/10) Pack the HSKEM-2 rev B release assets (tag hskem2-rev-b; uploaded only with the author's OK): gzip -9 -n of the
# parked final database and the implant-fixed GDS, their SHA-256 into results/fullchip/rev_b/release_sha256.txt.
set -euo pipefail
F=/root/t3/t3e_final_w1/results O=/root/release_revb R=/mnt/d/TKVM_ATTT_2026_test/codeachip_t3int/results/fullchip/rev_b
mkdir -p $O
sha256sum -c /root/t3/t3e_final_w1.sha256 | grep -v ": OK" || true
pack() { gzip -9 -n -c "$1" > "$O/hskem2_rev_b_$2.gz"; }
export -f pack; export O F
printf '%s\n' "$F/6_final.v 6_final.v" "$F/6_final.def 6_final.def" "$F/6_final.odb 6_final.odb" "$F/6_final.spef 6_final.spef" \
  "$F/6_final.sdc 6_final.sdc" "$F/6_final.gds 6_final.gds" "/root/t3/feol_t3e_w1/chip_v2_final7_implantfix.gds implant_fixed.gds" \
  | xargs -P 2 -L 1 bash -c 'pack $0 $1'
(cd $O && sha256sum hskem2_rev_b_*.gz) > $R/release_sha256.txt
ls -la $O; cat $R/release_sha256.txt
