"""Physical stage of the flow: the post-layout gate, and a generic DRC -> LVS -> extraction stage.

Used for the final layout (notebook §13):
    post_layout(p, spec, pex)   flow.verify_netlist on the extracted netlist: the gate the pick passed, unchanged, with
                                the lumped wiring allowance dropped (the extraction carries the real wiring)
    pex_summary(pex)            extracted capacitance per named node
    REPORT                      layout/layout_report.json, the sign-off verdicts the notebook reads. For the final layout
                                they come from the layout author's scripts (layout/generator/verify12t.py,
                                prove_signoff.sh), imported by tools/import_signoff.py.

Generic stage, not used for the final layout's sign-off (run(); magic + netgen with the open_pdks sky130A setup):
      -> GDS        an external generator named in layout/generator.json (optional), else the committed GDS
      -> DRC        magic, full DRC style
      -> LVS        magic extraction (ext2spice lvs) against the flow's LVS netlist, compared by netgen with the PDK
                    setup (device type, terminals, W summed over fingers and copies, L). It does not ignore shorted
                    dummy transistors; the author's verify12t.py does, so use that for layouts with dummies.
      -> PEX        magic extraction with every parasitic capacitance (C only; wiring resistance is not extracted)
run() writes its logs into layout/reports/ and overwrites layout/layout_report.json.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import json, os, re, shutil, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "layout"
REPORTS = LAYOUT / "reports"
TOP = "vga_core_12t"
SIZES = LAYOUT / f"{TOP}_sizes.json"
REF_NETLIST = LAYOUT / f"{TOP}.spice"
REPORT = LAYOUT / "layout_report.json"


# ----------------------------------------------------------------------------------------------- tools
def pdk_root() -> Path:
    return Path(os.environ.get("PDK_ROOT", "/foss/pdks"))


def magicrc() -> Path:
    return pdk_root() / "sky130A" / "libs.tech" / "magic" / "sky130A.magicrc"


def netgen_setup() -> Path:
    return pdk_root() / "sky130A" / "libs.tech" / "netgen" / "sky130A_setup.tcl"


def available() -> dict:
    """Which tools and PDK files this machine has; the stage runs only when all are present."""
    have = dict(magic=shutil.which("magic") is not None, netgen=shutil.which("netgen") is not None,
                magicrc=magicrc().exists(), netgen_setup=netgen_setup().exists())
    have["all"] = all(have.values())
    return have


def versions() -> dict:
    out = {}
    if shutil.which("magic"):
        r = subprocess.run(["magic", "--version"], capture_output=True, text=True, timeout=60)
        out["magic"] = (r.stdout or r.stderr).strip().splitlines()[0] if (r.stdout or r.stderr).strip() else "?"
    if shutil.which("netgen"):
        r = subprocess.run(["netgen", "-batch", "quit"], capture_output=True, text=True, timeout=60)
        m = re.search(r"Netgen\s+([\d.]+)", r.stdout + r.stderr)
        out["netgen"] = m.group(1) if m else "?"
    return out


def _run(cmd, cwd, log, stdin=None, timeout=7200):
    """Run a tool, keep its whole output in `log`, return (returncode, output)."""
    t0 = time.time()
    r = subprocess.run(cmd, cwd=cwd, input=stdin, capture_output=True, text=True, timeout=timeout,
                       env=dict(os.environ, PDK_ROOT=str(pdk_root())))
    out = r.stdout + r.stderr
    Path(log).write_text(f"$ {' '.join(map(str, cmd))}\n# {time.time() - t0:.1f} s, exit {r.returncode}\n{out}")
    return r.returncode, out


def _magic(script, cwd, log):
    return _run(["magic", "-dnull", "-noconsole", "-rcfile", str(magicrc())], cwd, log, stdin=script + "\nquit -noprompt\n")


# ----------------------------------------------------------------------------------------------- steps
def generate(sizes=SIZES, gds=None, config=LAYOUT / "generator.json"):
    """Run the layout generator named in `config` on the sizes file; returns the GDS path and a verdict."""
    cfg = json.loads(Path(config).read_text())
    top = cfg.get("top", TOP)
    gds = Path(gds or REPORTS / f"{top}.gds")
    REPORTS.mkdir(parents=True, exist_ok=True)
    cmd = [str(a).format(sizes=Path(sizes).resolve(), gds=gds.resolve(), top=top, root=ROOT) for a in cfg["cmd"]]
    rc, _ = _run(cmd, ROOT, REPORTS / "generate_log.txt")
    return dict(step="generate", ok=rc == 0 and gds.exists(), gds=str(gds), top=top, log="layout/reports/generate_log.txt")


DRC_TCL = """
gds read {gds}
load {top}
select top cell
expand
drc euclidean on
drc style drc(full)
drc check
drc catchup
set n [drc list count total]
puts "DRC_COUNT $n"
set fo [open {why} w]
foreach {{msg boxes}} [drc listall why] {{ puts $fo "[llength $boxes]\\t$msg" }}
close $fo
"""


def drc(gds, top=TOP):
    """Full DRC in magic. Passes when the error count is zero; the rule-by-rule list goes to reports/drc_why.txt."""
    REPORTS.mkdir(parents=True, exist_ok=True)
    why = REPORTS / "drc_why.txt"
    rc, out = _magic(DRC_TCL.format(gds=Path(gds).resolve(), top=top, why=why.resolve()), REPORTS, REPORTS / "drc_log.txt")
    m = re.findall(r"DRC_COUNT\s+(\d+)", out)
    n = int(m[-1]) if m else None
    rules = []
    if why.exists():
        for line in why.read_text().splitlines():
            k, _, msg = line.partition("\t")
            if k.strip().isdigit():
                rules.append([int(k), msg])
    return dict(step="drc", ok=n == 0, errors=n, rules=rules, log="layout/reports/drc_log.txt")


EXTRACT_TCL = """
gds read {gds}
load {top}
select top cell
extract path {wd}
extract do local
extract all
ext2spice path {wd}
{mode}
ext2spice -o {out}
"""


def extract(gds, top=TOP, pex=False):
    """magic extraction: for LVS (devices and connectivity only) or for PEX (every parasitic capacitance)."""
    wd = REPORTS / ("pex" if pex else "lvs")
    wd.mkdir(parents=True, exist_ok=True)
    out = wd / f"{top}_{'pex' if pex else 'lvs'}.spice"
    mode = ("ext2spice hierarchy off\next2spice subcircuit top on\next2spice cthresh 0\next2spice rthresh 0" if pex
            else "ext2spice lvs")
    rc, log_ = _magic(EXTRACT_TCL.format(gds=Path(gds).resolve(), top=top, wd=wd.resolve(), mode=mode, out=out.resolve()),
                      wd, REPORTS / f"extract_{'pex' if pex else 'lvs'}_log.txt")
    return out if out.exists() else None


def lvs(ext_netlist, ref_netlist=REF_NETLIST, top=TOP):
    """netgen LVS of the extracted layout against the flow's LVS netlist. Passes only on a unique match with no
    property (W, L, multiplicity) errors."""
    out = REPORTS / "lvs_report.txt"
    out.unlink(missing_ok=True)                            # never read a previous run's verdict
    rc, log_ = _run(["netgen", "-batch", "lvs", f"{Path(ext_netlist).resolve()} {top}", f"{Path(ref_netlist).resolve()} {top}",
                     str(netgen_setup()), str(out.resolve())], REPORTS, REPORTS / "lvs_log.txt")
    txt = out.read_text() if out.exists() else log_
    if "Cannot compare" in log_:
        txt += "\nNetlists do not match"
    unique = bool(re.search(r"(Circuits|Netlists) match uniquely", txt))
    prop = bool(re.search(r"Property errors were found", txt))
    mism = bool(re.search(r"(Netlists|Circuits) do not match|Top level cell failed pin matching", txt))
    return dict(step="lvs", ok=unique and not prop and not mism, unique=unique, property_errors=prop,
                log="layout/reports/lvs_report.txt")


def pex_summary(pex_netlist):
    """Parasitic capacitance extracted on each named node (sum of every capacitor touching it), in fF."""
    caps = {}
    for line in Path(pex_netlist).read_text().splitlines():
        t = line.split()
        if len(t) >= 4 and t[0][:1].upper() == "C":
            try:
                v = _si(t[3])
            except ValueError:
                continue
            for n in t[1:3]:
                caps[n] = caps.get(n, 0.0) + v
    keep = ("v_out", "net4", "net2", "net3", "net5", "iref", "vin_p", "vin_n")
    return {n: 1e15 * caps[n] for n in keep if n in caps}


def _si(s):
    """A SPICE number: '91.1218f' -> 91.1218e-15 (the first letter after the digits is the scale factor, as in SPICE;
    trailing unit letters such as the F of '20fF' are ignored)."""
    m = re.match(r"([-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?)(meg|[afpnumkgt])?", s.strip().lower())
    if not m:
        raise ValueError(s)
    mult = dict(a=1e-18, f=1e-15, p=1e-12, n=1e-9, u=1e-6, m=1e-3, k=1e3, meg=1e6, g=1e9, t=1e12)
    return float(m.group(1)) * mult.get(m.group(2), 1.0)


# ----------------------------------------------------------------------------------------------- the stage
def run(gds=None, sizes=SIZES, generate_layout=True):
    """The whole physical stage. With generate_layout the generator rebuilds the GDS from the sizes file first;
    otherwise `gds` (default layout/vga_core_12t.gds) is checked as committed. Writes layout/layout_report.json."""
    have = available()
    rep = dict(tools=versions(), available=have, steps=[], time=time.strftime("%Y-%m-%d %H:%M"))
    if not have["all"]:
        rep["skipped"] = "missing: " + ", ".join(k for k, v in have.items() if not v and k != "all")
        REPORT.write_text(json.dumps(rep, indent=1)); return rep
    top = TOP
    if generate_layout and (LAYOUT / "generator.json").exists():
        g = generate(sizes); rep["steps"].append(g); top = g["top"]
        if not g["ok"]:
            REPORT.write_text(json.dumps(rep, indent=1)); return rep
        gds = g["gds"]
    gds = Path(gds or LAYOUT / f"{top}.gds")
    rep["gds"] = str(gds.relative_to(ROOT)) if gds.is_relative_to(ROOT) else str(gds)
    t0 = time.time(); d = drc(gds, top); d["seconds"] = time.time() - t0; rep["steps"].append(d)
    t0 = time.time(); ext = extract(gds, top, pex=False)
    l_ = lvs(ext, REF_NETLIST, top) if ext else dict(step="lvs", ok=False, error="extraction failed")
    l_["seconds"] = time.time() - t0; rep["steps"].append(l_)
    t0 = time.time(); pex = extract(gds, top, pex=True)
    rep["steps"].append(dict(step="pex", ok=pex is not None, netlist=str(pex.relative_to(ROOT)) if pex else None,
                             node_caps_ff=pex_summary(pex) if pex else {}, seconds=time.time() - t0))
    rep["ok"] = all(s["ok"] for s in rep["steps"])
    REPORT.write_text(json.dumps(rep, indent=1))
    return rep


def post_layout(p, spec, pex_netlist=None):
    """The flow's SPICE gate on the extracted netlist (every corner, noise at tt); the lumped output-wiring allowance
    (spec.c_wire) is dropped because the extraction carries the real wiring."""
    import flow
    from dataclasses import asdict
    pex_netlist = pex_netlist or REPORTS / "pex" / f"{TOP}_pex.spice"
    spec = flow.Spec(**{**asdict(spec), "c_wire": 0.0})     # the extracted capacitors replace the lumped wiring allowance
    return flow.verify_netlist(pex_netlist, p, spec, name=TOP)
