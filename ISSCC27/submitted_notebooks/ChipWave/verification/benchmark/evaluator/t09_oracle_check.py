#!/usr/bin/env python3
"""Run frozen T09 ELF programs against the evaluator bus and commit oracles."""

from __future__ import annotations

import argparse
import gzip
import json
import subprocess
import tempfile
import time
from pathlib import Path

from elf_image import load_elf, write_hex_image
from public_check import sources_from_filelist
from sail_commit import compare_commits

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ORACLES = HERE / "t09_data" / "oracles" / "act4"
ELFS = HERE / "act4_elfs"
TB = HERE / "public" / "tb_cpu_elf.sv"


def run(submission: Path, seed: int, only: str | None = None,
        oracle_root: Path = ORACLES, elf_root: Path = ELFS,
        group: str = "CPU-ACT") -> dict:
    started = time.monotonic()
    source_files = sources_from_filelist(submission)
    manifest = json.loads((oracle_root / "MANIFEST.json").read_text())
    entries = manifest.get("oracles", manifest.get("cases"))
    if entries is None:
        raise ValueError("oracle manifest has no oracles/cases list")
    entries = [{"elf_path": row.get("elf_path", row.get("elf")),
                "oracle_path": row.get("oracle_path", row.get("oracle")),
                "commits": row.get("commits", row.get("steps"))}
               for row in entries]
    with tempfile.TemporaryDirectory(prefix="ic_bcmk_t09_act4_") as directory:
        work = Path(directory)
        build = work / "build"
        command = ["verilator", "--binary", "--timing", "--assert", "-Wno-fatal",
                   "-j", "4", "--top-module", "tb_cpu_elf", "--Mdir", str(build),
                   f"-I{ROOT}",
                   f"-I{(submission / 'rtl').resolve()}",
                   *map(str, source_files), str(TB)]
        compilation = subprocess.run(command, text=True, capture_output=True,
                                     timeout=180, check=False)
        if compilation.returncode:
            return {"task_id": "T09", "group": group, "phase": "compile",
                    "cases_total": len(entries), "cases_passed": 0,
                    "error": (compilation.stdout + compilation.stderr)[-8000:]}
        binary = build / "Vtb_cpu_elf"
        outcomes = []
        cases = [row for row in entries
                 if only is None or row["elf_path"] == only]
        if not cases:
            raise ValueError(f"unknown ELF path: {only}")
        for index, row in enumerate(cases):
            elf = elf_root / row["elf_path"]
            image = work / f"image_{index}.hex"
            trace = work / f"trace_{index}.jsonl"
            write_hex_image(load_elf(elf), image)
            max_cycles = row["commits"] * 100 + 10000
            executed = subprocess.run(
                [str(binary), f"+IMAGE={image}", f"+TRACE={trace}",
                 f"+SEED={seed}", f"+MAX_CYCLES={max_cycles}"],
                text=True, capture_output=True, timeout=180, check=False)
            with gzip.open(oracle_root / row["oracle_path"], "rt") as reference:
                expected = [json.loads(line) for line in reference]
            observed = ([json.loads(line) for line in trace.read_text().splitlines()]
                        if trace.is_file() else [])
            comparison = compare_commits(expected, observed)
            completed = executed.returncode == 0 and "CPU_ELF_PASS" in executed.stdout
            passed = completed and comparison["passed"]
            outcomes.append({"elf": row["elf_path"], "passed": passed,
                             "program_completed": completed,
                             "matched_commits": comparison["matched"],
                             "reason": comparison.get("reason"),
                             "expected_at_failure": comparison.get("expected"),
                             "observed_at_failure": comparison.get("observed"),
                             "expected_context": expected[max(0, comparison["matched"]-3):
                                                          comparison["matched"]+3]
                             if not passed else [],
                             "observed_context": observed[max(0, comparison["matched"]-3):
                                                          comparison["matched"]+3]
                             if not passed else [],
                             "log_tail": (executed.stdout + executed.stderr)[-1000:]
                             if not passed else ""})
            print(f"{row['elf_path']}: {'PASS' if passed else 'FAIL'} "
                  f"matched={comparison['matched']}/{row['commits']}", flush=True)
        return {"task_id": "T09", "group": group, "phase": "run",
                "cases_total": len(cases),
                "cases_passed": sum(row["passed"] for row in outcomes),
                "seed": seed, "elapsed_seconds": round(time.monotonic() - started, 3),
                "outcomes": outcomes}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("submission", type=Path)
    parser.add_argument("--seed", type=int, default=20260925)
    parser.add_argument("--only", help="exact ACT4 ELF path for local diagnosis")
    parser.add_argument("--oracle-root", type=Path, default=ORACLES)
    parser.add_argument("--elf-root", type=Path, default=ELFS)
    parser.add_argument("--group", default="CPU-ACT")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = run(args.submission.resolve(), args.seed, args.only,
                     args.oracle_root.resolve(), args.elf_root.resolve(), args.group)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        result = {"task_id": "T09", "group": args.group, "phase": "infrastructure",
                  "error": str(exc)}
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    else:
        print(json.dumps(result, indent=2))
    return 0 if result.get("cases_passed") == result.get("cases_total") else 1


if __name__ == "__main__":
    raise SystemExit(main())
