"""Physical verification with the open-source sign-off tools of the SKY130 PDK.

DRC: KLayout with the PDK's sky130A_mr.drc deck (FEOL + BEOL + off-grid) and magic's full DRC.
LVS: magic extraction + netgen with the PDK setup.  Also PNG rendering (KLayout batch).
Runs anywhere klayout / magic / netgen are on PATH (IIC-OSIC-TOOLS, or Colab after setup).
"""

import os
import re
import subprocess
from pathlib import Path

PDK_ROOT = Path(os.environ.get("PDK_ROOT", "/foss/pdks"))
TECH = PDK_ROOT / "sky130A" / "libs.tech"

_RENDER = """
import pya
lv = pya.LayoutView()
lv.load_layout(gds, 0)
try:
    lv.load_layer_props(lyp)
except Exception:
    pass
lv.set_config("background-color", "#ffffff")
lv.set_config("grid-visible", "false")
lv.max_hier()
lv.zoom_fit()
lv.save_image(png, int(size), int(size))
"""


def _run(cmd, cwd=None, timeout=1800):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def drc_klayout(gds, outdir) -> dict:
    """PDK KLayout deck; returns {'total': n, 'rules': {rule: count}}."""
    gds, outdir = Path(gds).resolve(), Path(outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    rpt = outdir / f"{gds.stem}_klayout.lyrdb"
    _run(["klayout", "-b", "-r", str(TECH / "klayout/drc/sky130A_mr.drc"), "-rd", f"input={gds}",
          "-rd", f"report={rpt}", "-rd", "feol=true", "-rd", "beol=true", "-rd", "offgrid=true",
          "-rd", "floating_met=false", "-rd", "seal=false"])
    # capm.10 (nothing but met2 and above under a MIM cap) is a written rule the deck above does not check
    rpt10 = outdir / f"{gds.stem}_capm10.lyrdb"
    _run(["klayout", "-b", "-r", str(Path(__file__).with_name("capm10.drc")), "-rd", f"input={gds}",
          "-rd", f"report={rpt10}"])
    cats = []
    for f in (rpt, rpt10):
        txt = f.read_text() if f.exists() else ""
        cats += [re.search(r"<category>'?([^<']*)", it).group(1)
                 for it in re.findall(r"<item>(.*?)</item>", txt, re.S)]
    rules = {}
    for c in cats:
        rules[c] = rules.get(c, 0) + 1
    ran = rpt.exists() and rpt10.exists()
    return dict(total=len(cats) if ran else -1, rules=rules, report=str(rpt), ran=ran)


def drc_magic(gds, cell, outdir) -> dict:
    gds, outdir = Path(gds).resolve(), Path(outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    tcl = outdir / f"{cell}_drc.tcl"
    tcl.write_text(f"""crashbackups stop
drc euclidean on
drc style drc(full)
gds read {gds}
load {cell}
select top cell
expand
drc check
drc catchup
set result [drc listall why]
set count 0
foreach {{msg boxes}} $result {{ set n [llength $boxes]; incr count $n; puts "RULE: $msg : $n" }}
puts "DRC_TOTAL $count"
quit -noprompt
""")
    r = _run(["magic", "-dnull", "-noconsole", "-rcfile", str(TECH / "magic/sky130A.magicrc"), str(tcl)], cwd=outdir)
    (outdir / f"{cell}_magic_drc.log").write_text(r.stdout + r.stderr)
    m = re.search(r"DRC_TOTAL (\d+)", r.stdout)
    rules = dict((a.strip(), int(b)) for a, b in re.findall(r"RULE: (.*) : (\d+)", r.stdout))
    return dict(total=int(m.group(1)) if m else -1, rules=rules)


def extract(gds, cell, outdir, parasitics=False, resistance=False) -> Path:
    """magic extraction to SPICE (LVS netlist, or with parasitic C when parasitics=True; with resistance=True
    also wiring R networks: `extract do resistance` runs extresist, `ext2spice extresist on` writes them)."""
    gds, outdir = Path(gds).resolve(), Path(outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    suffix = ("rcx" if resistance else "pex") if parasitics else "lvs"
    out = outdir / f"{cell}_{suffix}.spice"
    pex = "extract do capacitance\nextract do coupling\next2spice cthresh 0\n" if parasitics else ""
    if parasitics and resistance:
        pex += "extract do resistance\next2spice extresist on\next2spice rthresh 0\n"
    tcl = outdir / f"{cell}_ext_{suffix}.tcl"
    tcl.write_text(f"""crashbackups stop
gds read {gds}
load {cell}
select top cell
catch {{port makeall}}
extract do local
{pex}extract all
ext2spice {'' if parasitics else 'lvs'}
ext2spice -o {out}
quit -noprompt
""")
    r = _run(["magic", "-dnull", "-noconsole", "-rcfile", str(TECH / "magic/sky130A.magicrc"), str(tcl)], cwd=outdir)
    (outdir / f"{cell}_ext_{suffix}.log").write_text(r.stdout + r.stderr)
    return out


def lvs(gds, cell, ref_spice, ref_cell, outdir) -> dict:
    outdir = Path(outdir).resolve()
    ext = extract(gds, cell, outdir)
    rpt = outdir / f"{cell}_lvs.out"
    r = _run(["netgen", "-batch", "lvs", f"{ext} {cell}", f"{Path(ref_spice).resolve()} {ref_cell}",
              str(TECH / "netgen/sky130A_setup.tcl"), str(rpt)], cwd=outdir)
    (outdir / f"{cell}_lvs.log").write_text(r.stdout + r.stderr)
    txt = (rpt.read_text() if rpt.exists() else "") + r.stdout
    match = "Circuits match uniquely" in txt and "do not match" not in txt
    counts = re.findall(r"Circuit \d contains (\d+) devices", txt)
    return dict(match=match, report=str(rpt), devices=counts[-2:] if counts else [],
                summary=[ln for ln in txt.splitlines() if "MISMATCH" in ln or "match" in ln.lower()][-4:])


def render_png(gds, png, size=1400):
    script = Path(png).with_suffix(".render.py")
    script.write_text(_RENDER)
    _run(["klayout", "-b", "-r", str(script), "-rd", f"gds={Path(gds).resolve()}", "-rd", f"png={Path(png).resolve()}",
          "-rd", f"lyp={TECH / 'klayout/tech/sky130A.lyp'}", "-rd", f"size={size}"])
    script.unlink(missing_ok=True)
    return Path(png)
