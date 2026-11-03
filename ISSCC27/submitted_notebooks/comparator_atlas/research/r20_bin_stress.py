"""r20b: is the atlas width skew a design-neutral stress? Width skew versus an ideal (multiplier) skew.

r20 found that the SKY130 binned models give W-dependent current per um: inside the 5.05-7 um bin,
Id/W rises steeply with W, while above 7 um it is flat, and a pair at 3 um straddles a bin edge.
A +4 % width skew therefore produces a design-dependent effective current skew. Here each design's
code-0 offset at the 45 PVT conditions (skew +4 %) is measured twice with the same harness:
  width : the atlas definition, w = W(1 +/- s), junction geometry following W (as in the sealed record)
  mult  : nominal W and junctions, instance multiplier m = 1 +/- s (scales current and capacitance exactly)
The ratio width/mult is the bin amplification of the stress for that design and condition.
Nominal devices (no random mismatch). Local only.
  python -B r20_bin_stress.py run [design ...]   # appends out/r20/bin_stress.jsonl
"""
import csv
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r20_offset_mechanism as M  # noqa: E402  (registers w6_l1 / w12_l05 and patches circuit_text)
from comparator_atlas.designs import DESIGNS  # noqa: E402

OUT = M.OUT
SKEW = M.SKEW
# sealed record designs and the two r16/r19 research designs (validated r20 equivalents)
BASES = {"baseline": "baseline", "lvt_base_3b": "lvt_base_3b", "lvt_balanced_4b": "lvt_balanced_4b",
         "unit6_w6": "w6_l1", "u6_w12_l05": "w12_l05"}
_prev = M.S.circuit_text


def literal(design) -> str:
    text = _prev(design)
    if design.name == "baseline":  # hand-written netlist: inline its subckt parameters (input_w=2, L=0.15, trim L=1)
        head, body = text.split("+ params: pair_skew=0 input_w=2 input_l=0.15 trim_l=1\n")
        body = body.replace("{input_l}", "0.15").replace("{trim_l}", "1")
        body = body.replace("{input_w*(1", "{2*(1").replace("*input_w*(1", "*2*(1").replace("+input_w*(1", "+2*(1")
        assert "input_w" not in body and "input_l" not in body and "trim_l" not in body
        body = re.sub(r"^\+ w=([\d.]+) l=", r"+ w={\1} l=", body, flags=re.M)
        text = head + "+ params: pair_skew=0\n" + body
    return text


def mult_text(design) -> str:
    if not design.name.endswith("__m"):
        return literal(design)
    base = DESIGNS[design.name[:-3]]
    text = literal(base)
    w = base.input_w
    for name, sign in (("Xinp", "+"), ("Xinn", "-")):
        skewed = f"{w:g}*(1{sign}pair_skew)"
        block = re.search(rf"^{name} .+\n\+ w=\{{(.+)\}} (l=\S+)\n(\+ ad=.+)\n(\+ pd=.+)$", text, re.M)
        assert block and block.group(1) == skewed, name
        new = (block.group(0).split("\n")[0] + f"\n+ w={{{w:g}}} {block.group(2)}\n"
               f"+ ad={{{0.29 * w:g}}} as={{{0.29 * w:g}}}\n"
               f"+ pd={{{2 * (0.29 + w):g}}} ps={{{2 * (0.29 + w):g}}} m={{1{sign}pair_skew}}")
        text = text.replace(block.group(0), new)
    live = "\n".join(line for line in text.splitlines() if not line.startswith("*"))
    assert live.count("pair_skew") == 3, live.count("pair_skew")  # subckt param + two multipliers
    return text


for _key, _base in BASES.items():
    DESIGNS[_base + "__m"] = replace(DESIGNS[_base], name=_base + "__m")
M.S.circuit_text = mult_text
M.R3.circuit_text = mult_text
M.variant_text = mult_text  # Skewed() builds its circuit through this name


def conditions():
    rows = list(csv.DictReader((OUT / "r20_offset_lsb.csv").open()))
    seen = []
    for r in rows:
        c = (r["corner"], float(r["vdd"]), float(r["T"]))
        if r["design"] == "unit6_w6" and float(r["sk"]) == SKEW and c not in seen:
            seen.append(c)
    assert len(seen) == 45, len(seen)
    return seen


def one(job) -> dict:
    key, mode, cond = job
    name = BASES[key] + ("__m" if mode == "mult" else "")
    b = M.Skewed(name, cond).boundaries([0])
    row = {"design": key, "mode": mode, "cond": list(cond), "pair_skew": SKEW, "offset_mv": b[0]}
    print(json.dumps(row), flush=True)
    return row


