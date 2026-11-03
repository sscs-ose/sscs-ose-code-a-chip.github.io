#!/usr/bin/env python3
"""Collect the layout sign-off into layout/layout_report.json, the file the notebook's §13 reads.

The sign-off was run outside this repository with the layout author's scripts (layout/generator/verify12t.py,
layout/generator/prove_signoff.sh): once natively in the gLayout environment and once inside IIC-OSIC-TOOLS. This
script only reads their reports (layout/reports/, layout/reports/container_repro/), checks that the fingerprints they
recorded are those of the files committed here, and writes the verdicts; it decides nothing itself.

  python tools/import_signoff.py
SPDX-License-Identifier: Apache-2.0
"""
import sys, re, json, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import layout_flow as lf

REP = lf.REPORTS


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def proof(path):
    """Fingerprints, negative controls and timestamp recorded in a sign-off proof file."""
    t = Path(path).read_text()
    fp = {Path(m.group(2)).name: m.group(1) for m in re.finditer(r"^([0-9a-f]{64})\s+(\S+)$", t, re.M)}
    ctl = [(m.group(1).strip(), m.group(2)) for m in re.finditer(r"^\s{2}(\S.*)\s+->\s+((?:FAIL|PASS|ERROR).*)$", t, re.M)]
    neg = [dict(change=c, rejected="correctly rejected" in v) for c, v in ctl if "positive control" not in c]
    pos = [("correctly accepted" in v) for c, v in ctl if "positive control" in c]
    when = re.search(r"SIGN-OFF PROOF\s+(\S+ \S+)", t)
    tools = {}                                  # the tools line written by prove_signoff.sh from v3 on
    m = re.search(r"^tools: (.*)$", t, re.M)
    if m:
        for part in m.group(1).split("|"):
            part = part.strip()
            k = part.split()[0].lower().split("=")[0] if part else ""
            if k in ("klayout", "magic", "netgen"):
                v = part.split()[-1]
                tools[k] = (part.split()[0] if k != "magic" else "Magic") + " " + v
            elif k == "pdk_root" and "versions/" in part:
                tools["pdk"] = "sky130 " + part.rsplit("versions/", 1)[1][:8]
    return dict(fingerprints=fp, negative_controls=neg, positive_control=pos[0] if pos else None, time=when.group(1) if when else None,
                sizes_identical="netlist and JSON sizes IDENTICAL" in t, tools=tools)


def run(folder, proof_file, env_file=None):
    d = json.loads((folder / "drc_status.json").read_text())
    l_ = json.loads((folder / "lvs_status.json").read_text())
    pr = proof(folder / proof_file)
    committed = {n: sha(ROOT / "layout" / n) for n in ("vga_core_12t.spice", "vga_core_12t_sizes.json", "vga_core_12t.gds")}
    committed["verify12t.py"] = sha(ROOT / "layout" / "generator" / "verify12t.py")   # the checker the run used
    out = dict(drc=dict(passed=d["pass"], violations=d["violations"], time=d["time"]),
               lvs=dict(passed=l_["pass"], unique="match uniquely" in l_["final"], property_errors=l_["property_errors"],
                        time=l_["time"]),
               negative_controls=pr["negative_controls"], positive_control=pr["positive_control"],
               sizes_identical=pr["sizes_identical"], proof_time=pr["time"],
               fingerprints=pr["fingerprints"],
               fingerprints_match=all(pr["fingerprints"].get(n) == h for n, h in committed.items()))
    if env_file and (folder / env_file).exists():
        kv = dict(l.split(":", 1) for l in (folder / env_file).read_text().splitlines() if ":" in l)
        out["environment"] = {k.strip(): v.replace('"', "").strip() for k, v in kv.items()}
        m = re.match(r"Netgen\s+([\d.]+)", out["environment"].get("netgen", ""))
        if m:
            out["environment"]["netgen"] = "Netgen " + m.group(1)
    return out


