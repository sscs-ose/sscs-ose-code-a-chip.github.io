"""Experiment: which f_fir reference formulation can the engines close?

Patches the generated DUT's f_fir body with a candidate formulation, then runs
the stream BMC. Independence of the reference is preserved as long as it is a
direct transcription of  y[n] = sum_i h[i] * x[n-i]  (order/grouping/width are
proof-friendliness knobs, not verification holes: addition reassociation and
width extension cannot change a value).
"""
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # noqa: E402  (src/python)
import paths  # noqa: E402
from build_comparison import headline_configs  # noqa: E402
import formal_verify as fv  # noqa: E402

BODIES = {
    # A: straight MAC (current template formulation) -- the known-hard one
    "A_straight": """
            f_fir = d0 * C0 + d16 * C0 +
                    d1 * C1 + d15 * C1 +
                    d2 * C2 + d14 * C2 +
                    d3 * C3 + d13 * C3 +
                    d4 * C4 + d12 * C4 +
                    d5 * C5 + d11 * C5 +
                    d6 * C6 + d10 * C6 +
                    d7 * C7 + d9  * C7 +
                    d8 * C8;""",
    # B: symmetric pair products, sequential accumulation. In the 36-bit
    # assignment context the pair sums widen to ACC bits with sign extension,
    # so this is EXACTLY the folded datapath's arithmetic (no wraparound:
    # 2*min(in) fits fold_width signed). Reassociation-only => independent.
    "B_pair_seq": """
            f_fir = 0;
            f_fir = f_fir + (d0  + d16) * C0;
            f_fir = f_fir + (d1  + d15) * C1;
            f_fir = f_fir + (d2  + d14) * C2;
            f_fir = f_fir + (d3  + d13) * C3;
            f_fir = f_fir + (d4  + d12) * C4;
            f_fir = f_fir + (d5  + d11) * C5;
            f_fir = f_fir + (d6  + d10) * C6;
            f_fir = f_fir + (d7  + d9)  * C7;
            f_fir = f_fir +  d8         * C8;""",
    # C: pair products in per-pair width (fold_width) first, then extended
    "C_pair_wide": """
            f_fir = {ACC{1'b0}};
            f_fir = f_fir + $signed({{(FOLD+1){(d0  + d16)[FOLD]}}, (d0  + d16)} * C0);
            f_fir = f_fir + $signed({{(FOLD+1){(d1  + d15)[FOLD]}}, (d1  + d15)} * C1);
            f_fir = f_fir + $signed({{(FOLD+1){(d2  + d14)[FOLD]}}, (d2  + d14)} * C2);
            f_fir = f_fir + $signed({{(FOLD+1){(d3  + d13)[FOLD]}}, (d3  + d13)} * C3);
            f_fir = f_fir + $signed({{(FOLD+1){(d4  + d12)[FOLD]}}, (d4  + d12)} * C4);
            f_fir = f_fir + $signed({{(FOLD+1){(d5  + d11)[FOLD]}}, (d5  + d11)} * C5);
            f_fir = f_fir + $signed({{(FOLD+1){(d6  + d10)[FOLD]}}, (d6  + d10)} * C6);
            f_fir = f_fir + $signed({{(FOLD+1){(d7  + d9)[FOLD]}},  (d7  + d9)}  * C7);
            f_fir = f_fir + $signed({{(FOLD+1){d8[FOLD]}}, d8} * C8);""",
}


def patch_dut(dut_text: str, body_key: str, n_taps: int = 17,
              acc_bits: int = 36, fold_width: int = 14) -> str:
    # group 2 spans everything after the function's opening `begin` up to
    # `endfunction`, i.e. INCLUDING the closing `end` -- re-add it.
    body = BODIES[body_key] + "\n        end"
    # splice: replace everything between the f_fir begin..end
    m = re.search(r"(function signed \[\d+:0\] f_fir;.*?begin)(.*?)(\n\s*endfunction)",
                  dut_text, re.S)
    assert m, "f_fir body not found"
    return dut_text[:m.start(2)] + body + dut_text[m.end(2):]


def run(body_key: str, engine: str, mode: str, timeout: int) -> None:
    paths.ensure_dirs()
    info = headline_configs()["best_uniform"]
    dut_text = Path(info["rtl_path"]).read_text()
    if body_key != "A_straight":
        acc_bits = int(re.search(r"parameter\s+ACC_WIDTH\s*=\s*(\d+)",
                                 dut_text).group(1))
        fold_width = int(re.search(r"wire signed \[(\d+):0\] fold0",
                                   dut_text).group(1)) + 1
        dut_text = patch_dut(dut_text, body_key, acc_bits=acc_bits,
                             fold_width=fold_width)
        # the file is renamed; rename the module to match the harness instance
        dut_text = re.sub(r"module\s+fir_\w+", "module fir_patched",
                          dut_text, count=1)
    wd = Path(tempfile.mkdtemp(prefix=f"ffir_{body_key.split('_')[0]}_"))
    dut = wd / "fir_patched.v"
    dut.write_text(dut_text)
    module = "fir_patched"
    w = fv._render_harness(dut, module, wd, stream_env=True,
                           top_name="harness_stream")
    shutil.rmtree(wd / "stream_probe", ignore_errors=True)
    sby = fv._write_sby("stream_probe", mode, engine, "harness_stream",
                        [w, dut], wd)
    t0 = time.time()
    ok, log = fv._run_sby(sby, wd, timeout=timeout)
    steps = re.findall(r"Checking assertions in step (\d+)", log)
    print(f"[{engine} / {body_key}] {'PASS' if ok else 'FAIL'} "
          f"deepest={max(map(int, steps)) if steps else -1} "
          f"({time.time()-t0:.1f}s)", flush=True)


if __name__ == "__main__":
    eng = sys.argv[1] if len(sys.argv) > 1 else "smtbmc yices"
    mode = "prove" if "pdr" in eng else "bmc"
    to = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    for k in sys.argv[3:] or list(BODIES):
        run(k, eng, mode, to)
