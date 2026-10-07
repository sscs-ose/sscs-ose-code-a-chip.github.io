"""Integrated reader views over the unchanged saved-data strict selector."""
from collections import Counter
import hashlib
import html
import json
import math
from pathlib import Path
import re

import pandas as pd

import entry_tools as entry
from presentation import specification_map as spec

ROOT = entry.ROOT
STUDY = entry.STUDY
HEAD = "db82273a5df8b73d39ebf20593309e433d1a1d50"
LABEL = "Comparator Atlas | finite sampled design decisions"
WARNING = "Archived RC-deck outcomes; model physical fidelity not yet qualified"
DISCLOSURE = ("GitHub Copilot assisted implementation, experiment automation, figures and "
              "documentation; the author is responsible for the work.")
LEDE = ("Calibration does not necessarily mean correct before the deadline. First require every "
        "included sampled point to be correct; only then rank mean energy. If no compared circuit "
        "qualifies, return NONE - not the best average.")
OPENING = """Calibration does not necessarily mean correct before the deadline.
Comparator Atlas asks a concrete design question: for a sampled input band and deadline,
does any compared circuit qualify at every included point? Only then should mean energy
rank designs. A useful design tool must return NONE rather than a best-average fallback.
The same saved 49-condition schematic study gives three different answers at 1 ns:
>=1 mV: NONE; >=3 mV: lvt_balanced_4b, 294/294, 249.655 fJ;
>=30 mV: lvt_base_3b, 98/98, 150.531 fJ. This is a post-hoc comparison of three
designs under local_boundary calibration, both signed finite sampled inputs through
30 mV, not continuous coverage or a global optimization. Energies from different
input bands are not a same-specification energy improvement."""


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def load_payload():
    return json.loads((STUDY / "decision_data.json").read_bytes())


