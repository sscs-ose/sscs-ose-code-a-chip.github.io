#!/usr/bin/env bash
# Top-level integration LVS of chip v2, ported from the old chip's reviewed chain (asic/run_a3_rcx0114_lvs_run8
# .. run17): the same steps and per-object guards, with the old chip's fixed counts replaced by counts derived
# from the chip v2 reference netlist. The SRAM macros are LEF pin frames here; each SRAM master has its own
# independent transistor-level LVS (checked below). Scratch goes to drive C (drive D is nearly full and also
# holds the WSL disk image).
#
# usage: lvs_v2.sh <final dir> <work dir> <stage>
#   <final dir>: a parked final (results/6_final.gds, 6_final.def; objects/6_final_concat.cdl)
#   stages, in order:
#     extract   reference filter + CONB normalization + audit, SRAM pin frames, KLayout extraction (L2N, CDL)
#     prepare   top-pin probe, pin-object repair, name restore, SRAM pin order, top/power normalization,
#               name-independent and DEF-mapped topology audits (must show no merged or split net)
#     compare   Netgen compare; if only standard cells mismatch, truth-table audit of those cells,
#               abstraction of the proven cells, and a second compare
#     evidence  negative control (one mutated reference net must fail) and a repeat compare
set -euo pipefail
readonly FINAL="${1:?final dir}" WORK="${2:?work dir}" STAGE="${3:?stage}"
readonly ROOT=/mnt/d/TKVM_ATTT_2026_test
readonly L="${ROOT}/chip_v2/lvs"
readonly ORFS=/opt/eda/orfs-6101364b
readonly NETGEN=/opt/eda/netgen-vlsi/install/bin/netgen
readonly GDS="${FINAL}/results/6_final.gds" DEF="${FINAL}/results/6_final.def"
readonly CDL="${FINAL}/objects/6_final_concat.cdl"
readonly TOP=trustedge_asic_core
readonly -a SRAMS=(sky130_sram_1rw_24x256 sky130_sram_1rw_24x128 sky130_sram_1rw_8x768 sky130_sram_1rw_12x256_wpr8
  sky130_sram_1rw_12x512_wpr8 sky130_sram_1rw_12x640_wpr8 sky130_sram_1rw_12x768_wpr8)
readonly -a SRAM_DIRS=(
  /opt/eda/openram-smoke/sky130_sram_1rw_24x256_vdd_via_column_mux_candidate
  /opt/eda/openram-smoke/sky130_sram_1rw_24x128_vdd_via_column_mux_candidate
  /opt/eda/openram-smoke/sky130_sram_1rw_8x768_vdd_via_column_mux_candidate
  /opt/eda/openram-smoke/sky130_sram_1rw_12x256_wpr8_candidate
  /opt/eda/openram-smoke/sky130_sram_1rw_12x512_wpr8_candidate
  /opt/eda/openram-smoke/sky130_sram_1rw_12x640_wpr8_candidate
  /opt/eda/openram-smoke/sky130_sram_1rw_12x768_wpr8_candidate)
