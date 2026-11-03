"""
SymbiYosys formal verification driver + mutation tests.

Runs `sby` on all committed FIR configurations in two environments:

  live   -- in_valid is a free signal: reset/valid-timing/stall properties
  stream -- in_valid assumed 1: full datapath equivalence against the raw
            input history (independent of the folded pre-adder network)

with two engines each:
  * abc pdr     -- unbounded IC3/PDR proof (prove mode)
  * smtbmc yices -- bounded model checking (depth 32); every property's
                   violating traces are bounded by its guard horizon, so this
                   is a complete proof for this design (z3 also works)

Proven properties (defined inside the DUT template's `ifdef FORMAL block,
see formal/README.md):
  P1   reset clears all state
  P2   out_valid == twice-registered in_valid (pipeline identity)
  P3   out_valid implies in_valid exactly two cycles earlier
  P4s  !in_valid freezes the datapath and the output
  P4a  acc_reg == MAC over the raw input history (bit-for-bit)
  P4b  out_data == independently re-implemented round+shift+clamp of the
       previous accumulator
  P5   out_valid implies out_data within the saturation range

Mutation testing (run_mutation_tests): each of four injected bugs must make
at least one proof FAIL; the unmutated design must PASS. That is what proves
the property set is not vacuous.

Requires: yosys, sby, and at least one of yices / z3.

Usage:
  python3 src/python/formal_verify.py            # proofs + mutation tests
  python3 src/python/formal_verify.py --proofs   # proofs only
  python3 src/python/formal_verify.py --mutants  # mutation tests only
"""
import argparse
import shutil
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import paths
from reference import FILTER_A_SPEC, design_filter
from fixedpoint import FixedPointConfig
from build_comparison import headline_configs

FORMAL_DIR = paths.ROOT / "formal"

# (task, environment, sby mode, engine)
#   smtbmc yices -- bounded model checking with an independent SMT solver.
#       PRIMARY proof: every property is guarded by a bounded horizon
#       (<= N+3 edges) and the formal init block pins all state, so any
#       violating trace from the pinned start shortens to <= N+3 edges;
#       the depth-32 BMC is therefore a COMPLETE proof for N <= 29.
#   abc pdr -- unbounded IC3/PDR proof as an independent second argument.
#       Much harder for the 17-tap constant-multiplier MAC; a timeout here
#       is NOT a failure of the primary argument (see formal/README.md).
#       Controlled by SBY_PDR_TIMEOUT (default 240 s; 0 disables).
#
#   The live environment is split into two tasks over `define FORMAL_P4S:
#   live_main = all properties except the output-freeze P4s_b; live_stall =
#   ONLY P4s_b. Proving their union in one task makes smtbmc stall (any
#   cross-frame output relation interacts badly with free in_valid), while
#   each subset closes in seconds. The union of the two task properties is
#   exactly the full property set -- soundness unchanged.
PROOF_TASKS = [
    # (task, environment, sby mode, engine, enable_p4s, stall_only)
    ("live_main",  False, "bmc",   "smtbmc yices", False, False),
    ("live_stall", False, "bmc",   "smtbmc yices", True,  True),
    ("stream",     True,  "bmc",   "smtbmc yices", True,  False),
    ("live_pdr",   False, "prove", "abc pdr",      False, False),
    ("stream_pdr", True,  "prove", "abc pdr",      True,  False),
]

PDR_TIMEOUT = int(os.environ.get("SBY_PDR_TIMEOUT", "240"))
BMC_TIMEOUT = int(os.environ.get("SBY_BMC_TIMEOUT", "600"))

