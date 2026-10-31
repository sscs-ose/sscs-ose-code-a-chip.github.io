#!/usr/bin/env python3
"""Audit Flow-2 evidence without changing measured reports or checkpoints."""

from __future__ import annotations

import argparse
import ast
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = Path("results/receipts/flow2_baseline_audit.json")
REPORT = Path("results/reports/flow2_baseline_audit.md")
LEDGER = Path("docs/flow2_execution_ledger.md")
CORE = "automx_ternary_cim_4x4_core"

EVIDENCE = (
    ("Stage 4 manifest", "generated/sky130/spice/stage4_manifest.json", None),
    ("Stage 5 passive core", "results/receipts/physical/stage5_summary.json", "run_stage5_physical.py"),
    ("Stage 5 layout", "results/receipts/physical/layout.json", "run_stage5_physical.py"),
    ("Four-row calibration", "results/sky130/post49_calibration_tt/measured.json", "run_post49_calibration_tt.py"),
    ("2+2 targeted screen", "results/sky130/post49_row_partition/adjacent/measured.json", "run_post49_row_partition.py"),
    ("2+2 calibration", "results/sky130/post49_partition_full_tt/calibration/measured.json", "run_post49_partition_full_tt.py"),
    ("2+2 observed holdout", "results/sky130/post49_partition_full_tt/holdout/measured.json", "run_post49_partition_full_tt.py"),
    ("820 fF loaded TT", "results/sky130/wrapper_load_full_tt/c820ff/measured.json", "run_wrapper_load_full_tt.py"),
    ("Idle augmented TT", "results/sky130/wrapper_idle_augmented_tt/c820ff/measured.json", "run_wrapper_idle_augmented_tt.py"),
    ("Sample/hold TT", "results/sky130/wrapper_sample_hold_tt/measured.json", "run_wrapper_sample_hold_tt.py"),
    ("Sample/hold edge TT", "results/sky130/wrapper_sample_hold_edge_tt/measured.json", "run_wrapper_sample_hold_edge_tt.py"),
    ("Input loading", "results/sky130/wrapper_input_loading_screen/measured.json", "run_wrapper_input_loading_screen.py"),
    ("Decoder architecture", "results/sky130/post49_decoder_architecture/offline.json", "analyze_post49_decoder_architectures.py"),
    ("PVT smoke", "results/sky130/post49_pvt_smoke/measured.json", "run_post49_pvt_smoke.py"),
    ("Stage 6 historical model", "results/sky130/automx_ternary_cim_4x4_core_characterization.json", None),
    ("Stage 7 logical 2+2", "results/receipts/stage7_2p2_regression.json", "run_stage7_2p2_regression.py"),
    ("Full wrapper preflight", "results/receipts/stage8_preflight.json", "run_stage8_preflight.py"),
)
PRODUCER_OUTPUTS = {name: path for _, path, name in EVIDENCE if name}
PRODUCER_OUTPUTS.update({
    "audit_flow2_baseline.py": str(RECEIPT).replace("\\", "/"),
    "compare_flow2_staging.py": "results/receipts/flow2_staging_comparison.json",
    "audit_flow2_readout.py": "results/receipts/flow2_readout_gate.json",
    "run_core_candidate_full_tt.py": "results/sky130/core_candidate_full_tt/measured.json",
    "run_post49_holdout_tt.py": "results/sky130/post49_holdout_tt/measured.json",
    "run_post49_decoder_diagnostic.py": "results/sky130/post49_decoder_diagnostic.json",
    "analyze_wrapper_sample_hold_tt.py": "results/sky130/wrapper_sample_hold_tt/decomposition.json",
    "analyze_wrapper_load_common_mode.py": "results/sky130/wrapper_load_full_tt/c820ff/common_mode_diagnostic.json",
    "audit_core_bound_clean.py": "results/receipts/stage8_core_bound_clean.json",
    "run_notebook_core_bound.py": "results/receipts/notebook_core_bound.json",
    "run_stage8_core_bound_demo.py": "results/receipts/stage8_core_bound_demo.json",
    "run_stage7_regression.py": "results/receipts/stage7_regression.json",
    "run_stage7_stress.py": "results/receipts/stage7_stress.json",
    "run_stage8_digital_surrogate_gds.py": "results/receipts/stage8_digital_surrogate_gds.json",
    "run_stage8_prototype_gds.py": "results/receipts/stage8_prototype_gds.json",
    "run_flow2_remaining_measurements.py":
        "results/sky130/flow2_remaining_measurements/summary.json",
})


