"""Mutation test of the block testbenches: does the verification catch a wrong design?

Each mutant is one deliberate, plausible bug in a copy of the RTL (a wrong twiddle factor, an off-by-one bound in
a modular correction, a lost +q, a wrong twiddle index, a wrong rotation offset or round constant, a lost NOT in
chi). The unchanged testbench of Section 4 runs on the mutant with the committed golden vectors; a mutant is caught
when the testbench reports an error. The unmutated design (the control) must pass.

usage: python3 scripts/mutation_test.py [--out results/mutation/summary.json]
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
NTT = ["kyber_pkg.sv", "barrett_reduce_1c.v", "kyber_ntt_engine_packed.sv", "kyber_ntt_engine_packed2.sv"]
KEC = ["keccak_f1600_iter.sv"]
MUTANTS = [
    # (name, block, file, original text, mutated text, what it models)
    ("zeta_value", "ntt", "kyber_pkg.sv", "7'd5: kyber_zeta = 16'd630;", "7'd5: kyber_zeta = 16'd631;",
     "one twiddle factor off by one"),
    ("barrett_bound", "ntt", "barrett_reduce_1c.v", "(r0 >= Q) ? (r0 - Q) : r0", "(r0 > Q) ? (r0 - Q) : r0",
     "the final correction misses r = q"),
    ("sum_bound", "ntt", "kyber_ntt_engine_packed2.sv", "(sum_w >= Q13) ? (sum_w - Q13)", "(sum_w > Q13) ? (sum_w - Q13)",
     "modular addition misses a + b = q"),
    ("diff_no_q", "ntt", "kyber_ntt_engine_packed2.sv", "{1'b0, opb[gh]} + Q13 - opa[gh]", "{1'b0, opb[gh]} - opa[gh]",
     "modular subtraction without +q"),
    ("fsum_bound", "ntt", "kyber_ntt_engine_packed2.sv", "(f_sum_w >= Q13) ? (f_sum_w - Q13)",
     "(f_sum_w > Q13) ? (f_sum_w - Q13)", "the forward butterfly's modular addition misses x + r = q"),
    ("zeta_index", "ntt", "kyber_ntt_engine_packed2.sv", "(w_lo >> (3'd7 - m_fwd))", "(w_lo >> (3'd6 - m_fwd))",
     "forward twiddle index shifted by one level"),
    ("rho_offset", "keccak", "keccak_f1600_iter.sv", "2: rho_offset = 62;", "2: rho_offset = 61;",
     "one lane rotated by 61 instead of 62"),
    ("round_constant", "keccak", "keccak_f1600_iter.sv", "64'h8000000080008008", "64'h8000000080008009",
     "one bit of the last round constant"),
    ("chi_not_lane", "keccak", "keccak_f1600_iter.sv", "((~b[((x+1)%5)+5*y]) & b[((x+2)%5)+5*y])",
     "((b[((x+1)%5)+5*y]) & b[((x+2)%5)+5*y])", "chi without its NOT (lane-indexed form)"),
    ("chi_not_row", "keccak", "keccak_f1600_iter.sv", "a[x] = b[x] ^ ((~b[(x+1)%5]) & b[(x+2)%5]);",
     "a[x] = b[x] ^ ((b[(x+1)%5]) & b[(x+2)%5]);", "chi without its NOT (row form)"),
]
# a mutant that no input/output test can catch, with the reason (checked: 10,009 vectors with the corner cases pass)
EQUIVALENT = {"sum_bound": "the sum feeds only the inverse transform, where it is added, subtracted or multiplied again and "
                           "the final scaling multiplies every coefficient, so a stored q behaves exactly as 0"}
CONFIGS = {"ntt": [("packed2_x1", ["-DNTT_PACKED2", "-DXSTAGE=1"], "tb_ntt.sv", NTT, "NTT_RESULT")],
           "keccak": [("keccak_round", ["-DSERIAL=0"], "tb_keccak.sv", KEC, "KECCAK_RESULT"),
                      ("keccak_serial", ["-DSERIAL=1"], "tb_keccak.sv", KEC, "KECCAK_RESULT")]}


def simulate(rtl: pathlib.Path, vec: pathlib.Path, cfg) -> dict:
    name, defs, tb, files, tag = cfg
    vvp = rtl / f"{name}.vvp"
    c = subprocess.run(["iverilog", "-g2012", "-I", ".", *defs, "-o", str(vvp), *[str(rtl / f) for f in files],
                        str(ROOT / "tb" / tb)], cwd=vec, capture_output=True, text=True)
    if c.returncode:
        return {"compiled": False, "caught": True, "how": "compile error: " + c.stderr.strip().splitlines()[-1][:120]}
    r = subprocess.run(["vvp", "-n", str(vvp)], cwd=vec, capture_output=True, text=True, timeout=3600)
    line = next((l for l in r.stdout.splitlines() if l.startswith(tag)), "")
    errors = int(re.search(r"errors=(\d+)", line)[1]) if line else None
    passed = "PASS" in r.stdout.split() and errors == 0
    return {"compiled": True, "result": line, "errors": errors, "caught": not passed,
            "how": f"{errors} mismatching vectors" if errors else ("no result line" if errors is None else "passes")}


def formal(rtl: pathlib.Path) -> dict:
    """SAT proof of formal/prove_barrett.sh on the (possibly mutated) one-correction reducer."""
    t = rtl / "barrett_formal.v"
    t.write_text((rtl / "barrett_reduce_1c.v").read_text().replace("module barrett_reduce_1c", "module barrett_reduce"))
    r = subprocess.run(["yosys", "-q", "-p", f"read_verilog {t} barrett_prop.v; hierarchy -top barrett_prop; proc; "
                        "flatten; opt; sat -prove ok 1 -verify"], cwd=ROOT / "formal", capture_output=True, text=True)
    fail = "FAIL" in r.stdout + r.stderr or r.returncode != 0
    return {"proof": "fails (counterexample found)" if fail else "holds", "caught": fail}


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(ROOT / "results/mutation/summary.json"))
    a = ap.parse_args()
    vec = ROOT / "vectors"
    if not (vec / "ntt_in.hex").exists():
        subprocess.run(["python3", "gen_vectors.py", "--out", str(vec)], cwd=ROOT / "golden", check=True)
    res = {"method": __doc__.split("usage:")[0].strip(), "control": {}, "mutants": []}
    with tempfile.TemporaryDirectory() as td:
        base = pathlib.Path(td) / "base"; shutil.copytree(ROOT / "rtl", base)
        for block, cfgs in CONFIGS.items():
            for cfg in cfgs:
                res["control"][cfg[0]] = simulate(base, vec, cfg)
                print("control", cfg[0], res["control"][cfg[0]]["how"])
        res["base_formal"] = formal(base)
        for name, block, f, old, new, what in MUTANTS:
            m = pathlib.Path(td) / name; shutil.copytree(ROOT / "rtl", m)
            src = (m / f).read_text()
            assert src.count(old) == 1, (name, src.count(old))
            (m / f).write_text(src.replace(old, new))
            runs = {cfg[0]: simulate(m, vec, cfg) for cfg in CONFIGS[block]}
            entry = {"mutant": name, "block": block, "file": f"rtl/{f}", "models": what, "original": old, "mutated": new,
                     "runs": runs, "caught_by_simulation": any(r["caught"] for r in runs.values())}
            if f == "barrett_reduce_1c.v":
                entry["formal"] = formal(m)
            entry["equivalent"] = EQUIVALENT.get(name)
            entry["caught"] = entry["caught_by_simulation"] or entry.get("formal", {}).get("caught", False)
            res["mutants"].append(entry)
            print(name, {k: v["how"] for k, v in runs.items()})
    res["caught"] = sum(e["caught"] for e in res["mutants"]); res["total"] = len(res["mutants"])
    res["caught_by_simulation"] = sum(e["caught_by_simulation"] for e in res["mutants"])
    res["equivalent"] = sum(bool(e["equivalent"]) for e in res["mutants"])
    res["control_passes"] = all(not v["caught"] for v in res["control"].values())
    out = pathlib.Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1) + "\n")
    print(f"MUTATION caught {res['caught']}/{res['total']} (simulation {res['caught_by_simulation']}, equivalent "
          f"{res['equivalent']}), control passes: {res['control_passes']}, formal on the unmutated reducer: {res['base_formal']['proof']}")


if __name__ == "__main__":
    main()
