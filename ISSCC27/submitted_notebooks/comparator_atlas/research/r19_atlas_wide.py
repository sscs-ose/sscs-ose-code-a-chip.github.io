"""r19 (atlas part): sealed 49-condition test of the r18 candidate u6_w12_l05 (6-bit unit trim with
trim L 0.5 um, input W 12 um). Hypothesis: the wider input pair has lower overdrive, so the
width-skew offset to be trimmed shrinks along with the trim range (37 mV vs 44 mV for unit6_w6 at TT).
Same r2/r15 protocol: 49 conditions, local_boundary calibration, fit inputs (phase A), predictions
sealed by SHA-256, then held-out inputs (phase B). As in r15b, a local copy of select_trim with only its
max_code guard raised from 31 to 63 is used (disclosed protocol deviation). Local only.
  python -B r19_atlas_wide.py phase_a
  python -B r19_atlas_wide.py register
  python -B r19_atlas_wide.py phase_b
  python -B r19_atlas_wide.py evaluate
  python -B r19_atlas_wide.py residuals
"""
import inspect
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r2_prospective as R2  # noqa: E402  (puts the desktop root on sys.path)
import comparator_atlas.experiments as E  # noqa: E402
import comparator_atlas.spice as S  # noqa: E402
import comparator_atlas.study as ST  # noqa: E402
from comparator_atlas.designs import DESIGNS, Design  # noqa: E402
from r7_trim_dnl import unit_array  # noqa: E402

NAME = "u6_w12_l05"
DESIGNS[NAME] = Design(NAME, input_device="nfet_01v8_lvt", input_w=12, tail_w=7, trim_l=0.5, trim_bits=6)
_orig = S.circuit_text
S.circuit_text = lambda d: unit_array(_orig(d), d.trim_bits) if d.name == NAME else _orig(d)

R2.OUT = R2.HERE / "out" / "r19"
R2.CACHE = R2.HERE / "cache" / "spice_r19"
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

source = inspect.getsource(E.select_trim)
assert source.count("<= 31") == 1 and source.count("between 1 and 31") == 1
namespace = dict(vars(E))
exec(source.replace("<= 31", "<= 63").replace("between 1 and 31", "between 1 and 63"), namespace)
ST.select_trim = namespace["select_trim"]

if __name__ == "__main__":
    cmd = ARGS[0]
    if cmd == "phase_a":
        R2.run_phase(NAME, R2.FIT_INPUTS, "phase_a")
    elif cmd == "phase_b":
        R2.run_phase(NAME, R2.HELD_INPUTS, "phase_b")
    elif cmd == "register":
        R2.register("w12", [NAME])
    elif cmd == "evaluate":
        R2.evaluate()
    elif cmd == "residuals":
        table = R2.residual_table(NAME)[["case_id", "code", "residual_mv", "halfwidth_mv"]]
        table.to_csv(R2.OUT / f"{NAME}_residuals.csv", index=False, lineterminator="\n")
