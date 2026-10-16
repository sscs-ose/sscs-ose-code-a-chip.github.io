"""R5 (substitute for PEX, which needs a layout this entry does not have): pre-layout parasitic
sensitivity of the selected design. Symmetric node capacitance (routing load) and a one-sided
imbalance on xp (asymmetric routing) are added inside the comparator; each variant is recalibrated
with the same trim search as R3, then timed at +/-3, 10, 30 mV to refit tau.

  python r5_parasitic.py run <design>
"""
import json
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r3_mismatch_mc as r3  # noqa: E402
from r3_mismatch_mc import DEADLINES, Point, Sample, measure  # noqa: E402

OUT = r3.HERE / "out" / "r5"
VARIANTS = {
    "nominal": {},
    "sym_2fF": {"xp": 2, "xn": 2, "qp": 2, "qn": 2},
    "sym_5fF": {"xp": 5, "xn": 5, "qp": 5, "qn": 5},
    "xp_imb_0p2fF": {"xp": 0.2},
    "xp_imb_0p5fF": {"xp": 0.5},
    "qp_imb_0p5fF": {"qp": 0.5},
}
CONDITIONS = (("tt", 1.8, 27.0), ("ss", 1.62, -40.0), ("ff", 1.95, 125.0))
FIT_MV = (-30, -10, -3, 3, 10, 30)


class Parasitic(Sample):
    def __init__(self, design, caps, cond, sim, sig):
        super().__init__(design, 0, sim, sig)
        zero = {k: 0.0 for k in self.z}
        self.z = zero
        circuit = r3.mutated_circuit(design, zero, sig)
        extra = "\n".join(f"Cpar_{n} {n} 0 {c}f" for n, c in caps.items())
        self.circuit = circuit.replace(".ends atlas", (extra + "\n" if extra else "") + ".ends atlas")
        corner, vdd, temp = cond
        self.base = Point(design_name=design, pair_skew=0.0, trim_code=0, differential_v=0.0,
                          corner=corner, vdd_v=vdd, temperature_c=temp)


def run(design: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sig = r3.sigma(design)
    sim = r3.Simulator(r3.HERE / "cache" / "r3_unused", workers=1)
    path = OUT / f"r5_{design}.json"
    res = json.loads(path.read_text()) if path.exists() else {}
    for cond in CONDITIONS:
        for name, caps in VARIANTS.items():
            key = f"{cond[0]}|{cond[1]}|{cond[2]}|{name}"
            if key in res:
                continue
            s = Parasitic(design, caps, cond, sim, sig)
            cal = s.run()
            m = cal["m_mv"]
            pts = [replace(s.base, differential_v=v * 1e-3, trim_code=cal["code"]) for v in FIT_MV]
            xs, ys = [], []
            for tr in s.traces(pts):
                t = measure(tr, 3.5).decision_time_ns
                v = tr.point.differential_v * 1e3
                if t is not None and v != m:
                    xs.append(math.log(1.0 / abs(v - m)))
                    ys.append(t)
            tau, t0 = np.polyfit(xs, ys, 1) if len(xs) >= 3 else (math.nan, math.nan)
            vstar = {str(D): abs(m) + math.exp(-(D - t0) / tau) if tau > 0 else math.inf for D in DEADLINES}
            res[key] = {"b0_mv": cal["b0_mv"], "code": cal["code"], "m_mv": m, "tau_ps": tau * 1e3,
                        "t0_ns": t0, "vstar_mv": vstar, "evals": cal["evals"]}
            path.write_text(json.dumps(res, indent=1))
            print(f"{key}: b0={cal['b0_mv']:+.2f} code={cal['code']} m={m:+.2f} tau={tau*1e3:.1f}ps "
                  f"t0={t0:.3f} v*(1ns)={vstar['1.0']:.2f}", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(sys.argv[2])
