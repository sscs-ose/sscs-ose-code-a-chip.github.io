#!/usr/bin/env python3
"""The two schematic figures, from the xschem sources in schematic/, checked against the LVS reference netlist.

  schematic/vga_core_12t.sch  the 12-transistor core (Figure 6). Its W, L, nf and copies are written in from
                              layout/vga_core_12t_sizes.json, the file the layout was drawn from.
  schematic/vga_core_9t.sch   the 9-transistor core (Figure 1): the same drawing without the sinks M10, M11 and the
                              reference diode M12, the tail gate on `vbias`. Topology only: its device sizes are
                              xschem placeholders and the figure does not show them (the 9T sizes are in the tables).

  python tools/schematics.py              write the sizes into vga_core_12t.sch, netlist both drawings with xschem and
                                          compare them with layout/vga_core_12t.spice, render images/schematic_vga12t.png
                                          and images/schematic_vga.png
  python tools/schematics.py --check      the comparison only, nothing written

The comparison is device by device: the nets each terminal connects to (internal nets matched by what they connect, so
their names do not matter), the model, and W, L, nf and copies (12T); for the 9T drawing, the reference without M10,
M11 and M12 and with `iref` named `vbias`, sizes not compared. Needs xschem, and xvfb-run when there is no display, and
the sky130 xschem symbols ($PDK_ROOT/sky130A/libs.tech/xschem, or --symbols). The drawings refer to the symbols by
their IIC-OSIC-TOOLS path (/foss/pdks/...); a temporary copy points at the local ones.
SPDX-License-Identifier: Apache-2.0
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCH = ROOT / "schematic"
REF = ROOT / "layout" / "vga_core_12t.spice"
SIZES = ROOT / "layout" / "vga_core_12t_sizes.json"
PINS = {"vdd", "gnd", "vin_p", "vin_n", "iref", "vbias", "vctrl_p", "vctrl_n", "v_out"}
FOSS = "/foss/pdks/sky130A/libs.tech/xschem"


def write_sizes(sch, sizes):
    """Set W (total over the fingers), L, nf and mult of every MOSFET in `sch` from the sizes file. Returns True if the
    file changed."""
    J = json.loads(Path(sizes).read_text()); fw, D = J["finger_width_um"], J["devices"]
    t = Path(sch).read_text(); seen = set()

    def fix(m):
        head, body = m.group(1), m.group(2)
        name = re.search(r"\{name=(M\d+)", head).group(1); d = D[name]; seen.add(name)
        for k, v in dict(W=f"{d['nf'] * fw:g}", L=f"{d['L_um']:g}", nf=f"{d['nf']}", mult=f"{d['m']}").items():
            body, n = re.subn(rf"^{k}=\S+$", f"{k}={v}", body, flags=re.M)
            if n != 1:
                sys.exit(f"{sch}: {name} has {n} '{k}=' lines")
        return head + body
    new = re.sub(r"(^C \{[^}]*fet3_01v8\.sym\}[^\n]*\{name=M\d+\n)(.*?^\})", fix, t, flags=re.M | re.S)
    if seen != set(D):
        sys.exit(f"{sch}: devices {sorted(seen)} do not match the sizes file {sorted(D)}")
    if new != t:
        Path(sch).write_text(new)
    return new != t


def parse(spice):
    """{device: (nets d g s b, model, (W, L, nf, copies))} from a flat netlist (continuation lines joined)."""
    out = {}
    for l in Path(spice).read_text().replace("\n+", " ").splitlines():
        t = l.split()
        if not t or not t[0].upper().startswith("XM"):
            continue
        kv = dict(x.split("=", 1) for x in t[6:] if "=" in x)
        size = (float(kv["W"]), float(kv["L"]), int(kv["nf"]), int(kv.get("m", kv.get("mult", 1))))
        out[t[0].upper()] = ([n.lower() for n in t[1:5]], t[5], size)
    return out


def compare(got, want, sizes=True):
    """Device-by-device comparison; returns the list of differences (empty: identical)."""
    def sig(devs):
        conn = {}
        for d, (nets, _, _) in devs.items():
            for term, n in zip("dgsb", nets):
                conn.setdefault(n, set()).add(f"{d}.{term}")
        return {n: (n if n in PINS else frozenset(s)) for n, s in conn.items()}
    if set(got) != set(want):
        return [f"devices differ: {sorted(set(got) ^ set(want))}"]
    sg, sw, bad = sig(got), sig(want), []
    for d in sorted(want, key=lambda s: int(s[2:])):
        (ng, mg, zg), (nw, mw, zw) = got[d], want[d]
        if [sg[n] for n in ng] != [sw[n] for n in nw]:
            bad.append(f"{d}: connections {ng} vs {nw}")
        if mg != mw:
            bad.append(f"{d}: model {mg} vs {mw}")
        if sizes and zg != zw:
            bad.append(f"{d}: W/L/nf/copies {zg} vs {zw}")
    return bad


def reference_9t():
    ref = {d: v for d, v in parse(REF).items() if d not in ("XM10", "XM11", "XM12")}
    return {d: ([("vbias" if n == "iref" else n) for n in nets], m, z) for d, (nets, m, z) in ref.items()}


def local_copy(sch, tmp, symbols):
    """A copy of `sch` whose symbol paths point at `symbols` instead of the IIC-OSIC-TOOLS path."""
    p = Path(tmp) / Path(sch).name
    p.write_text(Path(sch).read_text().replace(FOSS, str(symbols)))
    return p


def render_symbols(symbols, tmp, sizes):
    """Copies of the two MOSFET symbols for the figures: without the operating-point texts (id=, gm=, ... which only
    mean something after a simulation) and, for a topology figure, without the size texts."""
    out = Path(tmp) / ("sym_sized" if sizes else "sym_topo")
    shutil.copytree(symbols, out, dirs_exist_ok=True)
    for f in ("nfet3_01v8.sym", "pfet3_01v8.sym"):
        p = out / "sky130_fd_pr" / f
        t = re.sub(r"^T \{[^{}]*spice_get[^{}]*\}[^\n]*\n", "", p.read_text(), flags=re.M)
        if not sizes:
            t = re.sub(r"^T \{(@mult x @W / @L|nf=@nf)\}[^\n]*\n", "", t, flags=re.M)
        p.write_text(t)
    return out


def xschem(args, tmp, display=False):
    rc = Path(tmp) / "xschemrc"
    rc.write_text(f"set dark_colorscheme 0\nset netlist_dir {tmp}\nset netlist_type spice\n")
    cmd = ["xschem", "--rcfile", str(rc)] + args
    if display and not os.environ.get("DISPLAY"):
        cmd = ["xvfb-run", "-a", "-s", "-screen 0 2800x1600x24"] + cmd
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=tmp)
    if r.returncode:
        sys.exit(f"xschem failed ({r.returncode}): {r.stderr[-800:]}")


def netlist(sch, tmp):
    xschem(["-q", "-x", "-n", "-s", "-o", str(tmp), str(sch)], tmp)
    return Path(tmp) / (Path(sch).stem + ".spice")


def render(sch, png, tmp):
    from PIL import Image
    import numpy as np
    raw = Path(tmp) / (Path(png).stem + "_raw.png")
    (Path(tmp) / "render.tcl").write_text(f"xschem load {sch}\nxschem zoom_full\nxschem print png {raw} 2600 1450\nexit\n")
    xschem(["--script", str(Path(tmp) / "render.tcl")], tmp, display=True)
    im = Image.open(raw).convert("RGB"); a = np.asarray(im).astype(int)
    ys, xs = np.where(np.abs(a - a[0, 0]).sum(-1) > 30); p = 30          # trim the empty margins
    im.crop((max(xs.min() - p, 0), max(ys.min() - p, 0), min(xs.max() + p, a.shape[1]), min(ys.max() + p, a.shape[0]))).save(png, optimize=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="compare only; write nothing")
    ap.add_argument("--symbols", help="folder holding sky130_fd_pr/*.sym (default $PDK_ROOT/sky130A/libs.tech/xschem)")
    a = ap.parse_args()
    symbols = Path(a.symbols or Path(os.environ.get("PDK_ROOT", "/foss/pdks")) / "sky130A" / "libs.tech" / "xschem")
    if not (symbols / "sky130_fd_pr" / "nfet3_01v8.sym").exists():
        sys.exit(f"sky130 xschem symbols not found under {symbols} (set PDK_ROOT or pass --symbols)")
    if not shutil.which("xschem"):
        sys.exit("xschem not found")
    s12, s9 = SCH / "vga_core_12t.sch", SCH / "vga_core_9t.sch"
    if not a.check:
        print(f"{s12.relative_to(ROOT)}: sizes {'written' if write_sizes(s12, SIZES) else 'already'} from {SIZES.relative_to(ROOT)}")
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        for sch, want, sizes in ((s12, parse(REF), True), (s9, reference_9t(), False)):
            bad = compare(parse(netlist(local_copy(sch, tmp, symbols), tmp)), want, sizes)
            what = "topology, models, W/L/nf/copies" if sizes else "topology and models"
            print(f"{sch.relative_to(ROOT)} vs {REF.relative_to(ROOT)}{'' if sizes else ' without M10-M12'} ({what}): "
                  + ("identical" if not bad else "DIFFERENT\n  " + "\n  ".join(bad)))
            ok &= not bad
        if ok and not a.check:
            for sch, png, sizes in ((s12, ROOT / "images" / "schematic_vga12t.png", True),
                                    (s9, ROOT / "images" / "schematic_vga.png", False)):
                render(local_copy(sch, tmp, render_symbols(symbols, tmp, sizes)), png, tmp)
                print(f"wrote {png.relative_to(ROOT)}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
