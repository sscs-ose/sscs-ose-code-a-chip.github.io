#!/usr/bin/env bash
# SRAM accesses of one decapsulation on HSKEM-2 rev B (t3e w1): the system simulation of fullchip_power_t3e.sh
# (same sources, same defines: chip configuration + the 14 tier-3 defines) with tb/sram_access_counter_v2.sv as
# an extra top level, then collect_sram_accesses.py and sram_energy_model.py as for rev A.
set -euo pipefail
readonly ROOT=/mnt/d/TKVM_ATTT_2026_test CAC=/mnt/d/TKVM_ATTT_2026_test/codeachip_t3
readonly W=/mnt/c/chipv2_signoff/power_t3e SRC=/mnt/c/chipv2_signoff/power_t3e/hskem_rtl
readonly STAGE="${ROOT}/chip_v2/signoff/fullchip_stage_t3e" O=/root/sram_access_t3e
mkdir -p "${O}"
DEFS=$(sed -n '/^H="-DTRUSTEDGE_PACKED_NTT/,/^for d in MAC_DEEP/p' "${ROOT}/chip_v2/fullchip_power_t3e.sh" > "${O}/defs.sh"; \
       echo 'echo "$DEFS"' >> "${O}/defs.sh"; bash "${O}/defs.sh")
echo "defines: $(echo ${DEFS} | wc -w)"
F=$(sed -n '/^F=(/,/)$/p' "${CAC}/scripts/run_system_sim.sh" | tr -d '()"' | sed 's/^F=//; s#\${CAC_TB:-sim/tb/tb_trustedge_spi.sv}#sim/tb/tb_trustedge_spi.sv#')
F="$F rtl/kyber/barrett_reduce_1c.v rtl/kyber/kyber_ntt_engine_packed.sv rtl/kyber/kyber_ntt_engine_packed2.sv"
[[ -f "${O}/tb.vvp" ]] || (cd "${SRC}" && iverilog -g2012 -I rtl/kyber ${DEFS} -s tb_trustedge_spi -s sram_access_counter -o "${O}/tb.vvp" \
    ${F} "${CAC}/tb/sram_access_counter_v2.sv") > "${O}/compile.log" 2>&1 || { tail -20 "${O}/compile.log"; exit 2; }
(cd "${CAC}/results/system_sim" && vvp -n "${O}/tb.vvp" +skip=1 > "${O}/sim.log" 2>&1) || true
grep -E "SRAM_|TB_TRUSTEDGE_SPI_RESULT|U1 Decaps" "${O}/sim.log" | head -40
python3 "${CAC}/scripts/collect_sram_accesses.py" "${O}/sim.log" "${STAGE}/sram_accesses.json"
python3 "${CAC}/scripts/sram_energy_model.py" "${ROOT}/codeachip/results/fullchip/sram_macro_spice.json" "${STAGE}/sram_accesses.json" \
    "${STAGE}/sram_energy.json" | tail -5
