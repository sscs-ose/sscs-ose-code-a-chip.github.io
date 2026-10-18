#!/usr/bin/env bash
# (18/10) rev B extras for results/fullchip/rev_b: FEOL summary (scripts/feol_summary.py in a mirror, as for rev A) and
# the full-system simulation log of the rev B RTL (sram_access_t3e.sh run: ALL PASS, decapsulation cycles, shared keys)
set -euo pipefail
R=/mnt/d/TKVM_ATTT_2026_test; OUT=$R/chip_v2/signoff/rev_b; M=$R/chip_v2/signoff/stage_root_t3e
mkdir -p $M/scripts $M/results/fullchip
cp $R/codeachip/scripts/feol_summary.py $M/scripts/
sed -i "s/summarize(orig, \"rest_\")/summarize(orig, \"chip_\")/" $M/scripts/feol_summary.py   # rev B: both runs named chip_*
python3 $M/scripts/feol_summary.py /root/t3/feol_t3e_w1/orig /root/t3/feol_t3e_w1/fixed \
  /root/t3/t3e_final_w1/results/6_final.gds /root/t3/feol_t3e_w1/chip_v2_final7_implantfix.gds | tail -3
cp $M/results/fullchip/feol_drc.json $OUT/feol_drc.json
grep -v "^VCD info" /root/sram_access_t3e/sim.log > $OUT/tb_trustedge_spi_rev_b.log
grep -c PASS $OUT/tb_trustedge_spi_rev_b.log; grep -E "TB_TRUSTEDGE_SPI_RESULT|U1 Decaps" $OUT/tb_trustedge_spi_rev_b.log
