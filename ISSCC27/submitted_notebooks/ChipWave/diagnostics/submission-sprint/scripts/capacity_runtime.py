"""Common protected native execution for C0 and the public Codex adapter."""
from __future__ import annotations

import fcntl
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

from capacity_live_usage import LiveUsage
from capacity_meter import InvalidMeasurement
from capacity_protocol import MODELS
from capacity_snapshots import associate_captures
from capacity_tool_router import ToolRouter, WRITABLE, permission_overrides
from study_isolation import prepare_credentials
from study_portability import sandbox_command
from study_protocol import write_json


def adapter_arguments(arguments, config):
    """Only accept the public adapter's known invocation, never arbitrary CLI flags."""
    expected = ["exec", "--json", "--dangerously-bypass-approvals-and-sandbox",
                "--skip-git-repo-check", "--cd", config["workspace"],
                "--model", config["model"], "--config", 'model_reasoning_effort="high"']
    if arguments[:len(expected)] != expected:
        raise ValueError("Adapter arguments differ from the frozen invocation")
    tail = arguments[len(expected):]
    if tail == ["-"]:
        return None
    if len(tail) == 3 and tail[0] == "resume" and tail[2] == "-":
        session = tail[1]
        if session and all(c in "0123456789abcdef-" for c in session):
            return session
    raise ValueError("Unapproved adapter continuation or CLI option")


