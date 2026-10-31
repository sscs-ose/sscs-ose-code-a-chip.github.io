#!/usr/bin/env python3
"""Check T09 card-specific illegal traps unsupported by the locked Sail model."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from t09_oracle_check import ROOT, TB, load_elf, sources_from_filelist, write_hex_image

HERE = Path(__file__).resolve().parent
CASES = HERE / "t09_data" / "programs" / "spec"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", type=Path, default=HERE / "reference/T09")
    parser.add_argument("--output", type=Path,
                        default=HERE / "t09_spec_qualification.json")
    args = parser.parse_args()
    submission = args.submission.resolve()
    entries = json.loads((CASES / "MANIFEST.json").read_text())["cases"]
    sources = sources_from_filelist(submission)
    rows = []
    with tempfile.TemporaryDirectory(prefix="ic_bcmk_t09_spec_") as directory:
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
        for index, row in enumerate(entries):
            image = work / f"image_{index}.hex"
            trace = work / f"trace_{index}.jsonl"
            write_hex_image(load_elf(CASES / row["elf"]), image)
            executed = subprocess.run(
                [str(binary), f"+IMAGE={image}", f"+TRACE={trace}",
                 "+SEED=20260925", "+MAX_CYCLES=10000"],
                text=True, capture_output=True, timeout=180)
            events = [json.loads(line) for line in trace.read_text().splitlines()]
            traps = [event for event in events if event["kind"] == "trap"]
            forbidden = {row["fault_pc"], row["fault_pc"] + 4}
            retired_fault_or_younger = [event for event in events
                                        if event["kind"] == "commit" and event["pc"] in forbidden]
            passed = (executed.returncode == 0 and "CPU_ELF_PASS" in executed.stdout
                      and len(traps) == 1 and traps[0]["pc"] == row["fault_pc"]
                      and traps[0]["cause"] == 2 and traps[0]["tval"] == row["fault_insn"]
                      and not retired_fault_or_younger)
            rows.append({"case": row["case"], "passed": passed,
                         "expected_trap": {"pc": row["fault_pc"], "cause": 2,
                                           "tval": row["fault_insn"]},
                         "observed_traps": traps,
                         "forbidden_commits": retired_fault_or_younger,
                         "log_tail": (executed.stdout + executed.stderr)[-1000:] if not passed else ""})
            print(f"{row['case']}: {'PASS' if passed else 'FAIL'}", flush=True)
    result = {"cases_total": len(rows), "cases_passed": sum(row["passed"] for row in rows),
              "outcomes": rows}
    output = args.output
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    return 0 if result["cases_passed"] == result["cases_total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
