"""r26c: nominal unit-cell transfer at 0.01 mV resolution (r3 bisection TOL 0.2 mV leaves +-0.15 mV per boundary,
so the coarse steps alternate within +-0.3 mV). Re-bisects codes 0..11 inside +-0.4 mV of the coarse boundary.

  python -B r26c_fine.py      # writes out/r26b/fine_transfer.json
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r26b_unit as U  # noqa: E402
import r26c_stats as R  # noqa: E402

CONDS = (("ss", 1.62, -40.0), ("tt", 1.8, 27.0), ("sf", 1.95, 125.0))
CODES = range(12)


def _job(args):
    cond, codes = args
    U.R3.TOL_MV = 0.01
    coarse = R._transfer("u5_k150")[cond[0]]
    s = U.T._nominal(U.register(5, 1.5), cond)
    return cond[0], {c: s.boundaries([c], lo=coarse[c] - 0.4, hi=coarse[c] + 0.4)[c] for c in codes}


def main():
    U.os.environ.pop("R24_PRIOR_MV", None)
    jobs = [(c, list(CODES)[i:i + 3]) for c in CONDS for i in range(0, len(CODES), 3)]
    res = {}
    with ProcessPoolExecutor(4) as ex:
        for k, o in ex.map(_job, jobs):
            res.setdefault(k, {}).update(o)
    (U.OUT / "fine_transfer.json").write_text(json.dumps({k: {str(c): v for c, v in sorted(o.items())}
                                                          for k, o in res.items()}, indent=1))
    for k, o in res.items():
        print(k, "step", " ".join(f"{o[c + 1] - o[c]:+.3f}" for c in sorted(o)[:-1]))


if __name__ == "__main__":
    main()
