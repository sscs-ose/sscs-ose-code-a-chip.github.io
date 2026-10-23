"""Summarize the full-system simulations of the streamed system (scripts/run_streamed_system.sh).

Reads results/system_sim/tb_trustedge_spi_<config>_str<milestone>.log for the four cumulative milestones
E, F, G and H of scripts/make_packed_system.py in the configurations sram_only, fpga and asic, and writes
results/system_sim/streamed_system.json with, for each build, the testbench verdict (which includes the
testbench's exact cycle model), the decapsulation latency for a valid and an implicitly rejected ciphertext,
the packed engine's write-contract check, the cycle profile and the time in each FSM state (the same fields
as packed_system.json), the runtime encryption's latency and the length of J(z||c).

It checks that every build passes, that valid and rejected ciphertexts take equally long, that no write
breaks the engine's contract, and that the FPGA configuration takes exactly as long as the single-port one
with the one-round Keccak (the two stores differ in ports, not in the schedule).

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import json
import re

import collect_packed_system as cps

MILESTONES = {
    "E": "the datapath moves one element per cycle",
    "F": "E + a two-lane engine and data in pairs",
    "G": "F + pipelined checks and products",
    "H": "G + data streaming between the engine and the datapath",
}
CONFIG_NOTE = {"sram_only": "single-port SRAM store, one-round Keccak",
               "fpga": "dual-port FPGA store, one-round Keccak",
               "asic": "single-port SRAM store, row-serialized Keccak (the chip's configuration)"}


def main() -> None:
    dn, en = cps.state_names()
    out = {"source": "run_system_sim.sh with CAC_PACKED_SYSTEM=1 and the defines of run_streamed_system.sh; "
                     "tb/decaps_profiler.sv, tb/decaps_state_profiler.sv, tb/ntt_packed_checker.sv, "
                     "tb/j_phase_probe.sv",
           "milestones": MILESTONES, "configs": {}}
    for m, desc in MILESTONES.items():
        for cfg, note in CONFIG_NOTE.items():
            tag = f"{cfg}_str{m}"
            cps.CONFIGS[tag] = (cfg, f"{m}: {desc} ({note})")
            v = cps.parse(tag, dn, en)
            log = (cps.D / f"tb_trustedge_spi_{tag}.log").read_text(errors="replace")
            enc = re.search(r"PASS runtime_encrypt_bound_keygen_spi .*?cycles=(\d+)", log)
            j = sorted({int(x) for x in re.findall(r"J_PHASE cycles=(\d+)", log)})
            v["runtime_encrypt_cycles"] = int(enc[1]) if enc else None
            v["j_cycles"] = j
            out["configs"][tag] = v
    c = {t: v["decaps_cycles_valid_and_rejected"] for t, v in out["configs"].items()}
    checks = {
        "all_pass": all(v["tb_result"].startswith("ALL PASS") for v in out["configs"].values()),
        "no_contract_violation": all(v["packed_contract_check"]["violations"] == 0 for v in out["configs"].values()),
        "fpga_equals_sram_only": all(c[f"fpga_str{m}"] == c[f"sram_only_str{m}"] for m in MILESTONES),
        "each_milestone_faster": all(c[f"sram_only_str{a}"] > c[f"sram_only_str{b}"]
                                     for a, b in zip("EFG", "FGH")),
    }
    out["checks"] = checks
    out["decaps_cycles"] = {m: {cfg: c[f"{cfg}_str{m}"] for cfg in CONFIG_NOTE} for m in MILESTONES}
    (cps.D / "streamed_system.json").write_text(json.dumps(out, indent=2) + "\n")
    for t, v in out["configs"].items():
        p = v["profile"]
        print(f"{t:16s} {v['tb_result'][:8]:8s} decaps {v['decaps_cycles_valid_and_rejected']:6d}  "
              f"encrypt {v['runtime_encrypt_cycles']}  J {v['j_cycles']}  ntt {p['ntt_busy']}  "
              f"sponge {p['sponge_busy']}  check {v['packed_contract_check']}")
    print("checks:", checks)
    assert all(checks.values()), checks


if __name__ == "__main__":
    main()
