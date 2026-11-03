"""Check the README metric tables (data/signoff/<task>.md) against the signoff data they are written from.

Every number in a design's column must be a rounding of a number in that design's signoff messages, possibly
rescaled by a power of 1000 or between fraction and percent. Every number in the Spec column must appear the same
way in the task specification or in any signoff message (the limits). Every number in the text above the table
must come from the specification. The Transistors row must match the counts in data/signoff/<task>.json.

    python tools/check_tables.py [TASK ...]      (default: every data/signoff/*.md)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
COLUMNS = {"Human": "reference", "GPT-6 Astra": "gpt-6-astra-thinking-max", "Claude Opus 5.5": "claude-opus-5-5-max"}
NUM = re.compile(r"(?<!\w)(?<!\d\.)[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
SCALES = (1, 1e3, 1e-3, 1e6, 1e-6, 1e9, 1e-9, 100, 0.01)


def numbers(text: str) -> list[float]:
    # Messages list values with commas ("[4.06,5.87]", "48.90,49.50"), so a comma separates numbers here.
    return [float(x) for x in NUM.findall(text.replace("−", "-").replace(",", " "))]


def shown(text: str) -> list[tuple[float, int]]:
    text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text.replace("−", "-").replace("**", ""))
    return [(float(x), len(x.split(".")[1]) if "." in x else 0) for x in NUM.findall(text)]


def matches(value: float, decimals: int, pool: list[float]) -> bool:
    tol = 0.5 * 10 ** -decimals + 1e-12
    return any(abs(abs(y * k) - abs(value)) <= tol for y in pool for k in SCALES)


def check(task: str) -> list[str]:
    data = json.loads((HERE / "data" / "signoff" / f"{task}.json").read_text())
    md = (HERE / "data" / "signoff" / f"{task}.md").read_text()
    spec_pool = numbers(data["spec"])
    msgs = {key: numbers(" ".join(c["message"] for c in data[key]["checks"])) for key in COLUMNS.values()}
    limit_pool = spec_pool + [x for pool in msgs.values() for x in pool]
    errors = []
    prose = md.split("<div", 1)[0]
    for v, d in shown(prose):
        if not matches(v, d, spec_pool):
            errors.append(f"text: {v} is not in the specification")
    rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in md.splitlines()
            if line.strip().startswith("|")]
    if len(rows) < 3:
        return errors + ["no table"]
    head = rows[0]
    if head[1:] != ["Spec", "Human", "GPT-6 Astra", "Claude Opus 5.5"]:
        errors.append(f"header is {head}")
        return errors
    body = rows[2:]
    if body[-1][0] != "Transistors":
        errors.append("last row is not Transistors")
    for row in body:
        label, spec, cells = row[0], row[1], row[2:]
        if label == "Transistors":
            for name, cell in zip(head[2:], cells):
                want = data[COLUMNS[name]]["transistors"]
                if cell.replace("**", "").strip() != str(want):
                    errors.append(f"Transistors/{name}: {cell} != {want}")
            continue
        for v, d in shown(spec):
            if not matches(v, d, limit_pool):
                errors.append(f"{label}/Spec: {v} not in the specification or limits")
        for name, cell in zip(head[2:], cells):
            for v, d in shown(cell):
                if not matches(v, d, msgs[COLUMNS[name]]):
                    errors.append(f"{label}/{name}: {v} not in that design's signoff messages")
    return errors


def main() -> None:
    tasks = sys.argv[1:] or sorted(p.stem for p in (HERE / "data" / "signoff").glob("*.md"))
    bad = 0
    for t in tasks:
        errs = check(t)
        bad += bool(errs)
        print(f"{'FAIL' if errs else 'ok  '} {t}")
        for e in errs:
            print(f"     {e}")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
