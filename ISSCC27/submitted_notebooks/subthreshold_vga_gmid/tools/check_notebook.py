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

BANNED = ["n_mirror", "TODO", "FIXME", "17.83 dB", "19.1 dB", "Flow-S", "Flow-R", "RERUN_SWEEP", "at five corners", "all five corners",
          "by_vctrl", "Pelgrom coefficients"]
LEAKS = ["/Users/", "/home/"]
UNITS = r"(?:dB|kHz|MHz|Hz|µA|µW|µV|µm|µS|MΩ|kΩ|mV|nV/√Hz|nV|V|%)"
FLAGS = ("REBUILD_LUT", "RERUN_FLOW", "RERUN_SPICE", "RUN_LAYOUT")

def out_text(c):
    t = []
    for o in c.get("outputs", []):
        if o["output_type"] == "stream": t.append("".join(o["text"]))
        elif o["output_type"] in ("display_data", "execute_result"):
            d = o["data"]; t.append("".join(d.get("text/markdown", d.get("text/plain", ""))))
        elif o["output_type"] == "error": t.append(o["ename"] + ": " + o["evalue"])
    return "\n".join(t)

PROSE_UNITS = r"(dB|kHz|µA|µV|nV/√Hz|mV|µm²|fF|pF|ms|µs|%)"
NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?\s?" + PROSE_UNITS)

def _numbers(text):
    """Every number in a text, as floats (thousands separators removed)."""
    return [float(m.replace(",", "")) for m in re.findall(r"(?<![\w.])-?\d[\d,]*\.?\d*(?:[eE][-+]?\d+)?", text)
            if re.fullmatch(r"-?\d{1,3}(,\d{3})*(\.\d*)?([eE][-+]?\d+)?|-?\d+(\.\d*)?([eE][-+]?\d+)?", m)]