SRAM_CSV="$(IFS=,; echo "${SRAMS[*]}")"
readonly SRAM_CSV
mkdir -p "${WORK}"
readonly LOG="${WORK}/lvs_${STAGE}.log"
exec > >(tee -a "${LOG}") 2>&1
echo "CHIPV2_LVS_STAGE=${STAGE} start=$(date -Is) final=${FINAL} work=${WORK}"
step() { echo "CHIPV2_LVS_STEP $1 $(date -Is)"; }
stat_of() { grep -m1 "^$2=" "$1" | cut -d= -f2; }
# LVS_ALLOW_PARALLEL=1 lets a stage run beside another KLayout/Netgen job (2026-10-05: the prepare stage of
# final #6 beside the extraction of final #7, about 6 GB each); OpenROAD always blocks
no_tools_running() {
  ! pgrep -x openroad >/dev/null || return 1
  [[ "${LVS_ALLOW_PARALLEL:-0}" == 1 ]] && return 0
  ! pgrep -x klayout >/dev/null && ! pgrep -x netgenexec >/dev/null
}
disk_gate() {
  (( $(df -Pk /mnt/c | awk 'NR==2 {print $4}') >= 15*1024*1024 )) || { echo "CHIPV2_LVS_GATE=FAIL drive C below 15 GB"; exit 5; }
  (( $(df -Pk /mnt/d | awk 'NR==2 {print $4}') >= 5*1024*1024 )) || { echo "CHIPV2_LVS_GATE=FAIL drive D below 5 GB"; exit 5; }
}
netgen_compare() {  # <layout> <reference> <outdir>
  local out="$3"; mkdir -p "${out}"
  # Netgen picks the reader from the file name and does not know .cdl: link the inputs as .spice
  ln -sfn "$1" "${out}/layout.spice"; ln -sfn "$2" "${out}/reference.spice"
  set +e
  "${NETGEN}" -batch lvs "${out}/layout.spice ${TOP}" "${out}/reference.spice ${TOP}" "${L}/netgen_setup.tcl" \
    "${out}/netgen_lvs.log" -blackbox \
    > "${out}/console.log" 2> "${out}/console.err.log"
  local rc=$?
  set -e
  [[ -s "${out}/netgen_lvs.log" ]] || { echo "CHIPV2_LVS_NETGEN=NO_LOG rc=${rc} (see ${out}/console.err.log)"; exit 8; }
  echo "${rc}" > "${out}/netgen_exit_code"
  awk '/^Final result:/{c=1; o=$0 ORS; next} c {o=o $0 ORS} END{printf "%s",o}' "${out}/netgen_lvs.log" > "${out}/final_result.txt"
  sha256sum "${out}"/netgen_lvs.log "${out}"/final_result.txt > "${out}/OUTPUT_SHA256SUMS.txt"
  if [[ ${rc} -eq 0 && -s "${out}/final_result.txt" ]] \
     && grep -Eqi 'match(es)? uniquely|netlists match|circuits match' "${out}/final_result.txt" \
     && ! grep -Eqi 'fail|error|mismatch|do not match|not checked|property errors' "${out}/final_result.txt" \
     && ! grep -Eqi 'error (in|sourcing).*setup|unable to permute model' "${out}/console.log" "${out}/console.err.log"; then
    echo PASS > "${out}/result"; return 0
  fi
  echo FAIL > "${out}/result"; return 1
}

