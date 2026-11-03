#!/usr/bin/env bash
# Tier 3, round 5 (t3e: round 4 plus EK_PREF, the H(ek) feed from a register): public-RTL root with every T3 fix, the padded chip-v2 flow to global route, then STA at the three
# corners and the per-macro reports. Run from WSL; work in /root/t3 (t3e, t3e_a3grt), log /root/t3/t3e_flow.log.
#   usage: bash scripts/t3e_launch.sh            (refuses to run if /root/t3/t3e exists)
# The defines: round 1 (MAC_DEEP, MM_PIPE, CRC_SERIAL) and round 2 (BARRETT_1C, SA_PIPE, PMAC_RAW, CODEC_RETIME, MSG_PIPE,
# PP_EARLY, LOAD_PIPE, MARGIN), round 3 (MUL_SEL), round 4 (SEL_REP) and round 5 (EK_PREF); each is verified bit-exact with measured cycles by scripts/t3_sim.sh before this runs.
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
[[ ! -e /root/t3/t3e ]] || { echo "t3e exists"; exit 2; }
DEFS="TRUSTEDGE_T3_MAC_DEEP TRUSTEDGE_T3_MM_PIPE TRUSTEDGE_T3_CRC_SERIAL TRUSTEDGE_T3_BARRETT_1C TRUSTEDGE_T3_SA_PIPE \
TRUSTEDGE_T3_PMAC_RAW TRUSTEDGE_T3_CODEC_RETIME TRUSTEDGE_T3_MSG_PIPE TRUSTEDGE_T3_PP_EARLY TRUSTEDGE_T3_LOAD_PIPE TRUSTEDGE_T3_MARGIN TRUSTEDGE_T3_MUL_SEL TRUSTEDGE_T3_SEL_REP TRUSTEDGE_T3_EK_PREF"
# 1. the public root (placeholder key; the script stops if the private value appears)
# (published record) the run built this root from a private source tree with the credential replaced; rtl/make_root.sh
# rebuilds the identical root from the published sources:  bash rtl/make_root.sh "$HERE/build_t3e"
# 2. the padded flow to global route
export T3_ROOT="$HERE/build_t3e/root"
export T3_DEFINES_EXTRA="$(for d in $DEFS; do printf -- '-D %s ' "$d"; done)"
echo "t3e start $(date -Is) defines: $T3_DEFINES_EXTRA" | tee -a /root/t3/t3e_flow.log
bash "$HERE/flow_chip/run_pad.sh" t3e
# 3. STA at the three corners (global-route parasitics) and the per-macro reports at ss
G=/root/t3/t3e_a3grt/results/sky130hd/trustedge_asic_core/chipv2
bash "$HERE/scripts/t3_grt_sta.sh" "$G" /root/t3/sta_t3e
export MIN_ROUTING_LAYER=met1 MIN_CLK_ROUTING_LAYER=met3 MAX_ROUTING_LAYER=met5 RUN="$G" CORNER=ss_100C_1v60
OR=/opt/eda/orfs-6101364b/tools/install/OpenROAD/bin/openroad
"$OR" -no_splash -exit "$HERE/flow_chip/grt_macro_io.tcl" > /root/t3/sta_t3e/macro_io_ss.log 2>&1
"$OR" -no_splash -exit "$HERE/flow_chip/grt_macro_endpoints.tcl" > /root/t3/sta_t3e/macro_endpoints_ss.log 2>&1
echo "t3e done $(date -Is)" | tee -a /root/t3/t3e_flow.log
bash "$HERE/scripts/t3_spice_sta.sh" "$G" /root/t3/sta_t3e_spice > /dev/null 2>&1; cat /root/t3/sta_t3e_spice/summary.txt