def prose_check(nb, results):
    """Numbers with units in hand-written (markdown) prose that match nothing the notebook computes: no code output,
    no value in results.json and no number of the specification table, at the precision the prose prints."""
    import bisect
    known = []
    for c in nb["cells"]:
        if c["cell_type"] == "code":
            known += _numbers(out_text(c))
        elif "*Table 2." in "".join(c["source"]):         # the specification: inputs, not results
            known += _numbers("".join(c["source"]))
    def walk(x):
        if isinstance(x, dict):
            for v in x.values(): yield from walk(v)
        elif isinstance(x, (list, tuple)):
            for v in x: yield from walk(v)
        elif isinstance(x, (int, float)) and not isinstance(x, bool):
            yield float(x)
        elif isinstance(x, str):
            yield from _numbers(x)
    # (results.json is not used directly: every value a reader can check is printed by a code cell)
    K = sorted(set(abs(k) for k in known))
    out = []
    for i, c in enumerate(nb["cells"]):
        src = re.sub(r"data:image/png;base64,[A-Za-z0-9+/=]+", "data:image", "".join(c["source"]))   # embedded figures
        if c["cell_type"] != "markdown" or "⟦FILL" in src or "*Table 2." in src:
            continue
        for m in NUM.finditer(src):
            ip, fp, unit = m.group(1), m.group(2) or "", m.group(3)
            v = float(ip.replace(",", "") + fp); tol = 0.5 * 10 ** -(len(fp) - 1 if fp else 0) + 1e-9
            j = bisect.bisect_left(K, v - tol)
            if not (j < len(K) and K[j] <= v + tol):
                out.append(f"cell {i}: '{m.group(0)}' in prose matches no computed value — "
                           + src[max(0, m.start() - 50):m.end() + 30].replace("\n", " "))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nb", default="subthreshold_vga_gmid.ipynb"); ap.add_argument("--final", action="store_true")
    ap.add_argument("--numbers", action="store_true"); a = ap.parse_args()
    nbp = Path(a.nb).resolve(); root = nbp.parent
    nb = json.loads(nbp.read_text(encoding="utf-8")); E, W = [], []
    bad = E if a.final else W

    fills = {}
    for i, c in enumerate(nb["cells"]):
        src = re.sub(r"data:image/png;base64,[A-Za-z0-9+/=]+", "data:image", "".join(c["source"]))   # embedded figures
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
    rjp = root / "cache/results.json"
    if rjp.exists():
        R = json.loads(rjp.read_text())
        W.extend(prose_check(nb, R))
        top_i = next((i for i, c in enumerate(nb["cells"]) if c["cell_type"] == "code" and "first_md" in "".join(c["source"])
                      and "display(Markdown" in "".join(c["source"])), None)
        top = out_text(nb["cells"][top_i]) if top_i is not None else ""
        norm = lambda t: re.sub(r"\s+", " ", t).strip()
        if R.get("first_md") and top_i is not None and norm(R["first_md"]) not in norm(top):
            E.append(f"cell {top_i}: the first screen shown at the top differs from the one this run generated - run the notebook twice")
        if R.get("first_md") and top_i is None:
            E.append("the first-screen cell (first_md) is missing")

    md = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "markdown")
    if "**(A — layout completed)**" in md and "**(B — layout not included)**" in md:
        bad.append("§13 still has BOTH layout paragraphs — keep exactly one")

    for f in ("LICENSE", "README.md", "cache/results.json", "cache/lut_sky130.npz"):
        if not (root / f).exists(): E.append(f"missing {f}")
    rj, rd = root / "cache/results.json", root / "README.md"
    if rj.exists() and rd.exists() and rd.stat().st_mtime < rj.stat().st_mtime - 1:
        W.append("README.md is older than results.json — re-run the last cells to regenerate it")
    lay = root / "layout"
    if (lay / "layout_report.json").exists():
        LR = json.loads((lay / "layout_report.json").read_text())
        st = {x["step"]: x for x in LR.get("steps", [])}
        if not LR.get("skipped") and not ("drc" in st and "lvs" in st):
            E.append("layout: layout_report.json lacks a DRC or LVS step")
        for k_, x in st.items():
            if not x.get("ok"): W.append(f"layout: step {k_} did not pass")
    import subprocess
    def ignored(path):                      # a stray file that git already ignores (or tracks on purpose) is not a problem
        try:
            return (subprocess.run(["git", "check-ignore", "-q", str(path)], cwd=root).returncode == 0
                    or subprocess.run(["git", "ls-files", "--error-unmatch", str(path)], cwd=root,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0)
        except Exception: return False
    for p in root.rglob("*"):
        if p.is_file() and (p.suffix in (".raw", ".log") or "__pycache__" in p.parts or ".ipynb_checkpoints" in p.parts) \
           and not ignored(p):
            W.append(f"stray file not in .gitignore: {p.relative_to(root)}")
    try:                                    # what a commit would carry: tracked and untracked files, not the ignored ones
        r_ = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=root, capture_output=True, check=True)
        shipped = {(root / f).resolve() for f in r_.stdout.decode().split("\0") if f}
    except Exception:
        shipped = None                      # not a git checkout: count every file
    size = lambda p: sum(f.stat().st_size for f in Path(p).rglob("*")
                         if f.is_file() and (shipped is None or f.resolve() in shipped)) / 1e6
    nbmb, cmb, tot = nbp.stat().st_size / 1e6, size(root / "cache") if (root / "cache").exists() else 0, size(root)
    print(f"sizes: notebook {nbmb:.1f} MB | cache {cmb:.1f} MB | folder {tot:.1f} MB")
    if nbmb > 10 or tot > 40: W.append("large submission — a past rejected entry was a 23 MB notebook")

    for m in W: print("WARN ", m)
    for m in E: print("ERROR", m)
    print(f"{len(E)} error(s), {len(W)} warning(s)" + ("  — FINAL CHECK" if a.final else ""))
    sys.exit(1 if E else 0)

if __name__ == "__main__":
    main()
