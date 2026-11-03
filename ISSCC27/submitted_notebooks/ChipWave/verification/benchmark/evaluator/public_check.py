#!/usr/bin/env python3
"""Run an evaluator-owned public smoke test against a submission's fixed RTL ports.

This is a public demonstration, not the hidden scorer or a source of official points.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SUPPORTED = {f"T{i:02d}" for i in range(1, 11)}


def sources_from_filelist(submission: Path) -> list[Path]:
    rtl = (submission / "rtl").resolve(strict=True)
    filelist = rtl / "files.f"
    paths = []
    for line_number, raw in enumerate(filelist.read_text().splitlines(), start=1):
        entry = raw.strip()
        if not entry or entry.startswith("#"):
            continue
        relative = Path(entry)
        if relative.is_absolute() or ".." in relative.parts or entry.startswith("-"):
            raise ValueError(f"unsafe filelist entry at line {line_number}: {entry}")
        source = (rtl / relative).resolve(strict=True)
        if not source.is_relative_to(rtl) or source.suffix not in {".sv", ".v"}:
            raise ValueError(f"invalid RTL source at line {line_number}: {entry}")
        paths.append(source)
    if not paths or len(paths) != len(set(paths)):
        raise ValueError("rtl/files.f must list at least one unique RTL source")
    return paths


def run(task: str, submission: Path, seed: int, width: int, depth: int, n_inputs: int) -> dict:
    sources = sources_from_filelist(submission)
    tb = ROOT / "public" / f"tb_{task}.sv"
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix=f"ic_bcmk_{task}_") as build_dir:
        binary_dir = Path(build_dir)
        compile_cmd = [
            "verilator", "--binary", "--timing", "--assert", "-Wno-fatal",
            "-j", "4", "--top-module", f"tb_{task}", "--Mdir", str(binary_dir),
            f"-I{ROOT.parent}",
            f"-I{(submission / 'rtl').resolve()}",
            *map(str, sources), str(tb),
        ]
        if task == "T10":
            compile_cmd.insert(2, "--hierarchical")
        if task in {"T02", "T05"}:
            compile_cmd[1:1] = [f"-GWIDTH={width}", f"-GDEPTH={depth}"]
        elif task == "T04":
            compile_cmd[1:1] = [f"-GWIDTH={width}", f"-GN={n_inputs}"]
        compiled = subprocess.run(compile_cmd, text=True, capture_output=True,
                                  timeout=600 if task == "T10" else 180, check=False)
        if compiled.returncode:
            return {"task": task, "passed": False, "phase": "compile",
                    "elapsed_seconds": round(time.monotonic() - start, 3),
                    "log_tail": (compiled.stdout + compiled.stderr)[-8000:]}
        binary = binary_dir / f"Vtb_{task}"
        executed = subprocess.run([str(binary), f"+SEED={seed}"], text=True,
                                  capture_output=True,
                                  timeout=180 if task == "T10" else 60, check=False)
        return {"task": task, "passed": executed.returncode == 0 and
                f"PUBLIC_PASS {task}" in executed.stdout, "phase": "run",
                "seed": seed,
                "parameters": ({"WIDTH": width, "DEPTH": depth} if task in {"T02", "T05"} else
                               {"WIDTH": width, "N": n_inputs} if task == "T04" else {}),
                "elapsed_seconds": round(time.monotonic() - start, 3),
                "log_tail": (executed.stdout + executed.stderr)[-8000:]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=sorted(SUPPORTED))
    parser.add_argument("submission", type=Path,
                        help="submission root containing rtl/files.f")
    parser.add_argument("--seed", type=int, default=20260925)
    parser.add_argument("--width", type=int, choices=[8, 32], default=8)
    parser.add_argument("--depth", type=int, choices=[3, 8, 16], default=3)
    parser.add_argument("--n-inputs", type=int, choices=[4, 8], default=4)
    args = parser.parse_args()
    if args.task == "T05" and args.depth == 3:
        parser.error("T05 requires --depth 8 or 16")
    try:
        result = run(args.task, args.submission, args.seed, args.width, args.depth, args.n_inputs)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        result = {"task": args.task, "passed": False, "phase": "infrastructure",
                  "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
