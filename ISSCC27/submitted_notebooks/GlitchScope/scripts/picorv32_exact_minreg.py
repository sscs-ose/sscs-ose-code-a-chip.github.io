"""PicoRV32 fast multiplier: exact minimum-register retiming as a reference.

`--optimize` measures a cut-based minimum-register heuristic alongside its own search; on PicoRV32 that
heuristic returned the original design.  This script solves the exact Leiserson-Saxe minimum-register
program (the reference of section 7) at the same pre-layout clock limit, measures the result on the same
cycles as the original (and, if given, GlitchScope's own `optimized.v`), writes the netlist and certifies it.

    python scripts/picorv32_exact_minreg.py <liberty> [<optimized.v>]   -> data/picorv32/exact_minreg.json
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.optimize import GlitchFix  # noqa: E402

NET = ROOT / "bench/external/netlists/picorv32_pcpi_fast_mul.v"
VCD = ROOT / "bench/external/picorv32/picorv32_fast_mul.vcd"
OUT = ROOT / "bench/external/picorv32/exact_minreg.v"          # netlists stay local


def main():
    lib = sys.argv[1]
    t0 = time.time()
    fx = GlitchFix(NET, lib, vcd=VCD, sample=16, seed=1, grid=10, log=lambda m: print(m, flush=True))
    T = fx.period_ps * (1 - 0.15)                    # --clock-margin default, as in the cached run
    exact = fx.classic_min_area(T, time_limit=7200.0)
    row = dict(target_ps=round(T, 1), seconds=round(time.time() - t0, 1),
               exact_min_register=exact.row() if exact is not None else None)
    if exact is not None:
        OUT.write_text(exact.text)
        from scripts.retiming_certificate import certify
        row["certificate"] = certify(lib, str(NET), str(OUT), 0)[1]
        nets = {"original": NET, "exact_min_register": OUT}
        if len(sys.argv) > 2:
            nets["glitchscope"] = Path(sys.argv[2])
            row["glitchscope_vs_exact_structural"] = certify(lib, str(OUT), sys.argv[2], 0)[1]
        same = {}
        for k, n in nets.items():                   # every netlist on the same 40 cycles
            f = GlitchFix(n, lib, vcd=VCD, sample=16, seed=1, grid=10, log=lambda m: None)
            b, = f.remeasure([f.original()], 40)
            same[k] = b.row()
        row["same_cycles"] = same
        row["saving_exact_vs_original_same_cycles"] = 1 - same["exact_min_register"]["total"] / same["original"]["total"]
    (ROOT / "data/picorv32/exact_minreg.json").write_text(json.dumps(row, indent=1))
    print(json.dumps({k: v for k, v in row.items() if k not in ("original", "glitchscope")}, indent=1))


if __name__ == "__main__":
    main()
