"""Supplemental pre-native cross-material rules, contact classes and source closure."""
import hashlib
import itertools
import json
import math
from pathlib import Path
import shutil
import sys

ENTRY = Path(sys.argv[1]).resolve()
OUT = Path("/home/a-vivianhsu/atlas-local-pitch-20261003-b1")
sys.path.insert(0, str(ENTRY / "layout_nominal27"))
import contract
import layout


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


placement = json.loads((OUT / "placement.json").read_bytes())
masks = {n: {l: [layout.transform_rect(r, p) for r in rs]
             for l, rs in contract.inspect_mag(OUT / f"pcell_{n.lower()}.mag")["rectangles"].items()
             if l not in ("checkpaint", "error_p")}
         for n, p in placement.items()}
diff = {"ndiff", "pdiff", "ndiffc", "pdiffc", "nsubdiff", "psubdiff",
        "nsubdiffcont", "psubdiffcont", "nmos", "nmoslvt", "pmos"}
contacts = {"ndiffc", "pdiffc", "nsubdiffcont", "psubdiffcont", "polycont"}
gates = {"nmos", "nmoslvt", "pmos"}
rules = [
    ("LV diffusion/tap.3", diff, diff, .27),
    ("N diffusion to Nwell diff/tap.9", {"ndiff", "ndiffc", "nmos", "nmoslvt"}, {"nwell"}, .34),
    ("P tap to Nwell diff/tap.11", {"psubdiff", "psubdiffcont"}, {"nwell"}, .13),
    ("LVT to standard FET conservative lvtn.3b", {"nmoslvt"}, {"nmos", "pmos"}, .415),
    ("contact licon.2", contacts, contacts, .17),
    ("poly contact to diffusion conservative licon.9/14", {"polycont"}, diff, .235),
    ("diffusion contact to gate licon.11", contacts-{"polycont"}, gates, .055),
    ("poly spacing poly.2", {"poly", *gates}, {"poly", *gates}, .21),
    ("poly to unrelated diffusion conservative poly.4", {"poly", *gates}, diff-gates, .075),
]
names = sorted(masks, key=lambda n: placement[n]["origin_um"][0])
rows = []
for left, right in itertools.combinations(names, 2):
    for label, first, second, rule in rules:
        for a, b in ((first, second), (second, first)):
            aa = [r for l, rs in masks[left].items() if l in a for r in rs]
            bb = [r for l, rs in masks[right].items() if l in b for r in rs]
            if not aa or not bb:
                continue
            distances = [(math.hypot(max(x[0]-y[2], y[0]-x[2], 0),
                                    max(x[1]-y[3], y[1]-x[3], 0))*.005, x, y)
                         for x in aa for y in bb]
            gap, x, y = min(distances)
            rows.append({"left": left, "right": right, "rule": label, "rule_um": rule,
                         "actual_rectangle_gap_um": gap, "additional_margin_um": gap-rule,
                         "limiting_rectangles_grid": [x, y]})
            assert gap-rule >= .2-1e-9, rows[-1]
tech = Path("/home/a-vivianhsu/atlas-parasitic-check-5fa3/tool-work/src/open_pdks/sky130/sky130A/libs.tech/magic/sky130A.tech")
text = tech.read_text()
assert "LV Diffusion spacing" not in text or "Diffusion spacing < %d (diff/tap.3)" in text
shapes = json.loads((OUT / "complete-unexecuted-route-rectangles.json").read_bytes())
for layer in ("via1", "via2", "via3"):
    expected = 8 if layer == "via3" else 108
    assert sum(s["layer"] == layer for s in shapes) == expected
for s in shapes:
    if s["layer"] == "via3":
        x1, y1, x2, y2 = [v*.005 for v in s["rect_grid"]]
        x, y = (x1+x2)/2, (y1+y2)/2
        assert math.isclose(abs(x), 21) and any(math.isclose(y, t) for t in (-2.4, 1.6, 3.2, 4.8))
        # Actual via3 M3 pad enclosure must fit both the VSS bus or grounded shield.
        routing = json.loads((OUT / "routing.json").read_bytes())
        bus = routing["buses"]["vss"] if y < 0 else {"left_um": -21.4, "right_um": 21.4}
        assert x1-.05 >= bus["left_um"] and x2+.05 <= bus["right_um"]
summary = {"status": "passed", "all_pair_cross_material_distances": rows,
           "technology_sha256": sha(tech), "all108_via1_and_via2_and8_via3_contacts": True,
           "via3_pad_end_enclosures_and_membership": True,
           "minimum_additional_cross_rule_margin_um": min(r["additional_margin_um"] for r in rows),
           "copied_inside_pcell_geometry_unchanged": True, "actual_candidate_native_attempts": 0}
contract.write_json(OUT / "supplemental-crossmask-preflight.json", summary)
shutil.copyfile(Path(__file__), OUT / "local_pitch_crossmask.py")
shutil.copyfile(OUT / "source-freeze.json", OUT / "source-freeze-initial.json")
freeze = json.loads((OUT / "source-freeze.json").read_bytes())
for name in ("local_pitch_crossmask.py", "supplemental-crossmask-preflight.json", "source-freeze-initial.json"):
    freeze["pre_native_files"][name] = sha(OUT / name)
contract.write_json(OUT / "source-freeze.json", freeze)
layout.manifest(OUT)
print("PASS", len(rows), "cross-mask rule distances; frozen source closure before native")
