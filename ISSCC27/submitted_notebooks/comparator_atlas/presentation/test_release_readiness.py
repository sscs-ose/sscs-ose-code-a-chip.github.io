import ast
import base64
import hashlib
import json
from pathlib import Path
import textwrap

import pytest

from presentation.release_facts import COLAB_URL, NOTEBOOK, load_facts


def bootstrap_source() -> str:
    path = Path(__file__).resolve().parents[1] / "scripts" / "build_entry_notebook.py"
    module = ast.parse(path.read_text(encoding="utf-8"))
    sources = [
        node.args[0].value for node in ast.walk(module)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id == "code" and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ]
    first = next(source for source in sources if "entry_root = next(" in source)
    return textwrap.dedent(first)


def execute_directory_detection(monkeypatch, cwd: Path) -> dict:
    # Use the exact generated bootstrap through its directory-detection block.
    source = bootstrap_source()
    source = source[:source.index("required = {")]
    monkeypatch.chdir(cwd)
    namespace = {}
    exec(compile(source, "<notebook-bootstrap>", "exec"), namespace)
    return namespace


def test_current_colab_link_is_to_the_live_submission_branch():
    assert "/github/WLHsu0827/sscs-ose-code-a-chip.github.io/" in COLAB_URL
    assert "/blob/wlhsu0827-comparator-atlas-isscc27/" in COLAB_URL
    assert COLAB_URL.endswith("/" + NOTEBOOK)
    root = Path(__file__).resolve().parents[1]
    notebook = json.loads((root / NOTEBOOK).read_bytes())
    introduction = "".join(notebook["cells"][0]["source"])
    assert f"[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]({COLAB_URL})" in introduction
    assert "Official-main Colab link (available only after merge)" in introduction


def test_notebook_abstract_reports_both_full_grid_deadlines(monkeypatch):
    from scripts import build_entry_notebook

    root = Path(__file__).resolve().parents[1]
    notebook = json.loads((root / NOTEBOOK).read_bytes())
    introduction = "".join(notebook["cells"][0]["source"])
    abstract = " ".join(
        introduction.split("## Abstract", 1)[1].split("## Getting started", 1)[0].split()
    )
    facts = load_facts()
    full = facts["postlayout_pvt45"]
    assert full["nominal_geometry"] is True
    assert full["trim_code"] == 0
    expected = (
        f"In the {full['conditions']}-condition nominal, code-zero study, archived RC "
        f"decks give {full['rc_correct_1ns']}/{full['points_per_mode']} correct "
        f"decisions at {full['parallel_deadline_ns']} ns "
        f"({full['rc_unresolved_1ns']} unresolved) and "
        f"{full['rc_correct_2ns']}/{full['points_per_mode']} at the prospectively "
        f"declared {full['primary_deadline_ns']} ns deadline; the worst sampled "
        f"decision time is {full['worst_rc_delay_ns']:.3f} ns."
    )
    assert expected in abstract
    assert "extracted-model physical fidelity is not yet qualified." in abstract
    assert "Schematic results are unaffected by this extraction concern." in abstract
    generated = []
    monkeypatch.setattr(
        build_entry_notebook.nbf, "write",
        lambda document, destination: generated.append(document),
    )
    build_entry_notebook.main()
    assert len(generated) == 1
    assert generated[0].cells[0].source == introduction


def test_reviewer_navigation_links_resolve_to_local_artifacts():
    root = Path(__file__).resolve().parents[1]
    for name in ("README.md", "REVIEWER_GUIDE.md"):
        text = (root / name).read_text(encoding="utf-8")
        first_section = text.index("\n## ")
        warning = "GitHub's file viewer does not execute its JavaScript"
        assert text.count(warning) == 1
        assert text.index(warning) < first_section
        for label, target in (
            ("interactive report", "results/study/report.html"),
            ("poster PDF", "results/study/Comparator_Atlas_Poster.pdf"),
            ("preview image", "results/study/poster_preview.png"),
        ):
            link = f"[{label}]({target})"
            assert text.count(link) == 1
            assert text.index(link) < first_section
            assert (root / target).is_file()


def test_static_review_sources_match_the_notebook_generator(monkeypatch):
    from scripts import build_entry_notebook

    root = Path(__file__).resolve().parents[1]
    notebook = json.loads((root / NOTEBOOK).read_bytes())
    generated = []
    monkeypatch.setattr(
        build_entry_notebook.nbf, "write",
        lambda document, destination: generated.append(document),
    )
    build_entry_notebook.main()
    for index in (0, 13, 14):
        assert generated[0].cells[index].source == "".join(notebook["cells"][index]["source"])


