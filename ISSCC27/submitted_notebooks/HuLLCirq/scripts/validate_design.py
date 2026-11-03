#!/usr/bin/env python3
"""Check saved design JSON with the same deterministic validators as the GUI.

This read-only command does not create a review decision or execute LLM/EDA.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hullcirq.domain import DomainError, IMPLEMENTED_STAGES, validate_stage
from hullcirq.store import strict_loads


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("design", type=Path, help="Design JSON, not a local state/history file.")
    parser.add_argument("--stage", choices=IMPLEMENTED_STAGES + ("all",), default="all")
    args = parser.parse_args()
    try:
        design = strict_loads(args.design.read_text(encoding="utf-8"))
        stages = IMPLEMENTED_STAGES if args.stage == "all" else (args.stage,)
        results = [{"stage_id": stage, "diagnostics": validate_stage(design, stage)} for stage in stages]
    except (DomainError, OSError, ValueError, RecursionError) as error:
        value = {"error": {"code": getattr(error, "code", "input_error"), "message": str(error)}}
        print(json.dumps(value, ensure_ascii=False, allow_nan=False))
        return 2
    failed = any(item["severity"] == "error" for stage in results for item in stage["diagnostics"])
    print(json.dumps({"validation_status": "Failed" if failed else "Passed", "scope": "M1_input_checks_only",
                      "stages": results}, indent=2, ensure_ascii=False, allow_nan=False))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
