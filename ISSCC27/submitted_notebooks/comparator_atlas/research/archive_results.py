"""Copy the compact research outputs into results/research and seal them with a manifest.

  python -B research/archive_results.py [source_out_dir]

The source defaults to research/out. Raw SPICE caches and the per-condition r2/r13/r21 phase files
(about 37 MB, reproducible with r2_prospective.py, r13_fix_atlas.py and r21_neutral_atlas.py) are not archived;
nor are the r23 per-device noise tables (research/cache/r23, rebuilt by r23_noise.py tables), nor the r24
trajectories and per-condition ISF scans (rebuilt by r24_isf.py traj / isf / atlas; r24_report.json keeps
every number the Notebook uses), nor the raw 200-seed r26c/r26d/r26e MC files (~14 MB; rebuilt by r26b_unit.py mc,
r26c_eqscale.py mc and r26e_seg.py mc, summarized per seed by r26c_stats.py), nor the raw 200-seed r26f MC files
(rebuilt by r26f_dec.py mc, summarized by r26f_dec.py compare), nor the r26g / r26h / r26i per-run probe logs
(`_probe_*.jsonl`, summarized in probe_drivers_*.json, probe_R*_C*.json and probe_d5_*.json), nor the r26j
calibration Monte Carlo files (r26j/mc_*.jsonl, rebuilt by r26j_verify.py mcflow and summarized in verify_k175.json).
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
    "r17": ["r17/r17_pvt45.jsonl", "r17/r17_report.json"],
    "r18": ["r18/screen.jsonl"],
    "r19": ["r19/r19_rc.jsonl", "r19/r19_rc_report.json", "r19/registered_predictions_w12.*",
            "r19/r2_evaluation.json", "r19/r2_atlas_new_designs.csv", "r19/u6_w12_l05_residuals.csv",
            "r19/mc_w12_*.jsonl"],
    "r20": ["r20/offset.jsonl", "r20/eff_skew.json", "r20/bin_stress.jsonl", "r20/bin_stress_summary.json"],
    "r21": ["r21/r21_score.json", "r21/r21_score_refined.json", "r21/refined.json"],
    "r22": ["r22/range.jsonl", "r22/mc_*.jsonl", "r22/sigma_*.json", "r22/r22_report.json"],
    "r23": ["r23/run_*.jsonl", "r23/validate_*.json", "r23/b0_*.json", "r23/r23_report.json"],
    "r24": ["r24/r24_report.json", "r24/atlas_pinned_*.jsonl", "r24/isf_*.jsonl", "r24/sym_*.jsonl",
            "r24/memory_*.json", "r24/trim_steps_swap.json", "r24/gain_law.json", "r24/fixmc_*.jsonl",
            "r24/fixrange_*.json"],
    "r25": ["r25/screen.jsonl", "r25/dnl_*.json", "r25/range_*.json", "r25/mc_*.jsonl", "r25/memory_*.json",
            "r25/r25_report.json"],
    "r26": ["r26/screen.jsonl", "r26/dnl_*.json", "r26/range_*.json", "r26/mc_*.jsonl", "r26/memory_*.json",
            "r26/r26_report.json"],
    "r26b": ["r26b/weights.jsonl", "r26b/screen.jsonl", "r26b/dnl_u5_*.json", "r26b/range_u5_*.json",
             "r26b/mc_sf*_u5_*.jsonl", "r26b/mc_ff*_u5_*.jsonl", "r26b/mc_tt*_u5_*.jsonl", "r26b/memory_*u5_*.json"],
    "r26c": ["r26c/seeds_*_k150.jsonl", "r26c/stats_*_k150.json", "r26c/inv_sweep.json", "r26b/dnl_e5_k150.json",
             "r26b/range_e5_k150.json", "r26b/memory_*e5_k150*.json", "r26b/fine_transfer*.json"],
    "r26d": ["r26c/seeds_e5_k175.jsonl", "r26c/stats_e5_k175.json", "r26b/dnl_e5_k1[67]*.json",
             "r26b/range_e5_k1[67]*.json", "r26b/memory_*e5_k175.json", "r26d/carry_e5_*.json",
             "r26d/segment_e5_*.json"],
    "r26e": ["r26c/seeds_g5_k175.jsonl", "r26c/stats_g5_k175.json", "r26b/dnl_g5_k175.json",
             "r26b/memory_energy_g5_k175.json", "r26e/carry_*.json", "r26e/compare_g5_k175.json"],
    "r26f": ["r26b/dnl_d5_k175.json", "r26b/memory_energy_d5_k175.json", "r26f/*.json"],
    "r26g": ["r26g/kick_*.json", "r26g/probe_drivers_*.json", "r26g/dip_law_*.json"],
    "r26h": ["r26h/kick_R*_C*.json", "r26h/probe_R*_C*.json", "r26h/thevenin_*.json", "r26h/states_*.json",
             "r26h/kick_d5_lin*.json", "r26h/probe_d5_lin*.json"],
    "r26i": ["r26i/kick_d5_*.json", "r26i/probe_d5_*.json", "r26i/fixes_k175.json"],
    "r26j": ["r26j/sigma_d5_*.json", "r26j/_mcloss_*.jsonl", "r26j/_para_*.jsonl", "r26j/energy_*.json",
             "r26j/verify_k175.json"],
}
# r26c extends the r26b MC files to 200 seeds; r26b keeps its 40 (r26c archives a per-seed summary instead).
SEED_LIMIT = {"r26b": 40}


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
                body = path.read_bytes().replace(b"\r\n", b"\n")
                if study in SEED_LIMIT and path.name.startswith("mc_"):
                    body = b"".join(ln for ln in body.splitlines(keepends=True)
                                    if json.loads(ln)["seed"] < SEED_LIMIT[study])
                target.write_bytes(body)
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
