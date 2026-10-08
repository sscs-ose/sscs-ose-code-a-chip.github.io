"""How many numbers of the notebook's prose are tied to the data by an assertion or a printed result?

    python3 scripts/prose_number_coverage.py [notebook.ipynb] [--list] [--json results/prose_number_coverage.json]

Every number in the markdown cells of the body (title to Section 13, without the reference list) is
classified as
  asserted  - it appears in the source of an assert statement or in an assertion's comment,
  shown     - it appears in an executed code cell's printed output or table (so it is computed from results/),
  -         - neither; such numbers are listed by --list and are candidates for a new assertion.
Definitional constants (the 1600-bit Keccak state, the 700 MB tool download) and the one figure taken from an
uncommitted development log (the 70 um of the pin repair, Appendix B.4) are expected to remain in this class.
Numbers that are labels rather than claims (section and appendix numbers, citations, years, standard numbers,
list markers, the paper's own identifiers) are skipped. The last cell of the notebook prints the totals.

SPDX-License-Identifier: Apache-2.0
"""
import json
import pathlib
import re
import sys

NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(?![\w])")
SKIP = [r"Sections?\s+[\d\w.,–\s]+", r"Appendix\s+[A-E](\.\d)?", r"§\s?[\d–,\s]+", r"\[\d+(?:,\s*\d+)*\]", r"FIPS\s+\d+", r"\bq\s*=\s*3329",
        r"\b(19|20)\d\d\b", r"HSKEM-\d", r"\b[A-H]\d?\b(?=[:.,)])", r"\$[^$]*\$", r"`[^`]*`", r"https?://\S+", r"\(\w\)", r"^\s*\d+\.\s",
        r"SKY130|SHA-?\d+|AES-?\d+|ML-KEM-\d+|Keccak-f\[1600\]|Agilex\s*5|DE25|IHP|ISSCC\s*\d+|Code-a-Chip|ESP32|M20K|OpenRAM|\d+\s*×\s*\d+"]


def norm(tok):
    return tok.replace(",", "")


def sig_round(x, s):
    """x rounded to s significant digits, as a float."""
    from math import floor, log10
    return 0.0 if x == 0 else round(x, s - 1 - floor(log10(abs(x))))


def sigfigs(tok):
    d = tok.replace(".", "").lstrip("0").rstrip("0") if "." not in tok else tok.replace(".", "").lstrip("0")
    return max(len(d), 1)


def matches(tok, pool):
    """tok is exact in the pool, or (two or more significant digits) is a rounding of a pooled value."""
    if tok in pool:
        return True
    s = sigfigs(tok)
    if s < 2:
        return False
    t = float(tok)
    return any(sig_round(f, s) == t for f in pool_floats(pool))


_cache = {}


def pool_floats(pool):
    k = id(pool)
    if k not in _cache:
        _cache[k] = [float(x) for x in pool if re.fullmatch(r"\d+(?:\.\d+)?", x)]
    return _cache[k]


def numbers(text):
    for pat in SKIP:
        text = re.sub(pat, " ", text, flags=re.M)
    return [norm(m) for m in NUM.findall(text)]


def main():
    argv = list(sys.argv[1:])
    out_json = argv.pop(argv.index("--json") + 1) if "--json" in argv else None
    args = [a for a in argv if not a.startswith("--")]
    nb = json.load(open(args[0] if args else "HSKEM_PQC_SKY130.ipynb", encoding="utf-8"))
    cells = nb["cells"]
    asserted, shown = set(), set()
    for c in cells:
        if c["cell_type"] != "code":
            continue
        src = "".join(c["source"])
        if "prose_number_coverage" in src:      # the cell that prints this count must not count itself
            continue
        for line in src.splitlines():
            if re.match(r"\s*(assert\b|if .*assert\b)", line) or "# \"" in line or re.search(r"#.*\d", line) and "assert" in line:
                asserted.update(numbers(line))
            elif "assert" in line:
                asserted.update(numbers(line))
            for n in list(numbers(line)):          # a share asserted as 0.995 covers "99.5 %" in the prose
                if re.fullmatch(r"0\.\d+", n):
                    asserted.add(f"{float(n) * 100:g}")
        out = ""
        for o in c.get("outputs", []):
            out += "".join(o.get("text", [])) if "text" in o else ""
            for k in ("text/plain", "text/html"):
                out += "".join(o.get("data", {}).get(k, []))
        shown.update(numbers(out))
        shown.update(norm(x) for x in re.findall(r"\b\d+(?:\.\d+)?\b", out))
    body = []
    for c in cells:
        if c["cell_type"] != "markdown":
            continue
        t = "".join(c["source"])
        if t.lstrip().startswith("# Appendices"):
            break
        if t.lstrip().startswith("### References"):
            continue
        if "### References" in t:
            t = t.split("### References")[0]
        title = next((l for l in t.splitlines() if l.startswith("#")), "(cell)").lstrip("# ")
        for n in numbers(t):
            body.append((title, n))
    # the results table of the first page is compared with the recomputed one by `assert rows == GLANCE`
    if any("assert rows == GLANCE" in "".join(c["source"]) for c in cells if c["cell_type"] == "code"):
        first = next(c for c in cells if c["cell_type"] == "markdown")
        for line in "".join(first["source"]).splitlines():
            if line.startswith("| ") and not line.startswith("| Result"):
                asserted.update(numbers(line))
    cls = {"asserted": 0, "shown": 0, "-": 0}
    missing = {}
    for title, n in body:
        if matches(n, asserted):
            cls["asserted"] += 1
        elif matches(n, shown):
            cls["shown"] += 1
        else:
            cls["-"] += 1
            missing.setdefault(title, []).append(n)
    total = len(body)
    print(f"prose numbers: {total}; asserted {cls['asserted']}, shown in an output {cls['shown']}, neither {cls['-']}")
    print(f"covered: {100 * (cls['asserted'] + cls['shown']) / total:.1f} %")
    if out_json:
        json.dump({"total": total, "asserted": cls["asserted"], "shown": cls["shown"], "neither": cls["-"],
                   "covered_pct": round(100 * (cls["asserted"] + cls["shown"]) / total, 1),
                   "neither_by_section": missing}, open(out_json, "w"), indent=1, ensure_ascii=False)
    if "--list" in sys.argv:
        for t, ns in missing.items():
            print(f"  {t[:60]:60s} {', '.join(ns)}")
    return cls, total


if __name__ == "__main__":
    main()
