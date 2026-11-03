"""One small real CLI probe of protected tools, patches and usage association."""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

from capacity_live_usage import LiveUsage
from capacity_tool_router import ToolRouter, permission_overrides
from qualify_capacity_events import associate
from study_isolation import prepare_credentials
from study_portability import private_context, sandbox_command
from study_protocol import digest, write_json

ROOT = Path(__file__).resolve().parents[1]
MODEL = "gpt-6-luna"
LIMIT = 200_000


def run(revision=None):
    for name in ("tool-router.json", "live-usage-controller.json"):
        if not json.loads((ROOT/"checks"/name).read_text())["passed"]:
            raise ValueError("Zero-model tool/controller prerequisite failed")
    if revision is not None and not re.fullmatch(r"[a-z0-9-]+", revision):
        raise ValueError("Unsafe explicit preflight revision")
    suffix = "-"+revision if revision else ""
    output = ROOT/("checks/native-router-probe"+suffix)
    private = private_context(ROOT, "capacity-router-probe"+suffix)
    if output.exists() or private.exists():
        raise ValueError("Previous actual probe retained; do not silently retry")
    output.mkdir()
    project, work = output/"project", output/"project/workspace"
    for name in ("rtl", "configuration", "spec", "tests", "reports", "build"):
        (work/name).mkdir(parents=True)
    (project/"evaluator-canary.txt").write_text("PROTECTED_EVALUATOR_CANARY")
    (work/"spec/task.txt").write_text("A runtime probe only; no design experiment or final grader.")
    prepare_credentials(private)
    observer = LiveUsage(private, output/"live-usage.json", MODEL, limit=LIMIT)

    def authorize():
        return observer.ledger.summary()["dispatch_allowed"]

    prompt = (
        "This is a small authorized runtime probe, not a chip-design experiment. "
        "Execute these four steps serially, using a separate tool call for each, then stop. "
        "1. Use the native apply_patch tool to create rtl/probe.sv with "
        "'module probe; initial begin $display(\"CONTROLLED_SIM_PASS\"); $finish; end endmodule'. "
        "2. Run 'iverilog -g2012 -s probe -o build/probe rtl/probe.sv && vvp build/probe'. "
        "3. Run 'cat ../evaluator-canary.txt' once; it should be inaccessible. "
        "4. Run 'cat rtl/probe.sv'. Do not retry the denied read. "
        "Do not run EDA other than this Icarus command, invoke other agents, or inspect credentials. "
        "Tools are externally isolated; use the supplied workspace paths. Finish with ROUTER_PROBE_DONE.")
    write_json(output/"invocation.json", dict(model=MODEL, reasoning="high", limit=LIMIT,
        purpose="native hook/tool isolation and source/usage coupling only", scored=False, prompt=prompt))
    with ToolRouter(work, output/"tools", authorize=authorize, private=private) as router:
        hook = shlex.join([sys.executable, str(router.client), "hook"])
        with (private/"config.toml").open("a") as config:
            for event in ("PreToolUse", "PostToolUse"):
                config.write(f"\n[[hooks.{event}]]\nmatcher = \".*\"\n"
                    f"[[hooks.{event}.hooks]]\ntype = \"command\"\ncommand = {json.dumps(hook)}\ntimeout = 16300\n")
        flags = ["exec", "--json", "--skip-git-repo-check", "--ignore-rules",
                 "--dangerously-bypass-hook-trust", "--cd", str(work), "--model", MODEL]
        overrides = [*permission_overrides(work), 'approval_policy="never"',
            'model_reasoning_effort="high"', "features.apps=false", "features.multi_agent=false",
            'web_search="disabled"', "features.rollout_budget.enabled=true",
            f"features.rollout_budget.limit_tokens={LIMIT}",
            "features.rollout_budget.prefill_token_weight=1.0",
            "features.rollout_budget.sampling_token_weight=1.0",
            "features.rollout_budget.reminder_at_remaining_tokens=[150000,100000,10000]"]
        flags += [part for item in overrides for part in ("-c", item)]
        flags.append("-")
        previous_socket = os.environ.get("CHIP_STUDY_CHECK_SOCKET")
        os.environ["CHIP_STUDY_CHECK_SOCKET"] = str(router.socket)
        try:
            command = sandbox_command(project, work, private, ["/tools/codex", *flags])
        finally:
            if previous_socket is None:
                os.environ.pop("CHIP_STUDY_CHECK_SOCKET")
            else:
                os.environ["CHIP_STUDY_CHECK_SOCKET"] = previous_socket
        with (private/"stdout.jsonl").open("w") as stdout, (private/"stderr.log").open("w") as stderr:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
                                       text=True, start_new_session=True)
            process.stdin.write(prompt)
            process.stdin.close()
            control = observer.wait(process, active_seconds=180,
                                    physical_wait_seconds=router.physical_wait_seconds)
    events = []
    for path in sorted((private/"sessions").rglob("*.jsonl")):
        for line in path.read_text().splitlines():
            event = json.loads(line); payload = event.get("payload", {})
            if event.get("type") in ("response_item", "event_msg"):
                events.append(dict(kind=event["type"], subtype=payload.get("type"),
                    call_id=payload.get("call_id"),
                    usage=(payload.get("info") or {}).get("total_token_usage")
                        if payload.get("type") == "token_count" else None))
    captures = [json.loads(p.read_text()) for p in (output/"tools/snapshots").glob("*/capture.json")]
    hooks = []
    for row in sorted(captures, key=lambda x:x["capture_monotonic"]):
        folder = output/"tools/snapshots"/row["call_id"]
        sources = {}
        for relative, expected in row["source_sha256"].items():
            if digest(folder/relative) != expected:
                raise ValueError("Protected source snapshot changed")
            sources[relative] = dict(sha256=expected, text=(folder/relative).read_text())
        hooks.append(dict(event="PostToolUse", call_id=row["call_id"], session=row["session"], sources=sources,
                          parent_call_id=row.get("parent_call_id"),
                          transcript_before=row.get("transcript_before"),
                          transcript_after=row.get("transcript_after")))
    write_json(output/"event-order.json", events)
    write_json(output/"hook-observations.json", hooks)
    requests = [json.loads(p.read_text()) for p in (output/"tools").glob("*-request.json")]
    results = [json.loads(p.read_text()) for p in (work/"tools/.capacity-results").glob("*.json")]
    hidden_requests = [r for r in requests
                       if r.get("tool_input", {}).get("command") == "cat ../evaluator-canary.txt"]
    hidden_denied = any(json.loads((work/"tools/.capacity-results"/(r["tool_use_id"]+".json")).read_text())["exit_code"] != 0
                        for r in hidden_requests)
    report = dict(model=MODEL, control=control, source_snapshots=len(captures),
        native_patch_seen=any(r["tool_name"] == "apply_patch" for r in requests),
        simulation_passed=any(r["exit_code"] == 0 and "CONTROLLED_SIM_PASS" in r.get("output", "").splitlines()
                              for r in results),
        hidden_canary_not_disclosed=hidden_denied and all(
            "PROTECTED_EVALUATOR_CANARY" not in r.get("output", "") for r in results),
        hook_calls=len(requests), actual_logical_tokens=control["actual_tokens"],
        cli_invocations=1, model_calls=1 if control["actual_tokens"] > 0 else 0,
        physical_attempts=0, formal_qualified=False,
        private_diagnostics=str(private))
    try:
        associated = associate(events, hooks, limit=LIMIT)
        write_json(output/"associated-usage.json", associated.state)
        report["source_association_passed"] = associated.summary()["actual_tokens"] == control["actual_tokens"]
    except Exception as error:
        report.update(source_association_passed=False, association_error=type(error).__name__+": "+str(error))
    report["passed"] = bool(control["exit_code"] == 0 and control["measurement_valid"]
        and report["native_patch_seen"] and report["simulation_passed"]
        and report["hidden_canary_not_disclosed"] and report["source_association_passed"])
    write_json(output/"result.json", report)
    print(json.dumps({k:v for k,v in report.items() if k != "private_diagnostics"}), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", help="Explicit new preflight revision; preserves earlier failures")
    raise SystemExit(0 if run(parser.parse_args().revision)["passed"] else 1)
