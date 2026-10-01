import hashlib
import json
from pathlib import Path
import re
import zlib

import matplotlib.pyplot as plt
from PIL import Image
import pytest

from presentation import contest_materials as poster, release_facts, specification_map
import entry_tools

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def facts():
    return release_facts.load_facts()


def test_poster_choices_are_checked_original_specification_rows(facts):
    analysis = specification_map.load_checked(entry_tools.load_evidence())
    rows = facts["sampled_schematic"]["poster_choices"]
    assert [row["minimum_abs_input_mv"] for row in rows] == [1, 3, 30]
    assert [row["winner"] for row in rows] == [None, "lvt_balanced_4b", "lvt_base_3b"]
    assert rows[0]["correct"] is rows[0]["points"] is rows[0]["mean_core_energy_fj"] is None
    assert rows[0]["sampled_limits"] is None
    for row in rows:
        expected = next(item for item in analysis["per_specification"]
                        if item["minimum_abs_input_mv"] == row["minimum_abs_input_mv"]
                        and item["deadline_ns"] == 1)
        assert {key: row[key] for key in expected} == expected
    assert (rows[1]["correct"], rows[1]["points"]) == (294, 294)
    assert rows[1]["mean_core_energy_fj"] == pytest.approx(249.6551218639529)
    assert rows[1]["sampled_limits"]["minimum_decision_margin_ps"] == pytest.approx(154.51661322480092)
    assert rows[1]["sampled_limits"]["maximum_core_energy_fj"] == pytest.approx(363.2168092468344)
    assert (rows[2]["correct"], rows[2]["points"]) == (98, 98)
    assert rows[2]["mean_core_energy_fj"] == pytest.approx(150.53079968338895)
    assert facts["sampled_schematic"]["selected_wrong"] == {
        "count_1ns": 20, "count_2ns": 20, "same_sample_set": True, "signed_inputs_mv": [-1.0, 1.0],
    }


def contrast_on_white(color):
    channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
              for value in channels]
    luminance = sum(weight * value for weight, value in zip((0.2126, 0.7152, 0.0722), linear))
    return 1.05 / (luminance + 0.05)


def test_actual_poster_text_bounds_columns_contrast_and_semantics(facts):
    figure, audit = poster.poster_figure(facts)
    try:
        saved = json.loads((poster.OUTPUT / "poster_manifest.json").read_bytes())
        assert saved["presentation"] == audit
        assert audit["page_inches"] == [24, 18]
        assert audit["columns"] == [0.04, 0.355, 0.67]
        assert audit["all_text_in_bounds"] and audit["text_overlaps"] == 0
        assert len(audit["images"]) == 2
        for item in audit["text"]:
            assert item["font_pt"] >= 14
            assert contrast_on_white(item["color"]) >= 4.5
            x, y, w, _ = item["bounds"]
            if 0.14 < y < 0.85:
                column = max(value for value in audit["columns"] if value <= x + 0.001)
                assert x + w <= column + audit["column_width"] + 0.002, item["text"]
        text = "\n".join(item["text"] for item in audit["text"])
        for required in (
            "local_boundary", "49", "through 30 mV", "294/294", "98/98",
            "249.655", "150.531", "154.517", "363.217", "NONE", "not defined",
            "Post-hoc", "do not identify a physical failure cause", "45 PVT", "code-zero",
            "156/180", "180/180", "24 unresolved", "zero wrong", "prospectively declared",
            "245.84", "425.49", "1.835", "structural checks only",
            "GitHub Copilot assisted", "the author is responsible",
        ):
            assert required in text.replace("\n", " "), required
        assert "Archived RC-deck outcomes; model physical fidelity not yet qualified" in text
        assert "timing signoff or a worst-cycle guarantee" in text
    finally:
        plt.close(figure)


def test_poster_artifacts_pdf_fonts_links_dimensions_and_integrity(facts):
    manifest = json.loads((poster.OUTPUT / "poster_manifest.json").read_bytes())
    assert manifest["facts"] == facts
    for name, digest in manifest["artifact_sha256"].items():
        assert hashlib.sha256((poster.OUTPUT / name).read_bytes()).hexdigest() == digest
    assert manifest["generator_sha256"] == entry_tools.digest(Path(poster.__file__))
    assert manifest["new_physical_experiments"] == 0
    assert manifest["design_provenance"]["copied_reference_assets"] is False
    assert manifest["design_provenance"]["native_size_changed"] is False
    assert Image.open(poster.OUTPUT / "poster_preview.png").size == (2400, 1800)
    pdf = (poster.OUTPUT / "Comparator_Atlas_Poster.pdf").read_bytes()
    assert re.findall(rb"/MediaBox\s*\[([^]]+)\]", pdf) == [b" 0 0 1728 1296 "]
    assert len(re.findall(rb"/Type /Page\b", pdf)) == 1
    assert pdf.count(b"/FontFile2") >= 2
    assert b"DejaVuSans" in pdf and b"/Subtype /Type0" in pdf
    assert b"/Title (" + poster.PRESENTATION_TITLE.encode() + b")" in pdf
    assert b"/Author (Wei-Lun Hsu)" in pdf
    assert re.findall(rb"/URI\s*\(([^)]+)\)", pdf) == [
        facts["notebook_url"].encode(), facts["colab_url"].encode(),
    ]
    streams = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", pdf, re.S):
        try:
            streams.append(zlib.decompress(match[1]))
        except zlib.error:
            continue
    assert any(b"BT" in stream and b" TJ" in stream for stream in streams), "Missing vector text"


def test_reviewer_guide_regeneration_preserves_early_map_failures_limits(monkeypatch, facts):
    captured = {}
    monkeypatch.setattr(Path, "write_text",
                        lambda path, text, **kwargs: captured.update({str(path): text}))
    release_facts.write_judge_guide(facts)
    guide = captured[str(ROOT / "REVIEWER_GUIDE.md")]
    assert guide == (ROOT / "REVIEWER_GUIDE.md").read_text(encoding="utf-8")
    assert guide.index("strict specification map") < guide.index("Inspect actual layout")
    assert guide.index("keyed transition matrices") < guide.index("Inspect actual layout")
    for item in ("1,176", "all exact limiting ties", "NONE stays null", "20 wrong",
                 "two-point RC sensitivity", "GDS geometry audit", "before its interactive controls",
                 "GitHub Copilot assisted", "Archived RC-deck outcomes; model physical fidelity"):
        assert item in guide