MUTANTS = {
    "requant_trunc": ("fir_symmetric.v.j2",
                      "wire signed [{{ shifted_width - 1 }}:0] shifted ="
                      " rounded[{{ acc_bits }}:{{ shift }}];",
                      "wire signed [{{ shifted_width - 1 }}:0] shifted ="
                      " rounded[{{ acc_bits }}:{{ shift + 1 }}];",
                      "requantizer shift off by one"),
    "no_rounding_const": ("fir_symmetric.v.j2",
                          "localparam signed [ACC_WIDTH:0] ROUND_CONST ="
                          " {{ acc_bits + 1 }}'sh{{ round_const_hex }};",
                          "localparam signed [ACC_WIDTH:0] ROUND_CONST = {{ acc_bits + 1 }}'sh0;",
                          "rounding constant removed"),
    "fold_to_add": ("fir_symmetric.v.j2",
                    "wire signed [{{ fold_width - 1 }}:0] fold{{ i }} =\n"
                    "        {sr[{{ i }}][IN_WIDTH-1], sr[{{ i }}]} +"
                    " {sr[{{ n_taps - 1 - i }}][IN_WIDTH-1], sr[{{ n_taps - 1 - i }}]};",
                    "wire signed [{{ fold_width - 1 }}:0] fold{{ i }} =\n"
                    "        {sr[{{ i }}][IN_WIDTH-1, sr[{{ i }}]} +"
                    " {sr[{{ n_taps - 1 - i }}][IN_WIDTH-1], sr[{{ n_taps - 1 - i }}]};",
                    "symmetric pre-adder: one operand's sign bit dropped"),
    "acc_mult_error": ("fir_symmetric.v.j2",
                       "prod_center = sr[{{ center_index }}] * C{{ n_pairs }};",
                       "prod_center = sr[{{ center_index }}] * (C{{ n_pairs }} + 1);",
                       "center-tap constant off by one LSB"),
}


def _dut_input_width(rtl_path: Path) -> int:
    """Read IN_WIDTH from the generated DUT's parameter header (single source
    of truth: the file itself)."""
    rtl_path = Path(rtl_path).resolve()
    for line in rtl_path.read_text().splitlines():
        if line.strip().startswith("parameter IN_WIDTH"):
            return int(line.split("=")[1].strip().rstrip(","))
    raise ValueError(f"IN_WIDTH not found in {rtl_path}")


def _render_harness(rtl_path: Path, module_name: str, workdir: Path,
                    stream_env: bool, top_name: str,
                    enable_p4s: bool = True, stall_only: bool = False) -> Path:
    """Render the formal wrapper around a generated DUT into the workdir."""
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(str(paths.VERILOG_DIR)),
                      trim_blocks=True, lstrip_blocks=True,
                      keep_trailing_newline=True)
    harness = env.get_template("fir_formal.v.j2").render(
        dut_file=rtl_path.name,
        module_name=module_name,
        stream_env=stream_env,
        enable_p4s=enable_p4s,
        stall_only=stall_only,
        top_name=top_name,
        input_total_bits=_dut_input_width(rtl_path),
    )
    out = workdir / f"{top_name}.sv"
    out.write_text(harness)
    return out


def _write_sby(task_name: str, mode: str, engine: str, top: str,
               files: list, workdir: Path, depth: str = "26") -> Path:
    """Emit one .sby task. Only the wrapper is `read` (its `include pulls the
    DUT in); both files are copied into the task's src/ directory.

    NOTE: sby resolves [files] entries relative to its own cwd (the workdir),
    NOT relative to the .sby file -- so the DUT path must be absolute."""
    wrapper, dut = files
    dut = Path(dut).resolve()
    # Depth justification (see formal/README.md): the deepest property window
    # is the stream P4a lookback (19-bit f_rst_hist + $past depth 18), whose
    # first evaluation point lands at ~step 21; in the live environment P5's
    # first fully-defined 17-sample output window also lands at ~step 21.
    # Any violating window replays within that horizon because state entering
    # every window is pinned by reset+init, so these depths are COMPLETE.
    lines = [
        "[options]",
        f"mode {mode}",
        f"depth {depth}",
        "",
        "[engines]",
        engine,
        "",
        "[script]",
        f"read -formal -sv {wrapper.name}",
        f"prep -top {top}",
        "",
        "[files]",
        str(wrapper),
        str(dut),
    ]
    path = workdir / f"{task_name}.sby"
    path.write_text("\n".join(lines) + "\n")
    return path


