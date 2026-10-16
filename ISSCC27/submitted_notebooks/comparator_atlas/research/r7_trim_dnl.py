"""r7: trim-DAC major-carry DNL of lvt_balanced_4b (nominal, no mismatch).

Compares the shipped binary-sized trim (bit k: W = 0.42*2^k) with a unit-element
array (bit k: 2^k parallel copies of the bit-0 cell). Local simulation only.
Usage: python -B r7_trim_dnl.py [variant ...]   (variants: binary, unit)
"""
import json
import re
import sys

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
from r3_mismatch_mc import HERE, OUT, Sample, Simulator, get_design, mutated_circuit, sigma

DESIGN = "lvt_balanced_4b"
CONDS = [("tt", 1.8, 27.0), ("ss", 1.62, -40.0), ("fs", 1.62, -40.0)]


def unit_array(text: str, bits: int) -> str:
    for side in ("p", "n"):
        for k in range(1, bits):
            for kind in ("t", "s"):
                name = f"X{kind}{side}{k}"
                m = re.search(rf"^{name} (.+)\n\+ w=\{{([0-9.]+)\}} (l=\S+)$", text, re.M)
                assert m, name
                unit_w = float(m.group(2)) / 2 ** k
                copies = "\n".join(f"{name}u{j} {m.group(1)}\n+ w={{{unit_w:g}}} {m.group(3)}" for j in range(2 ** k))
                text = text.replace(m.group(0), copies)
    return text


def transfer(variant: str, cond) -> dict:
    sig = sigma(DESIGN)
    sim = Simulator(HERE / "cache" / "r3_unused", workers=1)
    s = Sample(DESIGN, 0, sim, sig, cond)
    s.z = {k: 0.0 for k in s.z}
    s.circuit = mutated_circuit(DESIGN, s.z, sig)
    if variant == "unit":
        s.circuit = unit_array(s.circuit, get_design(DESIGN).trim_bits)
    mx = get_design(DESIGN).max_code
    b = s.boundaries(list(range(-mx, mx + 1)))
    steps = [b[c] - b[c + 1] for c in range(-mx, mx)]
    lsb = (b[-mx] - b[mx]) / (2 * mx)
    return {"variant": variant, "cond": list(cond), "boundaries": {str(c): v for c, v in b.items()},
            "steps": steps, "lsb_mv": lsb, "max_step_mv": max(steps),
            "worst_residual_mv": max(steps) / 2, "dnl_max_lsb": max(steps) / lsb - 1}


if __name__ == "__main__":
    variants = ARGS or ["binary", "unit"]
    path = OUT / "trim_dnl.jsonl"
    done = set()
    if path.exists():
        done = {(r["variant"], tuple(r["cond"])) for r in map(json.loads, path.read_text().splitlines())}
    with path.open("a") as f:
        for v in variants:
            for c in CONDS:
                if (v, c) in done:
                    continue
                r = transfer(v, c)
                f.write(json.dumps(r) + "\n")
                f.flush()
                print(v, c, f"LSB={r['lsb_mv']:.2f} max_step={r['max_step_mv']:.2f} "
                      f"DNLmax={r['dnl_max_lsb']:+.2f}LSB worst|m|={r['worst_residual_mv']:.2f}", flush=True)