def extras():
    """The Magic antenna check and the official KLayout deck's off-by-default checks (off-grid, floating metal).

    Both were run natively by the layout author with a demo script that also runs a control (a layout that MUST be flagged),
    so a check that cannot flag anything is detected. Read from the raw logs, not from the summaries: antenna violations are
    the growth of Magic's feedback count over antennacheck; the deck's findings are the items in its report databases."""
    import xml.etree.ElementTree as ET
    gds = sha(ROOT / "layout" / "vga_core_12t.gds")
    out = {}
    d = REP / "antenna"
    if (d / "verify_demo_antenna" / "layout.log").exists():
        def cnt(f):
            t = (d / "verify_demo_antenna" / f).read_text()
            b, a = re.findall(r"^BEFORE=(\d+)", t, re.M), re.findall(r"^AFTER=(\d+)", t, re.M)
            return int(a[-1]) - int(b[-1]), int(b[-1])
        ctl, _ = cnt("control.log")
        lay, pre = cnt("layout.log")
        summ = next(d.glob("ANTENNA_SUMMARY_*.txt")).read_text()
        m = re.search(r"layout ([0-9a-f]{16})", summ)
        tv = dict(l.split(":", 1) for l in next(d.glob("TOOL_VERSIONS_*.txt")).read_text().splitlines() if ":" in l)
        out["antenna"] = dict(control_flagged=ctl, violations=lay, extraction_warnings=pre,
                              gds_matches=bool(m) and gds.startswith(m.group(1)), magic="Magic " + tv["magic"].strip(),
                              valid=ctl > 0 and bool(m) and gds.startswith(m.group(1)),
                              unknown_layer_reads=(d / "verify_demo_antenna" / "layout.log").read_text().count("layer=64 type=44"))
    d = REP / "extra_drc"
    if (d / "verify_demo_extra_drc" / "layout.lyrdb").exists():
        def items(f):
            return len(ET.parse(d / "verify_demo_extra_drc" / f).getroot().findall(".//item"))
        summ = next(d.glob("EXTRA_DRC_SUMMARY_*.txt")).read_text()
        m = re.search(r"layout ([0-9a-f]{16})", summ)
        tv = dict(l.split(":", 1) for l in next(d.glob("TOOL_VERSIONS_*.txt")).read_text().splitlines() if ":" in l)
        c1, c2, lay = items("ctl_offgrid.lyrdb"), items("ctl_floating.lyrdb"), items("layout.lyrdb")
        out["extra_drc"] = dict(control_offgrid=c1, control_floating=c2, violations=lay, gds_matches=bool(m) and gds.startswith(m.group(1)),
                                klayout=tv["klayout"].strip(), deck="sky130A_mr.drc",
                                valid=c1 > 0 and c2 > 0 and bool(m) and gds.startswith(m.group(1)))
    return out


def main():
    native = run(REP, "signoff_proof_native.txt")
    native["environment"] = dict(where="layout author's machine, gLayout virtual environment")
    native_tools = proof(REP / "signoff_proof_native.txt")["tools"]
    if native_tools:
        native["environment"].update(native_tools)
    else:
        native["environment"]["note"] = "tool versions not recorded by the native proof"
    cont = run(REP / "container_repro", "signoff_proof_container.txt", "CONTAINER_ENV.txt")
    ext = json.loads((REP / "extract_status.json").read_text())
    pex = REP / "pex" / "vga_core_12t_pex.spice"
    env = cont.get("environment", {})
    tools = {k: env[k] for k in ("klayout", "magic", "netgen", "pdk") if k in env}
    steps = [dict(step="drc", ok=native["drc"]["passed"] and cont["drc"]["passed"],
                  errors=sum(native["drc"]["violations"].values()) + sum(cont["drc"]["violations"].values())),
             dict(step="lvs", ok=native["lvs"]["passed"] and cont["lvs"]["passed"],
                  unique=native["lvs"]["unique"] and cont["lvs"]["unique"],
                  property_errors=native["lvs"]["property_errors"] or cont["lvs"]["property_errors"]),
             dict(step="pex", ok=ext["pass"], netlist=str(pex.relative_to(ROOT)), n_caps=ext["capacitors"],
                  node_caps_ff=lf.pex_summary(pex))]
    N_NEG = 6                                   # the controls prove_signoff.sh runs; fewer means a run was cut short
    runs_ok = all(r["drc"]["passed"] and r["lvs"]["passed"] and r["lvs"]["unique"] and not r["lvs"]["property_errors"]
                  and r["sizes_identical"] and r["fingerprints_match"] and len(r["negative_controls"]) == N_NEG
                  and all(n["rejected"] for n in r["negative_controls"]) and r["positive_control"] is not False
                  for r in (native, cont))
    rep = dict(source="imported from the sign-off runs in layout/reports (tools/import_signoff.py)",
               gds="layout/vga_core_12t.gds", container_tools=tools, extraction="native (generator's environment)",
               time=native["proof_time"], steps=steps, runs=dict(native=native, container=cont),
               ok=runs_ok and all(s["ok"] for s in steps))
    rep.update(extras())
    lf.REPORT.write_text(json.dumps(rep, indent=1))
    for k, r in rep["runs"].items():
        print(f"{k}: DRC {'PASS' if r['drc']['passed'] else 'FAIL'} {r['drc']['violations']}; LVS "
              f"{'unique match' if r['lvs']['unique'] else 'NO MATCH'}{', property errors' if r['lvs']['property_errors'] else ''}; "
              f"negative controls rejected {sum(n['rejected'] for n in r['negative_controls'])}/{len(r['negative_controls'])}; "
              f"fingerprints of the committed files {'match' if r['fingerprints_match'] else 'DO NOT MATCH'}")
    for k, v in extras().items():
        print(f"{k}: " + ", ".join(f"{a}={b}" for a, b in v.items()))
    print("overall:", "PASS" if rep["ok"] else "FAIL", "->", lf.REPORT.relative_to(ROOT))


if __name__ == "__main__":
    main()
