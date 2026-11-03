#!/usr/bin/env python3
"""Record a real local-provider smoke run without recording human approval.

This developer check uses the same context, transport and candidate checks as
the GUI. It does not bypass GUI approval gates or insert jobs into a project.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.context import build_node_context
from hullcirq.domain import DomainError
from hullcirq.provider import ChatCompletionsClient, validate_profile
from hullcirq.rtl_checks import check_rtl, compare_rtl, extract_rtl
from hullcirq.store import strict_loads, utc_now


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--node", required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--compiler-config", type=Path)
    parser.add_argument("--out", type=Path, required=True, help="New empty evidence directory.")
    parser.add_argument("--repair-from", type=Path, help="Earlier run.json; its candidate and diagnostics are sent to the local model.")
    parser.add_argument("--instruction", default="")
    args = parser.parse_args()
    try:
        design_raw = args.design.read_bytes()
        design = strict_loads(design_raw.decode("utf-8"))
        profile = validate_profile(strict_loads(args.profile.read_text(encoding="utf-8")))
        if profile["execution_location"] != "Local":
            raise DomainError("local_only", "This smoke command only permits a local provider.")
        compiler = strict_loads(args.compiler_config.read_text(encoding="utf-8")) if args.compiler_config else None
        previous = strict_loads(args.repair_from.read_text(encoding="utf-8")) if args.repair_from else None
        if previous and (previous.get("node_id") != args.node or not previous.get("rtl")):
            raise DomainError("invalid_repair", "Repair needs an earlier candidate from this node.")
        if previous and not args.instruction.strip():
            raise DomainError("feedback_required", "Describe the requested repair.")
        revision = "input-sha256-" + hashlib.sha256(design_raw).hexdigest()
        context = build_node_context(design, revision, args.node, args.instruction,
                                     previous["rtl"] if previous else None, previous["diagnostics"] if previous else None)
        if context["estimated_input_tokens"] + profile["max_output_tokens"] > profile["context_window"]:
            raise DomainError("context_budget", "Conservative input estimate plus output exceeds the verified runtime window.")
        if args.out.exists() and any(args.out.iterdir()):
            raise DomainError("output_exists", "Evidence directory is not empty; use a new directory.")
        args.out.mkdir(parents=True, exist_ok=True)
        write_json(args.out / "input.json", design)
        write_json(args.out / "profile.json", profile)
        write_json(args.out / "context.json", context)
        events = []
        started = utc_now()
        def event(value):
            events.append({**value, "sequence": len(events) + 1, "created_at": utc_now()})
        print("Calling local model; evidence directory: " + str(args.out.resolve()), flush=True)
        result = ChatCompletionsClient(profile).generate(context["messages"], on_event=event)
        extracted = extract_rtl(result["raw_content"]) if result["execution_status"] == "Completed" else {"rtl": None, "diagnostics": []}
        rtl = extracted["rtl"]
        checked = check_rtl(rtl, context["interface"], context["interface"]["module_name"], compiler) if rtl else {
            "validation_status": "Not Checked", "diagnostics": [], "checks": {}}
        record = {**result, "events": events, "node_id": args.node, "revision_id": revision,
                  "origin": "local_llm", "execution_scope": "development_smoke_no_human_acceptance",
                  "instruction_actor": "development_assistant" if args.instruction else None,
                  "candidate_manual_edits": [], "reused_circuit_code": [],
                  "review_status": "Awaiting Review", "human_review_performed": False,
                  "operation": "repair" if previous else "generate", "instruction": args.instruction,
                  "base_run": str(args.repair_from) if previous else None,
                  "profile": profile, "context": context, "compiler": compiler,
                  "rtl": rtl, "validation_status": checked["validation_status"],
                  "diagnostics": extracted["diagnostics"] + checked["diagnostics"], "checks": checked["checks"],
                  "created_at": started, "finished_at": utc_now(),
                  "raw_content_sha256": hashlib.sha256(result["raw_content"].encode()).hexdigest(),
                  "rtl_sha256": hashlib.sha256(rtl.encode()).hexdigest() if rtl else None}
        write_json(args.out / "run.json", record)
        write_json(args.out / "checks.json", checked)
        (args.out / "raw_answer.txt").write_text(result["raw_content"], encoding="utf-8")
        if rtl:
            (args.out / "candidate.v").write_text(rtl, encoding="utf-8")
            (args.out / "candidate.diff").write_text(compare_rtl(previous["rtl"] if previous else "", rtl), encoding="utf-8")
        print(json.dumps({"execution_status": result["execution_status"], "validation_status": checked["validation_status"],
                          "review_status": "Awaiting Review", "finish_reason": result.get("finish_reason"),
                          "error": result.get("error"), "diagnostics": record["diagnostics"]}, indent=2), flush=True)
        return 0 if result["execution_status"] == "Completed" and checked["validation_status"] == "Passed" else 1
    except (DomainError, OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
