#!/usr/bin/env python3
"""Run the sizing flow outside the notebook (same code the notebook calls), writing every cache it reads.

  python tools/run_flow.py                 # 9T and 12T screens + SPICE verification for the Table 2 spec
  python tools/run_flow.py --rerun         # ignore caches
  python tools/run_flow.py --spec cl3p     # the generalisation run (second specification)

Run from the submission folder. Needs ngspice + SKY130 for the SPICE stages; the screen needs only Python.
SPDX-License-Identifier: Apache-2.0
"""
import sys, json, time, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import os; os.chdir(ROOT)
import vga_flow as vf, evaluator as ev, flow

LUT = ROOT / "cache" / "lut_sky130.npz"


SPECS = {
    "table2": flow.Spec(),
    # generalisation: a next stage with three times the input capacitance - same code, new constraint
    "cl3p": flow.Spec(name="CL3p (3 pF load)", CL=3e-12, max_spice=8),
    # generalisation: a tighter supply-current budget - same code, same screen, a different constraint
    "lowpower": flow.Spec(name="Low-power (3 µA budget)", i_tot_max=3e-6, max_spice=8),
    # layout in the loop: the first extracted layout's output wiring, as the lumped capacitance that reproduces its
    # effect on bandwidth (cache/wire_fit.json, tools/freeze_pick.py --fit), rounded up to 0.05 pF - same spec otherwise
    "wire": flow.wire_spec(ROOT / "cache"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rerun", action="store_true")
    ap.add_argument("--spec", default="table2", choices=list(SPECS))
    ap.add_argument("--only", choices=("9T", "12T"))
    ap.add_argument("--rescreen", action="store_true", help="re-run the LUT screens only (keeps SPICE caches)")
    a = ap.parse_args()
    spec = SPECS[a.spec]
    base = dict(vf.BASELINE)
    summary = {}
    library = [t for t in ("9T", "12T") if not a.only or t == a.only]
    if a.spec != "table2":
        library = [t for t in library if t != "9T"]
    t = time.time()
    loop = flow.run_topologies(spec, library, LUT, base, rerun_screen=a.rerun or a.rescreen, rerun_spice=a.rerun)
    for topo, res in loop["results"].items():
        if topo == "9T":
            f = ROOT / "cache" / "flow_9T_confirm.json"
            if a.rerun or not f.exists():
                f.write_text(json.dumps(flow.confirm_best(res, base, spec=spec), indent=0))
        dg = res["diagnosis"]
        summary[topo] = dict(n=res["n"], feasible=res["n_feasible"], front=res["n_front"],
                             passed=sum(v["passed"] for v in res["verified"]),
                             pick=res["pick"]["point"] if res["pick"] else None,
                             binding_limit=dg["binding"] + (" (structural)" if dg["structural"] else ""))
    summary["selected"] = loop["selected"]; summary["seconds"] = time.time() - t
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
