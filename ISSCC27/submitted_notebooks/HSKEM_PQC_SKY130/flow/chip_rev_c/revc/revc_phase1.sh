#!/usr/bin/env bash
# Rev C, phase 1: the rev B recipe (codeachip_t3/flow_chip, as recorded in codeachip/flow/chip_rev_b) on the rev C
# root: synthesis to CTS with the padded flow, global route with antenna jumpers, then STA at three corners with
# global-route parasitics and the SPICE-measured macro views.  Defines: rev B's (config.mk + 14 T3) + TRUSTEDGE_REVC.
# Work: /root/t3/revc1 and /root/t3/revc1_a3grt; log /root/t3/revc1_flow.log.  Refuses to overwrite.
set -euo pipefail
ROOT=/mnt/d/TKVM_ATTT_2026_test; FC="$ROOT/codeachip_t3/flow_chip"; TAG=revc1
[[ ! -e /root/t3/$TAG ]] || { echo "$TAG exists"; exit 2; }
DEFS="TRUSTEDGE_T3_MAC_DEEP TRUSTEDGE_T3_MM_PIPE TRUSTEDGE_T3_CRC_SERIAL TRUSTEDGE_T3_BARRETT_1C TRUSTEDGE_T3_SA_PIPE \
TRUSTEDGE_T3_PMAC_RAW TRUSTEDGE_T3_CODEC_RETIME TRUSTEDGE_T3_MSG_PIPE TRUSTEDGE_T3_PP_EARLY TRUSTEDGE_T3_LOAD_PIPE \
TRUSTEDGE_T3_MARGIN TRUSTEDGE_T3_MUL_SEL TRUSTEDGE_T3_SEL_REP TRUSTEDGE_T3_EK_PREF TRUSTEDGE_REVC"
export T3_ROOT="$ROOT/hskem_revc/revc/root"
export T3_DEFINES_EXTRA="$(for d in $DEFS; do printf -- '-D %s ' "$d"; done)"
# the root must be rev B's root plus the rev C edits only
( cd "$ROOT/hskem_revc" && diff -rq base/root revc/root | sort || true ) | tee /root/t3/${TAG}_root_diff.txt
echo "$TAG start $(date -Is) defines: $T3_DEFINES_EXTRA" | tee -a /root/t3/${TAG}_flow.log
bash "$FC/run_pad.sh" $TAG
G=/root/t3/${TAG}_a3grt/results/sky130hd/trustedge_asic_core/chipv2
bash "$ROOT/codeachip_t3/scripts/t3_grt_sta.sh" "$G" /root/t3/sta_$TAG
echo "$TAG grt+sta done $(date -Is)" | tee -a /root/t3/${TAG}_flow.log
bash "$ROOT/codeachip_t3/scripts/t3_spice_sta.sh" "$G" /root/t3/sta_${TAG}_spice > /dev/null 2>&1; cat /root/t3/sta_${TAG}_spice/summary.txt
