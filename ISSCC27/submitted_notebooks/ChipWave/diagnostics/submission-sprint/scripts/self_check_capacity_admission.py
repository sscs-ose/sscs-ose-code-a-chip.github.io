"""Verify source freezing and fail-closed tool admission using the real controller."""
import json
import tempfile
from pathlib import Path

from capacity_live_usage import LiveUsage
from capacity_tool_router import ToolRouter
from capacity_snapshots import associate_captures
from study_protocol import write_json


def check():
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)
        for tokens in (75,150):
            case=root/str(tokens);work=case/"workspace"
            (work/"rtl").mkdir(parents=True)
            (work/"rtl/top.sv").write_text("module example;endmodule\n")
            private=case/"private";(private/"sessions").mkdir(parents=True)
            usage=dict(input_tokens=tokens,output_tokens=0,cached_input_tokens=0,
                       reasoning_output_tokens=0,total_tokens=tokens)
            rows=[dict(type="session_meta",payload=dict(id="fixture")),
                  dict(type="turn_context",payload=dict(model="gpt-6-luna",effort="high")),
                  dict(type="response_item",payload=dict(type="custom_tool_call",call_id="parent")),
                  dict(type="token_usage_record",payload=dict(session_id="fixture",response_id="response",
                       usage=usage,thread_token_usage=usage))]
            transcript=private/"sessions/rollout-fixture.jsonl"
            transcript.write_text("".join(json.dumps(r)+"\n" for r in rows))
            observer=LiveUsage(private,case/"usage.json","gpt-6-luna",limit=100)
            observer.poll()
            assert observer.admit("fixture","missing") is None
            calls=[]
            def backend(source,identity):
                assert source!=work and (source/"rtl/top.sv").read_text()==(work/"rtl/top.sv").read_text()
                calls.append(identity)
                return dict(status="passed",evidence="Synthetic fixture; no EDA",exit_code=0,output="fixture")
            with ToolRouter(work,case/"tools",private=private,authorize=lambda:True,
                            admit_usage=observer.admit,handlers={"physical":backend}) as router:
                event=dict(hook_event_name="PreToolUse",cwd=str(work),session_id="fixture",
                           tool_use_id="child",tool_name="Bash",
                           tool_input=dict(command="capacity-check physical"))
                result=router.handle(event)
                if tokens>100:
                    assert result["hookSpecificOutput"]["permissionDecision"]=="deny" and not calls
                    assert not (case/"tools/tool-ledger.json").exists()
                    continue
                assert calls==[1]
                # The enclosing code-mode cell may finish before its long nested tool.
                with transcript.open("a") as handle:
                    handle.write(json.dumps(dict(type="response_item",payload=dict(
                        type="custom_tool_call_output",call_id="parent")))+"\n")
                router.handle(dict(event,hook_event_name="PostToolUse"))
            assert associate_captures(observer,case/"tools/snapshots")==1
            saved=observer.ledger.at(100)
            assert saved["tokens"]==75 and saved["witness"]["source_frozen_before_eda"]
    report=dict(passed=True,model_calls=0,physical_runs=0,
        checks=["own-response usage required","immutable input supplied to deterministic tool",
                "late nested-tool completion retains original source binding",
                "over-budget response invokes no backend and allocates no tool slot"])
    write_json(Path(__file__).resolve().parents[1]/"checks/response-admission.json",report)
    return report


if __name__=="__main__":
    print(json.dumps(check()))
