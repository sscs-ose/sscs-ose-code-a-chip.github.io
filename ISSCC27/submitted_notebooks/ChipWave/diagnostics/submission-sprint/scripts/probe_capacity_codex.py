"""Small, isolated connectivity/event-order probes, excluded from scored trials."""
from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

from capacity_protocol import MODELS
from study_isolation import prepare_credentials
from study_portability import private_context, sandbox_command
from study_protocol import digest, write_json

HOOK = r'''import hashlib,json,time
from pathlib import Path
import sys
event=json.load(sys.stdin)
transcript=event.get("transcript_path")
last=None; sequence=[]
if transcript and Path(transcript).is_file():
 for line in Path(transcript).read_text().splitlines():
  try: row=json.loads(line)
  except ValueError: continue
  p=row.get("payload",{})
  if row.get("type")=="event_msg" and p.get("type")=="token_count":
   last=p.get("info",{}).get("total_token_usage")
  if row.get("type") in ("response_item","event_msg"):
   sequence.append([row.get("type"),p.get("type"),p.get("call_id")])
sources={}
for path in sorted(Path(event["cwd"]).glob("rtl/**/*.sv")):
 if path.is_symlink():raise ValueError("Symlink source")
 sources[str(path.relative_to(event["cwd"]))]={
  "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"text":path.read_text()}
record=dict(event=event.get("hook_event_name"),tool=event.get("tool_name"),
 session=event.get("session_id"),model=event.get("model"),usage=last,
 sequence_tail=sequence[-8:],sources=sources,monotonic_ns=time.monotonic_ns())
with (Path.home()/".codex/probe-hooks.jsonl").open("a") as f:
 f.write(json.dumps(record)+"\n")
print("{}")
'''


