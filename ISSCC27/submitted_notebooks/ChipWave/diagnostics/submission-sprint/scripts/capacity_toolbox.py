"""Shared, host-owned tool quotas and a model-tool sandbox without credentials."""
from __future__ import annotations

import fcntl
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

from study_protocol import digest, write_json

LIMITS = dict(development=20, synthesis_sta=6, physical=2)


def inspect_argv(command):
    """Only these simple read operations are free; execute argv without a shell."""
    try:
        words=shlex.split(command)
    except ValueError:
        return None
    if not words or any(w in (";", "&&", "||", "|", "&", ">", ">>", "<") for w in words):
        return None
    name=words[0]
    if name not in ("pwd","ls","cat","head","tail","wc","rg"):
        return None
    allowed={
        "pwd":set(), "ls":{"-a","-l","-h","-al","-la","-lh","-lah","-R","-d"},
        "cat":{"-n","-A"}, "head":{"-n","-c"}, "tail":{"-n","-c"},
        "wc":{"-l","-c","-w"},
        "rg":{"--files","--hidden","--no-ignore","-n","-l","-i","-w","-F","-g","--glob",
              "-m","--max-count","--count","--files-with-matches","--no-heading"}}
    value_flags={"-n","-c"} if name in ("head","tail") else {"-g","--glob","-m","--max-count"} if name=="rg" else set()
    expect=False
    for word in words[1:]:
        if expect:
            expect=False
            continue
        if word.startswith("-") and word not in allowed[name]:
            return None
        expect=word in value_flags
    return None if expect else words


def sandbox_command(workspace, command, *, simulation=False, writable=("rtl","configuration","tests","reports","build")):
    """All executable model commands have no network, account home or hidden task."""
    work=Path(workspace).resolve()
    if not work.is_dir():
        raise ValueError("Missing workspace")
    args=["/usr/bin/env","-i",shutil.which("bwrap") or "/usr/bin/bwrap",
          "--unshare-user","--unshare-pid","--unshare-ipc","--unshare-net",
          "--die-with-parent","--new-session","--proc","/proc","--dev","/dev","--tmpfs","/tmp"]
    roots={Path(p) for p in ("/usr","/bin","/lib","/lib64","/etc",sys.prefix,sys.base_prefix)}
    for root in sorted(roots,key=lambda p:(len(p.parts),str(p))):
        if not root.exists():
            continue
        resolved=root.resolve()
        if work.is_relative_to(resolved):
            raise ValueError("A tool root would expose its containing task tree")
        args+=["--ro-bind",str(resolved),str(resolved)]
        if root.is_symlink():
            args+=["--symlink",str(resolved),str(root)]
    aliases={}
    executable=Path(sys.executable)
    for _ in range(40):
        for parent in executable.parents:
            if parent.is_symlink():aliases[parent]=parent.resolve()
        if not executable.is_symlink():break
        target=executable.readlink()
        executable=target if target.is_absolute() else Path(os.path.normpath(executable.parent/target))
    for alias,target in aliases.items():
        if not any(alias.is_relative_to(root.resolve()) for root in roots) and alias not in roots:
            args+=["--symlink",str(target),str(alias)]
    # The venv executable points into the separately mounted base interpreter.
    args+=["--ro-bind",str(work),str(work)]
    for name in writable:
        path=work/name
        if path.is_symlink() or not path.resolve().is_relative_to(work):
            raise ValueError("Writable tool directory escapes workspace")
        if path.exists():
            args+=["--bind",str(path),str(path)]
    args+=["--dir","/tools", "--ro-bind",str(Path(__file__).with_name("capacity_check_help.py")),"/tools/capacity-check"]
    for name in ("rg",):
        found=shutil.which(name)
        if found:
            args+=["--ro-bind",str(Path(found).resolve()),"/tools/"+name]
    if simulation:
        compiler=Path(shutil.which("iverilog") or "").resolve()
        runtime=Path(shutil.which("vvp") or "").resolve()
        support=compiler.parent.parent/"lib/ivl"
        if not compiler.is_file() or not runtime.is_file() or not support.is_dir():
            raise ValueError("Pinned Icarus compiler/runtime/support missing")
        args+=["--ro-bind",str(compiler),"/tools/iverilog",
               "--ro-bind",str(runtime),"/tools/vvp",
               "--ro-bind",str(support),str(support)]
    # Do not expose other globally installed EDA/model launchers through /usr.
    for name in ("codex","iverilog","vvp","verilator","yosys","openroad","klayout"):
        for directory in ("/usr/bin","/usr/local/bin","/bin"):
            path=Path(directory)/name
            if path.is_file():
                args+=["--ro-bind","/dev/null",str(path)]
    args+=["--dir","/home/agent","--setenv","HOME","/home/agent",
           "--setenv","PATH",f"/tools:{Path(sys.executable).parent}:/usr/bin:/bin",
           "--unsetenv","PYTHONPATH","--unsetenv","CODEX_HOME",
           "--unsetenv","OPENAI_API_KEY","--unsetenv","OPENAI_BASE_URL",
           "--unsetenv","HTTP_PROXY","--unsetenv","HTTPS_PROXY","--unsetenv","ALL_PROXY",
           "--unsetenv","http_proxy","--unsetenv","https_proxy","--unsetenv","all_proxy",
           "--chdir",str(work),"--",*command]
    return args