case "${STAGE}" in
extract)
  no_tools_running; disk_gate
  [[ "$(klayout -v 2>&1)" == "KLayout 0.30.7" ]]
  for f in "${GDS}" "${CDL}" "${DEF}"; do [[ -s "${f}" ]]; done
  [[ ! -e "${WORK}/6_lvs_extracted.cdl" ]] || { echo "CHIPV2_LVS_GATE=FAIL extraction exists"; exit 2; }
  step MACRO_LVS_CHECK
  for i in "${!SRAMS[@]}"; do
    m="${SRAMS[i]}"; d="${SRAM_DIRS[i]}"
    [[ -s "${d}/${m}.lef" && -s "${d}/${m}.gds" ]]
    grep -Fq 'Circuits match uniquely.' "${d}/${m}.independent.lvs.log"
    grep -Eq 'Finished \(0\) LVS using Netgen' "${d}/${m}.independent.lvs.log"
    sha256sum "${d}/${m}.lef" "${d}/${m}.gds" "${d}/${m}.independent.lvs.log"
  done > "${WORK}/macro_lvs_inputs.sha256"
  echo "macro_lvs_pass=${#SRAMS[@]}"
  sha256sum "${GDS}" "${CDL}" "${DEF}" > "${WORK}/INPUT_SHA256SUMS.txt"
  step REFERENCE
  python3 "${L}/filter_cdl.py" "${CDL}" "${WORK}/reference_filtered.cdl" "${WORK}/filter_stats.txt"
  python3 "${L}/normalize_conb.py" "${WORK}/reference_filtered.cdl" "${WORK}/reference_conb.cdl" "${WORK}/conb_stats.txt"
  retained=$(stat_of "${WORK}/filter_stats.txt" retained_top_instances)
  klayout -b -r "${L}/reference.rb" -rd cdl="${WORK}/reference_filtered.cdl" -rd stats="${WORK}/reference_stats.txt" \
    -rd masters="${SRAM_CSV}" -rd expected_top="${retained}"
  grep -Fxq CHIPV2_LVS_REFERENCE=PASS "${WORK}/reference_stats.txt"
  step SRAM_PIN_FRAMES
  spec=""
  for i in "${!SRAMS[@]}"; do spec="${spec:+${spec};}${SRAMS[i]}=${SRAM_DIRS[i]}/${SRAMS[i]}.lef"; done
  klayout -b -r "${L}/abstract.rb" -rd input_gds="${GDS}" -rd output_gds="${WORK}/6_final_abstract.gds" \
    -rd manifest="${WORK}/abstract_manifest.txt" -rd macro_spec="${spec}" \
    -rd reference_cdl="${WORK}/reference_filtered.cdl" -rd sram_instances="$(stat_of "${WORK}/reference_stats.txt" sram_instances)"
  grep -Fxq CHIPV2_LVS_ABSTRACT=PASS "${WORK}/abstract_manifest.txt"
  python3 "${L}/make_deck.py" "${ORFS}/flow/platforms/sky130hd/lvs/sky130hd.lylvs" "${WORK}/extract.lylvs" 8
  grep -Fq write_l2n "${WORK}/extract.lylvs"
  step EXTRACTION
  klayout -b -rd in_gds="${WORK}/6_final_abstract.gds" -rd cdl_file="${WORK}/reference_filtered.cdl" \
    -rd extracted_cdl="${WORK}/6_lvs_extracted.cdl" -rd l2n_file="${WORK}/6_lvs.l2n" -r "${WORK}/extract.lylvs" \
    2>&1 | tee "${WORK}/extract_klayout.log"
  [[ ${PIPESTATUS[0]} -eq 0 ]] && grep -Fq A3_RUN8_PHASE=CHECKPOINT_WRITTEN "${WORK}/extract_klayout.log"
  sha256sum "${WORK}"/reference_filtered.cdl "${WORK}"/reference_conb.cdl "${WORK}"/6_final_abstract.gds \
    "${WORK}"/6_lvs_extracted.cdl "${WORK}"/6_lvs.l2n > "${WORK}/EXTRACT_SHA256SUMS.txt"
  ;;