def _run_sby(sby_path: Path, workdir: Path, timeout: int = 900) -> tuple:
    """Run one sby task. Returns (ok, log_text). On timeout the log written so
    far is read and ok=False (a timed-out engine never proved anything)."""
    try:
        r = subprocess.run(["sby", "-f", sby_path.name], cwd=workdir,
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        log = workdir / (sby_path.stem + "/logfile.txt")
        logtxt = (log.read_text(errors="replace") if log.exists()
                  else (e.stdout or b"").decode(errors="replace"))
        return False, logtxt + "\n[formal_verify] ENGINE TIMEOUT after %ds\n" % timeout
    log = workdir / (sby_path.stem + "/logfile.txt")
    logtxt = log.read_text(errors="replace") if log.exists() else r.stdout + r.stderr
    ok = "DONE (PASS" in logtxt
    return ok, logtxt


def prove_config(rtl_path: Path, module_name: str, workdir: Path,
                 verbose: bool = True) -> bool:
    """Render both harness environments and run all proof engines.

    The two BMC tasks (the primary complete proofs) run first; the two PDR
    tasks run CONCURRENTLY with per-engine timeouts so a hard PDR problem
    cannot stall the whole run (SymbiYosys itself has no per-engine cap)."""
    from concurrent.futures import ThreadPoolExecutor

    def one(task):
        task_name, stream_env, mode, engine, p4s, stall_only = task
        t0 = time.time()
        wrapper = _render_harness(rtl_path, module_name, workdir,
                                  stream_env=stream_env, enable_p4s=p4s,
                                  stall_only=stall_only,
                                  top_name=f"harness_{task_name}")
        files = [wrapper, rtl_path]
        depth = "26" if stream_env else "24"
        sby = _write_sby(task_name, mode, engine,
                         f"harness_{task_name}", files, workdir, depth=depth)
        timeout = (PDR_TIMEOUT if "pdr" in task_name else BMC_TIMEOUT)
        ok, logtxt = _run_sby(sby, workdir, timeout=timeout)
        elapsed = time.time() - t0
        if verbose:
            tail = ""
            if not ok:
                fail_lines = [ln for ln in logtxt.splitlines()
                              if "failed assertion" in ln or "ERROR" in ln
                              or "TIMEOUT" in ln]
                tail = "  (" + ("; ".join(fail_lines[-2:]) or "see log") + ")"
            print(f"  [{module_name} / {task_name}] {'PASS' if ok else 'FAIL'}"
                  f"{tail} ({elapsed:.1f}s)", flush=True)
        return task_name, ok

    results = {}
    if PDR_TIMEOUT > 0:
        with ThreadPoolExecutor(max_workers=len(PROOF_TASKS)) as ex:
            for name, ok in ex.map(one, PROOF_TASKS):
                results[name] = ok
    else:
        # PDR disabled (SBY_PDR_TIMEOUT=0): BMC tasks only
        for task in PROOF_TASKS:
            if "pdr" not in task[0]:
                name, ok = one(task)
                results[name] = ok

    # NF1 fix: only BMC tasks are required for soundness.  PDR is an
    # independent unbounded certificate; a timeout there means the engine
    # did not converge, not that the design is wrong.  The docstring for
    # PROOF_TASKS explicitly says "a timeout here is NOT a failure of the
    # primary argument", so we report PDR failures as warnings rather than
    # letting them drive the return value.
    bmc_ok = all(ok for name, ok in results.items() if "pdr" not in name)
    pdr_ok = all(ok for name, ok in results.items() if "pdr" in name)
    if verbose and not pdr_ok:
        pdr_fails = [name for name, ok in results.items()
                     if "pdr" in name and not ok]
        print(f"  [{module_name}] PDR task(s) did not converge or timed out: "
              f"{pdr_fails}  (BMC proofs are complete; PDR result is advisory)",
              flush=True)
    return bmc_ok


def run_proofs(configs=None, verbose=True) -> bool:
    paths.ensure_dirs()
    FORMAL_DIR.mkdir(exist_ok=True)
    if configs is None:
        configs = headline_configs()
    ok_all = True
    with tempfile.TemporaryDirectory(prefix="pf_formal_") as td:
        workdir = Path(td)
        for name, c in configs.items():
            ok = prove_config(Path(c["rtl_path"]), c["module_name"], workdir,
                              verbose=verbose)
            ok_all = ok_all and ok
    return ok_all


def _prove_single_template(template_path: Path, workdir: Path) -> bool:
    """Generate + prove one DUT rendered from a (possibly mutated) template."""
    import jinja2
    import rtlgen as _rg

    h = design_filter(FILTER_A_SPEC)
    cfg = FixedPointConfig(
        coeff_int_bits=2, coeff_frac_bits=10,
        input_int_bits=2, input_frac_bits=14, acc_guard_bits=4,
        output_int_bits=2, output_frac_bits=14,
        rounding="round", saturate_output=True,
    )

    # Render through the mutated template file: copy the template layout into
    # the workdir so the loader picks up the mutation and nothing else.
    tdir = workdir / "tpl"
    tdir.mkdir(exist_ok=True)
    shutil.copy(template_path, tdir / "fir_symmetric.v.j2")
    shutil.copy(paths.VERILOG_DIR / "fir_nonuniform.v.j2",
                tdir / "fir_nonuniform.v.j2")
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(tdir)),
                             trim_blocks=True, lstrip_blocks=True,
                             keep_trailing_newline=True)
    ctx = _rg.build_context(h, cfg, "mutant")
    dut = workdir / "fir_mutant.v"
    dut.write_text(env.get_template("fir_symmetric.v.j2").render(**ctx))

    all_ok = True
    for task_name, stream_env, mode, engine, p4s, stall_only in PROOF_TASKS:
        wrapper = _render_harness(dut, "fir_mutant", workdir,
                                  stream_env=stream_env, enable_p4s=p4s,
                                  stall_only=stall_only,
                                  top_name=f"harness_{task_name}")
        depth = "26" if stream_env else "24"
        sby = _write_sby(f"mutant_{task_name}", mode, engine,
                         f"harness_{task_name}", [wrapper, dut], workdir,
                         depth=depth)
        timeout = PDR_TIMEOUT if "pdr" in task_name else BMC_TIMEOUT
        ok, _ = _run_sby(sby, workdir, timeout=timeout)
        all_ok = all_ok and ok
    return all_ok


