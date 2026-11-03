"""Native hook bridge to host-owned, isolated and metered development tools."""
from __future__ import annotations

import json
import hashlib
import os
import re
import shlex
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from capacity_toolbox import ToolBudget, execute_development, inspect_argv, sandbox_command, source_hashes
from study_protocol import digest, write_json

WRITABLE = ("rtl", "configuration", "tests", "reports", "build")

CLIENT = r'''import json,socket,sys
from pathlib import Path
if sys.argv[1]=='result':
 reply=json.loads(Path(sys.argv[2]).read_text())
 print(reply['output'],end='')
 raise SystemExit(reply['exit_code'])
event=json.load(sys.stdin)
try:
 with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
  connection.connect('/run/study-check.sock')
  connection.sendall(json.dumps(event).encode()+b'\n')
  connection.shutdown(socket.SHUT_WR)
  chunks=[]
  while True:
   chunk=connection.recv(65536)
   if not chunk:break
   chunks.append(chunk)
 reply=json.loads(b''.join(chunks))
except Exception:
 if event.get('hook_event_name')=='PreToolUse':
  reply={'hookSpecificOutput':{'hookEventName':'PreToolUse','permissionDecision':'deny',
   'permissionDecisionReason':'Protected tool controller unavailable; call rejected.'}}
 else:
  reply={'continue':False,'stopReason':'Protected tool observer unavailable.'}
print(json.dumps(reply))
'''


def patch_targets(workspace, patch, writable=WRITABLE):
    root = Path(workspace).resolve()
    if not patch.startswith("*** Begin Patch\n") or not patch.rstrip().endswith("*** End Patch"):
        raise ValueError("Invalid patch envelope")
    names = re.findall(r"^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+)$", patch, re.M)
    if not names:
        raise ValueError("Patch has no declared targets")
    for name in names:
        path = Path(name)
        path = path if path.is_absolute() else root/path
        if not path.resolve().is_relative_to(root):
            raise ValueError("Patch escapes workspace")
        relative = path.relative_to(root)
        if not relative.parts or relative.parts[0] not in writable or ".." in relative.parts:
            raise ValueError("Patch touches frozen inputs or runtime state")
        if any(p.is_symlink() for p in (path, *path.parents) if p.is_relative_to(root)):
            raise ValueError("Patch traverses a symlink")
    return names


