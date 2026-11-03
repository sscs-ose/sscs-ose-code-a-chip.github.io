"""r17: post-layout estimate of unit6_w6 (r15b: input W 6, 6-bit unit trim) on the b1 RC extraction,
plus a corrected unit-array schematic reference for the r11 5-bit fix.
Same method as r11 (r6 variant netlists: input x2, optional half q wiring; every bit-k trim device
split into 2^k unit copies on its extracted nodes), now adding bit 4 (16 copies, bit-3 s/t wiring
caps x2) and bit 5 (32 copies, caps x4) on bit-3's extracted x/vin/tail nodes (estimate, no extra
resistance). r11's "schematic" row simulated the binary-sized 5-bit netlist; schematic_unit5 here is
the unit-array netlist it should have used. Nominal devices, code 0, 5 fF loads. Local only.
  python -B r17_post_layout_6b.py run [threads]
  python -B r17_post_layout_6b.py report
"""
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r3_mismatch_mc as r3  # noqa: E402
import r6_layout_budget as r6  # noqa: E402
import r11_post_layout_5b as r11  # noqa: E402
from comparator_atlas.designs import DESIGNS, Design  # noqa: E402
from r3_mismatch_mc import COLUMNS, Point, Trace, circuit_text, get_design, measure  # noqa: E402
from r7_trim_dnl import unit_array  # noqa: E402
from r10_combo5b import NAME as NAME5  # noqa: E402

NAME6 = "unit6_w6"
DESIGNS[NAME6] = Design(NAME6, input_device="nfet_01v8_lvt", input_w=6, tail_w=7, trim_bits=6)
OUT = r6.HERE / "out" / "r17"
SPECS = {
    "rc_unit6": {"mode": "rc", "resize": {"input": 2.0}},
    "rc_unit6_half_q": {"mode": "rc", "resize": {"input": 2.0}, "caps": [(r6.touches(r6.Q), 0.5)]},
}
PORTS = "vinp vinn clk vdd vss qp qn " + " ".join(f"t{s}{b}" for s in "pn" for b in range(6))
ADDED = ((4, 16, 2.0), (5, 32, 4.0))  # bit, unit copies, bit-3 wiring-cap scale
SCHEM = {NAME5: circuit_text(get_design(NAME5)), NAME6: circuit_text(get_design(NAME6))}
assert f".subckt atlas {PORTS}" in SCHEM[NAME6]
NETS = {"schematic_unit5": (NAME5, unit_array(SCHEM[NAME5], 5)),
        "schematic_unit6": (NAME6, unit_array(SCHEM[NAME6], 6))}
INPUTS = {"schematic_unit5": (-10.0, -3.0, 3.0, 10.0)}
DEFAULT_INPUTS = (-10.0, -3.0, -1.0, 1.0, 3.0, 10.0)


class _SlowerTimeout:
    """Larger netlists under 12 parallel decks: scale only r3's wall-clock guard (900 s) by 4."""

    def __getattr__(self, name):
        return getattr(subprocess, name)

    @staticmethod
    def run(*args, timeout=None, **kwargs):
        return subprocess.run(*args, timeout=None if timeout is None else 4 * timeout, **kwargs)


r3.subprocess = _SlowerTimeout()


def build(spec: dict) -> str:
    out, bit3, caps3 = [], {}, []
    for line in r6.variant_netlist(spec).splitlines():
        if line.startswith(".subckt atlas"):
            out.append(f".subckt atlas {PORTS}")
            continue
        m = r11.DEV.match(line)
        if m:
            name, nodes, dev, w, l = m.group(1), list(m.group(2, 3, 4, 5)), m.group(6), float(m.group(11)), m.group(12)
            base = [r6.base(n) for n in nodes]
            trim = re.fullmatch(r"s([pn])(\d)", base[0]) or re.fullmatch(r"s([pn])(\d)", base[2])
            if trim:
                side, k = trim.group(1), int(trim.group(2))
                switch = base[1] == f"t{side}{k}"
                unit = 1.0 if switch else 0.42
                assert abs(w - unit * 2 ** k) < 1e-6, line
                out += r11.unit_dev(name, nodes, dev, unit, l, 2 ** k)
                if k == 3:
                    bit3[(side, switch)] = (name, nodes, dev, unit, l)
                continue
        cm = r6.CAP.match(line) or re.match(r"^(C\d+) (\S+) (\S+) ([\d.eE+-]+)f$", line)
        if cm and ({cm.group(2), cm.group(3)} & {"sp3", "sn3", "tp3", "tn3"}):
            caps3.append(cm)
        out.append(line)
    assert len(bit3) == 4, bit3.keys()
    extra = []
    for bit, copies, scale in ADDED:
        for (side, switch), (name, nodes, dev, unit, l) in bit3.items():
            new = [re.sub(rf"^(s|t){side}3\.\w+$", rf"\g<1>{side}{bit}", n) for n in nodes]
            assert sum(n in (f"s{side}{bit}", f"t{side}{bit}") for n in new) == (2 if switch else 1), new
            extra += r11.unit_dev(f"{name}b{bit}", new, dev, unit, l, copies)
        ren = {f"{t}{s}3": f"{t}{s}{bit}" for t in "st" for s in "pn"}
        for i, cm in enumerate(caps3):
            a, b = ren.get(cm.group(2), cm.group(2)), ren.get(cm.group(3), cm.group(3))
            extra.append(f"Cb{bit}_{i} {a} {b} {scale * float(cm.group(4)):.6g}f")
    ends = [i for i, l in enumerate(out) if l.strip() in (".ends", ".ends atlas")]
    assert len(ends) == 1
    return "\n".join(out[:ends[0]] + extra + out[ends[0]:]) + "\n"


