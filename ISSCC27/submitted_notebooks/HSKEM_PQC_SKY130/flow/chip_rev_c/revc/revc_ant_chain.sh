#!/usr/bin/env bash
# Antenna rounds in the old chip's style (one session per round, reloading the previous clean checkpoint) with the
# DRT-1231-patched OpenROAD (openroad_drt1231_skip.diff -> /opt/eda/openroad-t3patch). Stops when antenna = 0, when a
# round ends with DRC > 0 (no diodes piled into a corner the router cannot clear), after 6 rounds, or at 01:00.
# usage: revc_ant_chain.sh <start odb name>   (log: /root/t3/revc_ant_chain.log)
# env: REVC_W (work home, default /root/t3/revc1_a3grt), ANT_LOG (log), PFX / CPFX (round tag prefixes)
# Rev C copy of codeachip_t3/flow_chip/ant_chain_t3.sh: work home revc1_a3grt, rev C root and defines, no night rule.
set -u
ROOT=/mnt/d/TKVM_ATTT_2026_test
DEFS="TRUSTEDGE_T3_MAC_DEEP TRUSTEDGE_T3_MM_PIPE TRUSTEDGE_T3_CRC_SERIAL TRUSTEDGE_T3_BARRETT_1C TRUSTEDGE_T3_SA_PIPE TRUSTEDGE_T3_PMAC_RAW TRUSTEDGE_T3_CODEC_RETIME TRUSTEDGE_T3_MSG_PIPE TRUSTEDGE_T3_PP_EARLY TRUSTEDGE_T3_LOAD_PIPE TRUSTEDGE_T3_MARGIN TRUSTEDGE_T3_MUL_SEL TRUSTEDGE_T3_SEL_REP TRUSTEDGE_T3_EK_PREF TRUSTEDGE_REVC"
export T3_ROOT="$ROOT/hskem_revc/revc/root"
export T3_DEFINES_EXTRA="$(for d in $DEFS; do printf -- "-D %s " "$d"; done)"
W=${REVC_W:-/root/t3/revc1_a3grt}; D=sky130hd/trustedge_asic_core/chipv2; R=$W/results/$D; Lg=$W/logs/$D; Rp=$W/reports/$D
export OPENROAD_EXE=/opt/eda/openroad-t3patch/bin/openroad CHIPV2_DRT_END_ITER=20
in="$1"; LOG=${ANT_LOG:-/root/t3/revc_ant_chain.log}; k0=${2:-1}
for k in $(seq $k0 6); do
  dfree=$(df -Pk /mnt/d | awk 'NR==2{print int($4/1048576)}'); [ "$dfree" -ge 8 ] || { echo "$(date +%H:%M) STOP: drive D has only ${dfree} GB free" | tee -a $LOG; break; }
  tag=${PFX:-b}$k
  echo "$(date +%H:%M) round $tag from $in" | tee -a $LOG
  bash /mnt/d/TKVM_ATTT_2026_test/codeachip_t3/flow_chip/drt_round_t3.sh $W $tag $in antenna > /root/t3/revc_$tag.out 2>&1
  rc=$(grep -o "DRT_DONE session=$tag rc=[0-9]*" /root/t3/revc_$tag.out | sed 's/.*rc=//')
  before=$(grep -o "antenna_violations_before=[0-9]*" $Lg/5_2_route_$tag.log | sed 's/.*=//')
  after=$(grep -o "antenna_violations_after=[0-9]*" $Lg/5_2_route_$tag.log | sed 's/.*=//')
  drc=$(grep -c . $Rp/5_route_drc_$tag.rpt 2>/dev/null); skips=$(grep -c DRT-1231 $Lg/5_2_route_$tag.log)
  last=$(grep DRT-0199 $Lg/5_2_route_$tag.log | tail -1 | sed 's/.*= //; s/.$//')
  echo "$(date +%H:%M) $tag rc=$rc antenna $before -> $after, last DRC count $last, DRC report lines $drc, DRT-1231 skips $skips" | tee -a $LOG
  [ "$rc" = 0 ] && [ -f $R/5_2_route_$tag.odb ] || { echo "round failed" | tee -a $LOG; break; }
  chmod a-w $R/5_2_route_$tag.odb; echo "   $(sha256sum $R/5_2_route_$tag.odb | cut -c1-16) 5_2_route_$tag.odb" | tee -a $LOG
  in=5_2_route_$tag.odb
  # 26/10: no clean-up round once a clean-up has stopped lowering the markers (revc2: 10 -> 10 through cl2..cl4, 1 h each)
  if [ "$last" != "0" ] && [ -n "${lastcl:-}" ] && [ "$last" -ge "$lastcl" ]; then
    echo "$(date +%H:%M) cleanup skipped: DRC $last, the last clean-up left $lastcl" | tee -a $LOG
  elif [ "$last" != "0" ]; then          # cleanup round without new diodes (c1 cleared 64 -> 0 this way)
    ct=${CPFX:-cl}$k; echo "$(date +%H:%M) cleanup $ct from $in (DRC $last)" | tee -a $LOG
    bash /mnt/d/TKVM_ATTT_2026_test/codeachip_t3/flow_chip/drt_round_t3.sh $W $ct $in drc > /root/t3/revc_$ct.out 2>&1
    cl=$(grep DRT-0199 $Lg/5_2_route_$ct.log | tail -1 | sed 's/.*= //; s/.$//')
    ca=$(grep -o "antenna_violations_after=[0-9]*" $Lg/5_2_route_$ct.log | sed 's/.*=//')
    echo "$(date +%H:%M) $ct last DRC count $cl, DRC report lines $(grep -c . $Rp/5_route_drc_$ct.rpt 2>/dev/null), antenna $ca" | tee -a $LOG
    [ -f $R/5_2_route_$ct.odb ] && { chmod a-w $R/5_2_route_$ct.odb; echo "   $(sha256sum $R/5_2_route_$ct.odb | cut -c1-16) 5_2_route_$ct.odb" | tee -a $LOG; }
    if [ "$cl" != "0" ]; then          # the author (10/11): keep going while the rest sits only in the ekPKE corner
      python3 /mnt/d/TKVM_ATTT_2026_test/codeachip_t3/flow_chip/drc_in_corner.py $Rp/5_route_drc_$ct.rpt 20 | tee -a $LOG || { echo "STOP: cleanup $ct left DRC outside the ekPKE corner or more than 20" | tee -a $LOG; break; }
    fi
    in=5_2_route_$ct.odb; after=$ca; lastcl=$cl
  fi
  [ "$after" = "0" ] && { echo "ANTENNA CLEAN at $tag" | tee -a $LOG; break; }
done
echo "$(date +%H:%M) chain end; last clean checkpoint: $in" | tee -a $LOG