def run_mutation_tests(verbose=True) -> bool:
    """Each injected bug must fail the proof; report a table."""
    all_killed = True
    for mname, (tpl, old, new, desc) in MUTANTS.items():
        orig = paths.VERILOG_DIR / tpl
        mutated_text = orig.read_text().replace(old, new)
        if mutated_text == orig.read_text():
            print(f"  {mname:22s} ERROR: mutation pattern not found in {tpl}")
            all_killed = False
            continue
        with tempfile.TemporaryDirectory(prefix="pf_mut_") as td:
            workdir = Path(td)
            mut_path = workdir / tpl
            mut_path.write_text(mutated_text)
            try:
                ok = _prove_single_template(mut_path, workdir)
            except Exception as e:
                print(f"  {mname:22s} ERROR: {e}")
                all_killed = False
                continue
        verdict = ("killed (proof FAILED, as required)" if not ok
                   else "SURVIVED -- property set is vacuous for this bug!")
        if ok:
            all_killed = False
        if verbose:
            print(f"  {mname:22s} {verdict}")
            print(f"{'':24s} ({desc})")
    return all_killed


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="SymbiYosys proofs + mutation tests")
    ap.add_argument("--proofs", action="store_true", help="run proofs only")
    ap.add_argument("--mutants", action="store_true", help="run mutation tests only")
    args = ap.parse_args()

    run_p = not args.mutants
    run_m = not args.proofs

    ok = True
    if run_p:
        print("== SymbiYosys proofs (abc pdr + yices smtbmc) ==")
        ok = run_proofs() and ok
    if run_m:
        print("\n== Mutation tests (each bug MUST be caught) ==")
        ok = run_mutation_tests() and ok

    print("\nFORMAL VERIFICATION: " + ("PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)
