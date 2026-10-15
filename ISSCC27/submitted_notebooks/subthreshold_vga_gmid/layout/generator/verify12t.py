#!/usr/bin/env python
# Author: Vrinda Pandey (layout generator and sign-off scripts for this submission)
# SPDX-License-Identifier: Apache-2.0
"""DRC, LVS and extraction for vga_core_12t, callable from Python.

    import verify12t as v
    v.drc("layout/vga_core_12t.gds")                       -> True/False, writes verify/drc_report.txt + drc_status.json
    v.lvs("layout/vga_core_12t.gds", "layout/vga_core_12t_ref.spice")
                                                           -> True/False, writes verify/lvs_report.txt + lvs_status.json
    v.extract("layout/vga_core_12t.gds", "layout/vga_core_12t_ref.spice")
                                                           -> True/False, writes verify/vga_core_12t_pex.spice
                                                              (.subckt vga_core_12t, same pins and pin order as the reference)
Command line:  python verify12t.py [drc|lvs|extract|all]

Tools (from PATH / $PDK_ROOT): KLayout (DRC: official sky130A_mr.drc if present + gLayout's sky130 deck),
Magic (full-rule DRC cross-check, extraction), Netgen (LVS, PDK setup + dummies ignored as shorted devices).
"""
import json, os, re, subprocess, sys, time, xml.etree.ElementTree as ET
from pathlib import Path

TOP = "vga_core_12t"
PDK_ROOT = Path(os.environ.get("PDK_ROOT", ""))
MAGICRC = PDK_ROOT / "sky130A/libs.tech/magic/sky130A.magicrc"
NETGEN_SETUP = PDK_ROOT / "sky130A/libs.tech/netgen/sky130A_setup.tcl"
KLAYOUT_MR = PDK_ROOT / "sky130A/libs.tech/klayout/drc/sky130A_mr.drc"


def _glayout_deck():
    try:
        import glayout
    except ImportError:
        return None
    return Path(glayout.__file__).parent / "pdk/sky130_mapped/sky130.lydrc"


def _status(outdir, name, ok, details):
    outdir.mkdir(parents=True, exist_ok=True)
    d = {"check": name, "pass": bool(ok), "time": time.strftime("%Y-%m-%d %H:%M:%S"), **details}
    (outdir / f"{name}_status.json").write_text(json.dumps(d, indent=2) + "\n")
    print(f"{name.upper()}: {'PASS' if ok else 'FAIL'}  ({outdir / (name + '_status.json')})")
    return bool(ok)


def _lyrdb_items(path):
    root = ET.parse(path).getroot()
    out = {}
    for it in root.findall(".//item"):
        cat = (it.findtext("category") or "?").strip("'")
        out[cat] = out.get(cat, 0) + 1
    return out


def _magic(script, log):
    r = subprocess.run(["magic", "-dnull", "-noconsole", "-rcfile", str(MAGICRC)], input=script,
                       text=True, capture_output=True)
    Path(log).write_text(r.stdout + r.stderr)
    return r.stdout + r.stderr

# ---------------------------------------------------------------- DRC
def drc(gds, outdir="verify", top=TOP):
    gds, outdir = Path(gds).resolve(), Path(outdir).resolve(); outdir.mkdir(parents=True, exist_ok=True)
    decks = []
    if KLAYOUT_MR.exists():
        decks.append(("klayout_official", KLAYOUT_MR, ["-rd", "feol=true", "-rd", "beol=true"]))
    if _glayout_deck():
        decks.append(("klayout_glayout", _glayout_deck(), []))
    res, lines = {}, [f"DRC of {gds} ({time.strftime('%Y-%m-%d %H:%M:%S')})"]
    for name, deck, extra in decks:
        rep = outdir / f"drc_{name}.lyrdb"; rep.unlink(missing_ok=True)
        subprocess.run(["klayout", "-b", "-r", str(deck), "-rd", f"input={gds}", "-rd", f"report={rep}", *extra],
                       capture_output=True, text=True)
        items = _lyrdb_items(rep) if rep.exists() else {"(no report written)": 1}
        res[name] = sum(items.values())
        lines.append(f"\n[{name}] deck {deck}\n  violations: {res[name]}")
        lines += [f"    {k}: {v}" for k, v in sorted(items.items())]
    out = _magic(f"""gds read {gds}
load {top}
flatten {top}_drcflat
load {top}_drcflat
select top cell
drc euclidean on
drc style drc(full)
drc check
drc catchup
puts "MAGIC_DRC_TOTAL=[drc listall count total]"
foreach {{why boxes}} [drc listall why] {{ puts "MAGIC_WHY: [llength $boxes] :: $why" }}
quit -noprompt
""", outdir / "drc_magic.log")
    m = re.search(r"MAGIC_DRC_TOTAL=(\d+)", out)
    res["magic_full"] = int(m.group(1)) if m else -1
    lines.append(f"\n[magic_full] Magic drc(full), flattened\n  violations: {res['magic_full']}")
    lines += ["    " + l.split("MAGIC_WHY: ")[1] for l in out.splitlines() if l.startswith("MAGIC_WHY: ")]
    ok = all(v == 0 for v in res.values())
    lines.append(f"\nRESULT: {'PASS' if ok else 'FAIL'}")
    (outdir / "drc_report.txt").write_text("\n".join(lines) + "\n")
    return _status(outdir, "drc", ok, {"gds": str(gds), "violations": res, "report": str(outdir / "drc_report.txt")})