class ToolBudget:
    """The agent never receives this ledger's containing directory."""
    def __init__(self, directory):
        self.directory=Path(directory)
        self.directory.mkdir(parents=True,exist_ok=True)
        self.path=self.directory/"tool-ledger.json"

    def reserve(self, kind, source_hashes):
        if kind not in LIMITS:
            raise ValueError("Unknown metered tool")
        with (self.directory/".tool-ledger.lock").open("a") as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            state=json.loads(self.path.read_text()) if self.path.exists() else dict(limits=LIMITS,attempts=[])
            if state["limits"]!=LIMITS:
                raise ValueError("Frozen tool limits changed")
            rows=state["attempts"]
            if sum(r["kind"]==kind for r in rows)>=LIMITS[kind]:
                raise ValueError("Tool quota exhausted: "+kind)
            row=dict(id=len(rows)+1,kind=kind,status="allocated",source_sha256=source_hashes,
                     monotonic_start=time.monotonic())
            rows.append(row)
            write_json(self.path,state)
            return row["id"]

    def finish(self, identity, status, evidence):
        if status not in ("passed","failed","timeout","infrastructure_error"):
            raise ValueError("Explicit terminal state required")
        with (self.directory/".tool-ledger.lock").open("a") as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            state=json.loads(self.path.read_text())
            row=next(r for r in state["attempts"] if r["id"]==identity)
            if row["status"]!="allocated":
                raise ValueError("Terminal tool attempts are immutable")
            row.update(status=status,evidence=evidence,monotonic_end=time.monotonic())
            write_json(self.path,state)


def source_hashes(workspace):
    root=Path(workspace).resolve()
    files={}
    for directory in ("rtl","configuration"):
        for path in sorted((root/directory).rglob("*")):
            if path.is_symlink():
                raise ValueError("Source/configuration symlinks are forbidden")
            if path.is_file():
                if not path.resolve().is_relative_to(root):
                    raise ValueError("Source escapes workspace")
                files[str(path.relative_to(root))]=digest(path)
    return files


def execute_development(workspace, ledger, command, *, simulation=True, timeout=120,
                        writable=("rtl","configuration","tests","reports","build")):
    budget=ToolBudget(ledger)
    before=source_hashes(workspace)
    identity=budget.reserve("development",before)
    output=budget.directory/f"tool-{identity:04d}"
    output.mkdir()
    start=time.monotonic()
    status="infrastructure_error"
    try:
        result=subprocess.run(sandbox_command(workspace,["/bin/bash","-c",command],
            simulation=simulation, writable=writable),
            text=True,capture_output=True,timeout=timeout)
        text=result.stdout+result.stderr
        stable=source_hashes(workspace)==before
        status="passed" if result.returncode==0 and stable else "failed"
        code=result.returncode if stable else result.returncode or 1
        if not stable:
            text += "\nCheck invalid: RTL/configuration changed during tool execution; use scoped patches for edits.\n"
    except subprocess.TimeoutExpired:
        text="Tool deadline exceeded; isolated process namespace terminated."
        stable=False;code=124;status="timeout"
    except Exception as error:
        text=type(error).__name__+": "+str(error)
        stable=False;code=2
    (output/"output.log").write_text(text)
    row=dict(id=identity,status=status,exit_code=code,source_stable=stable,
             elapsed_seconds=time.monotonic()-start,source_sha256=before)
    write_json(output/"result.json",row)
    budget.finish(identity,status,str(output/"result.json"))
    return row,text
