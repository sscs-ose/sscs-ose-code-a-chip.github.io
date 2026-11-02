"""Copy layout/README.md into notebook Section 16 (paths prefixed with layout/, headings one level down, layout image)."""
import json, re, sys
D = sys.argv[1]
p = f"{D}/capless_ldo_por_rf_harvest_sky130.ipynb"
nb = json.load(open(p, encoding="utf-8"))
md = open(f"{D}/layout/README.md", encoding="utf-8").read()
md = re.sub(r"`(scripts|reports)/", r"`layout/\1/", md)
md = md.replace("(`ldo_top.gds`, `ldo_top.png`)", "(`layout/ldo_top.gds`)")
md = md.replace("This folder adds", "The `layout/` folder next to this notebook adds")
md = md.replace("Sections 1–14 of the notebook still use the ideal reference. The bandgap and post-layout results are in this folder.",
                "Sections 1–14 still use the ideal reference. The bandgap and post-layout results come from the scripts in `layout/scripts/`.")
lines = md.split("\n")
assert lines[0].startswith("# v3")
out = ['<a name="v3"></a>', "## 16. v3: transistor-level reference, physical layout and post-layout verification"]
for l in lines[1:]:
    out.append("#" + l if l.startswith("## ") else l)
    if l.startswith("## Layout"):
        out += ["", "![LDO + POR + bandgap layout (KLayout render)](layout/ldo_top.png)"]
text = "\n".join(out).rstrip()
def src(t):
    ls = t.split("\n"); return [l + "\n" for l in ls[:-1]] + [ls[-1]]
for c in nb["cells"]:
    s = "".join(c["source"])
    if c["cell_type"] == "markdown" and '<a name="v3"></a>' in s:
        c["source"] = src(text)
    elif c["cell_type"] == "markdown" and "this work has no layout or parasitic extraction yet (Section 14)" in s:
        c["source"] = src(s.replace("this work has no layout or parasitic extraction yet (Section 14)",
                                    "the comparison uses this work's schematic-level results (layout and post-layout results are in Section 16)"))
json.dump(nb, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
open(p, "a", encoding="utf-8").write("\n")
print("synced")
