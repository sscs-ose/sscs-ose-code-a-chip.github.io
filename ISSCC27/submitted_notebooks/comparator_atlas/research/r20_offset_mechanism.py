"""r20: why does the wider input pair need less trim? Code-0 offset under the atlas width skew.

r19 found that u6_w12_l05 needs about a third of the trim codes of unit6_w6, and the r15/r19 calibration
records show that this is an offset reduction in mV, not a different LSB (TT 1.8 V 27 C, skew +4%:
W 3 -> 11.0 mV, W 6 -> 16.2 mV, W 12 -> 6.8 mV). Lower overdrive alone would make the offset fall
monotonically with W. Hypothesis: the deterministic width skew scales both the input device current
and its drain junction capacitance (ad/pd follow W), and these two effects oppose each other at xp/xn;
the trim array (off at code 0) and other fixed node capacitance set how much of the cancellation remains.
One factor at a time, nominal devices, code 0, skew +4%: input W, trim L, trim present or removed,
skew applied to the channel only or the junction only, extra symmetric capacitance on xp/xn.
Local only.
  python -B r20_offset_mechanism.py run [variant ...]   # appends out/r20/offset.jsonl
"""
import json
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r3_mismatch_mc as R3  # noqa: E402  (puts the desktop root on sys.path)
import comparator_atlas.designs as D  # noqa: E402
import comparator_atlas.spice as S  # noqa: E402
from comparator_atlas.designs import DESIGNS, Design  # noqa: E402
from r3_mismatch_mc import HERE, Point, Sample, Simulator  # noqa: E402
from r7_trim_dnl import unit_array  # noqa: E402
from r8_unit_trim_mc import mutate  # noqa: E402

OUT = HERE / "out" / "r20"
SKEW = 0.04
CONDS = [("tt", 1.8, 27.0), ("sf", 1.95, 27.0)]
# name: (input W, trim L or None for no trim array, skew mode, extra symmetric C on xp/xn in fF)
VARIANTS = {
    "w3_l1": (3, 1.0, "both", 0), "w6_l1": (6, 1.0, "both", 0),
    "w12_l1": (12, 1.0, "both", 0), "w24_l1": (24, 1.0, "both", 0),
    "w6_l05": (6, 0.5, "both", 0), "w12_l05": (12, 0.5, "both", 0), "w24_l05": (24, 0.5, "both", 0),
    "w3_none": (3, None, "both", 0), "w6_none": (6, None, "both", 0),
    "w12_none": (12, None, "both", 0), "w24_none": (24, None, "both", 0),
    "w6_l1_channel": (6, 1.0, "channel", 0), "w6_l1_junction": (6, 1.0, "junction", 0),
    "w12_l05_channel": (12, 0.5, "channel", 0), "w12_l05_junction": (12, 0.5, "junction", 0),
    "w6_none_channel": (6, None, "channel", 0), "w12_none_channel": (12, None, "channel", 0),
    "w6_l1_cx30": (6, 1.0, "both", 30), "w12_l05_cx10": (12, 0.5, "both", 10),
    "w12_l05_cx30": (12, 0.5, "both", 30), "w12_none_cx30": (12, None, "both", 30),
    # same total W, built from parallel fingers that sit in another SKY130 W bin (5.05-7 um or 3.0 um edge)
    "w12_l05_2x6": (12, 0.5, "both", 0), "w12_none_2x6": (12, None, "both", 0),
    "w24_none_4x6": (24, None, "both", 0), "w6_none_2x3": (6, None, "both", 0),
    "w12_none_4x3": (12, None, "both", 0),
}
FINGERS = {"w12_l05_2x6": 2, "w12_none_2x6": 2, "w24_none_4x6": 4, "w6_none_2x3": 2, "w12_none_4x3": 4}
for _name, (_w, _l, _mode, _cx) in VARIANTS.items():
    DESIGNS[_name] = Design(_name, input_device="nfet_01v8_lvt", input_w=_w, tail_w=7,
                            trim_l=_l or 1.0, trim_bits=6)
_orig = D.circuit_text


