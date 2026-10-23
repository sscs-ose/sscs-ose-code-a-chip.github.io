#!/usr/bin/env bash
# System simulation of the chip configuration of this clone (the defines of fullchip_power.sh plus the extras given).
# usage: scripts/t3_sim.sh <tag> [extra defines]      log: results/system_sim/tb_trustedge_spi_sram_only_<tag>.log
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="$HOME/colabtest/oss-cad-suite/bin:$PATH"
eval "$(sed -n '/^H="-DTRUSTEDGE_PACKED_NTT/,/^H="\$H -DTRUSTEDGE_PRF_TO_NTT/p' "$ROOT/scripts/fullchip_power.sh" 2>/dev/null)"
[ -n "${H:-}" ] || { echo "no defines"; exit 2; }
TAG="${1:?tag}"; shift
CAC_PACKED_SYSTEM=1 CAC_SIM_TAG="_$TAG" CAC_EXTRA_DEFS="$H -DTRUSTEDGE_PMAC_RETIME -DTRUSTEDGE_SO_PIPE $*" \
  bash "$ROOT/scripts/run_system_sim.sh" sram_only