def test_getting_started_links_work_outside_the_repository():
    root = Path(__file__).resolve().parents[1]
    notebook = json.loads((root / NOTEBOOK).read_bytes())
    introduction = "".join(notebook["cells"][0]["source"])
    getting_started = introduction.split("## Getting started", 1)[1]
    fork = COLAB_URL.replace("https://colab.research.google.com/github/", "https://github.com/")
    entry_url = fork.rsplit("/", 1)[0]
    for target in ("REVIEWER_GUIDE.md", "results/study/report.html"):
        assert f"]({entry_url}/{target})" in getting_started
    assert "Download the report and open its HTML locally" in getting_started
    assert "remeasures saved waveforms" in getting_started
    assert "does not run new simulations" in getting_started


def test_static_waveform_examples_use_existing_one_ns_readings(monkeypatch):
    import subprocess
    import matplotlib.pyplot as plt
    import pandas as pd
    from presentation import waveform_lab

    root = Path(__file__).resolve().parents[1]
    notebook = json.loads((root / NOTEBOOK).read_bytes())
    source = "".join(notebook["cells"][14]["source"]).split("example_control =", 1)[0]
    calls, displayed = [], []
    original_figure = waveform_lab.figure

    def capture(data, identifier, deadline_ns):
        assert data["new_physical_simulations"] == 0
        calls.append((identifier, deadline_ns))
        return original_figure(data, identifier, deadline_ns)

    def forbid_subprocess(*args, **kwargs):
        pytest.fail("Static waveform examples must not start simulations or other subprocesses")

    monkeypatch.setattr(waveform_lab, "figure", capture)
    monkeypatch.setattr(subprocess, "run", forbid_subprocess)
    namespace = {"plt": plt, "pd": pd, "display": lambda *items: displayed.extend(items)}
    exec(compile(source, "<static-waveform-examples>", "exec"), namespace)
    assert calls == [("schematic_untrimmed", 1.0), ("schematic_calibrated", 1.0)]
    assert len(displayed) == 4
    for offset, (identifier, deadline) in enumerate(calls):
        _, retained = waveform_lab.inspect_sample(namespace["lab"], identifier, deadline)
        assert displayed[2 * offset + 1].to_dict("records") == [{
            "outcome": retained["outcome"],
            "deadline_ns": 1.0,
            "Q+_at_deadline_V": retained["qp_at_deadline_v"],
            "Q-_at_deadline_V": retained["qn_at_deadline_v"],
            "sampled_decision_time_ns": retained["decision_time_ns"],
            "full_cycle_core_energy_fJ": retained["core_energy_fj"],
        }]
    assert [displayed[index].iloc[0]["outcome"] for index in (1, 3)] == ["wrong", "correct"]


def test_saved_waveform_outputs_are_readable_without_widget_javascript():
    import matplotlib.pyplot as plt
    import pandas as pd
    from presentation import waveform_lab

    root = Path(__file__).resolve().parents[1]
    notebook = json.loads((root / NOTEBOOK).read_bytes())
    outputs = notebook["cells"][14]["outputs"]
    data = waveform_lab.load_lab()
    assert len(outputs) >= 7
    for index, identifier in enumerate(("schematic_untrimmed", "schematic_calibrated")):
        image = outputs[2 * index]["data"]["image/png"]
        encoded = "".join("".join(image).split())
        assert base64.b64decode(encoded, validate=True).startswith(b"\x89PNG\r\n\x1a\n")
        figure, reading = waveform_lab.figure(data, identifier, 1.0)
        plt.close(figure)
        columns = (
            "outcome", "deadline_ns", "Q+_at_deadline_V", "Q-_at_deadline_V",
            "sampled_decision_time_ns", "full_cycle_core_energy_fJ",
        )
        expected = pd.DataFrame([{key: reading[key] for key in columns}])
        table = outputs[2 * index + 1]["data"]
        assert "".join(table["text/html"]) == expected._repr_html_()
        assert reading["outcome"] in "".join(table["text/plain"])
    assert any(
        "application/vnd.jupyter.widget-view+json" in output.get("data", {})
        for output in outputs[4:]
    )


def test_completed_colab_checkout_is_reused_after_kernel_restart(tmp_path, monkeypatch):
    entry = tmp_path / "comparator-atlas-source" / "ISSCC27" / "submitted_notebooks" / "comparator_atlas"
    entry.mkdir(parents=True)
    (entry / "entry_tools.py").write_text("# fixture\n")
    result = execute_directory_detection(monkeypatch, tmp_path)
    assert result["entry_root"] == entry


def test_incomplete_download_is_not_silently_overwritten(tmp_path, monkeypatch):
    (tmp_path / "comparator-atlas-source").mkdir()
    with pytest.raises(RuntimeError, match="incomplete"):
        execute_directory_detection(monkeypatch, tmp_path)


