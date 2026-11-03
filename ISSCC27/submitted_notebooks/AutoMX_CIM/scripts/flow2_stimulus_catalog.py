"""Recreate Flow-2 vectors without claiming the historical simulations ran.

The old 74-job idle report is optional evidence. When present, its vectors
must match the deterministic generator; when absent, only stimulus selection
is recovered. No voltages or measurement status are synthesized here.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from automx_cim.config import Sky130MHAConfig
from scripts.run_core_pex_coverage import Case, mha_cases
from scripts.run_post49_row_partition import split_case
from scripts.run_wrapper_idle_augmented_tt import idle_training_cases
from automx_cim import attention as attention_source
from scripts import run_core_pex_coverage as core_source
from scripts import run_post49_row_partition as partition_source
from scripts import run_wrapper_idle_augmented_tt as idle_source

HISTORICAL = Path("results/sky130/wrapper_idle_augmented_tt/c820ff/measured.json")
OUTPUT = Path("results/sky130/flow2_stimulus_catalog")
CONFIG = Path("configs/sky130_mha_tiny.json")


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _vectors(case: Case) -> dict:
    return {"case": case.name, "activation_x2": list(case.acts),
            "ternary_weights": [list(row) for row in case.weights],
            "integer_sums": list(case.sums)}


def _phase_vectors(parent: Case) -> list[dict]:
    return [_vectors(phase) for phase in split_case(_vectors(parent), "adjacent")]


def load_stimuli(root: str | Path, *, model_sha256: str) -> tuple[dict, dict]:
    """Return deterministic 10+64 phase vectors and their honest provenance."""
    root = Path(root).resolve()
    config_path = root / CONFIG
    config = Sky130MHAConfig.from_json(config_path)
    parents = mha_cases(config, 128)
    if len(parents) != 128 or [case.name for case in parents[96:128]] != [
            f"mha_{rank:02d}" for rank in range(96, 128)]:
        raise ValueError("MHA generator no longer produces ranks 96..127")
    idle = [item for parent in idle_training_cases(config)
            for item in _phase_vectors(parent)]
    fresh = [item for parent in parents[96:128]
             for item in _phase_vectors(parent)]
    if (len(idle) != 10 or len(fresh) != 64 or
            len({item["case"] for item in idle + fresh}) != 74):
        raise ValueError("Flow-2 generator must produce 74 distinct phase vectors")
    catalog = {"format": "automx-cim-flow2-stimulus-catalog-v1",
               "status": "PREPARED_STIMULI_ONLY",
               "config_sha256": _sha(config_path),
               "generator_sha256": _sha(Path(__file__)),
               "dependency_sha256": {
                   "automx_cim/attention.py": _sha(Path(attention_source.__file__)),
                   "scripts/run_core_pex_coverage.py": _sha(Path(core_source.__file__)),
                   "scripts/run_post49_row_partition.py": _sha(Path(partition_source.__file__)),
                   "scripts/run_wrapper_idle_augmented_tt.py": _sha(Path(idle_source.__file__)),
               },
               "jobs": {"idle_training": idle, "fresh_holdout": fresh},
               "not_measurements": "vectors only; no historical ngspice run or voltage evidence"}
    dependencies_sha = sha256(json.dumps(
        catalog["dependency_sha256"], sort_keys=True).encode("utf-8")).hexdigest()
    path = (root / OUTPUT /
            f"config_{catalog['config_sha256'][:12]}_generator_{catalog['generator_sha256'][:12]}"
            f"_dependencies_{dependencies_sha[:12]}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        if json.loads(path.read_text(encoding="utf-8")) != catalog:
            raise FileExistsError(f"existing stimulus catalog differs: {path}")
    else:
        path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    historical_path = root / HISTORICAL
    historical_sha = None
    if historical_path.is_file():
        historical = json.loads(historical_path.read_text(encoding="utf-8"))
        if (historical.get("status") != "MEASURED_TT_IDLE_AUGMENTATION_DIAGNOSTIC" or
                historical.get("completed_new_sims") != 74 or
                historical.get("model_sha256") != model_sha256):
            raise ValueError("historical idle report is incomplete or uses another model")
        for group in ("idle_training", "fresh_holdout"):
            observed = [{key: job[key] for key in
                         ("case", "activation_x2", "ternary_weights", "integer_sums")}
                        for job in historical["jobs"][group]]
            if observed != catalog["jobs"][group]:
                raise ValueError(f"historical {group} vectors differ from generator")
        historical_sha = _sha(historical_path)
    provenance = {"catalog_path": str(path.relative_to(root)),
                  "catalog_sha256": _sha(path),
                  "historical_measured_report_sha256": historical_sha,
                  "stimulus_evidence_level": ("HISTORICAL_MEASURED_VECTORS_MATCHED"
                                              if historical_sha else
                                              "DETERMINISTIC_VECTORS_ONLY")}
    return catalog, provenance