def simulate(name, cond, v_mv):
    design, net = NETS[name]
    p = Point(design_name=design, corner=cond[0], vdd_v=cond[1], temperature_c=cond[2],
              differential_v=v_mv * 1e-3, pair_skew=0.0, trim_code=0, load_ff=5.0, max_step_ps=5.0)
    header = r6.SIM._header(p)
    assert SCHEM[design] in header
    header = header.replace(SCHEM[design], net)
    deck = "\n".join([header, ".control", "set wr_singlescale", "set wr_vecnames", "set numdgt=15",
                      r6.SIM._analysis(p, "p0.tsv"), "quit 0", ".endc", ".end"]) + "\n"
    _, files = r3.ngspice(deck)
    values = np.loadtxt(files["p0.tsv"].splitlines(), skiprows=1, dtype=np.float64)
    assert values.shape[1] == len(COLUMNS)
    tr = Trace(p, values, f"r17_{name}", OUT)
    ms = measure(tr, 3.5)
    return {"variant": name, "cond": list(cond), "v_mv": v_mv, "outcome": ms.outcome,
            "t_ns": ms.decision_time_ns, "energy_fj": ms.core_energy_fj,
            "at": {str(d): measure(tr, d).outcome for d in (0.75, 1.0, 2.0)}}


def run(threads: int) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for n, s in SPECS.items():
        NETS[n] = (NAME6, build(s))
        (OUT / f"{n}.spice").write_text(NETS[n][1])
    path = OUT / "r17_pvt45.jsonl"
    done = set()
    if path.exists():
        done = {(r["variant"], tuple(r["cond"]), r["v_mv"]) for r in map(json.loads, path.read_text().splitlines())}
    jobs = [(n, c, v) for n in NETS for c in r6.PVT45 for v in INPUTS.get(n, DEFAULT_INPUTS)
            if (n, tuple(c), v) not in done]
    with ThreadPoolExecutor(threads) as ex, path.open("a") as f:
        for res in ex.map(lambda j: simulate(*j), jobs):
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(res["variant"], res["cond"], res["v_mv"], res["at"], flush=True)


def report() -> None:
    rows = [json.loads(l) for l in (OUT / "r17_pvt45.jsonl").read_text().splitlines()]
    out = {}
    for n in ("schematic_unit5", "schematic_unit6", *SPECS):
        rs = [r for r in rows if r["variant"] == n]
        d = {"n": len(rs)}
        for group, keep in (("all", lambda r: True), ("1mv", lambda r: abs(r["v_mv"]) == 1.0),
                            ("3_10mv", lambda r: abs(r["v_mv"]) >= 3.0)):
            sub = [r for r in rs if keep(r)]
            if not sub:
                continue
            for dl in ("0.75", "1.0", "2.0"):
                d[f"{group}_correct@{dl}ns"] = f"{sum(r['at'][dl] == 'correct' for r in sub)}/{len(sub)}"
                d[f"{group}_wrong@{dl}ns"] = sum(r["at"][dl] == "wrong" for r in sub)
            d[f"{group}_worst_t_ns"] = max(r["t_ns"] or 99 for r in sub)
        d["energy_mean_fj"] = float(np.mean([r["energy_fj"] for r in rs])) if rs else None
        out[n] = d
    (OUT / "r17_report.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    if ARGS and ARGS[0] == "run":
        run(int(ARGS[1]) if len(ARGS) > 1 else 4)
    else:
        report()
