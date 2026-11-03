"""r26f probe: trim strength of the decoder design (default TT) against decoder channel length L and an optional square
nfet hold capacitor (side H um) on each segment gate.  usage: python -B r26f_kick.py <L> [H] [corner]
Writes out/r26f/kick_L<L>_H<H>[_<corner>].json with the code -31/-16 boundaries and the segment-gate dip at code -31."""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

if len(sys.argv) > 1:  # spawned workers inherit the environment, not argv
    os.environ["R26F_L"] = sys.argv[1]
    os.environ["R26F_HOLD"] = sys.argv[2] if len(sys.argv) > 2 else "0"
    os.environ["R26F_CORNER"] = sys.argv[3] if len(sys.argv) > 3 else "tt"
sys.argv = sys.argv[:1]
import r26f_dec as F  # noqa: E402

COND = next(c for c in F.G.S.DNL_CONDS if c[0] == os.environ.get("R26F_CORNER", "tt"))
CODES = [-31, -16]


def _one(c):
    s = F.G._nominal(F.DESIGN, COND)
    return c, s.boundaries([c], lo=-F.G.S.R22.LIMIT_MV, hi=F.G.S.R22.LIMIT_MV)[c]


if __name__ == "__main__":
    with ProcessPoolExecutor(len(CODES) + 1) as ex:
        dip = ex.submit(F._kick, ("d", COND))
        b = dict(ex.map(_one, CODES))
        dip = dip.result()
    res = {"L": F.L_DEC, "hold_um": F.HOLD, "cond": list(COND), "b_mv": b, "dip_mv": dip["dip_mv"],
           "below_10mv_ps": dip["below_10mv_ps"]}
    suffix = "" if COND[0] == "tt" else f"_{COND[0]}"
    (F.OUT_F / f"kick_L{F.L_DEC:g}_H{F.HOLD:g}{suffix}.json").write_text(json.dumps(res, indent=1))
    print(res, flush=True)