def test_project_directory_and_repository_root_are_supported(tmp_path, monkeypatch):
    entry = tmp_path / "ISSCC27" / "submitted_notebooks" / "comparator_atlas"
    entry.mkdir(parents=True)
    (entry / "entry_tools.py").write_text("# fixture\n")
    assert execute_directory_detection(monkeypatch, tmp_path)["entry_root"] == entry
    assert execute_directory_detection(monkeypatch, entry)["entry_root"] == entry


def test_final_presentation_facts_keep_schematic_and_layout_scopes_separate():
    facts = load_facts()
    assert facts["notebook"] == "Comparator_Atlas.ipynb"
    assert facts["schematic"]["selected_correct_at_1mv"] == 372
    assert facts["schematic"]["points_at_1mv"] == 392
    assert facts["layout"]["rc_correct_1ns"] == 12
    assert facts["layout"]["rc_correct_posthoc_2ns"] == 20
    assert facts["layout"]["rc_sampled_points"] == 20
    assert facts["layout"]["original_1ns_pilot_qualified"] is False
    assert facts["layout"]["posthoc_2ns_is_new_qualification"] is False


def test_pilot_limit_does_not_deny_the_subsequent_completed_full_grid():
    facts = load_facts()
    pilot, full = facts["layout"], facts["postlayout_pvt45"]
    assert pilot["scope"] == "original_five_condition_pilot"
    assert pilot["simulator"] == "ngspice-42"
    assert pilot["condition_count"] == 5
    assert pilot["pilot_full_45_condition_extracted_sweep_performed"] is False
    assert "full_45_condition_pex_performed" not in pilot
    assert full["scope"] == "subsequent_separately_declared_full_grid_study"
    assert full["simulator"] == "ngspice-47"
    assert full["full_45_condition_extracted_sweep_performed"] is True
    assert (full["conditions"], full["points_per_mode"]) == (45, 180)
    assert (full["primary_deadline_ns"], full["parallel_deadline_ns"]) == (2, 1)
    assert (full["rc_correct_2ns"], full["rc_correct_1ns"]) == (180, 156)
    assert full["old_five_condition_1ns_gate_reinterpreted"] is False
    limits = " ".join(facts["limits"])
    assert "that pilot did not perform a full 45-condition extracted sweep" in limits
    assert "ngspice-47 study completed 45 conditions and 180 RC points" in limits
    assert "Only the original ngspice-42 pilot's 2 ns result is post-hoc" in limits
    assert "prospectively declared 2 ns primary deadline" in limits


def test_published_fact_consumers_match_current_scoped_evidence():
    root = Path(__file__).resolve().parents[1]
    facts = load_facts()
    metadata = json.loads((root / "entry_metadata.json").read_bytes())
    pilot, full = metadata["layout_addendum"], metadata["postlayout_pvt45"]
    assert pilot["scope"] == facts["layout"]["scope"]
    assert pilot["simulator"] == facts["layout"]["simulator"]
    assert pilot["pilot_full_45_condition_extracted_sweep_performed"] is False
    assert "full_45_condition_pex_performed" not in pilot
    assert full["scope"] == facts["postlayout_pvt45"]["scope"]
    assert full["full_45_condition_extracted_sweep_performed"] is True
    assert (full["rc_correct_at_2ns"], full["rc_correct_at_1ns"]) == (180, 156)
    source_hash = hashlib.sha256((root / "presentation" / "release_facts.py").read_bytes()).hexdigest()
    for relative, source_key in (
        ("results/presentation/reviewer_guide_manifest.json", "source_sha256"),
        ("results/study/poster_manifest.json", "release_facts_source_sha256"),
    ):
        manifest = json.loads((root / relative).read_bytes())
        assert manifest["facts"] == facts
        assert manifest[source_key] == source_hash


def test_rc_model_applicability_is_not_numerical_or_structural_qualification():
    from presentation.pvt45_results import RC_MODEL_NOTICE

    facts = load_facts()
    scope = facts["rc_model_applicability"]
    assert scope["physical_fidelity_qualified"] is False
    assert scope["mutual_retained_and_ground_capacitance_increase_observed"] is True
    assert scope["physical_error_magnitude_and_direction"] == "unknown"
    assert scope["c_only_is_independent_ground_truth"] is False
    assert scope["rc_versus_c_difference_is_pure_resistance"] is False
    assert scope["drc_lvs_scope"] == "recorded_structural_checks_only"
    assert scope["schematic_results_affected_by_this_extraction_concern"] is False
    assert scope["historical_measurements_and_pass_fail_rewritten"] is False
    assert scope["notice"] == RC_MODEL_NOTICE
    assert RC_MODEL_NOTICE in facts["limits"]
    assert facts["layout"]["original_1ns_pilot_qualified"] is False
    assert facts["postlayout_pvt45"]["all_360_numerical_histories_qualified"] is True
    assert facts["postlayout_pvt45"]["rc_correct_1ns"] == 156
    assert facts["postlayout_pvt45"]["rc_correct_2ns"] == 180