prepare)
  no_tools_running; disk_gate
  sha256sum -c --quiet "${WORK}/EXTRACT_SHA256SUMS.txt"
  REF="${WORK}/reference_conb.cdl"
  step TOP_PIN_PROBE
  klayout -b -r "${L}/pin_activity.rb" -rd reference_cdl="${REF}" > "${WORK}/reference_top_pin_activity.txt"
  active=$(grep -o 'ACTIVITY=PASS|active=[0-9]*' "${WORK}/reference_top_pin_activity.txt" | cut -d= -f3)
  klayout -b -r "${L}/label_probe.rb" -rd l2n="${WORK}/6_lvs.l2n" -rd gds="${GDS}" -rd reference_cdl="${REF}" \
    -rd expected_active="${active}" > "${WORK}/gds_label_probe.txt"
  grep -Fxq A3_RUN10_GDS_LABEL_PROBE_L2N=PASS "${WORK}/gds_label_probe.txt"
  step LOGICAL_CONTRACT
  awk '
    function physical_only(model) { return model ~ /^VIA_/ || model ~ /^via_/ || model ~ /^sky130_fd_sc_hd__fill_/ || model == "sky130_fd_sc_hd__tapvpwrvgnd_1" || model == "sky130_fd_sc_hd__diode_2" || model == "sky130_fd_sc_hd__conb_1" }
    function flush_instance() { if (instance != "" && !physical_only(model)) printf "%s", instance; instance=""; model="" }
    /^X/ { flush_instance(); instance=$0 ORS; model=$NF; next }
    instance != "" && /^\+/ { instance=instance $0 ORS; model=$NF; next }
    { flush_instance(); print }
    END { flush_instance() }
  ' "${WORK}/6_lvs_extracted.cdl" > "${WORK}/layout_contract.cdl"
  ref_top=$(sed -n "1,/^\.ENDS ${TOP}\$/p" "${REF}" | grep -c '^X' || true)
  contract_top=$(sed -n "1,/^\.ENDS ${TOP}\$/p" "${WORK}/layout_contract.cdl" | grep -c '^X' || true)
  echo "reference_top_instances=${ref_top} layout_contract_top_instances=${contract_top}"
  [[ "${ref_top}" -gt 0 && "${ref_top}" == "${contract_top}" ]]
  export CHIPV2_LVS_TOP_INSTANCES="${ref_top}" CHIPV2_LVS_SRAMS="${SRAM_CSV}"
  export CHIPV2_LVS_SRAM_INSTANCES="$(stat_of "${WORK}/reference_stats.txt" sram_instances)"
  step PIN_OBJECT_REPAIR
  klayout -b -r "${L}/repair_pin_objects.rb" -rd l2n="${WORK}/6_lvs.l2n" -rd gds="${GDS}" \
    -rd layout_cdl="${WORK}/layout_contract.cdl" -rd reference_cdl="${REF}" -rd srams="${SRAM_CSV}" \
    -rd sram_instances="${CHIPV2_LVS_SRAM_INSTANCES}" \
    -rd output_cdl="${WORK}/layout_raw_net_objects.cdl" -rd output_manifest="${WORK}/net_object_manifest.txt"
  grep -Fxq A3_RUN15_NET_OBJECT_REPAIR=PASS "${WORK}/net_object_manifest.txt"
  step NORMALIZE
  python3 "${L}/restore_writer_net_names.py" --input "${WORK}/layout_raw_net_objects.cdl" --output "${WORK}/layout_raw_named.cdl"
  python3 "${L}/align_sram_pin_order.py" --layout "${WORK}/layout_raw_named.cdl" --reference "${REF}" \
    --output "${WORK}/layout_raw_sram_aligned.cdl"
  awk '
    function physical_only(model) { return model ~ /^VIA_/ || model ~ /^via_/ || model ~ /^sky130_fd_sc_hd__fill_/ || model == "sky130_fd_sc_hd__tapvpwrvgnd_1" || model == "sky130_fd_sc_hd__diode_2" || model == "sky130_fd_sc_hd__conb_1" }
    function flush_instance() { if (instance != "" && !physical_only(model)) printf "%s", instance; instance=""; model="" }
    /^X/ { flush_instance(); instance=$0 ORS; model=$NF; next }
    instance != "" && /^\+/ { instance=instance $0 ORS; model=$NF; next }
    { flush_instance(); print }
    END { flush_instance() }
  ' "${WORK}/layout_raw_sram_aligned.cdl" > "${WORK}/layout_logical_only.cdl"
  python3 "${L}/normalize_top.py" --layout "${WORK}/layout_logical_only.cdl" --reference "${REF}" \
    --probe "${WORK}/gds_label_probe.txt" --activity "${WORK}/reference_top_pin_activity.txt" \
    --layout-out "${WORK}/layout_top_normalized.cdl" --reference-out "${WORK}/reference_active_ports.cdl" \
    --manifest "${WORK}/top_normalization_manifest.txt"
  python3 "${L}/normalize_power.py" --layout "${WORK}/layout_top_normalized.cdl" \
    --reference "${WORK}/reference_active_ports.cdl" --layout-out "${WORK}/layout_ready.cdl" \
    --reference-out "${WORK}/reference_ready.cdl" --manifest "${WORK}/power_normalization_manifest.txt"
  step TOPOLOGY_AUDIT
  python3 "${L}/topology_audit.py" --layout "${WORK}/layout_ready.cdl" --reference "${WORK}/reference_ready.cdl" \
    --limit 20 > "${WORK}/topology_audit.txt"
  # The extraction names instances X$n and the reference keeps the real names, so this name-independent
  # audit cannot pair instances (common_instance_name_count=0) and prints no merged/split-net counts; the
  # DEF-mapped audit below pairs every instance by its exact placement and gates merges and splits.
  for gate in "layout_top_instances=${ref_top}" "reference_top_instances=${ref_top}" \
    'model_mismatch_count=0' 'pin_set_mismatch_count=0' \
    'model_count_mismatch_count=0' 'used_model_header_pin_set_mismatch_count=0' \
    'net_signature_multiset_equal=1' 'layout_only_signature_instances=0' 'reference_only_signature_instances=0' \
    'one_ended_endpoint_count_delta=0' 'VDD_signature_equal=1' 'VSS_signature_equal=1'; do
    grep -Fxq "${gate}" "${WORK}/topology_audit.txt" || { echo "CHIPV2_LVS_TOPOLOGY_GATE=FAIL ${gate}"; exit 6; }
  done
  lefs=(--lef "${ORFS}/flow/platforms/sky130hd/lef/sky130_fd_sc_hd_merged.lef")
  for i in "${!SRAMS[@]}"; do lefs+=(--lef "${SRAM_DIRS[i]}/${SRAMS[i]}.lef"); done
  python3 "${L}/topology_audit.py" --layout "${WORK}/layout_ready.cdl" --reference "${WORK}/reference_ready.cdl" \
    --def-file "${DEF}" --layout-contract "${WORK}/layout_contract.cdl" "${lefs[@]}" \
    --mapped-report "${WORK}/def_mapped_topology_review.json" --limit 5 > "${WORK}/def_mapped_audit.txt"
  python3 - "${WORK}/def_mapped_topology_review.json" "${ref_top}" > "${WORK}/exact_topology_gate.txt" <<'PY'