def validate_notebook_outputs(value, location="Notebook"):
    """Reject error outputs even when a widget swallowed the cell exception."""
    if isinstance(value, dict):
        if value.get("output_type") == "error":
            raise ValueError(f"Notebook reader error at {location}: {value.get('evalue')}")
        for key, item in value.items():
            validate_notebook_outputs(item, f"{location}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            validate_notebook_outputs(item, f"{location}[{index}]")


def build_payload():
    evidence = entry.load_evidence()
    saved = spec.load_checked(evidence)
    frame = evidence["frame"]
    observed = frame[frame.policy.eq("local_boundary") & frame.input_mv.ne(0)]
    lab = json.loads((ROOT / "evidence_traces/waveform_lab/waveform_lab.json").read_bytes())
    observations = []
    original_count = len(pd.read_csv(STUDY / "verified_measurements.csv"))
    for index, row in observed.iterrows():
        record = {field: (None if pd.isna(row[field]) else row[field]) for field in spec.OBSERVATION}
        record["trim_code"] = int(record["trim_code"])
        record["source_csv"] = ("professional/measurements.csv" if row.design_name == "lvt_base_3b"
                                else "verified_measurements.csv")
        record["source_record"] = int(index - original_count + 1
                                      if row.design_name == "lvt_base_3b" else index + 1)
        record["observation_id"] = len(observations)
        record["waveform_sample_id"] = None
        for sample in lab["samples"]:
            point = sample["point"]
            if sample["source_kind"] != "schematic" or sample["id"] != "schematic_calibrated":
                continue
            if sample["run_id"] != row.run_id or point["design_name"] != row.design_name:
                continue
            if any(point[field] != row[field] for field in ("corner", "vdd_v", "temperature_c",
                                                          "pair_skew", "trim_code")) \
                    or point["differential_v"] * 1000 != row.input_mv:
                continue
            reading = next(v for v in sample["observations"] if v["deadline_ns"] == row.deadline_ns)
            assert reading["outcome"] == row.outcome
            assert math.isclose(reading["core_energy_fj"], row.core_energy_fj, rel_tol=1e-12)
            assert (reading["decision_time_ns"] is None and pd.isna(row.decision_time_ns)) \
                or math.isclose(reading["decision_time_ns"], row.decision_time_ns, abs_tol=1e-12)
            record["waveform_sample_id"] = sample["id"]
        observations.append(record)
    candidates = []
    for row in saved["per_design"]:
        part = observed[observed.design_name.eq(row["design"])
                        & observed.deadline_ns.eq(row["deadline_ns"])
                        & observed.input_mv.abs().ge(row["minimum_abs_input_mv"])]
        counts = Counter(part.outcome)
        candidates.append({**row, "wrong": counts["wrong"], "unresolved": counts["unresolved"]})
    payload = {
        "schema": 1, "label": LABEL, "based_on": HEAD, "scope": saved["scope"],
        "minimums": list(spec.MINIMUMS_MV), "deadlines": list(spec.DEADLINES_NS),
        "designs": list(spec.DESIGNS), "selections": saved["per_specification"],
        "candidates": candidates, "observations": observations,
        "selected_wrong": saved["failure_analysis"]["selected_wrong"],
        "source_sha256": saved["source_sha256"],
        "waveform_lab_sha256": sha(ROOT / "evidence_traces/waveform_lab/waveform_lab.json"),
        "new_physical_simulations": 0,
    }
    write_json(STUDY / "decision_data.json", payload)
    original_cube = json.loads((STUDY / "explorer_data.json").read_bytes())
    local = frame[frame.policy.eq("local_boundary")]
    statuses = {"wrong": 0, "unresolved": 1, "correct": 2, "reference": 4}
    cube = {**original_cube, "designs": list(spec.DESIGNS),
            "policies": ["local_boundary"], "policyLabels": ["local_boundary: all 49 conditions"]}
    cube["rows"] = [
        [cube["designs"].index(row.design_name), cube["cases"].index(row.case_id), 0,
         cube["deadlines"].index(row.deadline_ns), cube["inputs"].index(row.input_mv),
         4 if row.input_mv == 0 else statuses[row.outcome],
         None if pd.isna(row.decision_time_ns) else row.decision_time_ns,
         row.core_energy_fj, int(row.trim_code)] for row in local.itertuples()
    ]
    assert len(cube["rows"]) == 3 * 49 * 13 * 6
    write_json(STUDY / "decision_map_data.json", cube)
    return payload, cube


def inspect(minimum, deadline, payload=None):
    data = payload or load_payload()
    if minimum not in data["minimums"] or deadline not in data["deadlines"]:
        raise ValueError("Select exactly a published sampled input and deadline")
    candidates = [r for r in data["candidates"]
                  if r["minimum_abs_input_mv"] == minimum and r["deadline_ns"] == deadline]
    choice = next(r for r in data["selections"]
                  if r["minimum_abs_input_mv"] == minimum and r["deadline_ns"] == deadline)
    actual = spec.choose(candidates)
    assert all(actual[key] == choice[key] for key in actual)
    return choice, candidates


def notebook_view(minimum, deadline):
    data = load_payload()
    choice, candidates = inspect(minimum, deadline, data)
    title = (f"NONE: no feasible compared design; winner energy and limits are null."
             if choice["winner"] is None else
             f"{choice['winner']}: {choice['mean_core_energy_fj']:.3f} fJ mean core / cycle; "
             f"exact ties: {', '.join(choice['minimum_energy_ties'])}.")
    table = pd.DataFrame(candidates)[["design", "correct", "wrong", "unresolved",
                                     "points", "all_correct", "mean_core_energy_fj"]]
    witnesses = [r for r in data["observations"] if r["deadline_ns"] == deadline
                 and abs(r["input_mv"]) >= minimum and r["outcome"] != "correct"]
    rows = []
    for record in witnesses:
        link = f"results/study/report.html#decision={minimum},{deadline},{record['observation_id']}"
        rows.append({
            "design": record["design_name"], "case": record["case_id"],
            "input_mV": record["input_mv"], "trim": record["trim_code"],
            "outcome": record["outcome"], "decision_ns": record["decision_time_ns"],
            "run_id": record["run_id"],
            "source": f"{record['source_csv']} record {record['source_record']}",
            "raw_waveform": record["waveform_sample_id"] or "No matching retained raw waveform",
            "inspect_exact_key": f'<a href="{html.escape(link, quote=True)}">Open keyed report/map</a>',
        })
    witness_table = pd.DataFrame(rows[:12]).to_html(index=False, escape=False, na_rep="null") if rows else "<p>No disqualifying measurements.</p>"
    return (f"<h3>Sampled |input| &gt;= {minimum:g} mV; {deadline:g} ns</h3><p><strong>{title}</strong></p>"
            + table.to_html(index=False, float_format=lambda v: f"{v:.3f}")
            + f"<p>{len(rows)} exact disqualifying measurements across all three designs. First twelve below; "
            "the report exposes every witness and its CSV location. Null unresolved latency is not zero.</p>"
            + witness_table + "<p>All 49 controlled-width-stress schematic conditions, local_boundary, "
            "both signed sampled inputs through 30 mV. Full-cycle 20-30 ns core energy; no interpolation, "
            "noise/yield/global optimum or driver/controller energy claim.</p>")


def integrate_notebook(notebook):
    notebook.cells[0].source = (
        "# Comparator Atlas: correct before the deadline - or NONE?\n\n"
        f"**{LABEL}**\n\n**Wei-Lun Hsu - National Tsing Hua University**\n\n"
        "IEEE SSCS Code-a-Chip - ISSCC 2027\n\n"
        "[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]"
        "(https://colab.research.google.com/github/WLHsu0827/"
        "sscs-ose-code-a-chip.github.io/blob/wlhsu0827-comparator-atlas-isscc27/"
        "ISSCC27/submitted_notebooks/comparator_atlas/Comparator_Atlas.ipynb)\n\n"
        + OPENING + "\n\n## Three-minute route\n\n"
        "Choose one of the three 1 ns presets in Section 4; inspect exact failing keys; "
        "separate the schematic decision lesson from the b1/a1 archived-layout result in Section 8. "
        "[Self-contained report](results/study/report.html), [quick tour](REVIEWER_GUIDE.md), "
        "[reproducibility and dated execution scope](REPRODUCIBILITY.md).\n\n"
        "Download the HTML and open it locally: GitHub's file viewer does not run its controls. "
        "Default execution verifies supplied evidence and remeasures saved waveforms, not new simulations. "
        "The bootstrap retrieves the submitted GitHub source when needed and uses requirements-review.txt. "
        "Optional RUN_LIVE_SPICE and RUN_FULL_CAMPAIGN require the explicit tools/models "
        "described in Reproducibility; both are false by default.\n\n"
        f"**{WARNING}**. StrongARM and calibration are established; this finite comparison "
        "is not a new topology or physical PPA/signoff claim.\n\n" + DISCLOSURE)
    notebook.cells[8].source = """import ipywidgets as widgets
from presentation.judge_decision import notebook_view


def inspect_tradeoff(minimum_mv, deadline_ns):
    display(HTML(notebook_view(minimum_mv, deadline_ns)))


minimum_control = widgets.SelectionSlider(
    options=[0.25, 0.5, 1.0, 3.0, 10.0, 30.0], value=1.0,
    description="Min |sampled input| (mV)", continuous_update=False,
    style={"description_width": "initial"},
)
deadline_control = widgets.SelectionSlider(
    options=[0.25, 0.35, 0.5, 0.75, 1.0, 2.0], value=1.0,
    description="Deadline (ns)", continuous_update=False,
    style={"description_width": "initial"},
)
interactive_table = widgets.interactive_output(
    inspect_tradeoff,
    {"minimum_mv": minimum_control, "deadline_ns": deadline_control},
)


def set_preset(value):
    with (
        minimum_control.hold_trait_notifications(),
        deadline_control.hold_trait_notifications(),
    ):
        minimum_control.value = value
        deadline_control.value = 1.0


presets = []
for value, label in ((1.0, "1 ns / >=1 mV: NONE"),
                     (3.0, "1 ns / >=3 mV: selected"),
                     (30.0, "1 ns / >=30 mV: control")):
    button = widgets.Button(
        description=label, layout=widgets.Layout(width="auto")
    )
    button.on_click(lambda clicked, band=value: set_preset(band))
    presets.append(button)
display(
    widgets.HBox(presets), minimum_control, deadline_control, interactive_table
)
print("Static saved-output fallback: all three teaching presets.")
for band in (1.0, 3.0, 30.0):
    display(HTML(notebook_view(band, 1.0)))
"""
    notebook.cells[8].outputs = []
    notebook.cells[8].execution_count = None
    return notebook


def integrate_report(document, payload, cube):
    document = re.sub(r"<header>.*?</header>", f"""<header>
<small>{LABEL}</small><h1>Correct before the deadline - or NONE?</h1>
<p><strong>Comparator Atlas | Wei-Lun Hsu - National Tsing Hua University</strong></p>
<p>{LEDE}</p><nav aria-label="Three-minute tour"><a href="#decision-panel">1. Specify and qualify</a> |
<a href="#decision-records">2. Inspect the exact failure</a> |
<a href="../../REVIEWER_GUIDE.md">3. Read the scope and reproduction route</a></nav>
<p><a href="../../Comparator_Atlas.ipynb">Notebook</a> | <a href="Comparator_Atlas_Poster.pdf">Poster</a></p>
<p class="muted">All controls use stored measurements;
no simulation, interpolation or independent physical qualification occurs here.</p></header>""",
                      document, count=1, flags=re.S)
    pattern = r'<section><h2>Stored decision map: circuit, calibration and deadline</h2>.*?</section>'
    match = re.search(pattern, document, re.S)
    assert match is not None
    old_section = match.group()
    map_part = old_section[old_section.index('<label>Circuit'):old_section.index('</section>')]
    map_part = map_part.replace('<label>Circuit ', '<label>Inspect compared design ')
    map_part = map_part.replace('<input type="checkbox" id="explorer-reserved">',
                                '<input type="checkbox" id="explorer-reserved" disabled>')
    map_part = map_part.replace('Exclude selection conditions', 'All 49 conditions are required here')
    # The existing map gets the complete three-design local_boundary grid, not fabricated missing policies.
    controls = ('<div class="controls"><label>Minimum |sampled input| '
                '<select id="explorer-guardband"></select></label>'
                '<label>Deadline <select id="explorer-deadline"></select></label></div>')
    map_part = re.sub(r'<label>Deadline .*?</label>', '', map_part, count=1)
    map_part = re.sub(r'<label>Scored inputs .*?</label>', '', map_part, count=1)
    map_part = '<div class="controls">' + map_part
    fallback = spec.example_table(json.loads((STUDY / "specification_map/summary.json").read_bytes())).to_html(
        index=False, float_format=lambda v: f"{v:.3f}", border=0)
    panel = f"""<section id="decision-panel"><h2>1. Specify, qualify, then compare energy</h2>
<p><strong>Calibrated SCHEMATIC only:</strong> local_boundary; all 49 controlled-width-stress conditions.
Both signs at the included finite sampled inputs through 30 mV. These six samples and six deadlines
form 36 specification cells: 28 NONE, 5 selected and 3 lower-energy control. No continuous-input guarantee.</p>
<div class="decision-presets" role="group" aria-label="Three teaching presets">
<button type="button" data-decision-preset="1">1 ns / &gt;=1 mV: NONE</button>
<button type="button" data-decision-preset="3">1 ns / &gt;=3 mV: selected</button>
<button type="button" data-decision-preset="30">1 ns / &gt;=30 mV: control</button></div>
{controls}<p id="decision-result" role="status" aria-live="polite"></p>
<p id="decision-error" role="alert"></p><div class="table-scroll" id="decision-candidates"></div>
<p class="muted">Every point must be correct before the deadline. Only qualifying designs are ranked
by measured mean core energy over the full 20-30 ns cycle, excluding drivers and calibration/controller
infrastructure. NONE has null energy/limits. Exact energy ties are all disclosed; the original design order breaks ties.</p>
<p class="muted">Different input-band energies are not a same-specification energy improvement.</p>
<h3>2. Why a circuit is disqualified: keyed observations, not a guessed cause</h3>
<p>The same 20 selected +/-1 mV wrong samples remain wrong at 2 ns. A wrong-sign decision is not
an unresolved (null-latency) decision. Condition, width stress and trim code identify records,
not a physical failure mechanism. <a href="specification_map/summary.json">Exact matched identities and transitions</a>.</p>
<p id="decision-page" role="status"></p><button id="decision-previous" type="button">Previous keys</button>
<button id="decision-next" type="button">Next keys</button><div id="decision-records"></div>
<details><summary>Stored map: inspect the selected design's individual cells</summary>{map_part}</details>
<details><summary>Static fallback: the exact sampled choices, readable without JavaScript</summary>
<div class="table-scroll">{fallback}</div><p>All records are retained in
<a href="decision_data.json">the integrated decision JSON</a> and the unchanged source tables.
The waveform lab below remains eight declared examples, not raw evidence for every key.</p></details></section>"""
    document = document[:match.start()] + document[match.end():]
    document = document.replace("<main>", "<main>" + panel, 1)
    def replace_payload(identifier, value):
        nonlocal document
        encoded = json.dumps(value, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c")
        document = re.sub(rf'(<script id="{identifier}" type="application/json">).*?(</script>)',
                          lambda m: m.group(1) + encoded + m.group(2), document, count=1, flags=re.S)
    replace_payload("atlas-cube", cube)
    encoded = json.dumps(payload, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c")
    extra = f'<script id="atlas-decision-data" type="application/json">{encoded}</script><script type="module">' \
        + (ROOT / "presentation/decision_explorer.mjs").read_text(encoding="utf-8") + "</script>"
    document = document.replace("</html>", extra + "</html>", 1)
    styles = """
button{font:inherit;padding:8px 11px;border:1px solid #c8d2dd;border-radius:6px;background:#f4f7fa;color:#203446;cursor:pointer}
button:disabled{opacity:.5;cursor:default}button:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid #087f76;outline-offset:3px}
.decision-presets{display:flex;flex-wrap:wrap;gap:9px;margin:15px 0}
#decision-result{font-size:19px;font-weight:650;padding:15px;background:#edf4f5;border-left:4px solid #365d7d}
#decision-error{color:#a32b3f}.measurement-record{padding:13px 0;border-bottom:1px solid #dce1e5;overflow-wrap:anywhere}
.measurement-record p{margin:5px 0}.measurement-record button,.measurement-record a{margin:8px 10px 4px 0}
.measurement-record code{white-space:normal}#decision-records ol{padding-left:22px}details{margin:15px 0}
@media(max-width:600px){header,main{padding-left:16px;padding-right:16px}.controls label{display:block}select{max-width:100%}h2{font-size:23px}}
"""
    document = document.replace("</style>", styles + "</style>", 1)
    document = document.replace("<title>Comparator Atlas | SKY130 StrongARM characterization</title>",
                                "<title>Comparator Atlas | Correct before deadline?</title>")
    return document


def write_reader_docs():
    """Keep the shipped technical history below a stable question-first tour."""
    marker = "\n## Technical evidence and version history\n\n"
    current = (ROOT / "README.md").read_text(encoding="utf-8")
    history = current.split(marker, 1)[1] if marker in current else current
    tour = f"""# Comparator Atlas: correct before the deadline - or NONE?

**{LABEL}**

**Wei-Lun Hsu - National Tsing Hua University**

{OPENING}

## A three-minute route

1. Open [the self-contained report](results/study/report.html) as a local HTML file. Use the **1 ns / >=1 mV** preset: every candidate fails strict qualification; NONE is not a low-energy result.
2. Change to **>=3 mV**, then **>=30 mV**. Compare all three designs' correct/wrong/unresolved counts before their mean energy. Inspect exact disqualifying keys, trim codes, recorded latencies and CSV record locations in the same panel/map.
3. Keep wrong and unresolved distinct: the selected design's same 20 +/-1 mV wrong samples remain at 2 ns. Only an actual identity-matched retained waveform gets a wave button. Other keys show the measurement record honestly. Then read the separate b1/a1 layout example and its physical-fidelity warning.

| 1 ns sampled band | Strict choice | Correct / included points | Mean core energy |
|---|---|---|---|
| >=1 mV | NONE | No candidate qualifies at all points | null, not zero |
| >=3 mV | lvt_balanced_4b | 294/294 | 249.655 fJ |
| >=30 mV | lvt_base_3b | 98/98 | 150.531 fJ |

This is a post-hoc comparison of exactly three schematic designs, local_boundary calibration, all 49 controlled-width-stress conditions and both signs at six finite sampled magnitudes through 30 mV. The six deadlines produce 36 cells: 28 NONE, 5 selected, 3 lower-energy control. Exact mean-energy ties retain every tied design; no interpolation or global optimization is implied. The original nine-candidate training choice is unchanged.

**Energy and evidence contract.** Full-cycle 20-30 ns core energy excludes input/clock drivers and calibration/controller infrastructure. A null unresolved latency is not zero; failed designs and NONE retain null sampled limits. The report shows all keyed witnesses with their source table and record number; a retained raw wave is not promised for every measurement.

## Separate secondary demonstration: archived b1 vs a1

The adopted b1's 110 x 17.03 um all-material GDS bbox is 1873.3 um2 versus matched a1's 2074.254 um2 (-9.688013%), not die or signoff area. Historical native proofs are reused, not rerun. In the separate known-nonblind nominal code-zero 45-PVT comparison, b1 RC gives 158 correct / 0 wrong / 22 unresolved at 1 ns versus a1's 156/0/24; both C modes 170/0/10; all four 180/0/0 at 2 ns. Only SS / 1.62 V / 125 C / +/-10 mV improve; FS 1 ns failures/nulls remain. Mean b1 RC 412.879469 fJ and worst sampled 1.760276 ns are archived finite observations, not robust physical PPA. 1440 actual transients differ from 720 numerical pairs, 720 finest traces and 1440 two-deadline rows.

**{WARNING}.** No silicon, independently qualified physical PEX, yield, physical uncertainty or timing-signoff claim.

## Notebook, artifacts and execution

The [Notebook](Comparator_Atlas.ipynb) has the same integrated strict Python selection controls and saved static presets. Run all in the review environment; its bootstrap retrieves the submitted GitHub entry when needed and checks requirements-review.txt. Default execution analyzes saved data. Optional live/full modes require the explicitly documented tools and models and are false by default.

[Poster PDF](results/study/Comparator_Atlas_Poster.pdf) | [Poster preview](results/study/poster_preview.png) | [Abstract](results/study/abstract.txt) | [Methodology and dated execution scope](REPRODUCIBILITY.md).

Different input-band energies in the teaching table are not a same-specification energy improvement. Saved results, source links and maintainer executions are distinct forms of evidence; see the dated reproduction scope rather than assuming an older run certifies changed source.

{DISCLOSURE}

"""
    (ROOT / "README.md").write_text(tour + marker + history, encoding="utf-8")
    (ROOT / "REVIEWER_GUIDE.md").write_text(
        tour + "\n## Audit route\n\n"
        "The integrated decision JSON is [here](results/study/decision_data.json); the unchanged "
        "[strict source](presentation/specification_map.py) and [original 36-cell summary]"
        "(results/study/specification_map/summary.json) define the selection. "
        "All disqualifying records link to [original/selected measurements](results/study/verified_measurements.csv) "
        "or [lower-energy-control measurements](results/study/professional/measurements.csv). "
        "Keys include design, condition, signed input, deadline and run ID. "
        "The record number is 1-based excluding the CSV header. "
        "The stored map is now the complete three-design local_boundary grid; other calibration policies "
        "remain in the original saved tables, not synthesized as missing control measurements.\n",
        encoding="utf-8")


def reseal():
    files = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(ROOT.rglob("*"))
             if p.is_file() and p.name != "entry_checksums.json"
             and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts}
    write_json(ROOT / "entry_checksums.json", files)


def build():
    from comparator_atlas.study_report import render_study
    from presentation.contest_materials import build as build_materials
    from scripts.build_entry_notebook import main as build_notebook

    render_study(refresh_figures=set())
    build_materials()
    build_notebook()
    write_reader_docs()
    reseal()
    print("Generated integrated report, Notebook, reader guide, poster and public seal from shipped source.")


if __name__ == "__main__":
    build()