# ---------------------------------------------------------------- extraction
def _ref_pins(ref_spice):
    for l in Path(ref_spice).read_text().splitlines():
        t = l.split()
        if t and t[0].lower() == ".subckt":
            return t[1], t[2:]
    raise SystemExit(f"no .subckt in {ref_spice}")


def _extract(gds, outdir, out_spice, pins, lvs_mode, top=TOP):
    flat = f"{top}_flat"
    raw = outdir / f"{top}_{'lvs' if lvs_mode else 'pex'}_raw.spice"
    opts = "ext2spice lvs" if lvs_mode else "ext2spice cthresh 0\next2spice subcircuit top on"
    _magic(f"""gds read {gds}
load {top}
flatten {flat}
load {flat}
select top cell
cd {outdir}
extract all
{opts}
ext2spice -o {raw}
quit -noprompt
""", outdir / f"extract_{'lvs' if lvs_mode else 'pex'}.log")
    if not raw.exists():
        return False, "Magic wrote no netlist", []
    txt = raw.read_text()
    m = re.search(rf"^\.subckt {re.escape(flat)}((?:\s+\S+)*?)\s*$", txt, re.M)
    if not m:
        return False, f"no .subckt {flat} in the extraction", []
    got = m.group(1).split()
    # continuation lines (+ ...) after the .subckt line
    after = txt[m.end():].splitlines()
    for l in after[1:]:
        if l.startswith("+"):
            got += l[1:].split()
        else:
            break
    if sorted(got) != sorted(pins):
        return False, f"extracted pins {sorted(got)} differ from reference pins {sorted(pins)}", got
    # rename the subcircuit and put the pins in the reference order (connections inside are by name)
    lines = txt.splitlines(); i = next(k for k, l in enumerate(lines) if l.startswith(f".subckt {flat}"))
    j = i + 1
    while j < len(lines) and lines[j].startswith("+"):
        j += 1
    lines[i:j] = [f".subckt {top} {' '.join(pins)}"]
    # Magic marks substrate capacitors with a trailing "**FLOATING"; ngspice rejects it, so drop the marker
    lines = [re.sub(r"\s+\*\*FLOATING\s*$", "", l) for l in lines]
    Path(out_spice).write_text("\n".join(lines) + "\n")
    return True, "ok", got


def extract(gds, ref_spice, outdir="verify", top=TOP):
    """Parasitic extraction (C and R thresholds 0) -> verify/vga_core_12t_pex.spice with .subckt vga_core_12t."""
    gds, outdir = Path(gds).resolve(), Path(outdir).resolve(); outdir.mkdir(parents=True, exist_ok=True)
    name, pins = _ref_pins(ref_spice)
    out = outdir / f"{top}_pex.spice"
    ok, msg, got = _extract(gds, outdir, out, pins, lvs_mode=False, top=top)
    ncap = len(re.findall(r"^C\d+", out.read_text(), re.M)) if ok else 0
    rep = [f"Extraction of {gds}", f"subcircuit: .subckt {top} {' '.join(pins)}", f"status: {msg}",
           f"parasitic capacitors: {ncap}", f"netlist: {out}"]
    (outdir / "extract_report.txt").write_text("\n".join(rep) + "\n")
    return _status(outdir, "extract", ok and name == top,
                   {"gds": str(gds), "netlist": str(out), "pins": pins, "capacitors": ncap, "message": msg})

# ---------------------------------------------------------------- LVS
def lvs(gds, ref_spice, outdir="verify", top=TOP):
    gds, ref_spice, outdir = Path(gds).resolve(), Path(ref_spice).resolve(), Path(outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    name, pins = _ref_pins(ref_spice)
    lay = outdir / f"{top}_lvs_extracted.spice"
    ok_x, msg, got = _extract(gds, outdir, lay, pins, lvs_mode=True, top=top)
    if not ok_x:
        (outdir / "lvs_report.txt").write_text(f"LVS not run: {msg}\n")
        return _status(outdir, "lvs", False, {"message": msg})
    setup = outdir / "lvs_setup.tcl"
    setup.write_text(f"""# SKY130 Netgen setup from the PDK, plus: devices whose terminals are all on one net
# (dummy transistors) carry no current and are ignored.
source {NETGEN_SETUP}
foreach dev {{sky130_fd_pr__nfet_01v8 sky130_fd_pr__pfet_01v8}} {{
    foreach c {{-circuit1 -circuit2}} {{ catch {{ignore shorted "$c $dev"}} }}
}}
""")
    rep = outdir / "lvs_report.txt"; rep.unlink(missing_ok=True)
    subprocess.run(["netgen", "-batch", "lvs", f"{lay} {top}", f"{ref_spice} {name}", str(setup), str(rep)],
                   capture_output=True, text=True)
    txt = rep.read_text() if rep.exists() else ""
    final = re.findall(r"Final result:.*", txt)
    ok = bool(final) and "Circuits match uniquely" in final[-1] and "Property errors were found" not in txt
    return _status(outdir, "lvs", ok, {"gds": str(gds), "reference": str(ref_spice),
                                       "final": final[-1] if final else "(no result)",
                                       "property_errors": "Property errors were found" in txt, "report": str(rep)})


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    gds, ref = "layout/vga_core_12t.gds", "layout/vga_core_12t_ref.spice"
    ok = True
    if what in ("drc", "all"):
        ok &= drc(gds)
    if what in ("lvs", "all"):
        ok &= lvs(gds, ref)
    if what in ("extract", "all"):
        ok &= extract(gds, ref)
    sys.exit(0 if ok else 1)
