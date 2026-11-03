#!/usr/bin/env python3
"""Resume feasible Flow-2 measurements, writing one append-only run history.

This orchestrates the four sample/hold screens, the gated readout campaign,
and Stage-6 v2 only when every campaign diagnostic gate passes. Per-job SPICE
logs and checkpoints remain separate as auditable measurement evidence.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automx_cim.spice import parse_measurements  # noqa: E402
from scripts.run_wrapper_input_loading_screen import _sources  # noqa: E402
from scripts import run_flow2_sample_hold_sweep as sweep  # noqa: E402
from scripts import run_flow2_sample_hold_settled_tt as settled  # noqa: E402
from scripts import run_flow2_sample_hold_aperture_tt as sparse  # noqa: E402
from scripts import run_flow2_sample_hold_refined_aperture_tt as refined  # noqa: E402
from scripts import run_flow2_remaining_measurements as campaign  # noqa: E402
from scripts import run_flow2_stage6_v2 as stage6  # noqa: E402

HISTORY = Path("results/sky130/flow2_one_shot/history.log")
SCREENS = (
    ("sweep", sweep, sweep.OUTPUT, "MEASURED_TT_SAMPLING_SWEEP_DIAGNOSTIC", 18),
    ("settled", settled, settled.OUTPUT, "MEASURED_TT_SETTLED_HOLD_DIAGNOSTIC", 6),
    ("sparse_aperture", sparse, sparse.OUTPUT,
     "MEASURED_TT_SELECTED_CASE_APERTURE_DIAGNOSTIC", 10),
    ("refined_aperture", refined, refined.OUTPUT,
     "MEASURED_TT_REFINED_APERTURE_DIAGNOSTIC", 12),
)


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


class _Tee:
    def __init__(self, *targets):
        self.targets = targets

    def write(self, message: str) -> int:
        for target in self.targets:
            target.write(message)
            target.flush()
        return len(message)

    def flush(self) -> None:
        for target in self.targets:
            target.flush()


def _event(log, message: str) -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[{stamp}] {message}", file=log, flush=True)
    print(f"[{stamp}] {message}", flush=True)


def _archive_interrupted_screen_job(root: Path, folder: Path, pex_sha: str,
                                    name: str, error: FileExistsError) -> list[dict]:
    """Preserve an incomplete job before retrying it; never touch its deck."""
    label = {"sweep": "sweep", "settled": "settled",
             "sparse_aperture": "aperture",
             "refined_aperture": "refined"}[name]
    prefix = f"inspect stale {label} log/checkpoint: "
    message = str(error)
    if not message.startswith(prefix):
        raise error
    deck = Path(message[len(prefix):])
    expected = (root / folder / f"pex_{pex_sha[:12]}").resolve()
    if (deck.is_symlink() or deck.suffix != ".spice" or
            deck.parent.resolve() != expected or not deck.is_file()):
        raise ValueError(f"stale job path is outside the current {name} run: {deck}")
    artifacts = (deck.with_suffix(".log"),
                 deck.with_name(f"{deck.stem}.receipt.json"))
    found = []
    for artifact in artifacts:
        if artifact.is_symlink() or (artifact.exists() and not artifact.is_file()):
            raise ValueError(f"unexpected stale artifact type: {artifact}")
        if artifact.is_file():
            found.append(artifact)
    if not found:
        raise ValueError(f"no stale log or checkpoint to archive: {deck}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    moves = [(item, item.with_name(f"{item.name}.stale.{stamp}")) for item in found]
    if any(target.exists() for _, target in moves):
        raise FileExistsError(f"stale archive already exists for: {deck}")
    saved = []
    for source, target in moves:
        digest = _sha(source)
        source.rename(target)
        saved.append({"path": str(target.relative_to(root)), "sha256": digest})
    return saved


def _source_hashes(root: Path, name: str, pex_prefix: str) -> dict[str, str]:
    suffix = f"pex_{pex_prefix}/measured.json"
    paths = {
        "settled": {"source_sweep_sha256": root / sweep.OUTPUT / suffix},
        "sparse_aperture": {"source_settled_sha256": root / settled.OUTPUT / suffix},
        "refined_aperture": {
            "source_sparse_sha256": root / sparse.OUTPUT / suffix,
            "source_settled_sha256": root / settled.OUTPUT / suffix},
    }.get(name, {})
    return {field: _sha(path) for field, path in paths.items()}


def _audit_screen(root: Path, name: str, module, path: Path, status: str,
                  count: int, *, pex_sha: str, model_sha: str,
                  version: str) -> dict:
    report = _read(path)
    completed_key = "completed_new_sims" if name == "refined_aperture" else "completed_sims"
    planned_key = "planned_new_sims" if name == "refined_aperture" else "planned_sims"
    if (report.get("status") != status or report.get(planned_key) != count or
            report.get(completed_key) != count or
            report.get("pex_sha256") != pex_sha or
            report.get("model_sha256") != model_sha or
            report.get("script_sha256") != _sha(Path(module.__file__)) or
            len(report.get("jobs", [])) != count):
        raise ValueError(f"{name} metadata, source script or job count changed")
    for field, digest in _source_hashes(root, name, pex_sha[:12]).items():
        if report.get(field) != digest:
            raise ValueError(f"{name} input report changed: {field}")
    if name == "sweep":
        _, provenance = sweep.load_stimuli(root, model_sha256=model_sha)
        if report.get("source_stimulus_catalog") != provenance:
            raise ValueError("sweep stimulus catalog or provenance changed")
        for field, source in (
                ("current_calibration_sha256", campaign.CALIBRATION),
                ("current_holdout_sha256",
                 Path("results/sky130/post49_partition_full_tt/holdout/measured.json"))):
            if report.get(field) != _sha(root / source):
                raise ValueError(f"sweep source changed: {field}")
    expected = sparse._expected() if name == "refined_aperture" else module._expected()
    for item in report["jobs"]:
        deck, output, receipt = (root / item[key] for key in
                                 ("deck", "log", "checkpoint"))
        if (not all(path.is_file() for path in (deck, output, receipt)) or
                _sha(deck) != item.get("deck_sha256") or
                _sha(output) != item.get("log_sha256")):
            raise ValueError(f"{name} deck/log missing or changed: {item['case']}")
        checkpoint = _read(receipt)
        parsed = parse_measurements(output.read_text(
            encoding="utf-8", errors="replace"), expected)
        if (checkpoint.get("status") != "PASS" or
                checkpoint.get("deck_sha256") != item["deck_sha256"] or
                checkpoint.get("log_sha256") != item["log_sha256"] or
                checkpoint.get("pex_sha256") != pex_sha or
                checkpoint.get("model_sha256") != model_sha or
                checkpoint.get("ngspice_version") != version or
                set(parsed) != set(expected) or
                parsed != checkpoint.get("measurements_v") or
                parsed != item.get("measurements_v")):
            raise ValueError(f"{name} checkpoint changed: {item['case']}")
    return report


def _audit_campaign(root: Path, *, pex_sha: str, model_sha: str) -> dict:
    report = _read(root / campaign.SUMMARY)
    if (report.get("status") not in (
            "BLOCKED_BROAD_APERTURE", "BLOCKED_5PS_APERTURE_GRID",
            "BLOCKED_HELD_NODE_TRAINING", "BLOCKED_FRESH_TT_HOLDOUT",
            "BLOCKED_READOUT_SENSITIVITY_OR_PVT",
            "MEASURED_READOUT_DIAGNOSTICS_NO_WRAPPER") or
            report.get("pex_sha256") != pex_sha or
            report.get("model_sha256") != model_sha or
            report.get("script_sha256") != _sha(Path(campaign.__file__)) or
            report.get("source_refined_sha256") != _sha(
                root / refined.OUTPUT / f"pex_{pex_sha[:12]}/measured.json")):
        raise ValueError("campaign source, script or status changed")
    groups = report.get("groups", {})
    for name, group in groups.items():
        if group.get("status") == "MEASURED_TT_DIAGNOSTIC":
            if group.get("completed_sims") != len(group.get("jobs", [])):
                raise ValueError(f"incomplete measured group: {name}")
            stage6._verified_jobs(root, report, name)
    return report


def run(root: str | Path, *, timeout_s: int = 600) -> dict:
    root = Path(root).resolve()
    if timeout_s <= 0:
        raise ValueError("positive ngspice timeout required")
    history_path = root / HISTORY
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8") as history:
        _event(history, "SESSION_START Flow-2 one-shot; existing valid evidence is reused")
        _event(history, f"RUNNER sha256={_sha(Path(__file__))}; timeout_s={timeout_s}")
        try:
            _, holdout, model, pex, _ = _sources(root)
            pex_sha, model_sha = _sha(pex), _sha(model)
            version = holdout["ngspice_version"]
            _event(history, f"INPUT PEX={pex_sha} model={model_sha} "
                    f"config={_sha(root / 'configs/sky130_mha_tiny.json')}")
            for name, module, folder, status, count in SCREENS:
                path = root / folder / f"pex_{pex_sha[:12]}/measured.json"
                if path.is_file():
                    try:
                        old = _audit_screen(root, name, module, path, status, count,
                                            pex_sha=pex_sha, model_sha=model_sha,
                                            version=version)
                    except (OSError, ValueError, KeyError, TypeError) as error:
                        archive = path.with_name(f"measured.prior.{_sha(path)[:12]}.json")
                        if archive.is_file() and _sha(archive) != _sha(path):
                            raise ValueError(f"prior archive differs: {archive}") from error
                        if not archive.is_file():
                            shutil.copy2(path, archive)
                        _event(history, f"REBUILD {name}: {error}; archived {archive.relative_to(root)}")
                    else:
                        _event(history, f"REUSE {name}: {status}; {count}/{count}; sha256={_sha(path)}")
                        continue
                _event(history, f"RUN {name}: {count} SPICE jobs maximum; timeout={timeout_s}s/job")
                tee = _Tee(sys.stdout, history)
                for recovery_attempt in range(count + 1):
                    try:
                        with redirect_stdout(tee), redirect_stderr(tee):
                            module.run(root, execute=True, timeout_s=timeout_s)
                        break
                    except FileExistsError as error:
                        if recovery_attempt == count:
                            raise
                        saved = _archive_interrupted_screen_job(
                            root, folder, pex_sha, name, error)
                        _event(history, f"RECOVER {name}: archived stale artifact(s) "
                               + json.dumps(saved, sort_keys=True))
                _audit_screen(root, name, module, path, status, count,
                              pex_sha=pex_sha, model_sha=model_sha,
                              version=version)
                _event(history, f"DONE {name}: {status}; sha256={_sha(path)}")
            summary = root / campaign.SUMMARY
            reuse = False
            if summary.is_file():
                try:
                    previous = _audit_campaign(root, pex_sha=pex_sha,
                                               model_sha=model_sha)
                    reuse = True
                    _event(history, f"REUSE campaign: {previous['status']}; sha256={_sha(summary)}")
                except (OSError, ValueError, KeyError, TypeError) as error:
                    _event(history, f"RESUME campaign: {error}")
            if not reuse:
                _event(history, "RUN campaign: aperture -> decoder -> fresh MHA -> sensitivity -> PVT")
                tee = _Tee(sys.stdout, history)
                with redirect_stdout(tee), redirect_stderr(tee):
                    previous = campaign.run(root, execute=True, timeout_s=timeout_s)
                _event(history, f"DONE campaign: {previous['status']}; sha256={_sha(summary)}")
            _event(history, "DECISION sample_off_ns={} decoder_sha256={} holdout={} sensitivity={} PVT={}".format(
                previous.get("selected_turnoff_start_ns"),
                previous.get("frozen_decoder_sha256"),
                previous.get("groups", {}).get("fresh_mha_holdout", {}).get(
                    "analysis", {}).get("tt_holdout_candidate"),
                previous.get("offline_sensitivity", {}).get("conclusion"),
                previous.get("groups", {}).get("pvt_smoke", {}).get(
                    "analysis", {}).get("conclusion")))
            metrics = {
                "groups": {name: {"status": group.get("status"),
                                   "completed": group.get("completed_sims"),
                                   "planned": group.get("planned_sims")}
                           for name, group in previous.get("groups", {}).items()},
                "training_minimum_gap_v": previous.get("groups", {}).get(
                    "held_node_training", {}).get("analysis", {}).get("minimum_gap_v"),
                "fresh_partial_decode_mismatches": previous.get("groups", {}).get(
                    "fresh_mha_holdout", {}).get("analysis", {}).get(
                        "partial_decode_mismatches"),
                "fresh_combined_decode_mismatches": previous.get("groups", {}).get(
                    "fresh_mha_holdout", {}).get("analysis", {}).get(
                        "combined_decode_mismatches"),
                "pvt_points": previous.get("groups", {}).get(
                    "pvt_smoke", {}).get("analysis", {}).get("points"),
            }
            _event(history, "METRICS " + json.dumps(metrics, sort_keys=True))
            if previous["status"] != "MEASURED_READOUT_DIAGNOSTICS_NO_WRAPPER":
                _event(history, f"SESSION_BLOCKED {previous['status']} at {previous.get('blocked_at')}; Stage-6 v2 not generated")
                return {"status": previous["status"], "history": str(HISTORY),
                        "campaign": str(campaign.SUMMARY), "stage6_v2": None}
            _event(history, "RUN Stage-6 v2 and tiny-MHA comparison")
            with redirect_stdout(_Tee(sys.stdout, history)):
                output = stage6.run(root)
            _event(history, f"SESSION_DONE {output['status']}; comparison={output['comparison']}")
            return {"status": output["status"], "history": str(HISTORY),
                    "campaign": str(campaign.SUMMARY), "stage6_v2": output}
        except KeyboardInterrupt:
            _event(history, "SESSION_INTERRUPTED; valid per-job checkpoints remain resumable")
            return {"status": "INTERRUPTED", "history": str(HISTORY)}
        except Exception as error:
            _event(history, f"SESSION_FAILED {type(error).__name__}: {error}")
            history.write(traceback.format_exc() + "\n")
            history.flush()
            return {"status": "FAILED", "history": str(HISTORY),
                    "error": f"{type(error).__name__}: {error}"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--timeout-s", type=int, default=600)
    args = parser.parse_args()
    result = run(args.root, timeout_s=args.timeout_s)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result["status"] == "DIAGNOSTIC_TT_HELD_NODE_LUT_V2"
                     else 2)
