#!/usr/bin/env python3
"""The flow's self-checks outside the notebook, stored in the caches the notebook reads: the convergence check (the
same search from a shifted grid and from random points) and the margin-cost check (designs that pass only without the
LUT margins, simulated in SPICE). Run after `tools/run_flow.py`.

  python tools/flow_checks.py [--rerun] [--spec table2|wire] [--margin-only]
SPDX-License-Identifier: Apache-2.0
"""
import sys, time, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import os; os.chdir(ROOT)
import vga_flow as vf, flow, nbutil as nu, run_flow as rf

LUT = ROOT / "cache" / "lut_sky130.npz"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--rerun", action="store_true")
    ap.add_argument("--spec", default="table2", choices=list(rf.SPECS))
    ap.add_argument("--margin-only", action="store_true", help="skip the convergence check")
    a = ap.parse_args()
    nu.CAN_RUN = True
    SPEC, BASE = rf.SPECS[a.spec], dict(vf.BASELINE)
    sfx = "" if a.spec == "table2" else f"_{a.spec}"
    R12 = flow.run_flow(SPEC, "12T", LUT, BASE, spice=False, log=lambda *x: None)
    t = time.time()
    m = nu.cached("flow_margin_check" + sfx, lambda: flow.margin_check(R12, SPEC, BASE), a.rerun)
    print(f"margin check {time.time()-t:.0f} s: {m.get('n_pass')} of {len(m.get('verified', []))} pass; "
          f"{m.get('beats_pick')} beat the pick", flush=True)
    if a.margin_only:
        return
    t = time.time()
    c = nu.cached("flow_convergence" + sfx, lambda: flow.convergence_check(SPEC, BASE, LUT), a.rerun)
    main_ = flow.lut_choice(R12, SPEC)
    print(f"convergence {time.time()-t:.0f} s: main best {1e6*main_['best_vrms']:.2f} uV; " +
          "; ".join(f"{k}: best {1e6*v['best_vrms']:.2f} uV, same choice {v['point'] == main_['point']}" if v else f"{k}: none"
                    for k, v in c.items()), flush=True)


if __name__ == "__main__":
    main()
