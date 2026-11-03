"""Does the testbench actually catch RTL bugs?  Inject known bugs into the generated Verilog
and check that cocotb fails on each, while the unmodified control passes.

    python tb/mutation_test.py           # writes results/mutation_test.csv (about 3 minutes)

Configuration: D=256, P=64, error-driven learning, 4-bit counters, stochastic updates (k=3),
the configuration that exercises every learning feature.
"""
import csv
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tb"))
import rtlgen  # noqa: E402
import run_verif as R  # noqa: E402
from rtlgen import RTLConfig  # noqa: E402

CFG = RTLConfig(D=256, P=64, learn=2, w=4, k=3)
CFG_CG = RTLConfig(D=256, P=64, learn=2, w=4, k=3, cg=1)   # clock-gated variant of the same chip
N = dict(N_RAND=20, N_REAL=5, N_STREAM=30)
MUTANTS = {
    "control (unmodified)": None,
    "binarize ignores the tie vector": ("((cnt == 0) & tbit[i])", "((cnt == 0) & 1'b0)"),
    "counter saturation off by one": ("(nx > 7) ? 7", "(nx > 6) ? 6"),
    "stochastic-update mask ignored": ("& mbit[i]) ? sat", ") ? sat"),
    "argmin ties go to the highest class": ("if (dacc[cc] < bestd)", "if (dacc[cc] <= bestd)"),
    # --- clock-gating bugs, run on the gated variant (cg=1)
    "gating: load/readout shifts forgotten": ("hdc_cg u_cg_ring (.clk(clk), .en(shift)", "hdc_cg u_cg_ring (.clk(clk), .en(shift & (state != IDLE))"),
    "gating: ring clock gated off during CLEAR": ("hdc_cg u_cg_ring (.clk(clk), .en(shift)", "hdc_cg u_cg_ring (.clk(clk), .en(shift & (state != CLEAR))"),
    "gating: ring clock never gated (always shifts)": ("hdc_cg u_cg_ring (.clk(clk), .en(shift)", "hdc_cg u_cg_ring (.clk(clk), .en(1'b1)"),
}
GATED = {n for n in MUTANTS if n.startswith("gating:")}
# Verilator is a 2-state simulator that starts every register at 0, so a missing power-up clear is
# invisible to it; a 4-state simulator (Icarus) starts from X and catches it.
SIM_FOR = {"gating: ring clock gated off during CLEAR": "icarus"}


def main():
    orig = rtlgen.generate
    rows = []
    for name, mut in MUTANTS.items():
        def gen(cfg, top="approxhdc_top", mut=mut):
            v = orig(cfg, top)
            if mut:
                assert mut[0] in v, f"mutation site not found: {mut[0]}"
                v = v.replace(*mut)
            return v

        R.write = lambda cfg, path, top="approxhdc_top", g=gen: (open(path, "w").write(g(cfg, top)), path)[1]
        sim = SIM_FOR.get(name, "verilator")
        _, nt, nf, _, _ = R.run_one(CFG_CG if name in GATED else CFG, sim, N)
        caught = nf > 0
        ok = (not caught) if mut is None else caught
        rows.append(dict(mutant=name, simulator=sim, tests=nt, failed=nf, expected="pass" if mut is None else "fail",
                         result="OK" if ok else "UNEXPECTED"))
        print(f"{'OK        ' if ok else 'UNEXPECTED'} {name:48s} [{sim}] tests={nt} failed={nf}", flush=True)
    out = ROOT / "results" / "mutation_test.csv"
    with out.open("w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    sys.exit(int(any(r["result"] != "OK" for r in rows)))


if __name__ == "__main__":
    main()
