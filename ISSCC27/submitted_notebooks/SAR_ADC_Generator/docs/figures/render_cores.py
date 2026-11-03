# Run from the project folder in IIC-OSIC-TOOLS:  mkdir -p build/figures && klayout -b -r docs/figures/render_cores.py
# then python3 docs/figures/layouts_to_scale.py. each core GDS -> PNG at a fixed pixels-per-micron, cropped to the cell bbox
import json, pya
PPUM = 12
lyp = "/foss/pdks/sky130A/libs.tech/klayout/tech/sky130A.lyp"
out = {}
for b in (4, 6, 8):
    gds = f"results/{b}bit/layout/sar{b}b_core.gds"
    v = pya.LayoutView()
    v.load_layout(gds, 0)
    v.load_layer_props(lyp)
    v.max_hier()
    v.set_config("background-color", "#ffffff")
    v.set_config("grid-visible", "false")
    v.set_config("text-visible", "false")
    bb = v.cellview(0).layout().top_cell().dbbox()
    w, h = int(round(bb.width() * PPUM)), int(round(bb.height() * PPUM))
    v.zoom_box(bb)
    v.save_image(f"build/figures/core{b}.png", w, h)
    out[b] = [bb.width(), bb.height(), w, h]
json.dump(out, open("build/figures/sizes.json", "w"))
print(out)
