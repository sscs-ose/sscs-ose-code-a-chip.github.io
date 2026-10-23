"""Tests of implant_fix.py and verify_untouched.py on a tiny synthetic macro (needs klayout on the PATH).  SPDX-License-Identifier: Apache-2.0"""
import filecmp
import pathlib
import shutil
import subprocess
import textwrap

import pytest

HERE = pathlib.Path(__file__).parent
KL = shutil.which("klayout")
pytestmark = pytest.mark.skipif(KL is None, reason="klayout not installed")


def klayout(script, **kw):
    args = [KL, "-b"] + [x for k, v in kw.items() for x in ("-rd", f"{k}={v}")] + ["-r", str(script)]
    return subprocess.run(args, capture_output=True, text=True)


def make_gds(path, with_diff_in_gap):
    s = path.with_suffix(".py")
    s.write_text(textwrap.dedent(f"""
        import pya
        ly = pya.Layout(); ly.dbu = 0.001
        top = ly.create_cell("sky130_sram_toy")
        for lay, gap in (((94, 20), 0.20), ((93, 44), 0.20), ((95, 20), 0.15)):
            li = ly.layer(*lay)
            top.shapes(li).insert(pya.DBox(0, 0, 1, 1)); top.shapes(li).insert(pya.DBox(1 + gap, 0, 2 + gap, 1))
            top.shapes(li).insert(pya.DBox(0, 5, 1, 6)); top.shapes(li).insert(pya.DBox(1 + 0.5, 5, 2.5, 6))   # legal gap
            break
        li = ly.layer(95, 20); top.shapes(li).insert(pya.DBox(10, 0, 11, 1)); top.shapes(li).insert(pya.DBox(11.15, 0, 12, 1))
        if {with_diff_in_gap}:
            top.shapes(ly.layer(65, 20)).insert(pya.DBox(1.0, 0.2, 1.2, 0.8))      # diffusion under the psdm gap
        ly.write("{path}")
    """))
    assert klayout(s).returncode == 0


def count(gds):
    return klayout(HERE / "count_implant_violations.py", gds=gds).stdout


def test_gap_is_closed_and_only_implants_change(tmp_path):
    g = tmp_path / "in.gds"; make_gds(g, False)
    assert "psdm: space 1" in count(g) and "npc: space 1" in count(g)
    out = tmp_path / "out.gds"
    r = klayout(HERE / "implant_fix.py", in_gds=g, out_gds=out)
    assert out.exists(), r.stdout + r.stderr
    after = count(out)
    assert "psdm: space 0" in after and "npc: space 0" in after
    v = klayout(HERE / "verify_untouched.py", a=g, b=out)
    assert "UNTOUCHED OK" in v.stdout, v.stdout + v.stderr


def test_nothing_is_written_when_the_gap_is_over_diffusion(tmp_path):
    g = tmp_path / "in.gds"; make_gds(g, True)
    out = tmp_path / "out.gds"
    r = klayout(HERE / "implant_fix.py", in_gds=g, out_gds=out)
    assert not out.exists()                                     # the check printed a non-zero implant change on diffusion
    assert "implant_changed_on_diff_tap_um2=0.12" in r.stdout


def test_copies_match_the_scripts_of_the_submission():
    scripts = HERE.parent.parent / "scripts"
    if scripts.exists():
        for f in ("implant_fix.py", "verify_untouched.py"):
            assert filecmp.cmp(HERE / f, scripts / f, shallow=False), f"{f} differs from scripts/{f}"