def report() -> dict:
    """Width/mult ratio per design over the 45 conditions, validated against the archived code-0 boundaries."""
    import statistics
    rows = [json.loads(line) for line in (OUT / "bin_stress.jsonl").read_text().splitlines()]
    val = {(r["design"], r["mode"], tuple(r["cond"])): r["offset_mv"] for r in rows}
    ref = {}
    for r in csv.DictReader((OUT / "r20_offset_lsb.csv").open()):
        if float(r["sk"]) == SKEW and r["design"] in BASES:
            ref[(r["design"], (r["corner"], float(r["vdd"]), float(r["T"])))] = float(r["b0"])
    study = ROOT_STUDY
    for rec in json.loads((study / "validation_calibration.json").read_text()):
        p = rec["point"]
        if p["pair_skew"] == SKEW:
            b = rec["local"]["selection"]["candidate_boundaries"]["0"]["midpoint_mv"]
            ref[(rec["design_name"], (p["corner"], p["vdd_v"], p["temperature_c"]))] = b
    for rec in json.loads((study / "professional" / "calibration.json").read_text()):
        p = rec["point"]
        if p["pair_skew"] == SKEW:
            b = rec["calibration"]["selection"]["baseline"]["midpoint_mv"]
            ref[("lvt_base_3b", (p["corner"], p["vdd_v"], p["temperature_c"]))] = b
    summary = {}
    for key in BASES:
        conds = [c for c in conditions() if (key, "width", c) in val and (key, "mult", c) in val]
        if not conds:
            continue
        # metastable at the 3.5 ns calibration deadline in both modes: no defined code-0 boundary
        unresolved = [c for c in conds if val[(key, "width", c)] == 0.0 and val[(key, "mult", c)] == 0.0]
        conds = [c for c in conds if c not in unresolved]
        pairs = [(val[(key, "width", c)], val[(key, "mult", c)]) for c in conds]
        slope = sum(a * b for a, b in pairs) / sum(b * b for _, b in pairs)  # LSQ width = k * mult
        ratio = [a / b for a, b in pairs if abs(b) >= 2.0]
        dev = [abs(val[(key, "width", c)] - ref[(key, c)]) for c in conds if (key, c) in ref]
        width = [abs(val[(key, "width", c)]) for c in conds]
        mult = [abs(val[(key, "mult", c)]) for c in conds]
        summary[key] = {
            "conditions": len(conds), "unresolved": [list(c) for c in unresolved],
            "input_w_um": DESIGNS[BASES[key]].input_w,
            "input_device": DESIGNS[BASES[key]].input_device,
            "lsq_slope": slope, "ratio_n": len(ratio),
            "ratio_median": statistics.median(ratio), "ratio_min": min(ratio), "ratio_max": max(ratio),
            "width_abs_median_mv": statistics.median(width), "mult_abs_median_mv": statistics.median(mult),
            "width_abs_max_mv": max(width), "mult_abs_max_mv": max(mult),
            "validated": len(dev), "max_dev_from_archive_mv": max(dev) if dev else None,
        }
        s = summary[key]
        print(f"{key:16s} n={s['conditions']:2d} slope {slope:.2f} ratio(n={len(ratio)})"
              f" med {s['ratio_median']:.2f} [{s['ratio_min']:.2f},"
              f"{s['ratio_max']:.2f}] |width| med {s['width_abs_median_mv']:5.2f} max {s['width_abs_max_mv']:5.2f}"
              f" |mult| med {s['mult_abs_median_mv']:5.2f} max {s['mult_abs_max_mv']:5.2f}"
              f" val {s['validated']} maxdev {s['max_dev_from_archive_mv']}")
    (OUT / "bin_stress_summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    return summary


ROOT_STUDY = next(p for p in (M.HERE.parent / "results" / "study",
                              M.HERE / ".." / "candidate" / "ISSCC27" / "submitted_notebooks" / "comparator_atlas"
                              / "results" / "study") if p.is_dir())

if __name__ == "__main__" and ARGS[:1] == ["report"]:
    report()
elif __name__ == "__main__":
    path = OUT / "bin_stress.jsonl"
    done = set()
    if path.exists():
        done = {(r["design"], r["mode"], tuple(r["cond"])) for r in map(json.loads, path.read_text().splitlines())}
    keys = ARGS[1:] or list(BASES)
    jobs = [(k, m, c) for c in conditions() for k in keys for m in ("width", "mult") if (k, m, c) not in done]
    with ThreadPoolExecutor(max_workers=12) as pool, path.open("a") as f:
        for row in pool.map(one, jobs):
            f.write(json.dumps(row) + "\n")
            f.flush()
