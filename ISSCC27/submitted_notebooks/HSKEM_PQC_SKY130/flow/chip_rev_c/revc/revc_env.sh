# Rev C environment for the rev B scripts of codeachip_t3/flow_chip (source it): root, defines, patched OpenROAD.
ROOT=/mnt/d/TKVM_ATTT_2026_test
FC=$ROOT/codeachip_t3/flow_chip
W=${REVC_W:-/root/t3/revc1_a3grt}; D=sky130hd/trustedge_asic_core/chipv2; R=$W/results/$D; Lg=$W/logs/$D; Rp=$W/reports/$D
DEFS="TRUSTEDGE_T3_MAC_DEEP TRUSTEDGE_T3_MM_PIPE TRUSTEDGE_T3_CRC_SERIAL TRUSTEDGE_T3_BARRETT_1C TRUSTEDGE_T3_SA_PIPE TRUSTEDGE_T3_PMAC_RAW TRUSTEDGE_T3_CODEC_RETIME TRUSTEDGE_T3_MSG_PIPE TRUSTEDGE_T3_PP_EARLY TRUSTEDGE_T3_LOAD_PIPE TRUSTEDGE_T3_MARGIN TRUSTEDGE_T3_MUL_SEL TRUSTEDGE_T3_SEL_REP TRUSTEDGE_T3_EK_PREF TRUSTEDGE_REVC"
export T3_ROOT="$ROOT/hskem_revc/revc/root"
export T3_DEFINES_EXTRA="$(for d in $DEFS; do printf -- "-D %s " "$d"; done)"
export OPENROAD_EXE=/opt/eda/openroad-t3patch/bin/openroad CHIPV2_DRT_END_ITER=20
export CHIPV2_CDL_MASTERS=$ROOT/hskem_revc/flow/sky130hd_with_openram_masters_v3.cdl   # rebuilt from rev B 6_final_concat.cdl minus 6_final.cdl (byte prefix match)
SS=$(ls /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib)
FF=$(ls /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ff_n40C_1v95.lib)
