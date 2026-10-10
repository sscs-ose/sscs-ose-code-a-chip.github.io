"""Which numbers in a notebook's prose are tied to its data?

A notebook that reports measurements should not let a number in its text drift away from the result it
quotes. This tool lists every number in the markdown of a Jupyter notebook and classifies it as

  asserted  - it appears in an assert statement (or in that statement's comment) of a code cell, or in a
              markdown table that a code cell compares as a whole (--table-assert-marker),
  shown     - it appears in the saved output of an executed code cell, i.e. it was computed,
  -         - neither: typed by hand. These are the numbers a reader cannot trace to the data.

A number counts as tied to the data if it equals a computed or asserted value or is a rounding of one to its
own number of significant digits (two or more), so "about 27 uJ" matches 26.62. Labels that are not claims (heading numbers among them)
are skipped: section and appendix numbers, citations [3], years, inline code and math, URLs, list markers,
and any pattern given with --skip.

    python3 prose_coverage.py notebook.ipynb [--body-end REGEX] [--skip REGEX ...]
                              [--table-assert-marker TEXT] [--exclude-cell-marker TEXT]
                              [--list] [--json out.json]

--body-end:  a regular expression; the scan stops at the first markdown cell that matches it (default: an
             "Appendix"/"Appendices"/"References" heading). The reference list is never scanned.
--exclude-cell-marker: code cells containing this text are ignored (e.g. the cell that prints this count).
Exit code 0; the result is printed and optionally written as JSON.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys

NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(?![\w])")
LABELS = [r"Sections?\s+[\d\w.,–\s]+", r"Appendix\s+[A-Z](\.\d)?", r"§\s?[\d–,\s]+", r"\[\d+(?:[,–-]\s*\d+)*\]",
          r"\b(19|20)\d\d\b", r"\$[^$]*\$", r"`[^`]*`", r"https?://\S+", r"\(\w\)", r"^\s*\d+\.\s",
          r"\b[A-Z]{2,}[-\s]?\d+\b", r"\d+\s*×\s*\d+", r"^#{1,6}\s*[A-Z]?\d+(?:\.\d+)*\.?\s"]
DEFAULT_BODY_END = r"^#{1,3}\s*(\d+\.?\s*)?(Appendi(x|ces)|References)\b"


def norm(tok: str) -> str:
    return tok.replace(",", "")


def numbers(text: str, labels: list[str]) -> list[str]:
    for pat in labels:
        text = re.sub(pat, " ", text, flags=re.M)
    return [norm(m) for m in NUM.findall(text)]


def sigfigs(tok: str) -> int:
    digits = tok.replace(".", "").lstrip("0")
    if "." not in tok:
        digits = digits.rstrip("0")
    return max(len(digits), 1)


def round_sig(x: float, s: int) -> float:
    return 0.0 if x == 0 else round(x, s - 1 - math.floor(math.log10(abs(x))))


class Pool:
    """Numbers of one kind (asserted or shown), matched exactly or as a rounding."""

    def __init__(self) -> None:
        self.tokens: set[str] = set()
        self.values: list[float] = []

    def add(self, toks) -> None:
        for t in toks:
            if t not in self.tokens:
                self.tokens.add(t)
                if re.fullmatch(r"\d+(?:\.\d+)?", t):
                    self.values.append(float(t))

    def __contains__(self, tok: str) -> bool:
        if tok in self.tokens:
            return True
        s = sigfigs(tok)
        if s < 2:
            return False
        t = float(tok)
        return any(round_sig(v, s) == t for v in self.values)


def output_text(cell) -> str:
    out = []
    for o in cell.get("outputs", []):
        if "text" in o:
            out.append("".join(o["text"]))
        for k in ("text/plain", "text/html", "text/markdown"):
            out.append("".join(o.get("data", {}).get(k, [])))
    return "\n".join(out)


def analyse(nb: dict, body_end: str = DEFAULT_BODY_END, skip: list[str] | None = None,
            table_assert_marker: str | None = None, exclude_cell_marker: str | None = None) -> dict:
    labels = LABELS + list(skip or [])
    cells = nb["cells"]
    asserted, shown = Pool(), Pool()
    for c in cells:
        if c["cell_type"] != "code":
            continue
        src = "".join(c["source"])
        if exclude_cell_marker and exclude_cell_marker in src:
            continue
        for line in src.splitlines():
            if "assert" in line:
                toks = numbers(line, labels)
                asserted.add(toks)
                # a share asserted as 0.995 covers "99.5 %" in the prose
                asserted.add(f"{float(t) * 100:g}" for t in toks if re.fullmatch(r"0\.\d+", t))
        out = output_text(c)
        shown.add(numbers(out, labels))
        shown.add(norm(x) for x in re.findall(r"\b\d+(?:\.\d+)?\b", out))
    if table_assert_marker and any(table_assert_marker in "".join(c["source"]) for c in cells if c["cell_type"] == "code"):
        for c in cells:
            if c["cell_type"] == "markdown":
                for line in "".join(c["source"]).splitlines():
                    if line.startswith("|") and not re.match(r"\|\s*:?-", line):
                        asserted.add(numbers(line, labels))
                break
    body = []
    for c in cells:
        if c["cell_type"] != "markdown":
            continue
        text = "".join(c["source"])
        if re.search(body_end, text.lstrip(), re.M | re.I) and re.match(body_end, text.lstrip(), re.I):
            break
        text = re.split(r"^#{1,4}\s*References\b", text, flags=re.M | re.I)[0]
        title = next((l.lstrip("# ").strip() for l in text.splitlines() if l.startswith("#")), "(untitled cell)")
        body += [(title, n) for n in numbers(text, labels)]
    counts = {"asserted": 0, "shown": 0, "neither": 0}
    missing: dict[str, list[str]] = {}
    for title, n in body:
        if n in asserted:
            counts["asserted"] += 1
        elif n in shown:
            counts["shown"] += 1
        else:
            counts["neither"] += 1
            missing.setdefault(title, []).append(n)
    total = len(body)
    executed = any(c.get("outputs") for c in cells if c["cell_type"] == "code")
    return {"total": total, **counts, "executed_outputs_present": executed,
            "covered_pct": round(100 * (counts["asserted"] + counts["shown"]) / total, 1) if total else None,
            "neither_by_section": missing}


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("notebook")
    ap.add_argument("--body-end", default=DEFAULT_BODY_END)
    ap.add_argument("--skip", action="append", default=[])
    ap.add_argument("--table-assert-marker")
    ap.add_argument("--exclude-cell-marker")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    res = analyse(json.load(open(a.notebook, encoding="utf-8")), a.body_end, a.skip, a.table_assert_marker,
                  a.exclude_cell_marker)
    print(f"prose numbers: {res['total']}; asserted {res['asserted']}, shown in an output {res['shown']}, "
          f"neither {res['neither']}")
    if res["total"]:
        print(f"covered: {res['covered_pct']} %")
    if not res["executed_outputs_present"]:
        print("warning: the notebook holds no executed outputs; run it first, or only asserted numbers can count")
    if a.list:
        for t, ns in res["neither_by_section"].items():
            print(f"  {t[:60]:60s} {', '.join(ns)}")
    if a.json:
        json.dump(res, open(a.json, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return res


if __name__ == "__main__":
    main(sys.argv[1:])
