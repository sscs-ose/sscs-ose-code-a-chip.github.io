#!/usr/bin/env python3
"""Recompute the frozen long-mirror candidate from retained simulation files."""
from __future__ import annotations

import hashlib
import json
import re
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

import dense_characterization
import mismatch_mc
import mismatch_sizing_sweep
import readout_budget
import run_sky130
import sizing_candidate_qualification

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results" / "long_mirror_candidate"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def unpack(archive: Path, manifest: dict, destination: Path) -> None:
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    require(digest == manifest["archive_sha256"], "raw archive hash mismatch")
    with tarfile.open(archive, "r:gz") as source:
        names = []
        for member in source.getmembers():
            path = PurePosixPath(member.name)
            require(member.isfile() and not path.is_absolute()
                    and ".." not in path.parts, "invalid archive member")
            require(member.name not in names, "duplicate archive member")
            names.append(member.name)
            content = source.extractfile(member).read()
            require(hashlib.sha256(content).hexdigest()
                    == manifest["files"].get(member.name),
                    f"raw member hash mismatch: {member.name}")
            target = destination / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    require(set(names) == set(manifest["files"]), "raw archive file set mismatch")


def check_raw(path: Path, temps: list[float], mode: str, frozen: dict,
              model_library: str, corner: str, seed: int | None = None) -> None:
    run_sky130.validate_csv(path, temps, mode)
    netlist = (path.parent / "netlists" / (path.stem + ".spice")).read_text()
    log = (path.parent / "logs" / (path.stem + ".log")).read_text()
    require(f'.lib "{model_library}" {corner}' in netlist,
            f"wrong model/corner: {path.name}")
    geometry = run_sky130.characterization_seed(
        sensor_linear_scale=frozen["sensor_linear_scale"],
        mirror_linear_scale=frozen["mirror_linear_scale"],
        mirror_length_multiplier=frozen["mirror_length_multiplier"],
    )
    sensor, mirror = geometry["sensor_nmos"], geometry["mirror_pmos"]
    expected = {
        "VDDVAL": frozen["vdd_v"],
        "LNS" if mode == "mirror" else "LCH": sensor["l_um"],
        "WNS1" if mode == "mirror" else "W1": sensor["w_small_um"],
        "WNS2" if mode == "mirror" else "W2": sensor["w_large_um"],
        "IREF" if mode == "mirror" else "IBIAS": frozen["reference_current_a"],
    }
    if mode == "mirror":
        expected.update(LPM=mirror["l_um"], WPM=mirror["w_um"])
    parameters = dict(re.findall(r"\b([A-Z][A-Z0-9]*)=([0-9.eE+\-]+)", netlist))
    for key, value in expected.items():
        require(key in parameters and float(parameters[key]) == value,
                f"wrong {key}: {path.name}")
    if seed is not None:
        require(f".option seed={seed}\n" in netlist
                and f"setseed {seed}\n" in netlist,
                f"wrong random seed: {path.name}")
    require("Compatibility modes selected: hs a" in log,
            f"missing hsa compatibility evidence: {path.name}")
    require(not re.search(r"(?im)^(?:error|fatal)|no matching model|"
                          r"could not find a valid model|timestep too small", log),
            f"simulation error: {path.name}")
    raw_rows = [line.removeprefix("PTAT_CSV ") for line in log.splitlines()
                if line.startswith("PTAT_CSV ")]
    require(path.read_text().splitlines()[1:] == raw_rows,
            f"CSV differs from simulator log: {path.name}")


