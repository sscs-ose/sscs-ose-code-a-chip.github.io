"""r15: does more trim range fix r13's saturation? Two unit-element candidates, same r2/r13 protocol.

  a: input W 3, 5-bit unit trim (coarser step, about twice the range in mV of the r13 fix)
  b: input W 6, 6-bit unit trim (same step as the r13 fix, twice the codes); uses a local copy of
     select_trim with only its max_code guard raised from 31 to 63 (disclosed protocol deviation)
Same 49 conditions, local_boundary calibration, fit/held-out split and sealed-registration rule as r2.
Local only.
  python -B r15_range.py <a|b> phase_a
  python -B r15_range.py <a|b> register
  python -B r15_range.py <a|b> phase_b
  python -B r15_range.py <a|b> evaluate
  python -B r15_range.py <a|b> residuals
"""
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r2_prospective as R2  # noqa: E402  (puts the desktop root on sys.path)
import comparator_atlas.spice as S  # noqa: E402
from comparator_atlas.designs import DESIGNS, Design  # noqa: E402
from r7_trim_dnl import unit_array  # noqa: E402

VARIANTS = {"a": ("unit5_w3", 3, 5), "b": ("unit6_w6", 6, 6)}
VARIANT = ARGS[0]
NAME, INPUT_W, BITS = VARIANTS[VARIANT]
DESIGNS[NAME] = Design(NAME, input_device="nfet_01v8_lvt", input_w=INPUT_W, tail_w=7, trim_bits=BITS)
_orig = S.circuit_text
S.circuit_text = lambda d: unit_array(_orig(d), d.trim_bits) if d.name == NAME else _orig(d)

R2.OUT = R2.HERE / "out" / f"r15{VARIANT}"
R2.CACHE = R2.HERE / "cache" / f"spice_r15{VARIANT}"
R2.NEW_DESIGNS = (NAME,)
R2.ThreadPoolExecutor = lambda max_workers: ThreadPoolExecutor(max_workers=8)


class _SlowerTimeout:
    """The unit-array netlists are larger; scale only the wall-clock guard (15 s/point) by 4."""

    def __getattr__(self, name):
        return getattr(subprocess, name)

    @staticmethod
    def run(*args, timeout=None, **kwargs):
        return subprocess.run(*args, timeout=None if timeout is None else 4 * timeout, **kwargs)


S.subprocess = _SlowerTimeout()

if BITS > 5:
    # Protocol deviation (b only): the shared select_trim validates max_code <= 31. A local copy with
    # only that guard raised to 63 is used; the scan/bisection algorithm itself is unchanged.
    import inspect
    import comparator_atlas.experiments as E
    import comparator_atlas.study as ST
    source = inspect.getsource(E.select_trim)
    assert source.count("<= 31") == 1 and source.count("between 1 and 31") == 1
    namespace = dict(vars(E))
    exec(source.replace("<= 31", "<= 63").replace("between 1 and 31", "between 1 and 63"), namespace)
    ST.select_trim = namespace["select_trim"]

if __name__ == "__main__":
    cmd = ARGS[1]
    if cmd == "phase_a":
        R2.run_phase(NAME, R2.FIT_INPUTS, "phase_a")
    elif cmd == "phase_b":
        R2.run_phase(NAME, R2.HELD_INPUTS, "phase_b")
    elif cmd == "register":
        R2.register(VARIANT, [NAME])
    elif cmd == "evaluate":
        R2.evaluate()
    elif cmd == "residuals":
        table = R2.residual_table(NAME)[["case_id", "code", "residual_mv", "halfwidth_mv"]]
        table.to_csv(R2.OUT / f"{NAME}_residuals.csv", index=False, lineterminator="\n")