import json, sys
r = json.load(open(sys.argv[1], encoding="utf-8")); n = int(sys.argv[2])
checks = {
    "status": r.get("status") == "MATCHED_TOPOLOGY",
    "mapped_instance_count": r.get("mapped_instance_count") == n,
    "layout_merged_net_count": len(r.get("layout_merged_nets", {})) == 0,
    "reference_split_net_count": len(r.get("reference_split_nets", {})) == 0,
    "differing_endpoint_count": len(r.get("differing_endpoints", [])) == 0,
    "one_ended_on_differing_net_count": len(r.get("one_ended_on_differing_nets", [])) == 0,
}
for k, v in checks.items():
    print(f"{k}={int(v)}")
print(f"paired_endpoint_count={r.get('paired_endpoint_count')}")
if not all(checks.values()):
    raise SystemExit("exact DEF-mapped topology gate failed")
print("CHIPV2_LVS_EXACT_TOPOLOGY_GATE=PASS")
PY
  sha256sum "${WORK}"/layout_ready.cdl "${WORK}"/reference_ready.cdl "${WORK}"/net_object_manifest.txt \
    "${WORK}"/top_normalization_manifest.txt "${WORK}"/power_normalization_manifest.txt \
    "${WORK}"/topology_audit.txt "${WORK}"/def_mapped_topology_review.json "${WORK}"/exact_topology_gate.txt \
    > "${WORK}/PREPARED_SHA256SUMS.txt"
  ;;
