"""Summarize the decapsulation cycle profiles (tb/decaps_profiler.sv).

Reads results/system_sim/tb_trustedge_spi_<config>_prof.log for the four
configurations and keeps the profiled intervals whose length equals the
decapsulation latency that the testbench itself reports (line "U1 Decaps"),
i.e. the valid and the implicitly rejected decapsulation. Those intervals must
agree exactly. Other busy intervals of the decapsulation unit (a one-cycle
pulse and an earlier, shorter run) are listed separately and not used.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
D = ROOT / "results" / "system_sim"
FIELDS = ["cycles", "ntt_busy", "sponge_busy", "perm_busy", "ntt_and_sponge", "ntt_starts",
          "ntt_inverse_starts", "perm_starts"]


def main() -> None:
    out = {"source": "tb/decaps_profiler.sv, read-only hierarchical probes in the full-system testbench",
           "configs": {}}
    for cfg in ["fpga", "keccak_only", "sram_only", "asic"]:
        log = (D / f"tb_trustedge_spi_{cfg}_prof.log").read_text(errors="replace")
        u1 = int(re.search(r"U1 Decaps busy latency valid/implicit-rejection=(\d+)", log)[1])
        prof = [{k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", ln) if k in FIELDS}
                for ln in log.splitlines() if ln.startswith("PROFILE")]
        used = [p for p in prof if p["cycles"] == u1]
        assert len(used) >= 2 and all(p == used[0] for p in used), f"{cfg}: profiles disagree"
        p = dict(used[0])
        p["other"] = p["cycles"] - p["ntt_busy"] - p["sponge_busy"] + p["ntt_and_sponge"]
        p["sponge_io"] = p["sponge_busy"] - p["perm_busy"]
        out["configs"][cfg] = {"profile": p, "profiled_intervals_used": len(used),
                               "other_intervals": [q for q in prof if q["cycles"] != u1]}
    (D / "decaps_profile.json").write_text(json.dumps(out, indent=2) + "\n")
    for cfg, v in out["configs"].items():
        print(cfg, v["profile"])


if __name__ == "__main__":
    main()
