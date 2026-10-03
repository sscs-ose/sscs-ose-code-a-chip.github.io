import json
from pathlib import Path

import single_row_evidence as area


ROOT = Path(__file__).resolve().parents[1]


def test_readme_labels_current_and_historical_results_locally():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    current, historical = text.split(
        "### Historical original compact control: schematic and archived RC", 1)
    assert "421.045" in current and "1.810632" in current
    assert "425.49" in historical and "1.835" in historical
    assert "Archived original-control RC" in historical
    assert "not the adopted area version" in historical
    assert "layout_single_row/v1/" in text
    assert "final layout" not in text


def test_report_marks_both_historical_physical_sections():
    report = (ROOT / "results/study/report.html").read_text(encoding="utf-8")
    assert "Historical original compact control: geometry and pilot" in report
    assert "Historical original compact control: 45-PVT schematic/RC grid" in report
    assert "not candidate data" in report
    assert "not a new comparator topology or silicon benchmark" in report
    assert "1440 transients" in report and "720 qualified 10/5 ps pairs" in report
    assert "original compact control measures 129.6 x 17.03" in report


def test_current_surfaces_preserve_warning_disclosure_and_readable_units():
    notebook = json.loads((ROOT / "Comparator_Atlas.ipynb").read_bytes())
    sources = "\n".join("".join(c["source"]) for c in notebook["cells"])
    texts = [
        sources,
        (ROOT / "README.md").read_text(encoding="utf-8"),
        (ROOT / "REVIEWER_GUIDE.md").read_text(encoding="utf-8"),
        (ROOT / "REPRODUCIBILITY.md").read_text(encoding="utf-8"),
        (ROOT / "results/study/report.html").read_text(encoding="utf-8"),
        (ROOT / "results/study/abstract.txt").read_text(encoding="utf-8"),
    ]
    for text in texts:
        assert area.NOTICE in text
        assert "Copilot" in text
        for compressed in ("27guardedMOS", "1440NEW", "all1440raw", "by6.01852%"):
            assert compressed not in text
    assert len(notebook["cells"]) == 28
    assert sum(c["cell_type"] == "code" for c in notebook["cells"]) == 13


def test_references_use_verified_complete_author_metadata():
    notebook = json.loads((ROOT / "Comparator_Atlas.ipynb").read_bytes())
    sources = "\n".join("".join(c["source"]) for c in notebook["cells"])
    report = (ROOT / "results/study/report.html").read_text(encoding="utf-8")
    for text in (sources, report):
        for name in ("Behzad Razavi", "Shuowei Li", "Zule Xu", "Tetsuya Iizuka"):
            assert name in text
        assert "10.1109/MSSC.2015.2418155" in text
        assert "10.1007/s10470-022-01992-6" in text
        assert "535" in text and "546" in text


def test_reproduction_and_abstract_keep_populations_separate():
    reproduction = (ROOT / "REPRODUCIBILITY.md").read_text(encoding="utf-8")
    abstract = (ROOT / "results/study/abstract.txt").read_text(encoding="utf-8")
    assert "third, distinct population" in reproduction
    assert "not the adopted candidate" in reproduction
    assert "unavailable private directories" in reproduction
    assert "historical original compact control" in abstract
    assert "24 unresolved" in abstract and "2 ns primary deadline" in abstract
    assert "not uncertainty bounds" in abstract
    assert "post-hoc" in abstract and "not a robust PPA" in abstract
