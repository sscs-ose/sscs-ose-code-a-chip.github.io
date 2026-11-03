"""SKY130 PDK PCells, generated with magic's device generator (the foundry-supplied PCell code)."""

import os
import subprocess
from pathlib import Path

PDK_ROOT = Path(os.environ.get("PDK_ROOT", "/foss/pdks"))
MAGICRC = PDK_ROOT / "sky130A" / "libs.tech" / "magic" / "sky130A.magicrc"
CACHE = Path(os.environ.get("SARGEN_PCELL_CACHE", "build/pcell")).resolve()


def _gencell(device, name, params):
    """Run magic's device generator for sky130::<device> with `params`; cached GDS, returns (path, name)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    gds = CACHE / f"{name}.gds"
    if not gds.exists():
        tcl = CACHE / f"{name}.tcl"
        tcl.write_text(f"""crashbackups stop
magic::gencell sky130::{device} xc {params}
foreach c [cellname list allcells] {{ if {{[string match "{device}*" $c]}} {{ set dev $c }} }}
cellname rename $dev {name}
load {name}
gds write {gds}
quit -noprompt
""")
        r = subprocess.run(["magic", "-dnull", "-noconsole", "-rcfile", str(MAGICRC), str(tcl)],
                           cwd=CACHE, capture_output=True, text=True, timeout=300)
        if not gds.exists():
            raise RuntimeError(f"PCell generation failed:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    return gds, name


def mim_cap(w, l, name=None):
    """GDS of sky130_fd_pr__cap_mim_m3_1 (w x l um) from the PDK PCell; returns (path, cell name).

    Layers drawn by the PCell: met3 bottom plate, capm, via3 + met4 top contact (label C1) and a
    via3 + met4 bottom-plate contact strip (label C2)."""
    name = name or f"mim_{w:g}x{l:g}".replace(".", "p")
    return _gencell("sky130_fd_pr__cap_mim_m3_1", name, f"w {w} l {l} nx 1 ny 1")


def fet(model, w, l, gate="bot", name=None):
    """GDS of a single-finger SKY130 FET PCell (e.g. model sky130_fd_pr__nfet_01v8_lvt), drawn on li only:
    no guard ring and no mcon/met1, source/drain li bars and one poly gate contact below (gate="bot") or
    above (gate="top") the diffusion.  Returns (path, cell name)."""
    topc, botc = (1, 0) if gate == "top" else (0, 1)
    name = name or f"{model.split('__')[-1]}_w{w:g}_l{l:g}_{gate}".replace(".", "p")
    return _gencell(model, name, f"w {w} l {l} nf 1 m 1 guard 0 topc {topc} botc {botc} "
                                 f"viasrc 0 viadrn 0 viagate 0")


def import_pcell(gds, name, drop_layers=((235, 4), (67, 5), (68, 5), (71, 5))):
    """Import a PCell GDS into gdsfactory, dropping magic's boundary and the PCell text labels (C1/C2, D/S/G),
    which would otherwise give every cell of an array identically named nets."""
    import gdsfactory as gf
    c = gf.import_gds(gds, cellname=name)
    c = c.flatten()
    if drop_layers:
        c = c.remove_layers(layers=list(drop_layers))
    c.name = f"{name}_pdk"
    return c
