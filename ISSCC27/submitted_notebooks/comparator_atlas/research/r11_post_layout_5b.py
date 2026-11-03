"""r11: post-layout estimate of the r10 design (input x2 + unit-element trim + 5 bits) on the b1 RC
extraction. Starts from r6 variant netlists (input x2, optional half q wiring), then
  * splits every bit-k trim device (lvt W=0.42*2^k, switch W=2^k) into 2^k unit copies on the same
    extracted nodes (total diffusion kept),
  * adds bit 4 as 16 unit copies on bit-3's extracted x/vin/tail nodes, with new nodes s{p,n}4 and
    ports t{p,n}4; bit-4 wiring = bit-3's s/t wiring caps x2 (estimate, no extra resistance).
Nominal devices (no mismatch), code 0, 5 fF loads. Local simulation only; no source file modified.
  python -B r11_post_layout_5b.py run [threads]
  python -B r11_post_layout_5b.py report
"""
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r3_mismatch_mc as r3
import r6_layout_budget as r6
from r3_mismatch_mc import COLUMNS, Point, Trace, circuit_text, get_design, measure
from r10_combo5b import NAME

OUT = r6.HERE / "out" / "r11"
DEV = re.compile(r"^(X\d+) (\S+) (\S+) (\S+) (\S+) (\S+) ad=(\S+) pd=(\S+) as=(\S+) ps=(\S+) w=(\S+) l=(\S+)$")
SPECS = {
    "rc_x2_unit5b": {"mode": "rc", "resize": {"input": 2.0}},
    "rc_x2_unit5b_half_q": {"mode": "rc", "resize": {"input": 2.0}, "caps": [(r6.touches(r6.Q), 0.5)]},
}
PORTS = "vinp vinn clk vdd vss qp qn " + " ".join(f"t{s}{b}" for s in "pn" for b in range(5))


def unit_dev(name, nodes, dev, w_unit, l, copies):
    a, p = 0.29 * w_unit, 2 * (0.29 + w_unit)
    return [f"{name}u{j} {' '.join(nodes)} {dev} ad={a:.6g} pd={p:.6g} as={a:.6g} ps={p:.6g} w={w_unit:.6g} l={l}"
            for j in range(copies)]


def build(spec: dict) -> str:
    out, bit3 = [], {}
    caps3 = []
    for line in r6.variant_netlist(spec).splitlines():
        if line.startswith(".subckt atlas"):
            out.append(f".subckt atlas {PORTS}")
            continue
        m = DEV.match(line)
        if m:
            name, nodes, dev, w, l = m.group(1), list(m.group(2, 3, 4, 5)), m.group(6), float(m.group(11)), m.group(12)
            base = [r6.base(n) for n in nodes]
            trim = re.fullmatch(r"s([pn])(\d)", base[0]) or re.fullmatch(r"s([pn])(\d)", base[2])
            if trim:
                side, k = trim.group(1), int(trim.group(2))
                switch = base[1] == f"t{side}{k}"
                unit = 1.0 if switch else 0.42
                assert abs(w - unit * 2 ** k) < 1e-6, line
                out += unit_dev(name, nodes, dev, unit, l, 2 ** k)
                if k == 3:
                    new = [re.sub(rf"^(s|t){side}3\.\w+$", rf"\g<1>{side}4", n) for n in nodes]
                    bit3[(side, switch)] = (name, new, dev, unit, l)
                continue
        cm = r6.CAP.match(line) or re.match(r"^(C\d+) (\S+) (\S+) ([\d.eE+-]+)f$", line)
        if cm and ({cm.group(2), cm.group(3)} & {"sp3", "sn3", "tp3", "tn3"}):
            caps3.append(cm)
        out.append(line)
    assert len(bit3) == 4, bit3.keys()
    extra = []
    for (side, switch), (name, nodes, dev, unit, l) in bit3.items():
        extra += unit_dev(f"{name}b4", nodes, dev, unit, l, 16)
    ren = {"sp3": "sp4", "sn3": "sn4", "tp3": "tp4", "tn3": "tn4"}
    for i, cm in enumerate(caps3):
        a, b = ren.get(cm.group(2), cm.group(2)), ren.get(cm.group(3), cm.group(3))
        extra.append(f"Cb4_{i} {a} {b} {2 * float(cm.group(4)):.6g}f")
    lines = out + extra
    ends = [i for i, l in enumerate(lines) if l.strip() in (".ends", ".ends atlas")]
    assert len(ends) == 1 and ends[0] < len(out)
    end = out.index(lines[ends[0]])
    return "\n".join(out[:end] + extra + out[end:]) + "\n"


