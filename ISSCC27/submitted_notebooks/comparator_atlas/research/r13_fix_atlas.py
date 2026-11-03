"""r13: prospective atlas test of the r10 fix (input pair x2 + unit-element trim + 5 bits).

Same 49 conditions, local_boundary calibration, fit/held-out split and sealed-registration rule as r2,
with separate output and cache folders. The design is registered in-process; its netlist is the
lvt_balanced_4b family generator with input_w=6, trim_bits=5 and every bit split into unit copies.
Local only.
  python -B r13_fix_atlas.py phase_a
  python -B r13_fix_atlas.py register
  python -B r13_fix_atlas.py phase_b
  python -B r13_fix_atlas.py evaluate
  python -B r13_fix_atlas.py residuals   (per-condition code and residual, from phase A)
"""
import sys
from concurrent.futures import ThreadPoolExecutor

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r2_prospective as R2  # noqa: E402  (puts the desktop root on sys.path)
import comparator_atlas.spice as S  # noqa: E402
from comparator_atlas.designs import DESIGNS, Design  # noqa: E402
from r7_trim_dnl import unit_array  # noqa: E402

NAME = "fix_x2_unit5b"
DESIGNS[NAME] = Design(NAME, input_device="nfet_01v8_lvt", input_w=6, tail_w=7, trim_bits=5)
_orig = S.circuit_text
S.circuit_text = lambda d: unit_array(_orig(d), d.trim_bits) if d.name == NAME else _orig(d)

R2.OUT = R2.HERE / "out" / "r13"
R2.CACHE = R2.HERE / "cache" / "spice_r13"
R2.NEW_DESIGNS = (NAME,)
R2.ThreadPoolExecutor = lambda max_workers: ThreadPoolExecutor(max_workers=8)

if __name__ == "__main__":
    cmd = ARGS[0]
    if cmd == "phase_a":
        R2.run_phase(NAME, R2.FIT_INPUTS, "phase_a")
    elif cmd == "phase_b":
        R2.run_phase(NAME, R2.HELD_INPUTS, "phase_b")
    elif cmd == "register":
        R2.register("fix", [NAME])
    elif cmd == "evaluate":
        R2.evaluate()
    elif cmd == "residuals":
        table = R2.residual_table(NAME)[["case_id", "code", "residual_mv", "halfwidth_mv"]]
        table.to_csv(R2.OUT / "fix_residuals.csv", index=False, lineterminator="\n")
