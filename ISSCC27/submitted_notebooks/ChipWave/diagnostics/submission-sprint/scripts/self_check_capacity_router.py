"""Real native sandbox, isolated tools and controller quotas; no model calls."""
import json
import shlex
import subprocess
import sys
import tempfile
import threading
import socket
from pathlib import Path

from capacity_tool_router import ToolRouter, patch_targets, permission_overrides
from capacity_toolbox import ToolBudget
from study_protocol import write_json
from study_portability import sandbox_command as outer_sandbox
from qualify_capacity_events import associate

BINARY = Path("/home/asic03/.codex/packages/standalone/current/bin/codex").resolve()


def native(work, command, writable=None):
    extra = {} if writable is None else dict(writable=writable)
    config = permission_overrides(work, binary_directory=str(BINARY.parent), **extra)
    flags = [part for item in config for part in ("-c", item)]
    result = subprocess.run([str(BINARY), "sandbox", "-P", "capacity", *flags, "-C", str(work),
                             "--", "/bin/bash", "-c", command],
                            text=True, capture_output=True, timeout=30)
    return result


def event(work, call, command, tool="Bash", kind="PreToolUse"):
    return dict(cwd=str(work), session_id="fixture-session", tool_use_id=call,
                tool_name=tool, hook_event_name=kind, tool_input=dict(command=command))


def denied(reply):
    return reply.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


