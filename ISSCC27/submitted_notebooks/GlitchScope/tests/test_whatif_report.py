"""Fix suggestions, group attribution, parallel equivalence, random-vector flow and HTML report."""
import json
import random
import re
import tempfile
from pathlib import Path

from glitchscope.test_support import lib_path_or_none

ROOT = Path(__file__).resolve().parents[1]


def _setup(bench="rca8", nv=40):
    from glitchscope.verilog import read_verilog
    from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
    lib_path = lib_path_or_none()
    lib = parse_liberty_file(lib_path)
    net = read_verilog(ROOT / f"bench/netlists/{bench}.v")
    rnd = random.Random(3)
    vecs = [{p: rnd.randint(0, 1) for p in net.primary_inputs} for _ in range(nv)]
    return lib_path, lib, net, LibertyDelayProvider(lib), vecs


def test_make_groups_partitions():
    from glitchscope.verilog import read_verilog
    from glitchscope.attribution import make_groups
    net = read_verilog(ROOT / "bench/netlists/mul4.v")
    for by in ("hier", "level"):
        g = make_groups(net, by, bands=4)
        cells = [c for cs in g.values() for c in cs]
        assert sorted(cells) == sorted(c.name for c in net.cells), by


def test_pin_swap_and_resize_edits_preserve_function():
    if not lib_path_or_none():
        return
    from glitchscope.functional import evaluate_stable
    from glitchscope.m2model import M2Model
    from glitchscope.model import ps_to_fs
    from glitchscope.whatif import WhatIf
    from dataclasses import replace
    lib_path, lib, net, dp, vecs = _setup(nv=12)
    wi = WhatIf(net, lib, lib_path, dp, M2Model(), vecs, sim_kwargs=dict(default_input_slew_fs=ps_to_fs(40)))
    name = max(wi.touched, key=lambda c: len(wi.touched[c]))
    edits = wi.edits_for(name)
    kinds = {e["kind"] for e in edits}
    assert "resize" in kinds or "pin swap" in kinds
    for e in edits:
        net2 = replace(net, cells=[e["cells"].get(c.name, c) for c in net.cells])
        for v in vecs[:6]:
            assert {o: evaluate_stable(net, v)[o] for o in net.primary_outputs} == \
                   {o: evaluate_stable(net2, v)[o] for o in net.primary_outputs}
    # an edit evaluated twice (serial) gives the same numbers; untouched steps are not re-run
    r1 = wi.evaluate(edits[:2]); r2 = wi.evaluate(edits[:2])
    assert [round(r["dE_total_fJ"], 9) for r in r1] == [round(r["dE_total_fJ"], 9) for r in r2]
    assert all(r["steps_resimulated"] <= len(vecs) for r in r1)


def test_parallel_attribution_identical():
    if not lib_path_or_none():
        return
    from glitchscope.analyze import EnergyModel
    from glitchscope.attribution import InterventionalAttribution
    from glitchscope.m2model import M2Model
    from glitchscope.model import ps_to_fs
    lib_path, lib, net, dp, vecs = _setup(nv=60)
    out = []
    for w in (1, 2):
        ia = InterventionalAttribution(net, dp, M2Model(), EnergyModel(lib_path, net, spice_scale=True), vecs,
                                       sim_kwargs=dict(default_input_slew_fs=ps_to_fs(40)), workers=w)
        r = ia.run(top_k=4, perms=4, candidates=5)
        out.append((r["top"], round(r["joint_top"], 9), [(c, round(g, 9)) for c, g in r["greedy"]]))
        # cone bound really bounds every evaluated single gain
        assert all(r["single"][c] <= ia.bound(c) + 1e-9 for c in r["single"])
    assert out[0] == out[1]


def test_random_vector_flow_writes_html_report():
    lib = lib_path_or_none()
    if not lib:
        return
    from glitchscope.flow import run_design, write_report
    res = run_design(ROOT / "bench/netlists/rca8.v", None, lib, random_vectors=30, workers=1,
                     groups="level:4", fixes=2, perms=4, top_k=4)
    with tempfile.TemporaryDirectory() as d:
        write_report(res, d)
        page = (Path(d) / "report.html").read_text()
        assert "<title>rca8 glitch report</title>" in page
        data = json.loads(re.search(r'<script id="gs-data" type="application/json">(.*?)</script>', page, re.S)
                          .group(1).replace("<\\/", "</"))
        assert data["attribution"]["top"] and data["groups"]["rows"] and data["whatif"]["rows"]
        assert len(data["cycles"]["glitch"]) == 30
        assert (Path(d) / "fix_suggestions.csv").exists()
