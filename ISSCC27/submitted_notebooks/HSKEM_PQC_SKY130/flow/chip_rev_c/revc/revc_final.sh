#!/usr/bin/env bash
# Rev C: final stage (fill, RC extraction -> 6_final.spef, timing, GDS, CDL) on a clean routed checkpoint, parking any
# previous final under final_from_<prev>/ (rev B's final_after_drv_t3.sh with the rev C work home).
# usage: revc_final.sh <clean odb name> <tag of the previous final, or none>
set -u
source /mnt/d/TKVM_ATTT_2026_test/hskem_revc/flow/revc_env.sh
IN=${1:?odb}; PREV=${2:?prev tag}
[ -e $R/5_2_route_main.odb ] || { cp -p $R/5_2_route.odb $R/5_2_route_main.odb; chmod a-w $R/5_2_route_main.odb; }
if [ "$PREV" != none ]; then
  P=$W/final_from_$PREV; mkdir -p $P/results $P/reports
  for f in $R/6_* $R/5_3_fillcell.odb $R/5_route.odb $R/5_route.sdc; do [ -e "$f" ] && mv "$f" $P/results/; done
  for f in $Rp/6_*; do [ -e "$f" ] && mv "$f" $P/reports/; done
  chmod -R a-w $P
fi
bash $FC/final_t3.sh $W $IN > /root/t3/revc_final_$IN.out 2>&1
grep -E "FINAL_(INPUT_HASH|DONE)|FINAL_STEP_FAIL" /root/t3/revc_final_$IN.out
grep -E "^(tns|wns|worst slack) max|period_min|violation count" $Rp/6_finish.rpt
