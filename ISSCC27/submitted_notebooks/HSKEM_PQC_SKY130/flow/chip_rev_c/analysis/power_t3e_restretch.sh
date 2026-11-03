#!/usr/bin/env bash
# (18/10) one-off: the first rev B power run wrote shadow0.vcd without the x4 time stretch; stretch it in place
# (its first timestamp is already 0) and rerun the power stage of fullchip_power_t3e.sh.
set -euo pipefail
W=/mnt/c/chipv2_signoff/power_t3e CAC=/mnt/d/TKVM_ATTT_2026_test/codeachip_t3
python3 "${CAC}/scripts/vcd_shift.py" "${W}/shadow0.vcd" "${W}/shadow0x4.vcd" 4
mv "${W}/shadow0x4.vcd" "${W}/shadow0.vcd"
tail -3 "${W}/shadow0.vcd" | head -1
bash /mnt/d/TKVM_ATTT_2026_test/chip_v2/fullchip_power_t3e.sh power
