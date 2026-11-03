"""Summarize the full-system simulations with the packed NTT (scripts/make_packed_system.py).

Reads results/system_sim/tb_trustedge_spi_<config>_sys<step>.log, written by run_system_sim.sh with
CAC_PACKED_SYSTEM=1, CAC_PROFILE=1, CAC_STATE_PROF=1 and CAC_PACKED_CHECK=1, and writes
results/system_sim/packed_system.json with, for each configuration:

  * the testbench verdict, the decapsulation latency it reports for a valid and an implicitly rejected
    ciphertext, and the packed engine's write-contract check (tb/ntt_packed_checker.sv);
  * the cycle profile of tb/decaps_profiler.sv and the time spent in each FSM state
    (tb/decaps_state_profiler.sv), grouped into the activities of a decapsulation.

It also checks that every step's change in latency follows from the cycle model: the packed engine
saves the per-transform difference on each of the 4 forward and 4 inverse transforms, the one-round
Keccak saves 144 cycles on each of 26 permutations, and running the hashes during the decryption saves
the shorter of the two phases less one hand-over cycle.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
D = ROOT / "results" / "system_sim"
RTL = ROOT / "hskem_rtl" / "rtl" / "mlkem512"
FIELDS = ["cycles", "ntt_busy", "sponge_busy", "perm_busy", "ntt_and_sponge", "ntt_starts",
          "ntt_inverse_starts", "perm_starts"]
CONFIGS = {   # log tag: (configuration of run_system_sim.sh, description)
    "asic_sysR": ("asic", "published engines, built through make_packed_system.py without its defines"),
    "asic_sysA": ("asic", "A: packed NTT"),
    "sram_only_sysB": ("sram_only", "B: A + one-round Keccak"),
    "sram_only_sysBC": ("sram_only", "C: B + the three hashes during the decryption"),
    "asic_sysAC": ("asic", "A + the three hashes during the decryption (row-serialized Keccak)"),
    "fpga_sysFC": ("fpga", "FPGA configuration + packed NTT + hashes during the decryption"),
    "sram_only_sysBCD": ("sram_only", "D: C + one wait state less in ten read loops"),
    "fpga_sysFCD": ("fpga", "FPGA configuration with A, C and D: the board's bitstream"),
}
# activities of a decapsulation, by FSM state (decapsulation controller, then re-encryption controller)
GROUPS = {
    "NTT transforms": ["ST_NTT_", "ST_INV_", "S_Y_NTT_", "S_INV_"],
    "Keccak": ["ST_HEK_", "ST_HC_", "ST_G_", "ST_J_", "ST_HASH_JOIN", "S_PRF_"],
    "pointwise products": ["ST_PAIR_", "ST_MUL", "ST_ACCUM", "ST_WRITE", "S_OPERAND", "S_MUL", "S_ACCUM",
                           "S_NTT_WRITE", "S_PAIR_INIT"],
    "coefficients in and out of the NTT": ["ST_U_", "ST_MSG_", "S_Y_FETCH", "S_Y_WAIT", "S_Y_WRITE", "S_Y_READ",
                                           "S_READ_"],
    "ciphertext encoding": ["S_CODEC"],
    "ciphertext comparison": ["ST_CMP_"],
}


def state_names() -> tuple[dict, dict]:
    dec = (RTL / "mlkem512_partial_kem_selftests.sv").read_text()
    dn = {int(v): k for k, v in re.findall(r"(ST_[A-Z0-9_]+)=6'd(\d+)", dec)}
    dn.update({52: "ST_HASH_JOIN", 53: "ST_HASH_JOIN2"})          # added by make_packed_system.py
    enc = (RTL / "mlkem512_kpke_encrypt_selftest.sv").read_text()
    en = {int(v, 16).bit_length() - 1: k for k, v in re.findall(r"(S_[A-Z0-9_]+)\s*=32'h([0-9A-Fa-f]+)", enc)}
    return dn, en


def group_of(name: str) -> str:
    for g, prefixes in GROUPS.items():
        if any(name.startswith(p) for p in prefixes):
            return g
    return "control and other"


def parse(tag: str, dn: dict, en: dict) -> dict:
    log = (D / f"tb_trustedge_spi_{tag}.log").read_text(errors="replace")
    res = re.search(r"TB_TRUSTEDGE_SPI_RESULT: (.*)", log)[1].strip()
    u1 = int(re.search(r"U1 Decaps busy latency valid/implicit-rejection=(\d+)", log)[1])
    chk = re.search(r"NTT_PACKED_CHECK writes=(\d+) starts=(\d+) violations=(\d+)", log)
    prof = {}
    for ln in log.splitlines():
        if ln.startswith("PROFILE"):
            p = {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", ln)}
            prof[p["decaps"]] = {k: p[k] for k in FIELDS}
    used = [i for i, p in prof.items() if p["cycles"] == u1]
    assert len(used) >= 2 and all(prof[i] == prof[used[0]] for i in used), f"{tag}: profiles disagree"
    n = used[0]
    states = {}
    for kind, s, a in re.findall(rf"STATEPROF decaps={n} (dec_state|enc_state_bit)=(\d+) all=(\d+)", log):
        name = dn[int(s)] if kind == "dec_state" else en[int(s)]
        if name != "ST_REENC_WAIT":                    # its time is split by the re-encryption states
            states[name] = states.get(name, 0) + int(a)
    assert sum(states.values()) == u1, f"{tag}: state profile {sum(states.values())} != {u1}"
    groups = {g: 0 for g in list(GROUPS) + ["control and other"]}
    for name, a in states.items():
        groups[group_of(name)] += a
    # the decryption: decaps-controller states from u's load to the recovered message
    phase = {"decryption": sum(a for k, a in states.items() if k.startswith(
                 ("ST_U_", "ST_NTT_", "ST_PAIR_", "ST_MUL", "ST_ACCUM", "ST_WRITE", "ST_INV_", "ST_MSG_"))),
             "hashes_h_ek_h_c_j": sum(a for k, a in states.items() if k.startswith(("ST_HEK_", "ST_HC_", "ST_J_")))}
    return {"config": CONFIGS[tag][0], "description": CONFIGS[tag][1], "tb_result": res,
            "decaps_cycles_valid_and_rejected": u1, "profiled_intervals_used": len(used),
            "packed_contract_check": (dict(zip(["writes", "starts", "violations"], map(int, chk.groups())))
                                      if chk else None),
            "profile": prof[n], "states": states, "groups": groups, "phases": phase}


def main() -> None:
    dn, en = state_names()
    out = {"source": "run_system_sim.sh with CAC_PACKED_SYSTEM=1; tb/decaps_profiler.sv, "
                     "tb/decaps_state_profiler.sv, tb/ntt_packed_checker.sv", "configs": {}}
    for tag in CONFIGS:
        out["configs"][tag] = parse(tag, dn, en)
    c = {t: v["decaps_cycles_valid_and_rejected"] for t, v in out["configs"].items()}
    published = json.loads((D / "summary.json").read_text())["configs"]
    fwd, inv = 6274 - 988, 7554 - 1116                 # cycles saved per transform, ASIC store -> packed
    ph = {t: v["phases"] for t, v in out["configs"].items()}
    model = {
        "regression_equals_published_asic": c["asic_sysR"] == int(published["asic"]["decaps_cycles"]),
        "A_packed_ntt": c["asic_sysR"] - 4 * fwd - 4 * inv == c["asic_sysA"],
        "B_one_round_keccak": c["asic_sysA"] - 26 * 144 == c["sram_only_sysB"],
        "C_hash_overlap": c["sram_only_sysB"] - min(ph["sram_only_sysB"]["decryption"],
                                                   ph["sram_only_sysB"]["hashes_h_ek_h_c_j"]) + 1 == c["sram_only_sysBC"],
        "A_plus_overlap": c["asic_sysA"] - min(ph["asic_sysA"]["decryption"],
                                              ph["asic_sysA"]["hashes_h_ek_h_c_j"]) + 1 == c["asic_sysAC"],
        "fpga_equals_sram_only_with_packed_ntt": c["fpga_sysFC"] == c["sram_only_sysBC"],
        # D: decryption 512 + 2 x 256 + 256, encryption 256 + 512 + 768, codec 768 + 768, comparison 768;
        # the shortened decryption still outlasts the hashes, which therefore stay hidden
        "D_streamed_loops": c["sram_only_sysBC"] - (1280 + 1536 + 1536 + 768) == c["sram_only_sysBCD"]
                            and ph["sram_only_sysBCD"]["decryption"] > ph["sram_only_sysB"]["hashes_h_ek_h_c_j"],
        "fpga_equals_sram_only_with_D": c["fpga_sysFCD"] == c["sram_only_sysBCD"],
    }
    out["model_checks"] = model
    out["steps"] = {"published": c["asic_sysR"], "A": c["asic_sysA"], "B": c["sram_only_sysB"], "C": c["sram_only_sysBC"],
                    "D": c["sram_only_sysBCD"]}
    (D / "packed_system.json").write_text(json.dumps(out, indent=2) + "\n")
    for t, v in out["configs"].items():
        print(f"{t:16s} {v['tb_result'][:8]:8s} decaps {v['decaps_cycles_valid_and_rejected']:6d}  "
              f"phases {v['phases']}  check {v['packed_contract_check']}")
    print("model checks:", model)
    assert all(model.values()), model


if __name__ == "__main__":
    main()