class ToolRouter:
    def __init__(self, workspace, ledger, *, authorize, handlers=None, writable=WRITABLE,
                 private=None, admit_usage=None):
        self.workspace, self.ledger = Path(workspace).resolve(), Path(ledger).resolve()
        if self.ledger.is_relative_to(self.workspace):
            raise ValueError("Tool evidence must stay outside the model workspace")
        self.ledger.mkdir(parents=True, exist_ok=True)
        self.authorize, self.handlers, self.writable = authorize, handlers or {}, writable
        self.private = Path(private).resolve() if private else None
        self.admit_usage = admit_usage
        self.physical_pause = lambda paused: None
        self.budget_status = lambda: {"dispatch_allowed": bool(self.authorize())}
        self.admissions = {}
        self.deterministic_inputs = {}
        self.parents = {}
        self.active = None
        self.lock = threading.RLock()
        self.completed = set()
        self.physical_started = None
        self.physical_elapsed = 0.0
        # Git worktrees omit empty directories; native write grants need their roots.
        for name in WRITABLE:
            path = self.workspace/name
            if path.is_symlink():
                raise ValueError("Controlled workspace root cannot be a symlink")
            path.mkdir(exist_ok=True)
        self.client = self.workspace/"tools/capacity_bridge.py"
        self.responses = self.workspace/"tools/.capacity-results"
        self.client.parent.mkdir(parents=True, exist_ok=True)
        if self.client.exists() and self.client.read_text() != CLIENT:
            raise ValueError("Existing tool bridge differs")
        self.client.write_text(CLIENT)
        self.responses.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="capacity-router-")
        self.socket = Path(self.temporary.name)/"socket"
        owner = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                try:
                    raw = self.rfile.readline(2_000_001)
                    if len(raw) > 2_000_000 or not raw.endswith(b"\n"):
                        raise ValueError("Invalid hook payload")
                    reply = owner.handle(json.loads(raw))
                except Exception as error:
                    reason = type(error).__name__+": "+str(error)
                    write_json(owner.ledger/"router-error.json", dict(error=reason))
                    reply = ({"continue": False, "stopReason": reason}
                             if "raw" in locals() and b'"PostToolUse"' in raw else owner.deny(reason))
                try:
                    self.wfile.write(json.dumps(reply).encode())
                except BrokenPipeError:
                    pass

        self.server = socketserver.ThreadingUnixStreamServer(str(self.socket), Handler)
        # Accepted EDA must finish and record its result even after the model stops.
        self.server.daemon_threads = False
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()
        self.temporary.cleanup()

    @staticmethod
    def deny(reason):
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                "permissionDecision": "deny", "permissionDecisionReason": reason}}

    def physical_wait_seconds(self):
        with self.lock:
            return self.physical_elapsed + (time.monotonic()-self.physical_started
                                            if self.physical_started is not None else 0)

    def capture(self, call, event, *, before_tool=False, completed=False):
        parent = (self.parents[call] if completed else self.parent_witness(event)) if self.private else None
        if parent and parent["parent_call_id"] != self.parents[call]["parent_call_id"]:
            raise ValueError("Tool changed its model response owner")
        hashes = source_hashes(self.workspace)
        folder = self.ledger/"snapshots"/call
        folder.mkdir(parents=True)
        for relative, expected in hashes.items():
            source = self.workspace/relative
            target = folder/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
            if digest(target) != expected:
                raise ValueError("Source changed during protected snapshot")
        record = dict(call_id=call, session=event["session_id"], source_sha256=hashes,
                      capture_monotonic=time.monotonic(), usage_associated=False,
                      capture_phase="before_deterministic_tool" if before_tool else "after_tool")
        if parent:
            record.update(parent_call_id=parent["parent_call_id"],
                          transcript_before=self.parents[call], transcript_after=parent)
        if call in self.admissions:
            record["response_admission"] = self.admissions[call]
        if completed and self.private and self.admit_usage is not None:
            paths = list((self.private/"sessions").rglob("*-"+event["session_id"]+".jsonl"))
            if len(paths) != 1 or paths[0].is_symlink():
                raise ValueError("No unique completion transcript")
            data = paths[0].read_bytes()
            data = data[:data.rfind(b"\n")+1]
            if len(data)<parent["bytes"] or hashlib.sha256(data[:parent["bytes"]]).hexdigest()!=parent["sha256"]:
                raise ValueError("Original admitted response changed before tool completion")
            record.update(capture_phase="after_controlled_tool",
                completion_fence=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
        write_json(folder/"capture.json", record)
        return folder

    def parent_witness(self, event):
        """Hooks inside code-mode exec have their own IDs; bind to the open response."""
        paths = list((self.private/"sessions").rglob("*-"+event["session_id"]+".jsonl"))
        if len(paths) != 1 or paths[0].is_symlink():
            raise ValueError("No unique protected transcript for hook")
        data = paths[0].read_bytes()
        if not data.endswith(b"\n"):
            raise ValueError("Incomplete transcript at tool boundary")
        before = self.parents.get(event["tool_use_id"])
        if before and hashlib.sha256(data[:before["bytes"]]).hexdigest() != before["sha256"]:
            raise ValueError("Transcript prefix changed during tool execution")
        pending, records, offset = {}, [], 0
        for line in data.splitlines(keepends=True):
            row = json.loads(line)
            position = offset
            offset += len(line)
            if row.get("type") == "token_usage_record":
                records.append((position,row["payload"].get("response_id")))
            if row.get("type") != "response_item":
                continue
            item = row["payload"]
            if item.get("type") in ("function_call", "custom_tool_call"):
                identity = item.get("call_id")
                if not identity or identity in pending:
                    raise ValueError("Invalid native parent identity")
                pending[identity] = position
            elif item.get("type") in ("function_call_output", "custom_tool_call_output"):
                pending.pop(item.get("call_id"),None)
        if len(pending) != 1:
            raise ValueError("Ambiguous concurrent parent calls")
        parent, start = next(iter(pending.items()))
        usage = [(position,identity) for position,identity in records if position>start]
        if len(usage)>1:
            raise ValueError("Ambiguous response usage for pending parent")
        return dict(parent_call_id=parent, bytes=len(data),
                    sha256=hashlib.sha256(data).hexdigest(),
                    usage_event_key="byte-"+str(usage[0][0]) if usage else None,
                    response_id=usage[0][1] if usage else None)

    def await_admission(self,event):
        deadline = time.monotonic()+10
        while time.monotonic()<deadline:
            witness = self.parent_witness(event)
            if witness["parent_call_id"] != self.parents[event["tool_use_id"]]["parent_call_id"]:
                raise ValueError("Parent changed before usage admission")
            if witness["usage_event_key"]:
                admitted = self.admit_usage(event["session_id"],witness["usage_event_key"])
                if admitted is not None:
                    return dict(admitted,parent_call_id=witness["parent_call_id"],
                                response_id=witness["response_id"],event_key=witness["usage_event_key"])
            if not self.authorize():
                raise ValueError("Response exceeded shared budget before tool admission")
            time.sleep(.01)
        raise ValueError("Native response usage unavailable before tool execution")

    def handle(self, event):
        kind, tool, call = event.get("hook_event_name"), event.get("tool_name"), event.get("tool_use_id")
        if kind not in ("PreToolUse", "PostToolUse"):
            return {}
        if not isinstance(call, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", call):
            return self.deny("Missing or unsafe native tool identity")
        if not event.get("session_id") or Path(event.get("cwd", "")).resolve() != self.workspace:
            return self.deny("Hook belongs to another context/workspace")
        with self.lock:
            if kind == "PostToolUse":
                if self.active != call:
                    # Denied calls do not own the active source snapshot.
                    return {}
                if call in self.deterministic_inputs:
                    if source_hashes(self.workspace)!=self.deterministic_inputs[call]:
                        raise ValueError("Source changed while deterministic EDA was running")
                else:
                    self.capture(call, event, completed=True)
                self.completed.add(call)
                self.active = None
                return {}
            if not self.authorize():
                return self.deny("Shared budget is exhausted or measurement invalid")
            if self.active is not None:
                return self.deny("Finish the current tool before starting another")
            if call in self.completed or (self.ledger/(call+"-request.json")).exists():
                return self.deny("Native tool identity reused")
            if self.private:
                self.parents[call] = self.parent_witness(event)
            command = (event.get("tool_input") or {}).get("command")
            if tool not in ("Bash", "apply_patch") or not isinstance(command, str):
                return self.deny("Only controlled shell and scoped source patches are allowed")
            if tool == "apply_patch":
                patch_targets(self.workspace, command, self.writable)
            self.active = call
            write_json(self.ledger/(call+"-request.json"), event)
        if self.admit_usage is not None:
            try:
                self.admissions[call] = self.await_admission(event)
                write_json(self.ledger/(call+"-admission.json"),self.admissions[call])
            except Exception as error:
                with self.lock:
                    self.active = None
                    self.completed.add(call)
                write_json(self.ledger/(call+"-admission-denied.json"),dict(reason=str(error)))
                return self.deny(str(error))
        if tool == "apply_patch":
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}
        try:
            words = shlex.split(command)
            if words == ["capacity-check", "status"]:
                budget=ToolBudget(self.ledger)
                state=json.loads(budget.path.read_text()) if budget.path.exists() else {"attempts":[]}
                from capacity_toolbox import LIMITS
                counts={kind:sum(r["kind"]==kind for r in state["attempts"]) for kind in LIMITS}
                result=dict(exit_code=0,output=json.dumps(dict(self.budget_status(),
                    tool_limits=LIMITS,tool_attempts=counts,tool_remaining={k:LIMITS[k]-counts[k] for k in LIMITS})))
            elif words in (["capacity-check", "synth"], ["capacity-check", "physical"], ["capacity-check", "integration"]):
                operation = {"synth":"synthesis_sta","physical":"physical","integration":"development"}[words[1]]
                if operation not in self.handlers:
                    raise ValueError("This preflight has no "+operation+" backend")
                budget = ToolBudget(self.ledger)
                identity = budget.reserve(operation, source_hashes(self.workspace))
                before = time.monotonic()
                if operation == "physical":
                    with self.lock:
                        self.physical_started = before
                try:
                    frozen = self.capture(call,event,before_tool=True)
                    self.deterministic_inputs[call] = source_hashes(frozen)
                    if operation == "physical":
                        self.physical_pause(True)
                    result = self.handlers[operation](frozen, identity)
                    if source_hashes(frozen)!=self.deterministic_inputs[call]:
                        raise ValueError("Deterministic backend modified its frozen input")
                    budget.finish(identity, result["status"], result["evidence"])
                except Exception as error:
                    result = dict(exit_code=2, output=type(error).__name__+": "+str(error)+"\n")
                    budget.finish(identity, "infrastructure_error", result["output"])
                finally:
                    if operation == "physical":
                        self.physical_pause(False)
                        with self.lock:
                            self.physical_elapsed += time.monotonic()-before
                            self.physical_started = None
            elif inspect_argv(command) is not None:
                completed = subprocess.run(sandbox_command(self.workspace, inspect_argv(command),
                    writable=()), text=True, capture_output=True, timeout=30)
                result = dict(exit_code=completed.returncode, output=completed.stdout+completed.stderr)
            else:
                row, output = execute_development(self.workspace, self.ledger, command,
                    writable=self.writable,timeout=min(120,self.budget_status().get("active_seconds_remaining",120)))
                result = dict(exit_code=row["exit_code"], output=output)
        except Exception as error:
            result = dict(exit_code=2, output=type(error).__name__+": "+str(error)+"\n")
        response = self.responses/(call+".json")
        write_json(response, result)
        write_json(self.ledger/(call+"-result.json"), dict(result_sha256=digest(response),
                                                        source_sha256=source_hashes(self.workspace)))
        # Host work is finished; the native replacement only reads its immutable result.
        with self.lock:
            if call in self.deterministic_inputs:
                if source_hashes(self.workspace)!=self.deterministic_inputs[call]:
                    raise ValueError("Source changed while deterministic tool ran")
            else:
                self.capture(call,event,completed=True)
            self.completed.add(call)
            self.active = None
        rewrite = shlex.join([str(Path(sys.executable).resolve()), str(self.client), "result", str(response)])
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow",
                                       "updatedInput": {"command": rewrite}}}


def permission_overrides(workspace, *, binary_directory="/tools", writable=WRITABLE):
    """Native tools remain restricted even if a hook crashes; hooks run outside it."""
    root = Path(workspace).resolve()
    policy = {":minimal": "read", binary_directory: "read", "/codex-resources": "read", str(root): "read",
              str(Path(sys.prefix).resolve()): "read", str(Path(sys.base_prefix).resolve()): "read"}
    policy.update({str(root/name): "write" for name in writable})
    policy[str(root/"tools")] = "read"
    encoded = "{"+",".join(json.dumps(k)+"="+json.dumps(v) for k, v in policy.items())+"}"
    return ['default_permissions="capacity"', "permissions.capacity.filesystem="+encoded,
            "permissions.capacity.network.enabled=false", 'shell_environment_policy.inherit="none"',
            'shell_environment_policy.set={PATH="/usr/bin:/bin"}']
