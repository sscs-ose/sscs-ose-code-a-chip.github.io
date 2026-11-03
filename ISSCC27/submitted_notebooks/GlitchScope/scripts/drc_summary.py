"""Summarise a KLayout DRC report database (.lyrdb): violations per rule.

    python scripts/drc_summary.py <report.lyrdb> <out.json>
"""
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter


def summarise(path):
    root = ET.parse(path).getroot()
    descr = {}
    for c in root.iter("category"):
        name = c.findtext("name")
        if name:
            descr[name.strip("'")] = (c.findtext("description") or "").strip().strip("'")
    counts = Counter()
    items = root.find("items")
    for it in (items if items is not None else []):
        counts[(it.findtext("category") or "?").strip("'")] += 1
    return dict(total=sum(counts.values()),
                rules={k: dict(count=v, description=descr.get(k, "")) for k, v in counts.most_common()},
                rules_checked=len(descr))


if __name__ == "__main__":
    s = summarise(sys.argv[1])
    open(sys.argv[2], "w").write(json.dumps(s, indent=1))
    print(f"{sys.argv[1]}: {s['total']} violations in {len(s['rules'])} of {s['rules_checked']} rules"
          + "".join(f"\n   {k}: {v['count']}  {v['description'][:70]}" for k, v in list(s['rules'].items())[:8]))
