#!/usr/bin/env python3
"""Calibrate T09 data-bus backpressure across 20 fixed latency seeds."""

from __future__ import annotations

import argparse
import gzip
import json
import re
import subprocess
import tempfile
from pathlib import Path

from t09_oracle_check import ROOT, TB, compare_commits, load_elf, sources_from_filelist, write_hex_image

HERE = Path(__file__).resolve().parent
PROGRAMS = HERE / "t09_data" / "programs"
CASES = (
    (PROGRAMS / "directed", "haz_load_use_immediate_v1.elf"),
    (PROGRAMS / "directed", "trap_store_access_fault_v1.elf"),
    (PROGRAMS / "random", "diff_mem_seed034_v0.elf"),
    (PROGRAMS / "random", "diff_trap_seed067_v0.elf"),
)
SEEDS = tuple(range(20260925, 20260945))
METRICS = re.compile(r"CPU_ELF_PASS .*delays=([0-9a-fA-F]+) backpressure=(\d+)")


def run(submission: Path) -> dict:
    sources = sources_from_filelist(submission)
    with tempfile.TemporaryDirectory(prefix="ic_bcmk_t09_wait_") as directory:
        work = Path(directory)
        build = work / "build"
        command = ["verilator", "--binary", "--timing", "--assert", "-Wno-fatal",
                   "-j", "4", "--top-module", "tb_cpu_elf", "--Mdir", str(build),
                   f"-I{ROOT}",
                   f"-I{(submission / 'rtl').resolve()}", *map(str, sources), str(TB)]
        compiled = subprocess.run(command, text=True, capture_output=True, timeout=180)
        if compiled.returncode:
            raise RuntimeError((compiled.stdout + compiled.stderr)[-8000:])
        binary = build / "Vtb_cpu_elf"
        rows = []
        delay_mask = 0
        backpressure_cycles = 0
        for case_index, (root, filename) in enumerate(CASES):
            manifest = json.loads((root / "MANIFEST.json").read_text())
            entry = next(row for row in manifest["cases"] if row["elf"] == filename)
            image = work / f"image_{case_index}.hex"
            write_hex_image(load_elf(root / filename), image)
            with gzip.open(root / entry["oracle"], "rt") as reference:
                expected = [json.loads(line) for line in reference]
            for seed in SEEDS:
                trace = work / "trace.jsonl"
                executed = subprocess.run(
                    [str(binary), f"+IMAGE={image}", f"+TRACE={trace}",
                     f"+SEED={seed}", f"+MAX_CYCLES={entry['steps'] * 100 + 10000}"],
                    text=True, capture_output=True, timeout=180)
                observed = [json.loads(line) for line in trace.read_text().splitlines()]
                comparison = compare_commits(expected, observed)
                match = METRICS.search(executed.stdout)
                passed = executed.returncode == 0 and comparison["passed"] and match is not None
                row = {"elf": filename, "seed": seed, "passed": passed,
                       "matched": comparison["matched"], "expected": len(expected),
                       "reason": comparison.get("reason"),
                       "log_tail": (executed.stdout + executed.stderr)[-1000:] if not passed else ""}
                rows.append(row)
                if match:
                    delay_mask |= int(match.group(1), 16)
                    backpressure_cycles += int(match.group(2))
                print(f"{filename} seed={seed}: {'PASS' if passed else 'FAIL'}",
                      flush=True)
        return {"runs": len(rows), "passed": sum(row["passed"] for row in rows),
                "distinct_seeds": len(SEEDS), "delay_mask": delay_mask,
                "all_1_to_8_cycle_delays_seen": delay_mask & 0x1FE == 0x1FE,
                "backpressure_cycles": backpressure_cycles,
                "outcomes": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", type=Path, default=HERE / "reference/T09")
    parser.add_argument("--output", type=Path,
                        default=HERE / "t09_wait_qualification.json")
    args = parser.parse_args()
    result = run(args.submission.resolve())
    output = args.output
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "outcomes"},
                     indent=2))
    return 0 if result["passed"] == result["runs"] and result["all_1_to_8_cycle_delays_seen"] and result["backpressure_cycles"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