def audit(results: Path = RESULTS) -> dict:
    frozen = load(ROOT / "long_mirror_candidate.json")
    temps = run_sky130.parse_temps(frozen["temperature_spec"])
    anchors = frozen["calibration_anchors_c"]
    design = run_sky130.load_design()
    require(frozen["vdd_v"] == design["nominal_characterization_seed"]["vdd_v"],
            "candidate metrics require the nominal VDD")
    sweep = load(results / "sizing_summary.json")
    metrics = {}
    with tempfile.TemporaryDirectory(prefix="ptat-long-mirror-") as temp:
        raw = Path(temp)
        unpack(results / "raw_evidence.tar.gz", load(results / "manifest.json"), raw)
        metadata = load(raw / "dense" / "run_metadata.json")
        provenance = sweep["provenance"]
        require(provenance["pdk_revision"] == frozen["pdk_revision"]
                and provenance["model_sha256"] == frozen["model_sha256"],
                "candidate PDK provenance mismatch")
        require(provenance["design_requirements_sha256"]
                == run_sky130.sha256_file(ROOT / "design_requirements.json"),
                "design requirements changed since simulation")
        for name, start, count in (
            ("screen", frozen["screen_seed_start"], frozen["screen_samples"]),
            ("independent_validation", frozen["initial_validation_seed_start"],
             frozen["validation_samples"]),
        ):
            directory = raw / name
            summary = load(directory / "summary.json")
            require(summary["provenance"] == provenance, f"{name}: provenance mismatch")
            require(summary["seed_start"] == start and summary["seed_end"] == start + count - 1,
                    f"{name}: seed metadata mismatch")
            require(summary["operating_point"] == {
                "vdd_v": frozen["vdd_v"], "reference_current_a": frozen["reference_current_a"]
            }, f"{name}: operating point mismatch")
            for key in ("sensor_linear_scale", "mirror_linear_scale", "mirror_length_multiplier"):
                require(summary["geometry"][key] == frozen[key], f"{name}: geometry mismatch")
            files = sorted(directory.glob("sample_*.csv"))
            expected = [f"sample_{seed:05d}.csv" for seed in range(start, start + count)]
            require([path.name for path in files] == expected, f"{name}: missing/extra seeds")
            for seed, path in zip(range(start, start + count), files):
                check_raw(path, temps, "mirror", frozen, provenance["model_library"], "tt_mm", seed)
            recomputed = mismatch_mc.analyze(files, temps, anchors)
            for key, value in recomputed.items():
                require(summary[key] == value, f"{name}: stale {key}")
            metrics[name] = mismatch_sizing_sweep.candidate_metrics(recomputed, files)
        selected = sweep["recommended_for_independent_validation"]
        validation = sweep["independent_validation"]
        require(selected["candidate"] == validation["candidate"] == frozen["candidate"],
                "candidate identity mismatch")
        for key in ("sensor_linear_scale", "mirror_linear_scale", "mirror_length_multiplier"):
            require(selected[key] == frozen[key] == metadata[key], "dense geometry mismatch")
        for name, record in (("screen", selected), ("independent_validation", validation)):
            for key, value in metrics[name].items():
                require(record[key] == value, f"{name}: stale sizing metric {key}")
        require(sweep["seed_start"] == frozen["screen_seed_start"]
                and sweep["samples_per_candidate"] == frozen["screen_samples"]
                and validation["seed_start"] == frozen["initial_validation_seed_start"]
                and validation["samples"] == frozen["validation_samples"], "sizing seed mismatch")
        for mode in ("ideal", "mirror"):
            for corner in ("tt", "ff", "ss"):
                check_raw(raw / "dense" / f"ptat_{mode}_{corner}.csv", temps, mode,
                          frozen, metadata["model_library"], corner)
        dense = dense_characterization.analyze(raw / "dense", anchors, frozen["vdd_v"])
        dense["provenance"] = dense_characterization.load_provenance(raw / "dense")
        dense["operating_point"] = metadata["operating_point"]
        readout = readout_budget.analyze_directory(raw / "dense", anchors)
        require(dense == load(results / "dense_analysis.json"), "stale dense analysis")
        require(readout == load(results / "readout_analysis.json"), "stale readout analysis")
        result = sizing_candidate_qualification.analyze(
            sweep, dense, metadata, readout,
            design["nominal_characterization_seed"]["reference_current_a"],
        )
        require(result == load(results / "qualification.json"), "stale qualification")
        require(result["qualified_for_release_review"], "candidate failed qualification")
    return {"status": "PASS", "candidate": frozen["candidate"],
            "raw_simulations_checked": frozen["screen_samples"] + frozen["validation_samples"] + 6,
            "qualification": result["status"],
            "independent_validation": metrics["independent_validation"]}


if __name__ == "__main__":
    try:
        print(json.dumps(audit(), indent=2, sort_keys=True))
    except (ValueError, KeyError, OSError, tarfile.TarError) as exc:
        raise SystemExit(f"LONG MIRROR EVIDENCE AUDIT: FAIL: {exc}")