def test_current_public_text_retains_the_rc_model_warning():
    from presentation.contest_materials import PRESENTATION_TITLE
    from presentation.pvt45_results import RC_MODEL_LABEL, RC_SCOPE_NOTE

    root = Path(__file__).resolve().parents[1]
    for name in ("README.md", "REVIEWER_GUIDE.md", "REPRODUCIBILITY.md", "presentation/LAYOUT.md"):
        assert RC_MODEL_LABEL in (root / name).read_text(encoding="utf-8")
    assert RC_SCOPE_NOTE in (root / "results/study/report.html").read_text(encoding="utf-8")
    assert RC_SCOPE_NOTE in (root / "results/study/abstract.txt").read_text(encoding="utf-8")
    assert (root / "results/study/abstract.txt").read_text(encoding="utf-8").splitlines()[0] == PRESENTATION_TITLE
    assert b"/Title (" + PRESENTATION_TITLE.encode("ascii") + b")" in (
        root / "results/study/Comparator_Atlas_Poster.pdf"
    ).read_bytes()
    notebook = json.loads((root / NOTEBOOK).read_bytes())
    markdown = "\n".join("".join(cell["source"]) for cell in notebook["cells"]
                         if cell["cell_type"] == "markdown")
    assert RC_MODEL_LABEL in markdown
    assert "C-only is not independent ground truth" in markdown


@pytest.mark.parametrize("separator", ["/", "\\"])
def test_scoped_report_reuses_checked_figures_without_running_factories(monkeypatch, separator):
    from comparator_atlas import study_report
    from presentation.pvt45_results import RC_SCOPE_NOTE

    captured = {}
    read_text = Path.read_text

    def portable_manifest(path, *args, **kwargs):
        text = read_text(path, *args, **kwargs)
        if path == study_report.STUDY / "presentation_manifest.json":
            manifest = json.loads(text)
            manifest["artifact_sha256"] = {
                name.replace("\\", "/").replace("/", separator): digest
                for name, digest in manifest["artifact_sha256"].items()
            }
            return json.dumps(manifest)
        return text

    def forbid_regeneration(*args, **kwargs):
        raise AssertionError("Unselected figure factory must not run")

    monkeypatch.setattr(study_report, "cold_waveform_figure", forbid_regeneration)
    monkeypatch.setattr(Path, "read_text", portable_manifest)
    monkeypatch.setattr(study_report.shutil, "copyfile", lambda *args: None)
    monkeypatch.setattr(study_report, "write_json", lambda path, value: captured.update({path.name: value}))
    monkeypatch.setattr(Path, "write_text", lambda path, text, **kwargs: captured.update({path.name: text}))
    study_report.render_study(refresh_figures=set())
    assert RC_SCOPE_NOTE in captured["report.html"]
    assert captured["report.html"].count('<img ') == 15
    assert captured["presentation_manifest.json"]["rc_model_applicability_notice"] == RC_SCOPE_NOTE
    assert 'class="card"' not in captured["report.html"]
    for slogan in ("When calibration is not enough", "Inspect every decision yourself",
                   "A real weak-corner waveform", "not only a weak baseline"):
        assert slogan not in captured["report.html"]
    assert "12/20 correct points" in captured["report.html"]
    assert "180/180 correct at 2 ns; 156/180 at 1 ns" in captured["report.html"]
    from presentation import specification_map
    import entry_tools
    sampled = specification_map.load_checked(entry_tools.load_evidence())
    for table in (specification_map.failure_table(sampled),
                  specification_map.selected_wrong_table(sampled)):
        assert table.to_html(index=False, border=0) in captured["report.html"]
        assert table.to_html(index=False, border=0) in (
            study_report.STUDY / "report.html").read_text(encoding="utf-8")
    assert captured["presentation_manifest.json"]["sampled_schematic_analysis"] == {
        "source_sha256": entry_tools.digest(Path(specification_map.__file__)),
        "summary_sha256": entry_tools.digest(specification_map.FOLDER / "summary.json"),
    }


def test_scoped_report_rejects_changed_cached_figure(monkeypatch):
    from comparator_atlas import study_report

    original = study_report.sha256
    monkeypatch.setattr(study_report, "sha256",
                        lambda path: "changed" if Path(path).name == "search.png" else original(path))
    with pytest.raises(ValueError, match="Cannot reuse changed report figure: search.png"):
        study_report.render_study(refresh_figures=set())