def run(campaign, model, resume=False, external_limit=None):
    campaign = Path(campaign).resolve()
    if model not in MODELS.values():
        raise ValueError("Only the two approved models may be probed")
    for name in ("zero-model-core.json", "zero-model-isolation.json"):
        if not json.loads((campaign / "checks" / name).read_text())["passed"]:
            raise ValueError("Zero-model prerequisite failed")
    label = model.replace(".", "-")
    if external_limit is not None and (not resume or external_limit <= 0):
        raise ValueError("External-stop probe requires a positive limit and an existing context")
    output = campaign / "checks" / (("stopped-" if external_limit else "resume-" if resume else "connectivity-") + label)
    if output.exists():
        raise ValueError("Retain the existing probe; do not silently retry")
    output.mkdir()
    private = private_context(campaign, "capacity-connectivity", label)
    if private.exists() and not resume:
        raise ValueError("Existing private context preserved")
    if resume:
        original=campaign/"checks"/("connectivity-"+label)
        prior=json.loads((original/"result.json").read_text())
        if external_limit:
            prior=json.loads((campaign/"checks"/("resume-"+label)/"result.json").read_text())
        if not prior["connectivity_pass"]:
            raise ValueError("Cannot resume a failed connectivity probe")
        sessions={r["session"] for r in json.loads((original/"hook-observations.json").read_text())}
        if len(sessions)!=1:raise ValueError("Ambiguous probe context")
        session=sessions.pop()
        from capacity_context import IsolatedCodexAdapter
        transcript=IsolatedCodexAdapter(private)._session_file_path(session)
        write_json(output/"before-resume.json",dict(session=session,transcript_sha256=digest(transcript),
            prior_total_usage=prior["actual_usage"]))
        project=original/"project"
    else:
        project=output/"project"
    work=project/"workspace"
    if not resume:
        (work/"tools").mkdir(parents=True)
        (work/"rtl").mkdir()
        hook=work/"tools/observer.py";hook.write_text(HOOK)
        prepare_credentials(private)
        command=shlex.join([sys.executable,str(hook)])
        with (private/"config.toml").open("a") as handle:
            for name in ("PreToolUse","PostToolUse","Stop","SessionEnd"):
                handle.write(f"\n[[hooks.{name}]]\n")
                if name in ("PreToolUse","PostToolUse"):handle.write('matcher = ".*"\n')
                handle.write(f"[[hooks.{name}.hooks]]\ntype = \"command\"\n"
                             f"command = {json.dumps(command)}\ntimeout = 10\n")
    flags = ["exec", "--json", "--skip-git-repo-check",
             "--dangerously-bypass-approvals-and-sandbox", "--dangerously-bypass-hook-trust",
             "--cd", str(work), "--model", model, "-c", 'model_reasoning_effort="high"',
             "-c", "features.multi_agent=false", "-c", "features.apps=false",
             "-c", 'web_search="disabled"', "-c", "features.rollout_budget.enabled=true",
             "-c", "features.rollout_budget.limit_tokens=50000",
             "-c", "features.rollout_budget.prefill_token_weight=1.0",
             "-c", "features.rollout_budget.sampling_token_weight=1.0",
             "-c", "features.rollout_budget.reminder_at_remaining_tokens=[25000,10000]"]
    if resume:flags+=["resume",session]
    flags+=["-"]
    prompt = (
        "This is a tiny authorized tool-event probe, not a chip design experiment. "
        "Do exactly this: use one tool call to write rtl/probe.sv containing "
        "'module probe(input wire a, output wire y); assign y=a; endmodule'. "
        "Then use a separate tool call to read that file. "
        "Do not use other agents, browse, inspect credentials, or run EDA. "
        "Finish with PROBE_DONE. Do not inspect files outside this workspace.")
    if resume:
        prompt=("Resume the same tiny probe context. Read rtl/probe.sv, then in a separate "
                "tool call write rtl/resume.sv containing 'module resumed; endmodule'. "
                "Do not run other agents, EDA or inspect credentials. Finish with RESUME_DONE. "
                "The existing 50000-token rollout ceiling is intentional; honor it.")
    if external_limit:
        prompt=("Small authorized external-budget-stop probe, not a design experiment. "
                "Use separate tool calls to read rtl/probe.sv, write rtl/stopped.sv containing "
                "'module stopped; endmodule', read rtl/stopped.sv, and write rtl/after_stop.sv "
                "containing 'module after_stop; endmodule'. Do not combine calls. "
                "Do not use agents, network, EDA or inspect files outside this workspace. "
                "An external observer may terminate this probe. Finish with STOP_PROBE_DONE.")
    write_json(output / "invocation.json", dict(model=model, effort="high", token_limit=50000,
        external_scoring_limit=external_limit,
        purpose="connectivity and hook/event ordering only", scored=False,
        physical_attempts=0, prompt=prompt, cli_version=subprocess.check_output(
            ["/home/asic03/.codex/packages/standalone/current/bin/codex", "--version"], text=True).strip()))
    started = time.monotonic()
    timed_out = False
    prefix="stopped-" if external_limit else "resume-" if resume else ""
    stop_report=None
    with (private / (prefix+"stdout.jsonl")).open("w") as stdout, (private / (prefix+"stderr.log")).open("w") as stderr:
        process = subprocess.Popen(sandbox_command(project, work, private, ["/tools/codex", *flags]),
            stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, text=True, start_new_session=True)
        try:
            if external_limit:
                from capacity_live_usage import LiveUsage
                observer=LiveUsage(private,output/"live-usage.json",model,limit=external_limit)
                process.stdin.write(prompt)
                process.stdin.close()
                stop_report=observer.wait(process,active_seconds=180)
            else:
                process.communicate(prompt, timeout=180)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
    hooks = [json.loads(line) for line in (private / "probe-hooks.jsonl").read_text().splitlines()
             ] if (private / "probe-hooks.jsonl").exists() else []
    usage, identities, event_order, errors = None, [], [], []
    for path in sorted((private / "sessions").glob("**/*.jsonl")):
        for line in path.read_text().splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            p = event.get("payload", {})
            if event.get("type") == "turn_context":
                identities.append(dict(model=p.get("model"), effort=p.get("effort")))
            if event.get("type") == "event_msg" and p.get("type") == "token_count":
                usage = p.get("info", {}).get("total_token_usage")
            if event.get("type") in ("response_item", "event_msg"):
                event_order.append(dict(kind=event.get("type"), subtype=p.get("type"),
                                        call_id=p.get("call_id"),
                                        usage=(usage if p.get("type") == "token_count" else None)))
    for line in (private / (prefix+"stdout.jsonl")).read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") in ("error", "turn.failed"):
            errors.append(event)
    # Preserve detailed private transport diagnostics locally, never copy credentials.
    write_json(output / "hook-observations.json", hooks)
    write_json(output / "event-order.json", event_order)
    target = work / ("rtl/stopped.sv" if external_limit else "rtl/resume.sv" if resume else "rtl/probe.sv")
    result = dict(model=model, exit_code=process.returncode, timed_out=timed_out,
                  elapsed_seconds=time.monotonic()-started, actual_usage=usage,
                  observed_contexts=identities, hook_events=len(hooks), errors=errors,
                  source_sha256=digest(target) if target.exists() else None,
                  connectivity_pass=process.returncode == 0 and bool(usage) and target.exists(),
                  source_association_qualified=False,
                  note="A successful probe is not formal metering or workflow qualification.",
                  private_diagnostics=str(private))
    if resume:
        result.update(resumed_session=session,
            same_context=all(h["session"]==session for h in hooks),
            incremental_tokens=(usage["total_tokens"]-prior["actual_usage"]["total_tokens"]) if usage else None)
    if external_limit:
        result.update(external_stop=stop_report, external_scoring_limit=external_limit,
                      requested_final_tool_executed=(work/"rtl/after_stop.sv").exists(),
                      native_source_snapshot_scoring_qualified=False)
    write_json(output / "result.json", result)
    print(json.dumps({k: v for k, v in result.items() if k not in ("errors", "private_diagnostics")}), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--model", choices=list(MODELS.values()), required=True)
    parser.add_argument("--resume",action="store_true")
    parser.add_argument("--external-limit",type=int)
    args = parser.parse_args()
    run(args.campaign, args.model, args.resume, args.external_limit)
