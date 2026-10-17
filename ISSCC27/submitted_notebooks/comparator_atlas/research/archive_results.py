"""Copy the compact research outputs into results/research and seal them with a manifest.

  python -B research/archive_results.py [source_out_dir]

The source defaults to research/out. Raw SPICE caches and the per-condition r2/r13 phase files
(about 25 MB, reproducible with r2_prospective.py and r13_fix_atlas.py) are not archived.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEST = ROOT / "results" / "research"
STUDIES = {
    "r1": ["r1_report.json", "r1_residuals.csv"],
    "r2": ["r2/r2_evaluation.json", "r2/r2_atlas_new_designs.csv",
           "r2/registered_predictions_batch1.json", "r2/registered_predictions_batch1.sha256",
           "r2/registered_predictions_batch2.json", "r2/registered_predictions_batch2.sha256"],
    "r3": ["r3/r3_report.json", "r3/mc_*.jsonl", "r3/sigma_*.json"],
    "r4": ["r4_report.json", "r4b_report.json", "r4_samples.csv"],
    "r5": ["r5/r5_lvt_balanced_4b.json"],
    "r6": ["r6/r6_report.json", "r6/r6_runs.jsonl", "r6/r6_pvt45_report.json", "r6/r6_pvt45.jsonl"],
    "r7": ["r3/trim_dnl.jsonl"],
    "r8": ["r8/*.json*"],
    "r9": ["r9/mc_combo_t*.jsonl", "r9/r9_report.json"],
    "r10": ["r9/mc_combo_5b_*.jsonl"],
    "r11": ["r11/r11_pvt45.jsonl", "r11/r11_report.json"],
    "r12": ["r12/*.json*"],
    "r13": ["r13/registered_predictions_fix.*", "r13/r2_evaluation.json", "r13/r2_atlas_new_designs.csv",
            "r13/fix_residuals.csv"],
    "r14": ["r14/energy.json"],
    "r15a": ["r15a/registered_predictions_a.*", "r15a/r2_evaluation.json", "r15a/r2_atlas_new_designs.csv",
             "r15a/unit5_w3_residuals.csv"],
    "r15b": ["r15b/registered_predictions_b.*", "r15b/r2_evaluation.json", "r15b/r2_atlas_new_designs.csv",
             "r15b/unit6_w6_residuals.csv"],
    "r16": ["r16/mc_unit6_*.jsonl", "r16/energy.json"],
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(source: Path) -> None:
    if DEST.exists():
        shutil.rmtree(DEST)
    files = {}
    for study, patterns in STUDIES.items():
        for pattern in patterns:
            matches = sorted(source.glob(pattern))
            if not matches:
                raise SystemExit(f"{study}: nothing matches {pattern} in {source}")
            for path in matches:
                target = DEST / study / path.name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
                files[f"{study}/{path.name}"] = sha256(target)
    manifest = {
        "schema": "comparator-atlas-research-archive-v1",
        "scope": "Local follow-on schematic and archived-extraction simulations; see research/README.md",
        "artifact_sha256": files,
        "script_sha256": {p.name: sha256(p) for p in sorted(HERE.glob("*.py"))},
    }
    (DEST / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"archived {len(files)} files; manifest sha256 {sha256(DEST / 'manifest.json')}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "out")
