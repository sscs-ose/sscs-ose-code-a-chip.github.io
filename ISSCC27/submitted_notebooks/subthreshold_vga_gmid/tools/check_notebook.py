#!/usr/bin/env python3
"""Pre-push lint for the Code-a-Chip submission folder. Exit 1 on errors; warnings never fail.

  python tools/check_notebook.py            # day-to-day
  python tools/check_notebook.py --final    # before the PR: FILL markers, layout choice become errors
  python tools/check_notebook.py --numbers  # list every number-with-unit in hand-written prose
                                            # (compare against Table 12 / results.json by eye)
Edit BANNED for strings that must never appear (stale values, old node names).
"""
import argparse, json, re, sys
from pathlib import Path

BANNED = ["n_mirror", "TODO", "FIXME", "17.83 dB", "19.1 dB"]
LEAKS = ["/Users/", "/home/"]
UNITS = r"(?:dB|kHz|MHz|Hz|µA|µW|µV|µm|µS|MΩ|kΩ|mV|nV/√Hz|nV|V|%)"
FLAGS = ("REBUILD_LUT", "RERUN_SWEEP", "RERUN_SPICE")

def out_text(c):
    t = []
    for o in c.get("outputs", []):
        if o["output_type"] == "stream": t.append("".join(o["text"]))
        elif o["output_type"] in ("display_data", "execute_result"):
            d = o["data"]; t.append("".join(d.get("text/markdown", d.get("text/plain", ""))))
        elif o["output_type"] == "error": t.append(o["ename"] + ": " + o["evalue"])
    return "\n".join(t)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nb", default="notebook.ipynb"); ap.add_argument("--final", action="store_true")
    ap.add_argument("--numbers", action="store_true"); a = ap.parse_args()
    nbp = Path(a.nb).resolve(); root = nbp.parent
    nb = json.loads(nbp.read_text(encoding="utf-8")); E, W = [], []
    bad = E if a.final else W

    fills = {}
    for i, c in enumerate(nb["cells"]):
        src = "".join(c["source"])
        n = src.count("⟦FILL")
        if n: fills[i] = n
        if c["cell_type"] == "code":
            if c.get("execution_count") is None: E.append(f"cell {i}: code cell not executed")
            if any(o["output_type"] == "error" for o in c.get("outputs", [])): E.append(f"cell {i}: has an error output")
            for f in FLAGS:
                if re.search(rf"^{f}\s*=\s*True", src, re.M): E.append(f"cell {i}: {f} is True (ship with False)")
        blob = src + "\n" + out_text(c)
        for s in BANNED:
            if s in blob: E.append(f"cell {i}: banned string {s!r}")
        for s in LEAKS:
            if s in blob: E.append(f"cell {i}: local path leak {s!r}")
        if a.numbers and c["cell_type"] == "markdown":
            toks = sorted(set(re.findall(rf"\d[\d,]*\.?\d*\s?{UNITS}", src)))
            if toks: print(f"cell {i:2d}: " + " | ".join(toks))
    if fills: bad.append(f"{sum(fills.values())} ⟦FILL⟧ markers left, in cells {sorted(fills)}")

    md = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "markdown")
    if "**(A — layout completed)**" in md and "**(B — layout not included)**" in md:
        bad.append("§10 still has BOTH layout paragraphs — keep exactly one")

    for f in ("LICENSE", "README.md", "cache/results.json", "cache/lut_sky130.npz"):
        if not (root / f).exists(): E.append(f"missing {f}")
    rj, rd = root / "cache/results.json", root / "README.md"
    if rj.exists() and rd.exists() and rd.stat().st_mtime < rj.stat().st_mtime - 1:
        W.append("README.md is older than results.json — re-run the last cells to regenerate it")
    lay = root / "layout"
    if (lay / "drc_report.txt").exists() != (lay / "lvs_report.txt").exists():
        E.append("layout: DRC and LVS reports must both exist or both be absent")
    for p in root.rglob("*"):
        if p.is_file() and (p.suffix in (".raw", ".log") or "__pycache__" in p.parts or ".ipynb_checkpoints" in p.parts):
            W.append(f"stray file: {p.relative_to(root)}")
    size = lambda p: sum(f.stat().st_size for f in Path(p).rglob("*") if f.is_file()) / 1e6
    nbmb, cmb, tot = nbp.stat().st_size / 1e6, size(root / "cache") if (root / "cache").exists() else 0, size(root)
    print(f"sizes: notebook {nbmb:.1f} MB | cache {cmb:.1f} MB | folder {tot:.1f} MB")
    if nbmb > 10 or tot > 40: W.append("large submission — a past rejected entry was a 23 MB notebook")

    for m in W: print("WARN ", m)
    for m in E: print("ERROR", m)
    print(f"{len(E)} error(s), {len(W)} warning(s)" + ("  — FINAL CHECK" if a.final else ""))
    sys.exit(1 if E else 0)

if __name__ == "__main__":
    main()
