"""r19 (RC part): does the r18 candidate u6_w12_l05 (6-bit unit trim, trim L 0.5 um, input W 12 um)
reach +/-1 mV at 1 ns on the b1 RC extraction estimate where unit6_w6 does not (r17)?
Same method as r17 with the extracted input pair resized x4 (3 -> 12 um) and every trim channel
shortened to L = 0.5 um (wiring kept as extracted). Nominal devices, code 0, 5 fF, 45 PVT,
v = +/-1, 3 mV. Also: unit6_w6 with no q-node wiring (bounds what wiring alone can recover).
Local only.
  python -B r19_rc_wide.py run [threads]
  python -B r19_rc_wide.py report
"""
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r6_layout_budget as r6  # noqa: E402
import r17_post_layout_6b as r17  # noqa: E402
from comparator_atlas.designs import DESIGNS, Design  # noqa: E402
from r3_mismatch_mc import circuit_text, get_design  # noqa: E402
from r7_trim_dnl import unit_array  # noqa: E402

NAMEW = "u6_w12_l05"
DESIGNS[NAMEW] = Design(NAMEW, input_device="nfet_01v8_lvt", input_w=12, tail_w=7, trim_l=0.5, trim_bits=6)
OUT = r6.HERE / "out" / "r19"
r17.OUT = OUT
r17.SCHEM[NAMEW] = circuit_text(get_design(NAMEW))
r17.NETS = {"schematic_w12_l05": (NAMEW, unit_array(r17.SCHEM[NAMEW], 6))}
SPECS = {
    "rc_w12_l05": ({"mode": "rc", "resize": {"input": 4.0}}, NAMEW, 0.5),
    "rc_w12_l05_half_q": ({"mode": "rc", "resize": {"input": 4.0}, "caps": [(r6.touches(r6.Q), 0.5)]}, NAMEW, 0.5),
    "rc_unit6_no_q": ({"mode": "rc", "resize": {"input": 2.0}, "caps": [(r6.touches(r6.Q), 0.0)]}, r17.NAME6, 1.0),
}
INPUTS = (-3.0, -1.0, 1.0, 3.0)
ORDER = ("schematic_w12_l05", "rc_w12_l05", "rc_w12_l05_half_q", "rc_unit6_no_q")


def build(spec: dict, trim_l: float) -> str:
    text = r17.build(spec)
    if trim_l == 1.0:
        return text
    lines, n = text.splitlines(), 0
    for i, line in enumerate(lines):
        if "nfet_01v8_lvt" in line and line.endswith(" w=0.42 l=1"):
            lines[i] = line[:-len("l=1")] + f"l={trim_l:g}"
            n += 1
    assert n == 2 * 63, n
    return "\n".join(lines) + "\n"


def run(threads: int) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (spec, design, trim_l) in SPECS.items():
        r17.NETS[name] = (design, build(spec, trim_l))
        (OUT / f"{name}.spice").write_text(r17.NETS[name][1])
    path = OUT / "r19_rc.jsonl"
    done = set()
    if path.exists():
        done = {(r["variant"], tuple(r["cond"]), r["v_mv"]) for r in map(json.loads, path.read_text().splitlines())}
    jobs = [(n, c, v) for n in ORDER for c in r6.PVT45 for v in INPUTS if (n, tuple(c), v) not in done]
    with ThreadPoolExecutor(threads) as ex, path.open("a") as f:
        for res in ex.map(lambda j: r17.simulate(*j), jobs):
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(res["variant"], res["cond"], res["v_mv"], res["at"], flush=True)


def report() -> None:
    rows = [json.loads(l) for l in (OUT / "r19_rc.jsonl").read_text().splitlines()]
    out = {}
    for n in ORDER:
        rs = [r for r in rows if r["variant"] == n]
        d = {"n": len(rs)}
        for group, keep in (("1mv", lambda r: abs(r["v_mv"]) == 1.0), ("3mv", lambda r: abs(r["v_mv"]) == 3.0)):
            sub = [r for r in rs if keep(r)]
            for dl in ("0.75", "1.0", "2.0"):
                d[f"{group}_correct@{dl}ns"] = f"{sum(r['at'][dl] == 'correct' for r in sub)}/{len(sub)}"
                d[f"{group}_wrong@{dl}ns"] = sum(r["at"][dl] == "wrong" for r in sub)
            d[f"{group}_worst_t_ns"] = max(r["t_ns"] or 99 for r in sub)
        d["energy_mean_fj"] = float(np.mean([r["energy_fj"] for r in rs]))
        out[n] = d
    (OUT / "r19_rc_report.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    if ARGS and ARGS[0] == "run":
        run(int(ARGS[1]) if len(ARGS) > 1 else 4)
    else:
        report()
