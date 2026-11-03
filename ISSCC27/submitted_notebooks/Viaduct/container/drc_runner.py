"""Viaduct DRC runner: the SKY130 KLayout DRC deck in batch, results as JSON.

Deck: /foss/pdks/<pdk>/libs.tech/klayout/drc/<pdk>_mr.drc (the PDK's manufacturing
rules deck, shipped with the image). Each run gets runs/drc_<run_id>/ with the
input GDS, drc.lyrdb (KLayout report database, opens in the Marker Browser),
klayout.log and metrics.json.

The deck is the open-source community deck: it is not the foundry signoff deck,
and density rules are not part of it. Report the deck and its release with results.
"""
import json
import os
import re
import secrets
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUNS_DIR = os.path.join(ROOT, "runs")


def deck_path(pdk):
    return "/foss/pdks/%s/libs.tech/klayout/drc/%s_mr.drc" % (pdk, pdk)


def new_run():
    run_id = time.strftime("%Y%m%d_%H%M%S_") + secrets.token_hex(2)
    run_dir = os.path.join(RUNS_DIR, "drc_" + run_id)
    os.makedirs(run_dir)
    return run_id, run_dir


def parse_lyrdb(path, max_examples=3):
    root = ET.parse(path).getroot()
    descriptions = {}
    for cat in root.iter("category"):
        name = cat.findtext("name")
        if name:
            descriptions[name] = (cat.findtext("description") or "").strip()
    counts, examples = {}, {}
    for item in root.iter("item"):
        cat = (item.findtext("category") or "").strip().strip("'")
        counts[cat] = counts.get(cat, 0) + 1
        if len(examples.setdefault(cat, [])) < max_examples:
            vals = [v.text for v in item.iter("value") if v.text]
            examples[cat].append(vals[0][:160] if vals else "")
    rules = [{"rule": c, "count": n, "description": descriptions.get(c, ""), "examples": examples.get(c, [])}
             for c, n in sorted(counts.items(), key=lambda kv: -kv[1])]
    return {"violations": sum(counts.values()), "rules_violated": len(counts), "rules": rules,
            "rules_checked": len(descriptions)}


def run(gds, pdk="sky130A", options=None, timeout=1800, run=None):
    run_id, run_dir = run or new_run()
    local = os.path.join(run_dir, os.path.basename(gds))
    if os.path.abspath(gds) != os.path.abspath(local):
        shutil.copy2(gds, local)
    deck = deck_path(pdk)
    report = os.path.join(run_dir, "drc.lyrdb")
    # The deck defaults every rule group to OFF ($feol/$beol/$offgrid = "false" when
    # not given), which silently checks nothing; turn them on unless told otherwise.
    opts = dict({"feol": "true", "beol": "true", "offgrid": "true"}, **(options or {}))
    rd = ["-rd", "input=%s" % local, "-rd", "report=%s" % report]
    for k, v in opts.items():
        rd += ["-rd", "%s=%s" % (k, v)]
    t0 = time.time()
    proc = subprocess.run(["bash", "-lc", "klayout -b -r %s %s" % (deck, " ".join("'%s'" % a for a in rd))],
                          capture_output=True, text=True, timeout=timeout)
    log = "\n".join(l for l in (proc.stdout + proc.stderr).splitlines() if not l.startswith("[INFO]"))
    with open(os.path.join(run_dir, "klayout.log"), "w") as f:
        f.write(log)
    release = None
    try:
        with open(deck) as f:
            m = re.search(r'release\s*=\s*"([^"]+)"', f.read())
        release = m.group(1) if m else None
    except OSError:
        pass
    out = {"run_id": run_id, "run_dir": run_dir, "engine": "klayout-drc", "deck": deck, "deck_release": release,
           "pdk": pdk, "gds": local, "report": report, "options": opts, "exit_code": proc.returncode,
           "seconds": round(time.time() - t0, 2),
           "note": "community SKY130 deck (no density rules); not a foundry signoff"}
    if proc.returncode == 0 and os.path.exists(report):
        out.update(parse_lyrdb(report))
        out["sections_run"] = [s for s in ("FEOL section", "BEOL section", "OFFGRID section") if s in log]
        if not out["sections_run"]:
            out["status"] = "FAILED"
            out["error"] = "the deck ran no rule section; nothing was checked"
        else:
            out["status"] = "COMPLETE"
            out["clean"] = out["violations"] == 0
    else:
        out["status"] = "FAILED"
        out["log_tail"] = log.splitlines()[-20:]
    with open(os.path.join(run_dir, "metrics.json"), "w") as f:
        json.dump(out, f, indent=2)
    return out
