"""Do the part reports of a split DRC run hold exactly the markers of the unsplit run?

    python3 compare_reports.py <full.lyrdb> <part1.lyrdb> [<part2.lyrdb> ...]

Each marker is identified by its category and its geometry (the value text of the KLayout report database),
so the comparison is a multiset of (rule, shape) pairs. Prints the per-rule counts of both sides and
EQUIVALENT or the differences; exit code 1 on any difference.
SPDX-License-Identifier: Apache-2.0
"""
import collections
import sys
import xml.etree.ElementTree as ET


def markers(path):
    root = ET.parse(path).getroot()
    items = root.find("items")
    out = collections.Counter()
    for it in (items.findall("item") if items is not None else []):
        cat = it.findtext("category").strip("'")
        vals = tuple(sorted(v.text or "" for v in it.find("values").findall("value"))) if it.find("values") is not None else ()
        out[(cat, vals)] += 1
    return out


def main(full, *parts):
    a = markers(full)
    b = collections.Counter()
    for p in parts:
        b += markers(p)
    by_rule = lambda c: collections.Counter({k[0]: 0 for k in c}) + collections.Counter(k[0] for k in c.elements())
    ra, rb = by_rule(a), by_rule(b)
    for r in sorted(set(ra) | set(rb)):
        print(f"{r:14s} full {ra.get(r, 0):6d}   parts {rb.get(r, 0):6d}")
    if a == b:
        print(f"EQUIVALENT: {sum(a.values())} markers, identical rule and geometry")
        return 0
    print(f"DIFFERENT: only in full {sum((a - b).values())}, only in parts {sum((b - a).values())}")
    return 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