def run(config, prompt, *, session=None, handlers=None):
    if config.get('preflight_fixture'):
        if config.get('scored') or config.get('eda') is not None or handlers is not None:
            raise ValueError('Fixture cannot be used for scored execution or actual EDA')
        from sprint_preflight_fixture import handlers as fixture_handlers
        handlers=fixture_handlers(config)
    if config.get("scored",False):
        from capacity_admission import validate_runtime
        validate_runtime(config)
    root, private, work, project = (Path(config[k]).resolve()
                                    for k in ("record","private","workspace","project"))
    model = config["model"]
    if model not in MODELS.values():
        raise ValueError("Unapproved model")
    if root.is_relative_to(project) or private.is_relative_to(project):
        raise ValueError("Runtime evidence/account must remain outside the model project")
    backend = None
    if config.get("eda") is not None:
        if handlers is not None:
            raise ValueError("Actual EDA cannot be mixed with injected fixture callbacks")
        from capacity_backends import Backends
        eda = config["eda"]
        if set(eda) - {"task", "trial", "category"} or "task" not in eda:
            raise ValueError("Invalid controlled EDA configuration")
        stage = config.get("stage", "autonomous")
        if not re.fullmatch(r"[a-z_]+", stage):
            raise ValueError("Invalid EDA report stage")
        backend = Backends(root/"eda", feedback=work/"reports"/stage/"eda", **eda)
        handlers = backend.handlers()
    writable = tuple(config.get("writable", WRITABLE))
    if any(name not in WRITABLE for name in writable):
        raise ValueError("Invalid writable root")
    limit, active_limit = config.get("limit",1_000_000), config.get("active_seconds",5400)
    compact_at = config.get("preflight_compact_at")
    if compact_at is not None and (type(compact_at) is not int or compact_at < 1000):
        raise ValueError("Invalid explicit preflight compaction threshold")
    if not 0 < limit <= 1_000_000 or not 0 < active_limit <= 5400:
        raise ValueError("Runtime budget exceeds protocol")
    root.mkdir(parents=True, exist_ok=True)
    with (root/".invocation.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        clock_path = root/"clock.json"
        boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        clock = json.loads(clock_path.read_text()) if clock_path.exists() else dict(
            boot_id=boot_id, start=time.monotonic(), physical_seconds=0,
            active_limit=active_limit, token_limit=limit, model=model)
        if any(clock[key] != value for key,value in
               (("boot_id",boot_id),("active_limit",active_limit),("token_limit",limit),("model",model))):
            raise ValueError("Shared runtime clock/model/budget changed")
        write_json(clock_path, clock)
        remaining = active_limit-(time.monotonic()-clock["start"]-clock["physical_seconds"])
        observer = LiveUsage(private, root/"usage.json", model, limit=limit)
        observer.poll()
        if remaining <= 0 or not observer.ledger.summary()["dispatch_allowed"]:
            raise ValueError("Shared active time or Token budget exhausted")
        if session:
            from capacity_context import IsolatedCodexAdapter
            IsolatedCodexAdapter(private)._session_file_path(session)
        invocations = root/"invocations"
        invocations.mkdir(exist_ok=True)
        invocation = invocations/f"{len(list(invocations.iterdir()))+1:04d}"
        invocation.mkdir()
        invocation_start = time.monotonic()
        write_json(invocation/"request.json",dict(model=model,session=session,
            workspace=str(work), writable=writable, prompt=prompt, scored=config.get("scored",False),
            preflight_compact_at=compact_at, stage=config.get("stage","autonomous"),
            role=config.get("role","native-engineer")))
        prepare_credentials(private)
        before_tokens = observer.ledger.summary()["actual_tokens"]
        previous_physical_seconds = clock["physical_seconds"]
        with ToolRouter(work, root/"tools", private=private, writable=writable,
                        authorize=lambda: observer.ledger.summary()["dispatch_allowed"],
                        handlers=handlers,admit_usage=observer.admit) as router:
            router.budget_status=lambda: dict(observer.ledger.summary(),active_seconds_remaining=max(0,
                active_limit-(time.monotonic()-clock["start"]-previous_physical_seconds-router.physical_wait_seconds())))
            router.authorize=lambda: (observer.ledger.summary()["dispatch_allowed"] and
                                      router.budget_status()["active_seconds_remaining"]>0)
            if backend is not None:
                router.handlers=backend.handlers(deadline=lambda: time.monotonic()+router.budget_status()["active_seconds_remaining"])
            hook = shlex.join([str(Path(sys.executable).resolve()), str(router.client), "hook"])
            with (private/"config.toml").open("a") as handle:
                for kind in ("PreToolUse","PostToolUse"):
                    handle.write(f"\n[[hooks.{kind}]]\nmatcher=\".*\"\n[[hooks.{kind}.hooks]]\n"
                                 f"type=\"command\"\ncommand={json.dumps(hook)}\ntimeout=16300\n")
            flags = ["exec","--json","--skip-git-repo-check","--ignore-rules",
                     "--dangerously-bypass-hook-trust","--cd",str(work),"--model",model]
            config_values = [*permission_overrides(work,writable=writable), 'approval_policy="never"',
                'model_reasoning_effort="high"',"features.apps=false","features.multi_agent=false",
                'web_search="disabled"']
            if compact_at is not None:
                config_values.append(f"model_auto_compact_token_limit={compact_at}")
            flags += [part for item in config_values for part in ("-c",item)]
            if session:
                flags += ["resume",session]
            flags += ["-"]
            old_socket = os.environ.get("CHIP_STUDY_CHECK_SOCKET")
            os.environ["CHIP_STUDY_CHECK_SOCKET"] = str(router.socket)
            try:
                command = sandbox_command(project,work,private,["/tools/codex",*flags])
            finally:
                if old_socket is None:
                    os.environ.pop("CHIP_STUDY_CHECK_SOCKET",None)
                else:
                    os.environ["CHIP_STUDY_CHECK_SOCKET"] = old_socket
            stdout_path = invocation/"stdout.jsonl"
            with stdout_path.open("w") as stdout, (invocation/"stderr.log").open("w") as stderr:
                process = subprocess.Popen(command,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr,
                                           text=True,start_new_session=True)
                stopped_native={}
                def physical_pause(paused):
                    nonlocal stopped_native
                    from capacity_process import stop_tree,resume_tree
                    if paused:
                        if process.poll() is None:
                            try:stopped_native=stop_tree(process.pid)
                            except ProcessLookupError:
                                if process.poll() is None:raise
                    else:
                        resume_tree(stopped_native)
                        stopped_native={}
                router.physical_pause = physical_pause
                try:
                    process.stdin.write(prompt)
                    process.stdin.close()
                    remaining = active_limit-(time.monotonic()-clock["start"]-clock["physical_seconds"])
                    control = observer.wait(process,active_seconds=max(0,remaining),
                                            physical_wait_seconds=router.physical_wait_seconds)
                except BaseException:
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGTERM)
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid, signal.SIGKILL)
                            process.wait()
                    raise
                finally:
                    clock["physical_seconds"] = previous_physical_seconds+router.physical_wait_seconds()
                    write_json(clock_path,clock)
        clock["physical_seconds"] = previous_physical_seconds+router.physical_wait_seconds()
        write_json(clock_path,clock)
        try:
            error_path=root/"tools/router-error.json"
            if error_path.exists():
                raise InvalidMeasurement("Protected tool lifecycle failed: "+json.loads(error_path.read_text())["error"])
            if router.active is not None and control["reason"]=="native_exit":
                raise InvalidMeasurement("Native exit left an unfinished controlled tool")
            new_snapshots = associate_captures(observer,root/"tools/snapshots",
                interrupted=control["reason"] in ("token_budget","active_time_budget"))
        except InvalidMeasurement as error:
            try:
                observer.ledger.invalid(str(error))
            except InvalidMeasurement:
                write_json(observer.record,observer.ledger.state)
            control.update(measurement_valid=False, reason="source_association_invalid",
                           association_error=str(error))
            new_snapshots = 0
        control.update(actual_logical_tokens=observer.ledger.summary()["actual_tokens"],
            invocation_tokens=observer.ledger.summary()["actual_tokens"]-before_tokens,
            invocation_active_seconds=time.monotonic()-invocation_start-(clock["physical_seconds"]-previous_physical_seconds),
            invocation_physical_seconds=clock["physical_seconds"]-previous_physical_seconds,
            new_source_snapshots=new_snapshots,
            active_seconds=time.monotonic()-clock["start"]-clock["physical_seconds"],
            physical_seconds=clock["physical_seconds"])
        control["passed"] = (control["exit_code"] == 0 and control["measurement_valid"]
                             and control["reason"] == "native_exit")
        write_json(invocation/"result.json",control)
        return control, stdout_path


if __name__ == "__main__":
    if len(sys.argv)<3 or sys.argv[1] != "--adapter-config":
        raise SystemExit("Use the controlled adapter configuration")
    config = json.loads(Path(sys.argv[2]).read_text())
    session = adapter_arguments(sys.argv[3:],config)
    result, stdout = run(config,sys.stdin.read(),session=session)
    sys.stdout.write(stdout.read_text())
    raise SystemExit(0 if result["passed"] else 1)