def digest(path: Path) -> str | None:
    return sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def read_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def hash_check(root: Path, label: str, relative: str,
               expected: str | None) -> dict:
    actual = digest(root / relative)
    status = ("MISSING_INPUT" if actual is None else
              "MISSING_EXPECTED_HASH" if not expected else
              "MATCH" if actual == expected else "CURRENT_SOURCE_DIFFERS")
    return {"label": label, "path": relative, "status": status,
            "expected_sha256": expected, "actual_sha256": actual}


def _git(root: Path) -> dict:
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                              capture_output=True, text=True, timeout=10)
        state = subprocess.run(["git", "status", "--porcelain"], cwd=root,
                               capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return {"commit": None, "dirty": None}
    return {"commit": head.stdout.strip() if head.returncode == 0 else None,
            "dirty": bool(state.stdout.strip()) if state.returncode == 0 else None}


def _scripts(root: Path) -> list[dict]:
    records = []
    for path in sorted((root / "scripts").iterdir()):
        if not path.is_file() or path.suffix not in (".py", ".sh"):
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        description = ""
        if path.suffix == ".py":
            try:
                description = (ast.get_docstring(ast.parse(source)) or "").splitlines()[0]
            except SyntaxError:
                description = "Python source cannot be parsed"
        else:
            description = next((line.lstrip("# ").strip() for line in source.splitlines()
                                if line.startswith("#") and not line.startswith("#!")), "")
        output = PRODUCER_OUTPUTS.get(path.name)
        observed = read_json(root / output) if output else None
        flow2_results = {
            "run_flow2_sample_hold_sweep.py": "flow2_sample_hold_sweep",
            "run_flow2_sample_hold_settled_tt.py": "flow2_sample_hold_settled_tt",
            "run_flow2_sample_hold_aperture_tt.py": "flow2_sample_hold_aperture_tt",
            "run_flow2_sample_hold_refined_aperture_tt.py": "flow2_sample_hold_refined_aperture_tt",
        }
        if path.name in flow2_results:
            directory = flow2_results[path.name]
            candidates = sorted((root / "results/sky130" / directory).glob(
                "pex_*/measured.json"))
            if not candidates:
                candidates = sorted((root / "results/sky130" / directory).glob(
                    "pex_*/prepared.json"))
            if candidates:
                output = candidates[-1].relative_to(root).as_posix()
                observed = read_json(candidates[-1])
            else:
                output = f"results/sky130/{directory}/pex_*/measured.json"
        records.append({
            "script": f"scripts/{path.name}", "description": description,
            "output": output,
            "result": (observed.get("status", "UNKNOWN") if observed else
                       "NOT_RUN" if path.name in flow2_results else
                       "MISSING_LOCAL" if output else "SUPPORT_OR_MANUAL"),
        })
    return records


def _openlane_runs(root: Path) -> list[dict]:
    design = root / "openlane/automx_cim_core_bound_demo"
    if not design.is_dir():
        return []
    folders = [p for p in design.iterdir()
               if p.is_dir() and p.name.startswith("core_bound_")]
    if (design / "runs").is_dir():
        folders += [p for p in (design / "runs").iterdir()
                    if p.is_dir() and p.name.startswith("core_bound_")]
    records = []
    for folder in sorted(folders):
        metrics = folder / "reports/metrics.csv"
        if not metrics.is_file():
            continue
        try:
            with metrics.open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
        except (OSError, UnicodeError):
            continue
        if len(rows) != 1:
            continue
        row = rows[0]
        gds = folder / "results/final/gds/automx_cim_core_bound_demo.gds"
        records.append({
            "tag": folder.name, "run_dir": folder.relative_to(root).as_posix(),
            "flow_status": row.get("flow_status"), "gds_sha256": digest(gds),
            **{key: row.get(key) for key in
               ("tritonRoute_violations", "Magic_violations",
                "klayout_violations", "lvs_total_errors")},
        })
    return records


def inspect(root: str | Path) -> dict:
    root = Path(root).resolve()
    reports = []
    by_label = {}
    for label, relative, producer in EVIDENCE:
        data = read_json(root / relative)
        by_label[label] = data
        reports.append({
            "label": label, "path": relative, "producer": producer,
            "status": data.get("status", "UNKNOWN") if data else "MISSING_LOCAL",
            "conclusion": data.get("conclusion") if data else None,
            "sha256": digest(root / relative),
            "planned_sims": data.get("planned_sims") if data else None,
            "completed_sims": data.get("completed_sims") if data else None,
        })

    checks = []
    def check(label: str, relative: str, expected: str | None) -> None:
        checks.append(hash_check(root, label, relative, expected))

    stage5 = by_label["Stage 5 passive core"] or {}
    layout = by_label["Stage 5 layout"] or {}
    check("Stage-5 contract", "physical/sky130/macro/macro_contract.json",
          stage5.get("contract_sha256"))
    check("Stage-5 config", "configs/sky130_mha_tiny.json",
          stage5.get("config_sha256"))
    check("Stage-5 layout generator",
          "physical/sky130/layout/generate_automx_ternary_cim_4x4_core.tcl",
          layout.get("generator_sha256"))
    for view, relative in {
        "blackbox_rtl": f"rtl/{CORE}_blackbox.sv",
        "spice": f"generated/sky130/spice/macro/{CORE}.spice",
        "extracted_spice": f"physical/sky130/macro/{CORE}.pex.spice",
        "gds": f"physical/sky130/macro/{CORE}.gds",
        "lef": f"physical/sky130/macro/{CORE}.lef",
    }.items():
        check(f"Stage-5 {view}", relative,
              (stage5.get("views", {}).get(view) or {}).get("sha256"))
    for filename, expected in stage5.get("receipts", {}).items():
        check(f"Stage-5 receipt {filename}",
              f"results/receipts/physical/{filename}", expected)

    calibration = by_label["2+2 calibration"] or {}
    holdout = by_label["2+2 observed holdout"] or {}
    loaded = by_label["820 fF loaded TT"] or {}
    for name, report in (("2+2 calibration", calibration),
                         ("2+2 holdout", holdout)):
        check(f"{name} script", "scripts/run_post49_partition_full_tt.py",
              report.get("script_sha256"))
        check(f"{name} PEX", f"physical/sky130/macro/{CORE}.pex.spice",
              report.get("pex_sha256"))
        check(f"{name} targeted source",
              "results/sky130/post49_row_partition/adjacent/measured.json",
              report.get("targeted_sha256"))
        for key, relative in {
            "cell49": "results/sky130/core_candidate_full_tt/measured.json",
            "old_holdout": "results/sky130/post49_holdout_tt/measured.json",
            "calibration": "results/sky130/post49_calibration_tt/measured.json",
        }.items():
            check(f"{name} input {key}", relative,
                  (report.get("input_report_sha256") or {}).get(key))
    check("2+2 holdout calibration",
          "results/sky130/post49_partition_full_tt/calibration/measured.json",
          holdout.get("calibration_sha256"))
    check("820 fF source calibration",
          "results/sky130/post49_partition_full_tt/calibration/measured.json",
          loaded.get("source_calibration_sha256"))
    check("820 fF source holdout",
          "results/sky130/post49_partition_full_tt/holdout/measured.json",
          loaded.get("source_holdout_sha256"))

    integrity = []
    if stage5.get("status") != "PASS":
        integrity.append("Stage-5 summary is not PASS")
    for label, value, required in (
        ("2+2 calibration", calibration, "MEASURED_2P2_LEVEL_SCREEN"),
        ("2+2 holdout", holdout, "MEASURED_2P2_HOLDOUT_TT"),
    ):
        if value.get("status") != required:
            integrity.append(f"{label}: expected {required}")
    for label, value in (("2+2 calibration", calibration), ("2+2 holdout", holdout)):
        planned = value.get("planned_sims")
        if not isinstance(planned, int) or planned <= 0 or (
                value.get("completed_sims") != planned or value.get("failures")):
            integrity.append(f"{label}: incomplete jobs or failures")
    if calibration and holdout:
        for field in ("pex_sha256", "model_sha256", "ngspice_version",
                      "partition", "load_ff", "pwm_unit_ps"):
            if calibration.get(field) != holdout.get(field):
                integrity.append(f"2+2 calibration/holdout disagree on {field}")
    for label in ("Stage 5 passive core", "2+2 calibration", "2+2 observed holdout"):
        if by_label[label] is None:
            integrity.append(f"required measured report missing: {label}")
    differences = [item for item in checks if item["status"] != "MATCH"]
    required_local = {"Stage 4 manifest", "Stage 5 passive core",
                      "2+2 calibration", "2+2 observed holdout",
                      "Idle augmented TT", "Sample/hold TT", "Sample/hold edge TT"}
    missing_local = [x for x in reports if x["status"] == "MISSING_LOCAL"
                     and x["label"] in required_local]
    handoff_claim = None
    handoff = root / "flow_2.md"
    if handoff.is_file():
        match = re.search(r"(\d+) common-mode samples outside the training range",
                          handoff.read_text(encoding="utf-8", errors="replace"))
        if match:
            handoff_claim = int(match.group(1))
    local_common_mode = (holdout.get("analysis") or {}).get(
        "common_mode_outside_training_samples")
    handoff_issues = []
    if (handoff_claim is not None and local_common_mode is not None and
            handoff_claim != local_common_mode):
        handoff_issues.append(
            f"flow_2.md records {handoff_claim} common-mode outliers, "
            f"copied 2+2 holdout report records {local_common_mode}")
    environment = read_json(root / "results/receipts/environment.json") or {}
    return {
        "format": "automx-cim-flow2-baseline-audit-v1",
        "status": ("BLOCKED_LOCAL_EVIDENCE" if
                   differences or integrity or missing_local or handoff_issues
                   else "AUDITED_DIAGNOSTIC_EVIDENCE"),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "read-only copied-evidence audit; no new physical measurement or sign-off",
        "repository": _git(root), "tool_versions": environment.get("tools", {}),
        "pdk": environment.get("pdk", {}),
        "operating_point": {"architecture": "2+2 adjacent row pairs",
                            "training_load_ff": calibration.get("load_ff"),
                            "training_pwm_unit_ps": calibration.get("pwm_unit_ps"),
                            "loaded_diagnostic_ff": loaded.get("load_ff")},
        "evidence": reports, "hash_checks": checks,
        "integrity_issues": integrity,
        "handoff_consistency": {
            "flow2_common_mode_outliers": handoff_claim,
            "copied_holdout_common_mode_outliers": local_common_mode,
            "issues": handoff_issues,
        },
        "current_source_differences": differences,
        "missing_local_required": missing_local,
        "openlane_runs": _openlane_runs(root), "scripts": _scripts(root),
        "staging_comparison": read_json(
            root / "results/receipts/flow2_staging_comparison.json"),
        "readout_gate": read_json(root / "results/receipts/flow2_readout_gate.json"),
        "dependency_graph": [
            ["Stage 4 manifest", "Stage 5 passive core"],
            ["Stage 5 passive core", "2+2 calibration"],
            ["2+2 calibration", "2+2 observed holdout"],
            ["2+2 calibration", "820 fF loaded TT"],
            ["820 fF loaded TT", "Idle augmented TT"],
            ["Idle augmented TT", "Sample/hold TT"],
            ["Sample/hold TT", "Sample/hold edge TT"],
            ["Sample/hold edge TT", "held-node calibration and untouched MHA holdout"],
            ["held-node calibration and untouched MHA holdout", "read-margin / PVT"],
            ["read-margin / PVT", "Stage-6 v2 then wrapper sign-off"],
        ],
    }


def _table(rows: list[list[object]], headings: list[str]) -> str:
    def safe(value: object) -> str:
        return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")
    return "\n".join([
        "| " + " | ".join(headings) + " |",
        "| " + " | ".join("---" for _ in headings) + " |",
        *["| " + " | ".join(safe(value) for value in row) + " |"
          for row in rows],
    ])


def markdown(report: dict) -> str:
    issues = report["current_source_differences"]
    point = report["operating_point"]
    rows = []
    for item in report["evidence"]:
        jobs = (f"{item['completed_sims']}/{item['planned_sims']}"
                if item["planned_sims"] is not None else "")
        rows.append([item["label"], item["status"], item["conclusion"] or "",
                     jobs, item["path"]])
    lines = [
        "# Flow 2 execution ledger",
        "",
        "Generated with: python3 scripts/audit_flow2_baseline.py --root .",
        "The audit reads existing measurements and writes only its own reports.",
        "",
        f"Audit status: {report['status']}. No new SPICE/OpenLane run was performed.",
        "",
        "## Repository, PDK and operating point",
        "",
        f"- Commit: {report['repository']['commit'] or 'unavailable'}; "
        f"working tree dirty: {report['repository']['dirty']}.",
        f"- PDK recorded by the environment receipt: "
        f"{report['pdk'].get('resolved_path', 'not recorded')}. "
        "This does not prove local PDK availability.",
        f"- Selected direction: {point['architecture']}; "
        f"training load {point['training_load_ff']} fF, "
        f"PWM {point['training_pwm_unit_ps']} ps/unit.",
        "- Tool identities are copied from the server environment receipt below.",
        "",
        _table([[name, item.get("path"), item.get("version", "not recorded")]
                for name, item in sorted(report["tool_versions"].items())
                if isinstance(item, dict)] or [["No environment receipt", "", ""]],
               ["Tool", "Recorded path", "Recorded version"]),
        "",
        "## Existing reports",
        "",
        _table(rows, ["Evidence", "Status", "Conclusion", "Jobs", "Path"]),
        "",
        "## Current-source and copied-evidence differences",
        "",
        "A hash difference means the current checkout differs from the measured "
        "receipt. Historical measured results remain intact; do not overwrite them.",
        "",
        _table([[item["label"], item["status"], item["path"],
                 (item["expected_sha256"] or "")[:12],
                 (item["actual_sha256"] or "")[:12]]
                for item in issues] or [["No differences found", "", "", "", ""]],
               ["Check", "Result", "Path", "Receipt SHA prefix", "Current SHA prefix"]),
        "",
    ]
    if report["integrity_issues"]:
        lines += ["Integrity issues: " + "; ".join(report["integrity_issues"]), ""]
    if report["handoff_consistency"]["issues"]:
        lines += ["## Handoff versus copied report", "",
                  *["- " + issue for issue in report["handoff_consistency"]["issues"]]]
        staged_outliers = (report.get("staging_comparison") or {}).get(
            "staged_holdout_common_mode_outliers")
        if staged_outliers == report["handoff_consistency"]["flow2_common_mode_outliers"]:
            lines += [f"- The separate server_results copy contains the newer "
                      f"{staged_outliers}-outlier report and matches the handoff. "
                      "The older checkout report remains intact.", ""]
        else:
            lines += ["Copy the exact latest server report and rerun this audit. "
                      "The existing copied report is not rewritten.", ""]
    staged = report.get("staging_comparison") or {}
    readout = report.get("readout_gate") or {}
    if staged:
        lines += ["## Server artifact staging and readout", "",
                  f"- Staging path: {staged.get('staging_root')}.",
                  f"- Comparison status: {staged.get('status')}.",
                  f"- Historical readout lineage issues: "
                  f"{len(staged.get('readout_lineage_issues', []))}.",
                  f"- Readout gate: {readout.get('status', 'NOT_RUN')}; "
                  "details in docs/flow2_readout_gate.md.",
                  "- Current checkout receipts and staged server receipts remain separate.",
                  ""]
    lines += ["## Server stdout review", "",
              "The 2026-10-12 18-job S/H sweep summary is recorded in "
              "docs/flow2_sweep_log_review.md. Its stdout has not been "
              "re-verified against a copied measured.json/checkpoint folder.", ""]
    lines += [
        "## Copied OpenLane runs",
        "",
        _table([[item["tag"], item["flow_status"],
                 item["gds_sha256"] or "MISSING",
                 item["Magic_violations"], item["klayout_violations"],
                 item["lvs_total_errors"]]
                for item in report["openlane_runs"]] or
               [["No copied run with metrics", "", "", "", "", ""]],
               ["Tag", "Flow", "GDS SHA-256", "Magic", "KLayout", "LVS"]),
        "",
        "## Script inventory and observed outputs",
        "",
        "SUPPORT_OR_MANUAL means no direct JSON output was mapped. MISSING_LOCAL "
        "means the mapped result was absent from this checkout.",
        "",
        _table([[item["script"], item["description"],
                 item["output"] or "—", item["result"]]
                for item in report["scripts"]],
               ["Script", "Purpose", "Mapped result", "Observed status"]),
        "",
        "## Dependency order and commands",
        "",
        _table(report["dependency_graph"], ["From", "Required before"]),
        "",
        "1. Keep the copied server_results tree intact. Run "
        "python3 scripts/compare_flow2_staging.py --root . --staging server_results "
        "and python3 scripts/audit_flow2_readout.py --root . "
        "--evidence-root server_results. Do not combine the current-PEX 2+2 "
        "reports with older-PEX sample/hold measurements.",
        "2. The server completed the 18-job current-PEX sample/hold sweep and "
        "the six-job settled-edge check. The 5 ps option reaches 0.754 mV "
        "late capture error in only two inspected cases, leaving 0.046 mV "
        "against the 0.8 mV target. See docs/flow2_settled_log_review.md; "
        "copy the measured files back for independent audit.",
        "3. The server completed the ten-job sparse turnoff-time diagnostic. "
        "Only 2.065/2.105 ns passed in two inspected cases; 2.065 ns reached "
        "0.516 mV late capture error. Run the twelve-job 10 ps refinement, "
        "then test broader patterns and actual held-node decoding. Reserve "
        "a genuinely untouched MHA cohort.",
        "4. Run offset/noise and a small PVT screen only after readout is credible. "
        "Then regenerate Stage-6 v2 and the MHA comparison.",
        "5. Add notebook cells only for scripts with verified outputs and explicit "
        "scope. Core-bound GDS remains external-analog; strict wrapper Stage 8 "
        "needs real analog views and checks.",
        "",
        "Server command:",
        "",
        "    cd /home/nam/Vihn/interface_verify/fpga_export_18x18_mnist_softreset/test_folder/AutoMX-CIM",
        "    python3 scripts/audit_flow2_baseline.py --root .",
        "    python3 scripts/run_flow2_sample_hold_refined_aperture_tt.py --root .",
        "    python3 scripts/run_flow2_sample_hold_refined_aperture_tt.py --root . --run --timeout-s 600",
        "",
        "This refined selected-case aperture screen writes to "
        "results/sky130/flow2_sample_hold_refined_aperture_tt/"
        "pex_4e5d1d9b1341/ for the currently staged Stage-5 PEX. "
        "Copy its measured.json and twelve job decks/logs/checkpoints back for "
        "audit. Historical results remain in their original folders.",
        "",
        "Outputs: results/receipts/flow2_baseline_audit.json, "
        "results/reports/flow2_baseline_audit.md, and this ledger.",
        "",
    ]
    return "\n".join(lines)


def run(root: str | Path) -> dict:
    root = Path(root).resolve()
    report = inspect(root)
    content = markdown(report)
    for relative, payload in (
        (RECEIPT, json.dumps(report, indent=2, ensure_ascii=False) + "\n"),
        (REPORT, content),
        (LEDGER, content),
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--require-current", action="store_true",
                        help="exit 1 when copied evidence is incomplete or differs")
    args = parser.parse_args()
    result = run(args.root)
    print(json.dumps({
        "status": result["status"],
        "evidence_count": len(result["evidence"]),
        "script_count": len(result["scripts"]),
        "source_differences": len(result["current_source_differences"]),
        "integrity_issues": result["integrity_issues"],
        "handoff_issues": result["handoff_consistency"]["issues"],
        "outputs": [str(RECEIPT), str(REPORT), str(LEDGER)],
    }, indent=2))
    if args.require_current and result["status"] != "AUDITED_DIAGNOSTIC_EVIDENCE":
        raise SystemExit(1)
