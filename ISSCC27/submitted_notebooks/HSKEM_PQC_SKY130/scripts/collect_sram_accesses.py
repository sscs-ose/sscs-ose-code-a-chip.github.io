"""Collect the SRAM accesses of one decapsulation from a system-simulation log into results/fullchip/sram_accesses.json.

The log comes from scripts/run_system_sim.sh with an access counter (tb/sram_access_counter.sv, or
tb/sram_access_counter_v2.sv for chip v2) and lists, per macro, the write cycles and the useful accesses (a
write, or a read at a new address) in the decapsulation window. A macro whose chip select is tied active
performs one access in every cycle of the window, a read whenever it does not write; a macro selected by its
block's requests (the v2 counter prints its accesses) performs only those.

usage: python3 collect_sram_accesses.py <simulation log> <out.json>
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import json
import re
import sys

# the SRAM master of each macro instance of the chip (path below u_common)
MASTER = {
    "u_c3_pk_pair_sram": "sky130_sram_1rw_24x256",
    "u_mlkem512_decaps_partial.u_ciphertext_ref_sram": "sky130_sram_1rw_8x768",
    "u_mlkem512_decaps_partial.u_product_pair_sram": "sky130_sram_1rw_24x128",
    "u_mlkem512_encaps_partial.u_codec.u_ciphertext_sram": "sky130_sram_1rw_8x768",
    "u_mlkem512_encaps_partial.u_codec.u_coeff_sram": "sky130_sram_1rw_12x768_wpr8",
    "u_mlkem512_encaps_partial.u_codec.u_decoded_coeff_sram": "sky130_sram_1rw_12x768_wpr8",
    "u_mlkem512_encaps_partial.u_noise_even_sram": "sky130_sram_1rw_12x640_wpr8",
    "u_mlkem512_encaps_partial.u_noise_odd_sram": "sky130_sram_1rw_12x640_wpr8",
    "u_mlkem512_kpke_partial.u_matrix_mac.u_dkpke_pair_sram": "sky130_sram_1rw_24x256",
    "u_mlkem512_kpke_partial.u_matrix_mac.u_ekpke_pair_sram": "sky130_sram_1rw_24x256",
    "u_mlkem512_kpke_partial.u_matrix_mac.u_error_even_sram": "sky130_sram_1rw_12x256_wpr8",
    "u_mlkem512_kpke_partial.u_matrix_mac.u_error_odd_sram": "sky130_sram_1rw_12x256_wpr8",
    "u_mlkem512_kpke_partial.u_matrix_mac.u_matrix_even_sram": "sky130_sram_1rw_12x512_wpr8",
    "u_mlkem512_kpke_partial.u_matrix_mac.u_matrix_odd_sram": "sky130_sram_1rw_12x512_wpr8",
    "u_mlkem512_kpke_partial.u_matrix_mac.u_noise_byte_sram": "sky130_sram_1rw_8x768",
    "u_mlkem512_kpke_partial.u_matrix_mac.u_secret_even_sram": "sky130_sram_1rw_12x256_wpr8",
    "u_mlkem512_kpke_partial.u_matrix_mac.u_secret_odd_sram": "sky130_sram_1rw_12x256_wpr8",
    "u_shared_ntt.u_sram": "sky130_sram_1rw_24x128",          # chip v2: the NTT engine's pair store
    "u_shared_ntt.u_coeff_ram": "sky130_sram_1rw_16x256_wpr8",  # the original chip's NTT store
}


def main(log: str, out: str) -> None:
    text = open(log, encoding="utf-8", errors="replace").read()
    window = int(re.search(r"SRAM_WINDOW cycles=(\d+)", text)[1])
    inst = {}
    for m in re.finditer(r"SRAM_ACCESS (\S+) writes=(\d+) useful=(\d+)(?: accesses=(\d+))?", text):
        path, writes, useful, acc = m[1], int(m[2]), int(m[3]), m[4]
        selected = acc is not None
        accesses = int(acc) if selected else window
        inst[path] = {"master": MASTER[path], "chip_select": "block requests" if selected else "tied active",
                      "writes": writes, "reads": accesses - writes, "useful_accesses": useful}
    if len(inst) != 18:
        raise SystemExit(f"expected 18 macros, found {len(inst)}")
    res = {"window_cycles": window,
           "window": "the first profiled decapsulation, from its second busy cycle (same window as the power estimate)",
           "note": "a macro whose chip select is tied active performs one access per cycle: a write in the counted "
                   "cycles, a read in all others; a macro selected by its block's requests performs only those; "
                   "useful_accesses counts the cycles with a write or a read at a new address, the accesses a "
                   "chip-select gate would have to keep",
           "instances": inst}
    open(out, "w").write(json.dumps(res, indent=1) + "\n")
    tied = sum(1 for v in inst.values() if v["chip_select"] == "tied active")
    print(f"window {window} cycles; {tied} macros tied active, {18 - tied} selected by requests; "
          f"accesses {sum(v['reads'] + v['writes'] for v in inst.values())}, "
          f"useful {sum(v['useful_accesses'] for v in inst.values())}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
