# klayout -b -r docs/figures/export_unitcell.py : polygons of the 4-bit CDAC unit cell per layer -> build/figures/unitcell_layers.json
import json, pya
LAYERS = {"nwell": (64, 20), "diff": (65, 20), "tap": (65, 44), "poly": (66, 20), "li": (67, 20), "met1": (68, 20),
          "met2": (69, 20), "met3": (70, 20), "capm": (89, 44), "met4": (71, 20), "via3": (70, 44)}
ly = pya.Layout(); ly.read("results/4bit/layout/cdac_unit.gds")
top = ly.top_cell(); out = {"bbox": [top.dbbox().left, top.dbbox().bottom, top.dbbox().right, top.dbbox().top]}
for name, (l, d) in LAYERS.items():
    li = ly.find_layer(l, d)
    if li is None:
        out[name] = []; continue
    reg = pya.Region(top.begin_shapes_rec(li)).merged()
    out[name] = [[[p.x * ly.dbu, p.y * ly.dbu] for p in poly.each_point_hull()] for poly in reg.each()]
json.dump(out, open("build/figures/unitcell_layers.json", "w"))
print({k: len(v) for k, v in out.items() if k != "bbox"}, out["bbox"])