SIM = r6.SIM
SCHEM = circuit_text(get_design(NAME))
NETS = {}


def simulate(name, cond, v_mv):
    p = Point(design_name=NAME, corner=cond[0], vdd_v=cond[1], temperature_c=cond[2],
              differential_v=v_mv * 1e-3, pair_skew=0.0, trim_code=0, load_ff=5.0, max_step_ps=5.0)
    header = SIM._header(p)
    if name != "schematic":
        assert SCHEM in header
        header = header.replace(SCHEM, NETS[name])
    deck = "\n".join([header, ".control", "set wr_singlescale", "set wr_vecnames", "set numdgt=15",
                      SIM._analysis(p, "p0.tsv"), "quit 0", ".endc", ".end"]) + "\n"
    _, files = r3.ngspice(deck)
    values = np.loadtxt(files["p0.tsv"].splitlines(), skiprows=1, dtype=np.float64)
    assert values.shape[1] == len(COLUMNS)
    tr = Trace(p, values, f"r11_{name}", OUT)
    ms = measure(tr, 3.5)
    return {"variant": name, "cond": list(cond), "v_mv": v_mv, "outcome": ms.outcome,
            "t_ns": ms.decision_time_ns, "energy_fj": getattr(ms, "core_energy_fj", None),
            "at": {str(d): measure(tr, d).outcome for d in (0.75, 1.0, 2.0)}}


def run(threads: int) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for n, s in SPECS.items():
        NETS[n] = build(s)
        (OUT / f"{n}.spice").write_text(NETS[n])
    path = OUT / "r11_pvt45.jsonl"
    done = set()
    if path.exists():
        done = {(r["variant"], tuple(r["cond"]), r["v_mv"]) for r in map(json.loads, path.read_text().splitlines())}
    jobs = [(n, c, v) for n in ["schematic", *SPECS] for c in r6.PVT45 for v in (-10.0, -3.0, 3.0, 10.0)
            if (n, tuple(c), v) not in done]
    with ThreadPoolExecutor(threads) as ex, path.open("a") as f:
        for res in ex.map(lambda j: simulate(*j), jobs):
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(res["variant"], res["cond"], res["v_mv"], res["at"], flush=True)


def report() -> None:
    rows = [json.loads(l) for l in (OUT / "r11_pvt45.jsonl").read_text().splitlines()]
    out = {}
    for n in ["schematic", *SPECS]:
        rs = [r for r in rows if r["variant"] == n]
        d = {"n": len(rs)}
        for dl in ("0.75", "1.0", "2.0"):
            d[f"correct@{dl}ns"] = sum(r["at"][dl] == "correct" for r in rs)
            d[f"fail@{dl}ns"] = sorted({"/".join(map(str, r["cond"])) for r in rs if r["at"][dl] != "correct"})
        d["worst_t_ns"] = max(r["t_ns"] or 99 for r in rs) if rs else None
        d["energy_mean_fj"] = float(np.mean([r["energy_fj"] for r in rs])) if rs else None
        out[n] = d
    (OUT / "r11_report.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    if ARGS and ARGS[0] == "run":
        run(int(ARGS[1]) if len(ARGS) > 1 else 4)
    else:
        report()