def check():
    with tempfile.TemporaryDirectory(prefix="capacity-router-check-") as tmp:
        root = Path(tmp); work = root/"workspace"
        for name in ("rtl", "configuration", "spec", "tests", "reports", "build"):
            (work/name).mkdir(parents=True)
        (root/"hidden.txt").write_text("hidden-reference")
        (work/"spec/task.txt").write_text("frozen")
        (work/"rtl/check.sv").write_text('module test; initial begin $display("SIM_PASS");$finish;end endmodule')
        private = root/"private"
        private.mkdir()
        flags = [part for item in permission_overrides(work) for part in ("-c", item)]
        nested = subprocess.run(outer_sandbox(work, work, private,
            ["/tools/codex", "sandbox", "-P", "capacity", *flags, "-C", str(work),
             "--", "/bin/cat", str(work/"spec/task.txt")]),
             text=True, capture_output=True, timeout=30)
        assert nested.returncode == 0 and nested.stdout.strip() == "frozen", nested.stdout+nested.stderr
        callbacks = []
        def physical_fixture(workspace, identity):
            callbacks.append(identity)
            return dict(status="failed", evidence="Zero-model quota fixture; no EDA",
                        output="FIXTURE_PHYSICAL_FAILURE\n", exit_code=1)
        with ToolRouter(work, root/"ledger", authorize=lambda: True,
                        handlers={"physical": physical_fixture,"development":lambda workspace,identity:dict(
                            status="passed",evidence="integration quota fixture; no EDA",output="INTEGRATION_FIXTURE",exit_code=0)}) as router:
            for index, command in enumerate(("cat spec/task.txt",
                    "iverilog -g2012 -s test -o build/sim rtl/check.sv && vvp build/sim")):
                request = event(work, "call-"+str(index), command)
                reply = router.handle(request)
                assert not denied(reply), reply
                assert router.active is None, "Completed host tool left stale ownership"
                result = native(work, reply["hookSpecificOutput"]["updatedInput"]["command"])
                assert result.returncode == 0, result.stdout+result.stderr
                assert ("frozen" if index == 0 else "SIM_PASS") in result.stdout
                router.handle(dict(request, hook_event_name="PostToolUse"))
                assert denied(router.handle(request)), "Repeated call accepted"
            assert len(json.loads((root/"ledger/tool-ledger.json").read_text())["attempts"]) == 1
            for call,command in (("integration-status","capacity-check integration"),("budget-status","capacity-check status")):
                request=event(work,call,command);reply=router.handle(request)
                result=native(work,reply["hookSpecificOutput"]["updatedInput"]["command"])
                assert result.returncode==0,result.stdout+result.stderr
                router.handle(dict(request,hook_event_name="PostToolUse"))
            shared=json.loads(result.stdout)
            assert shared["tool_attempts"]["development"]==2 and shared["tool_remaining"]["development"]==18
            assert len(json.loads((root/"ledger/tool-ledger.json").read_text())["attempts"])==2
            assert denied(router.handle(event(work, "unsupported", "", tool="spawn_agent")))
            for target in ("spec/task.txt", "../hidden.txt", str(root/"hidden.txt"), "tools/capacity_bridge.py"):
                try:
                    patch_targets(work, "*** Begin Patch\n*** Delete File: "+target+"\n*** End Patch\n")
                except ValueError:
                    pass
                else:
                    raise AssertionError("Protected patch target accepted")
            (work/"rtl/link.sv").symlink_to(root/"hidden.txt")
            try:
                patch_targets(work, "*** Begin Patch\n*** Delete File: rtl/link.sv\n*** End Patch\n")
            except ValueError:
                pass
            else:
                raise AssertionError("Symlink patch accepted")
            (work/"rtl/link.sv").unlink()
            for index in range(3):
                request = event(work, "physical-"+str(index), "capacity-check physical")
                reply = router.handle(request)
                result = native(work, reply["hookSpecificOutput"]["updatedInput"]["command"])
                assert result.returncode != 0
                router.handle(dict(request, hook_event_name="PostToolUse"))
            assert len(callbacks) == 2, "Third physical backend invoked"
            assert "quota exhausted" in result.stdout
            # Even an unrewritten native command cannot read the evaluator or alter the contract.
            script = f"""from pathlib import Path
import socket
try:Path({str(root/'hidden.txt')!r}).read_text()
except (PermissionError,FileNotFoundError):pass
else:raise AssertionError('Hidden reference readable')
try:Path({str(work/'spec/task.txt')!r}).write_text('changed')
except OSError:pass
else:raise AssertionError('Contract writable')
try:socket.create_connection(('127.0.0.1',7897),timeout=1)
except OSError:pass
else:raise AssertionError('Provider proxy reachable')
print('NATIVE_BACKSTOP_PASS')
"""
            result = native(work, shlex.join(["/usr/bin/python3", "-c", script]))
            assert result.returncode == 0, result.stdout+result.stderr
            assert "NATIVE_BACKSTOP_PASS" in result.stdout
            result = native(work, shlex.join(["/usr/bin/python3","-c",
                "from pathlib import Path\n"
                "try:Path('rtl/check.sv').write_text('unauthorized')\n"
                "except OSError:pass\n"
                "else:raise AssertionError('Reviewer changed RTL')\n"
                "Path('reports/review.txt').write_text('permitted')\n"]),
                writable=("tests","reports","build"))
            assert result.returncode == 0, result.stdout+result.stderr
            assert (work/"reports/review.txt").read_text() == "permitted"
            router.authorize = lambda: False
            assert denied(router.handle(event(work, "exhausted", "cat rtl/check.sv")))
        snapshots = list((root/"ledger/snapshots").glob("*/capture.json"))
        assert len(snapshots) == 7
        assert all(not json.loads(p.read_text())["usage_associated"] for p in snapshots)
        sessions = private/"sessions"
        sessions.mkdir()
        transcript = sessions/"fixture-fixture-session.jsonl"
        call = {"type": "response_item", "payload": {"type": "custom_tool_call", "call_id": "parent"}}
        transcript.write_text(json.dumps(call)+"\n")
        with ToolRouter(work, root/"nested-ledger", authorize=lambda: True, private=private) as router:
            request = event(work, "exec-child", "cat spec/task.txt")
            assert not denied(router.handle(request))
            router.handle(dict(request, hook_event_name="PostToolUse"))
            capture = json.loads((root/"nested-ledger/snapshots/exec-child/capture.json").read_text())
            assert capture["parent_call_id"] == "parent"
            sources = {p: dict(text=(work/p).read_text(), sha256=h) for p,h in capture["source_sha256"].items()}
            usage = dict(input_tokens=100, output_tokens=10, total_tokens=110,
                         cached_input_tokens=0, reasoning_output_tokens=0)
            events = [dict(kind="response_item", subtype="custom_tool_call", call_id="parent"),
                      dict(kind="response_item", subtype="custom_tool_call_output", call_id="parent"),
                      dict(kind="event_msg", subtype="token_count", usage=usage)]
            hook = dict(event="PostToolUse", call_id="exec-child", session="fixture-session", sources=sources,
                        **{k:capture[k] for k in ("parent_call_id","transcript_before","transcript_after")})
            assert associate(events,[hook]).state["snapshots"][0]["tokens"] == 110
            transcript.write_text(transcript.read_text()+json.dumps(dict(call,payload={
                "type":"custom_tool_call","call_id":"concurrent"}))+"\n")
            try:
                router.parent_witness(event(work, "exec-other", "cat spec/task.txt"))
            except ValueError:
                pass
            else:
                raise AssertionError("Ambiguous parent accepted")
        entered, finished = threading.Event(), threading.Event()
        def accepted_eda(workspace, identity):
            entered.set()
            release.wait(5)
            finished.set()
            return dict(status="passed",evidence="shutdown fixture; no EDA",exit_code=0,output="done")
        release = threading.Event()
        with ToolRouter(work,root/"shutdown-ledger",authorize=lambda:True,
                        handlers={"physical":accepted_eda}) as router:
            def request():
                with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
                    connection.connect(str(router.socket))
                    connection.sendall(json.dumps(event(work,"shutdown-call","capacity-check physical")).encode()+b"\n")
                    connection.shutdown(socket.SHUT_WR)
                    while connection.recv(65536):
                        pass
            client=threading.Thread(target=request)
            client.start()
            assert entered.wait(5)
            threading.Timer(.1,release.set).start()
        client.join(timeout=5)
        assert finished.is_set() and not client.is_alive()
        assert json.loads((root/"shutdown-ledger/tool-ledger.json").read_text())["attempts"][0]["status"]=="passed"
        empty=root/"empty-worktree";empty.mkdir()
        with ToolRouter(empty,root/"empty-ledger",authorize=lambda:True):
            result=native(empty,shlex.join(["/usr/bin/python3","-c",
                "from pathlib import Path;Path('rtl/new.sv').write_text('module example;endmodule')"]))
            assert result.returncode==0, result.stdout+result.stderr
            assert (empty/"rtl/new.sv").is_file()
    result = dict(passed=True, model_calls=0, physical_runs=0,
        checks=["native permissions independently hide references/protect contract/block network",
                "native sandbox starts within the isolated Codex package",
                "reviewer can write reports but cannot change RTL",
                "actual Icarus tool output routed through native call",
                "free inspection excluded from check quota", "serial call guard",
                "unsafe/symlink patch rejection", "third physical callback refused",
                "accepted deterministic work finishes on controller shutdown",
                "empty Git worktree write roots are prepared",
                "source snapshots preserved pending usage association", "shared-budget dispatch refusal"],
        scope="Router and native sandbox with synthetic hook events; real native hook coupling still pending")
    write_json(Path(__file__).resolve().parents[1]/"checks/tool-router.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(check()))
