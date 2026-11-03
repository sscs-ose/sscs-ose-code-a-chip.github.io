"""r18: can a 6-bit unit trim reach the same step for less energy? Screen at TT, nominal devices.

Trim step scales roughly with (W_unit / L_unit) / W_input, and trim energy with trim gate area. W_unit is
already the 0.42 um minimum, so variants trade a wider input pair for a shorter trim L (same step,
less trim area) and a narrower per-unit switch. Per variant: core energy (r14 deck: +3 mV, 5 fF,
codes 0 and 63) and the code-0 / +-16 / +-63 switching inputs at the 3.5 ns calibration deadline.
Local only.
  python -B r18_energy_screen.py screen [variant ...]   # appends out/r18/screen.jsonl
"""
import json
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r3_mismatch_mc as R3  # noqa: E402  (puts the desktop root on sys.path)
import r14_energy as R14  # noqa: E402
import comparator_atlas.spice as S  # noqa: E402
from comparator_atlas.designs import DESIGNS, Design  # noqa: E402
from r3_mismatch_mc import HERE, Point, Sample, Simulator  # noqa: E402
from r7_trim_dnl import unit_array  # noqa: E402
from r8_unit_trim_mc import mutate  # noqa: E402

OUT = HERE / "out" / "r18"
# name: (input_w, trim_l, switch unit w[, "drain": switch between xp/xn and the trim device])
VARIANTS = {
    "u6_w6_l1_s1": (6, 1.0, 1.0),      # r15b unit6_w6
    "u6_w6_l1_s042": (6, 1.0, 0.42),
    "u6_w6_l05_s1": (6, 0.5, 1.0),
    "u6_w12_l05_s1": (12, 0.5, 1.0),
    "u6_w12_l05_s042": (12, 0.5, 0.42),
    "u6_w24_l025_s042": (24, 0.25, 0.42),
    "d6_w6_l1_s1": (6, 1.0, 1.0, "drain"),
    "d6_w12_l05_s1": (12, 0.5, 1.0, "drain"),
}
SWITCH, DRAIN = {}, set()
for _name, (_w, _l, _s, *_side) in VARIANTS.items():
    DESIGNS[_name] = Design(_name, input_device="nfet_01v8_lvt", input_w=_w, tail_w=7, trim_l=_l, trim_bits=6)
    SWITCH[_name] = _s
    if _side:
        DRAIN.add(_name)
    R14.VARIANTS[_name] = (_w, 6, "unit")
_designs_text = R3.circuit_text


def drain_side(text: str) -> str:
    """xp - trim(vin) - sp - switch - tail  ->  xp - switch - sp - trim(vin) - tail (and n side)."""
    out, n = [], 0
    for line in text.splitlines():
        m = re.match(r"^(Xt([pn])\d+(?:u\d+)?) (x[pn]) (vin[pn]) (s[pn]\d+) vss (.*)$", line)
        if m:
            line = f"{m[1]} {m[5]} {m[4]} tail vss {m[6]}"
            n += 1
        m = re.match(r"^(Xs([pn])\d+(?:u\d+)?) (s[pn]\d+) (t[pn]\d+) tail vss (.*)$", line)
        if m:
            line = f"{m[1]} x{m[2]} {m[4]} {m[3]} vss {m[5]}"
            n += 1
        out.append(line)
    assert n == 4 * 63, n
    return "\n".join(out) + "\n"


def variant_text(design) -> str:
    text = _designs_text(design)
    if design.name not in SWITCH:
        return text
    text = unit_array(text, design.trim_bits)
    if design.name in DRAIN:
        text = drain_side(text)
    s = SWITCH[design.name]
    if s != 1.0:
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if re.match(r"^Xs[pn]\d", line):
                assert lines[i + 1].startswith("+ w={1} "), lines[i + 1]
                lines[i + 1] = lines[i + 1].replace("w={1}", f"w={{{s:g}}}")
                lines[i + 2] = f"+ ad={{{0.29 * s:g}}} as={{{0.29 * s:g}}}"
                lines[i + 3] = f"+ pd={{{2 * (0.29 + s):g}}} ps={{{2 * (0.29 + s):g}}}"
        text = "\n".join(lines) + "\n"
    return text


S.circuit_text = variant_text


class Nominal(Sample):
    """Zero-mismatch sample; the series gate sources are all 0 V."""

    def __init__(self, name, cond):
        self.design, self.seed, self.cond, self.runs = name, 0, cond, 0
        self.sim = Simulator(HERE / "cache" / "r3_unused", workers=1)
        text = variant_text(DESIGNS[name])
        self.z = defaultdict(float)
        self.circuit = mutate(text, self.z, defaultdict(float))
        self.base = Point(design_name=name, pair_skew=0.0, trim_code=0, differential_v=0.0,
                          corner=cond[0], vdd_v=cond[1], temperature_c=cond[2])


R3.circuit_text = variant_text  # Sample.traces swaps this (header) text for the zero-shift mutated copy


def transfer(name: str, cond) -> dict:
    b = Nominal(name, cond).boundaries([0, -16, 16, -63, 63])
    return {"boundaries_mv": {str(k): v for k, v in b.items()},
            "lsb_mv": (b[-63] - b[63]) / 126, "lsb16_mv": (b[-16] - b[16]) / 32}


def screen(name: str) -> dict:
    cond = ("tt", 1.8, 27.0)
    e0, e63 = (R14.one((name, cond, code)) for code in (0, 63))
    row = {"variant": name, "input_w": VARIANTS[name][0], "trim_l": VARIANTS[name][1],
           "switch_w": VARIANTS[name][2], "cond": list(cond),
           "energy_fj_code0": e0["core_energy_fj"], "energy_fj_code63": e63["core_energy_fj"],
           "t_ns_code0": e0["decision_time_ns"], "gate_area_proxy_um2": DESIGNS[name].gate_area_um2,
           **transfer(name, cond)}
    print(json.dumps(row), flush=True)
    return row


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    R14.OUT = OUT
    names = ARGS[1:] or list(VARIANTS)
    with ThreadPoolExecutor(max_workers=len(names)) as pool, (OUT / "screen.jsonl").open("a") as f:
        for row in pool.map(screen, names):
            f.write(json.dumps(row) + "\n")
