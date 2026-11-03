#!/usr/bin/env python3
"""Set CLOCK_PERIOD in every flow/*/config.json and hier.json (except counter) from spec/spec.yaml."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = json.loads((ROOT / "flow/common_settings.json").read_text())  # flow knobs shared by all designs
per = int(re.search(r"clock_period_ns:\s*(\d+)", (ROOT / "spec/spec.yaml").read_text()).group(1))
for p in list((ROOT / "flow").glob("*/config.json")) + list((ROOT / "flow").glob("*/hier.json")) + list((ROOT / "flow").glob("scale/*/config.json")):
    if p.parent.name == "counter":
        continue
    c = json.loads(p.read_text())
    c["CLOCK_PERIOD"] = per
    c.update(SHARED)
    if json.loads(p.read_text()) != c:
        p.write_text(json.dumps(c, indent=2) + "\n")
        print("set", p, per)
print("clock_period_ns =", per)