def skew_lines(text: str, w: float, mode: str) -> str:
    """'channel': junction geometry at nominal W; 'junction': channel at nominal W, junction skewed."""
    if mode == "both":
        return text
    for name, sign in (("Xinp", "+"), ("Xinn", "-")):
        skewed = f"{w:g}*(1{sign}pair_skew)"
        block = re.search(rf"^{name} .+\n\+ w=\{{(.+)\}} (l=\S+)\n(\+ ad=.+)\n(\+ pd=.+)$", text, re.M)
        assert block and block.group(1) == skewed, name
        if mode == "channel":
            new = (block.group(0).split("\n")[0] + f"\n+ w={{{skewed}}} {block.group(2)}\n"
                   f"+ ad={{{0.29 * w:g}}} as={{{0.29 * w:g}}}\n+ pd={{{2 * (0.29 + w):g}}} ps={{{2 * (0.29 + w):g}}}")
        else:
            new = (block.group(0).split("\n")[0] + f"\n+ w={{{w:g}}} {block.group(2)}\n"
                   f"{block.group(3)}\n{block.group(4)}")
        text = text.replace(block.group(0), new)
    return text


def variant_text(design) -> str:
    if design.name not in VARIANTS:
        return _orig(design)
    w, trim_l, mode, cx = VARIANTS[design.name]
    text = unit_array(_orig(design), design.trim_bits)
    if trim_l is None:
        keep, skipping = [], False
        for line in text.splitlines():
            if re.match(r"^X[ts][pn]\d", line):
                skipping = True
                continue
            if skipping and line.startswith("+"):
                continue
            skipping = False
            keep.append(line)
        assert not any(re.match(r"^X[ts][pn]\d", line) for line in keep)
        assert sum(line.startswith("X") for line in keep) == 11, sum(line.startswith("X") for line in keep)
        text = "\n".join(keep) + "\n"
    text = skew_lines(text, w, mode)
    n = FINGERS.get(design.name, 1)
    if n > 1:
        for name, sign in (("Xinp", "+"), ("Xinn", "-")):
            block = re.search(rf"^{name} (.+)\n(\+ w=.+)\n(\+ ad=.+)\n(\+ pd=.+)$", text, re.M)
            whole, skewed = f"{w:g}*(1{sign}pair_skew)", f"{w / n:g}*(1{sign}pair_skew)"
            assert block and block.group(2).count(whole) == 1 and block.group(3).count(whole) == 2
            body = "\n".join(block.group(k).replace(whole, skewed) for k in (2, 3, 4))
            text = text.replace(block.group(0), "\n".join(f"{name}f{k} {block.group(1)}\n{body}" for k in range(n)))
    if cx:
        text = text.replace(".ends atlas", f"Cxp xp vss {cx}f\nCxn xn vss {cx}f\n.ends atlas")
    return text


S.circuit_text = variant_text
R3.circuit_text = variant_text  # Sample.traces swaps this (header) text for the zero-shift mutated copy


class Skewed(Sample):
    """Nominal devices (all series gate sources 0 V), deterministic input-pair width skew."""

    def __init__(self, name, cond):
        self.design, self.seed, self.cond, self.runs = name, 0, cond, 0
        self.sim = Simulator(HERE / "cache" / "r3_unused", workers=1)
        self.z = defaultdict(float)
        self.circuit = mutate(variant_text(DESIGNS[name]), self.z, defaultdict(float))
        self.base = Point(design_name=name, pair_skew=SKEW, trim_code=0, differential_v=0.0,
                          corner=cond[0], vdd_v=cond[1], temperature_c=cond[2])


def one(job) -> dict:
    name, cond = job
    w, trim_l, mode, cx = VARIANTS[name]
    b = Skewed(name, cond).boundaries([0])
    row = {"variant": name, "input_w": w, "trim_l": trim_l, "skew_mode": mode, "cx_ff": cx,
           "cond": list(cond), "pair_skew": SKEW, "offset_mv": b[0]}
    print(json.dumps(row), flush=True)
    return row


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "offset.jsonl"
    done = set()
    if path.exists():
        done = {(r["variant"], tuple(r["cond"])) for r in map(json.loads, path.read_text().splitlines())}
    names = ARGS[1:] or list(VARIANTS)
    jobs = [(n, c) for c in CONDS for n in names if (n, c) not in done]
    with ThreadPoolExecutor(max_workers=12) as pool, path.open("a") as f:
        for row in pool.map(one, jobs):
            f.write(json.dumps(row) + "\n")
            f.flush()
