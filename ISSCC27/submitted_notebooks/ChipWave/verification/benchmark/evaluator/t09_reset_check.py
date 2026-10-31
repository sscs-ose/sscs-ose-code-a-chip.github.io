#!/usr/bin/env python3
"""Inject live resets into T09 and compare the post-reset trace with Sail."""

from __future__ import annotations

import argparse
import gzip
import json
import subprocess
import tempfile
from pathlib import Path

from t09_oracle_check import ROOT, TB, compare_commits, load_elf, sources_from_filelist, write_hex_image

HERE = Path(__file__).resolve().parent
CASES = (
    ("alu", "int_add_sub_v1.elf", 20260925),
    ("branch", "haz_load_to_branch_v1.elf", 20260926),
    ("load_wait", "diff_mem_seed034_v0.elf", 20260927),
    ("load_wait", "diff_trap_seed067_v0.elf", 20260928),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", type=Path, default=HERE / "reference/T09")
    parser.add_argument("--output", type=Path,
                        default=HERE / "t09_reset_qualification.json")
    args = parser.parse_args()
    submission = args.submission.resolve()
    sources = sources_from_filelist(submission)
    rows = []
    with tempfile.TemporaryDirectory(prefix="ic_bcmk_t09_reset_") as directory:
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
        for index, (phase, filename, seed) in enumerate(CASES):
            root = HERE / "t09_data" / "programs" / ("random" if filename.startswith("diff_") else "directed")
            manifest = json.loads((root / "MANIFEST.json").read_text())
            entry = next(row for row in manifest["cases"] if row["elf"] == filename)
            image = work / f"image_{index}.hex"
            trace = work / f"trace_{index}.jsonl"
            write_hex_image(load_elf(root / filename), image)
            with gzip.open(root / entry["oracle"], "rt") as reference:
                expected = [json.loads(line) for line in reference]
            executed = subprocess.run(
                [str(binary), f"+IMAGE={image}", f"+TRACE={trace}",
                 f"+SEED={seed}", f"+RESET_WHEN={phase}",
                 f"+MAX_CYCLES={entry['steps'] * 100 + 10000}"],
                text=True, capture_output=True, timeout=180)
            observed = [json.loads(line) for line in trace.read_text().splitlines()]
            comparison = compare_commits(expected, observed)
            reset_seen = f"CPU_RESET_INJECT phase={phase}" in executed.stdout
            passed = (executed.returncode == 0 and reset_seen and
                      "CPU_ELF_PASS" in executed.stdout and comparison["passed"])
            rows.append({"phase": phase, "elf": filename, "seed": seed,
                         "passed": passed, "matched": comparison["matched"],
                         "expected": len(expected), "reason": comparison.get("reason"),
                         "log_tail": (executed.stdout + executed.stderr)[-1000:] if not passed else ""})
            print(f"{phase} {filename}: {'PASS' if passed else 'FAIL'}", flush=True)
    result = {"cases_total": len(rows), "cases_passed": sum(row["passed"] for row in rows),
              "outcomes": rows}
    output = args.output
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    return 0 if result["cases_passed"] == result["cases_total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