compare)
  no_tools_running
  sha256sum -c --quiet "${WORK}/PREPARED_SHA256SUMS.txt"
  grep -Fxq CHIPV2_LVS_EXACT_TOPOLOGY_GATE=PASS "${WORK}/exact_topology_gate.txt"
  step NETGEN_COMPARE1
  if netgen_compare "${WORK}/layout_ready.cdl" "${WORK}/reference_ready.cdl" "${WORK}/compare1"; then
    cp "${WORK}/layout_ready.cdl" "${WORK}/layout_final.cdl"; cp "${WORK}/reference_ready.cdl" "${WORK}/reference_final.cdl"
    echo compare1 > "${WORK}/primary_compare"
  else
    step CELL_TRUTH_TABLE_AUDIT
    python3 "${L}/cell_equivalence_audit.py" --layout "${WORK}/layout_ready.cdl" --reference "${WORK}/reference_ready.cdl" \
      --console "${WORK}/compare1/netgen_lvs.log" --output "${WORK}/multifinger_cell_audit.txt"
    python3 "${L}/prepare_verified_abstractions.py" --layout "${WORK}/layout_ready.cdl" \
      --reference "${WORK}/reference_ready.cdl" --audit "${WORK}/multifinger_cell_audit.txt" \
      --layout-out "${WORK}/layout_final.cdl" --reference-out "${WORK}/reference_final.cdl" \
      --manifest "${WORK}/abstraction_manifest.txt"
    step NETGEN_COMPARE2
    netgen_compare "${WORK}/layout_final.cdl" "${WORK}/reference_final.cdl" "${WORK}/compare2"
    echo compare2 > "${WORK}/primary_compare"
  fi
  sha256sum "${WORK}"/layout_final.cdl "${WORK}"/reference_final.cdl > "${WORK}/FINAL_NETLISTS_SHA256SUMS.txt"
  echo "CHIPV2_LVS_COMPARE=PASS primary=$(cat "${WORK}/primary_compare")"
  ;;
evidence)
  no_tools_running
  sha256sum -c --quiet "${WORK}/FINAL_NETLISTS_SHA256SUMS.txt"
  step NEGATIVE_CONTROL
  mkdir -p "${WORK}/negative"
  # rename one net on one reference top instance; the compare must fail
  awk -v top="${TOP}" '
    $1 == ".SUBCKT" && $2 == top { intop=1; print; next }
    intop && !done && /^X/ && NF > 4 { $2="__LVS_NEGATIVE_CONTROL_NET__"; done=1 }
    { print }' "${WORK}/reference_final.cdl" > "${WORK}/negative/reference_mutated.cdl"
  ! cmp -s "${WORK}/reference_final.cdl" "${WORK}/negative/reference_mutated.cdl"
  [[ "$(grep -Fc __LVS_NEGATIVE_CONTROL_NET__ "${WORK}/negative/reference_mutated.cdl")" == 1 ]]
  if netgen_compare "${WORK}/layout_final.cdl" "${WORK}/negative/reference_mutated.cdl" "${WORK}/negative"; then
    echo "CHIPV2_LVS_NEGATIVE_CONTROL=FAIL (mutation not detected)"; exit 7
  fi
  echo "CHIPV2_LVS_NEGATIVE_CONTROL=PASS"
  step REPEAT_COMPARE
  netgen_compare "${WORK}/layout_final.cdl" "${WORK}/reference_final.cdl" "${WORK}/repeat"
  cmp -s "${WORK}/$(cat "${WORK}/primary_compare")/final_result.txt" "${WORK}/repeat/final_result.txt"
  echo "CHIPV2_LVS_REPEAT=PASS"
  ;;
*) echo "unknown stage ${STAGE}"; exit 64 ;;
esac
echo "CHIPV2_LVS_STAGE_DONE=${STAGE} rc=0 end=$(date -Is)"
