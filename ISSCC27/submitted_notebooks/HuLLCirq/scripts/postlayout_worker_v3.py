"""Pinned Icarus 13 process-group supervisor for the original NPU job.

Derived by the development assistant from postlayout_worker_v1.py SHA-256
1b1dadd83b974d2414fdcf606d662f3a62ae8e98c257ef9c3117b2bf8f497e48.
This version adds pinned read-only value-change capture alongside IOPATH readback.
The original v2 supervisor is preserved byte-for-byte in its own source file.
The VPI source, binary and complete original-SDF manifest are byte-pinned.
The original worker is unchanged; both project sources use Apache-2.0.
Process identity, group termination and recovery retain the prior semantics.
This version changes admission to exact pinned Icarus commands and input hashes.

The adapter freezes this file and request bytes before execution. This module
never interprets model output or invokes a shell. Cleanup is independently
bounded and refuses an ambiguous/reused process identity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import time

VERSION = "hullcirq-postlayout-worker-v3"
TERM_SECONDS = 5.0
KILL_SECONDS = 5.0
POLL_SECONDS = 0.1
# Fixed Linux signal numbers also let Windows run the isolated fake-/proc QA.
TERM_SIGNAL = 15
KILL_SIGNAL = 9


class WorkerError(RuntimeError):
    pass


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def load_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise WorkerError("Duplicate JSON key: " + key)
            result[key] = value
        return result

    def invalid(value):
        raise WorkerError("Nonfinite JSON number: " + value)

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def atomic_json(path, value):
    pending = path.with_name(path.name + ".pending")
    pending.write_bytes(canonical(value) + b"\n")
    os.replace(pending, path)


def read_process(pid, proc_root=Path("/proc")):
    """Read Linux identity correctly even when comm contains spaces/parentheses."""
    try:
        # Linux comm is arbitrary bytes. It is discarded before numeric parsing.
        raw = (proc_root / str(pid) / "stat").read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return None
    except OSError as error:
        raise WorkerError("Cannot inspect Linux process identity: " + str(error)) from error
    try:
        number, rest = raw.split(" (", 1)
        fields = rest.rsplit(")", 1)[1].split()
        if int(number) != pid or len(fields) < 20:
            raise ValueError("Truncated/mismatched process stat")
        return {"pid": pid, "state": fields[0], "ppid": int(fields[1]),
                "process_group": int(fields[2]), "session": int(fields[3]),
                "starttime": int(fields[19])}
    except (ValueError, IndexError) as error:
        raise WorkerError("Invalid Linux process identity: " + str(pid)) from error


def live_group_members(pgid, proc_root=Path("/proc")):
    try:
        entries = list(proc_root.iterdir())
    except OSError as error:
        raise WorkerError("Cannot enumerate Linux process groups: " + str(error)) from error
    members = []
    for entry in entries:
        if not entry.name.isascii() or not entry.name.isdecimal():
            continue
        process = read_process(int(entry.name), proc_root)
        if process is not None and process["process_group"] == pgid and process["state"] not in ("Z", "X", "x"):
            members.append(process)
    return sorted(members, key=lambda item: item["pid"])


def signal_group(pgid, sig):
    try:
        os.killpg(pgid, sig)
    except ProcessLookupError:
        pass  # The subsequent /proc scan establishes whether it actually ended.
    except OSError as error:
        raise WorkerError("Cannot signal Linux process group: " + str(error)) from error


def terminate_group(pgid, *, proc_root=Path("/proc"), clock=time.monotonic,
                    sleeper=time.sleep, sender=signal_group):
    """Never equate leader exit or killpg success with group termination."""
    proof = {"process_group": pgid, "signals": [], "before": [], "after": [],
             "verified_terminated": False, "inspection_error": None}
    try:
        proof["before"] = live_group_members(pgid, proc_root)
        members = proof["before"]
        for sig, name, duration in ((TERM_SIGNAL, "SIGTERM", TERM_SECONDS), (KILL_SIGNAL, "SIGKILL", KILL_SECONDS)):
            if not members:
                break
            sender(pgid, sig)
            proof["signals"].append(name)
            deadline = clock() + duration
            while True:
                members = live_group_members(pgid, proc_root)
                if not members or clock() >= deadline:
                    break
                sleeper(min(POLL_SECONDS, max(0.0, deadline - clock())))
        proof["after"] = members
        proof["verified_terminated"] = not members
    except (WorkerError, OSError) as error:
        proof["inspection_error"] = str(error)
    return proof


def frozen_request(request_path, expected_request_sha256, expected_worker_sha256, worker_source_path):
    for value in (expected_request_sha256, expected_worker_sha256):
        if type(value) is not str or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise WorkerError("Require explicit frozen request and worker SHA256 identities.")
    request_raw = request_path.read_bytes()
    worker_raw = worker_source_path.read_bytes()
    if digest(request_raw) != expected_request_sha256 or digest(worker_raw) != expected_worker_sha256:
        raise WorkerError("Frozen request/worker bytes do not match their launch identities.")
    request = load_json(request_raw)
    if type(request) is not dict or set(request) != {"version", "argv", "cwd", "timeout_seconds", "worker_sha256", "input_files", "configuration_sha256"}:
        raise WorkerError("Require the exact fixed postlayout v3 request schema.")
    if request["version"] != VERSION or request["worker_sha256"] != expected_worker_sha256:
        raise WorkerError("Wrong frozen postlayout worker identity.")
    if request["configuration_sha256"] != digest(canonical(CONFIGURATION)):
        raise WorkerError("Require the exact pinned Icarus configuration identity.")
    timeout = request["timeout_seconds"]
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 7200:
        raise WorkerError("Require a finite bounded timeout.")
    validate_inputs(request, require_fresh=True)
    validate_tool_files()
    return request

RUNTIME_ROOT = "/mnt/c/dev/isscc2027-code-a-chip/ISSCC27/submitted_notebooks/HuLLCirq/.work/m2k/simulator_research/icarus13/installed"
WORK_ROOT = "/mnt/c/dev/isscc2027-code-a-chip/ISSCC27/submitted_notebooks/HuLLCirq/.work/m2l/dynamic"
BASE_DIRECTORY = RUNTIME_ROOT + "/usr/lib/x86_64-linux-gnu/ivl"
CONFIGURATION = {"kind": "wsl", "distribution": "Ubuntu", "executable": RUNTIME_ROOT + "/usr/bin/iverilog", "base_directory": BASE_DIRECTORY}
COMPILE_INPUTS = ("primitives.v", "original-cell-models.v", "input.nl.v", "timed-testbench.v", "input.sdf")
COMPILE_ARGV = (RUNTIME_ROOT + "/usr/bin/iverilog", "-B", BASE_DIRECTORY, "-g2005", "-gspecify", "-ginterconnect", "-Ttyp", "-s", "hullcirq_global_tb", "-o", "simulation.vvp", *COMPILE_INPUTS[:-1])
PLUGIN_SHA256 = {
    "hullcirq_readback.vpi": "3a5c10e7bcfc12e98cd37a2c16a74ffd2503385f7cb8851d8d2aea712bbe97e3",
    "hullcirq_readback.c": "5e476247443e686b95b781b6945882c79c440477ea40f4bbeab3039236ee2e08",
    "sdf-readback-manifest.tsv": "cf5d42a93b750a3cc2339c574d36db88fa58931279b95ca86a9904fd7da964da",
    'postlayout_event_capture.c': '0ac1830699df1436182803cd31d377ec355b44db4f11ba85dd5f10e5fc1726cd',
    'hullcirq_event_capture.vpi': '8f06ee2a54191de017dad678f899b7910e150444ebaede356296fdbabca56283',
    'event-signal-manifest.tsv': '46a7593396792f43238f5bf3673cde1a9b1fa9d4cddd82d1d74e8215f294fb19',
}

def simulation_argv(cwd):
    return (RUNTIME_ROOT + "/usr/bin/vvp", "-M", cwd, "-m", "hullcirq_readback", "-m", "hullcirq_event_capture", "simulation.vvp", "-sdf-verbose",
            "+hullcirq_readback_manifest=sdf-readback-manifest.tsv", "+hullcirq_event_manifest=event-signal-manifest.tsv")
TOOL_SHA256 = {'usr/bin/iverilog': 'e29c891c741689c5d06791dc57f12e3a6df2eeac010a3913f7be57e9ef493bb3', 'usr/bin/vvp': 'a97a941d8d32415537b36397e4dab991bf8087896840c0ac53dd0e4b14fd04f8', 'usr/lib/x86_64-linux-gnu/ivl/blif-s.conf': '3ce285013d51a0f632be229a513c17d4f8a314319c0e7d7fbbe53a2339580e1c', 'usr/lib/x86_64-linux-gnu/ivl/blif.conf': '3ce285013d51a0f632be229a513c17d4f8a314319c0e7d7fbbe53a2339580e1c', 'usr/lib/x86_64-linux-gnu/ivl/blif.tgt': 'a241c8677c002b1fdaf9cbcb473a4a6cdc3bb0b14c7dba4e8bdbfb615d51d773', 'usr/lib/x86_64-linux-gnu/ivl/cadpli.vpl': '24bbaaab4c0526d6d5362114659607654b8d104a901e70021245c821024cd4e9', 'usr/lib/x86_64-linux-gnu/ivl/include/constants.vams': '48cb40767dd73f50a3288c0b8b5fc779a6462b4e27f565dd9aae31a53f4a6f09', 'usr/lib/x86_64-linux-gnu/ivl/include/disciplines.vams': '6540e1f3f01b64eee3a26239c1bab6fe80db5b1fca30e336fe40189b52add231', 'usr/lib/x86_64-linux-gnu/ivl/ivl': 'bded7d31f3124a3bf1d085a610ff0071ca15bd2705e04f98f912c61c4d0c13a4', 'usr/lib/x86_64-linux-gnu/ivl/ivlpp': '4e082bfa1b1c435c928d40aac354ef66f02b8afc71f9dfcaa86732c8cd6ea8fb', 'usr/lib/x86_64-linux-gnu/ivl/null-s.conf': '8a4b79342b5d58fcd576238e928403c986bf623e5e9c63fc7e199f5c5bf57fae', 'usr/lib/x86_64-linux-gnu/ivl/null.conf': '313ef43d707cf69cabac9b02c1cee5223b7179007aa627c0963a567691751cd0', 'usr/lib/x86_64-linux-gnu/ivl/null.tgt': '181c49f2a1a1239568ed3ecd08f00c106977f716f690efbd4c09532085b03bb6', 'usr/lib/x86_64-linux-gnu/ivl/pcb-s.conf': '2f184346cab431bfa26ef1bf0a906a8d78469aae495f93974896ec952dee3657', 'usr/lib/x86_64-linux-gnu/ivl/pcb.conf': '5a84492e9e830658590cc28d5c39d8b137124ac2f6e5c111a838d91b99aa3cb9', 'usr/lib/x86_64-linux-gnu/ivl/pcb.tgt': '6e107f4eef908d5278070beb75f1670b983ca61952c94c9efdcf22cd8de6df4e', 'usr/lib/x86_64-linux-gnu/ivl/sizer-s.conf': '03a8f24468995e87b23840915b613abd339843a6ec6d0931b57ea56720ff415d', 'usr/lib/x86_64-linux-gnu/ivl/sizer.conf': '03a8f24468995e87b23840915b613abd339843a6ec6d0931b57ea56720ff415d', 'usr/lib/x86_64-linux-gnu/ivl/sizer.tgt': 'ba753c7489d2e179569374383c1acc1473ade88f0d555ca8e75cf7a43c8ab394', 'usr/lib/x86_64-linux-gnu/ivl/stub-s.conf': 'ca77cff51d74ad77e33efd589c82fb410823ad88a5933a5e4aca86251250b302', 'usr/lib/x86_64-linux-gnu/ivl/stub.conf': '03c9241decbe4502f087790fe7eaf6568fb7992788fbf56be0f69737a98c67fb', 'usr/lib/x86_64-linux-gnu/ivl/stub.tgt': 'a8b41f527afc316f2409b31f719a1d556a2e894621ea1db93d05d0539caf4812', 'usr/lib/x86_64-linux-gnu/ivl/system.vpi': '1e34912b0c1a1a49e2c214967de97d651b4871a645bc749a9232ee3ee9314926', 'usr/lib/x86_64-linux-gnu/ivl/v2005_math.vpi': 'a685d241e870677b9828756e9e3113b094de612c3bb66d5adaac8973a071a2ae', 'usr/lib/x86_64-linux-gnu/ivl/v2009.vpi': '31d46ce1afa5bfe5b036299df070061f9626ba26cdcf2416d3817c6ad3e0693b', 'usr/lib/x86_64-linux-gnu/ivl/va_math.vpi': '5e673e0ba1e659451c4e00cf78a9a0d46b897676eaa14b93fa1feb7c3f0fe611', 'usr/lib/x86_64-linux-gnu/ivl/vhdl-s.conf': 'd9b3d7de12e25e14c86738110f4e2baf3711f60a161e34ad329104f13ccabc5d', 'usr/lib/x86_64-linux-gnu/ivl/vhdl.conf': '7f8563bd0a386bedf111f5f23ce827b8efd6749cb3b104cf236358324ccd840a', 'usr/lib/x86_64-linux-gnu/ivl/vhdl.tgt': '4d6f4ab3febe96d47327dde542eabc9783ea66ff0c03ee6d47d92ac4450802a8', 'usr/lib/x86_64-linux-gnu/ivl/vhdl_sys.vpi': 'e37ee87abe16262f19a6d58d9353da4a18025b0c91eb4e870380058298da0a64', 'usr/lib/x86_64-linux-gnu/ivl/vhdl_textio.vpi': '2996df698d61fe92b7e73fbe487df90843acfe702ff9b64042b0bb4fd231b0f6', 'usr/lib/x86_64-linux-gnu/ivl/vhdlpp': 'a004975144bf03eaa3b3369ac0b6a1e732b6fd8b7a349029fa48ec1894282b8e', 'usr/lib/x86_64-linux-gnu/ivl/vlog95-s.conf': 'f4f09237dc90f1e4e58658b2bb14bb446e93619c911b8ead10cc0240f64cad51', 'usr/lib/x86_64-linux-gnu/ivl/vlog95.conf': '47d4a923819bdf601c5fa62065b6787f81d2ea64cb0e6b33c33c4e9001d356c0', 'usr/lib/x86_64-linux-gnu/ivl/vlog95.tgt': 'd68a8934cf2f1a9d4300a6572a2147aebeb13fd470d99a38104a96b954ff7001', 'usr/lib/x86_64-linux-gnu/ivl/vpi_debug.vpi': '4741c811242a55d02cfdd71987371de82de4d31968ad544ccd4a27617d628814', 'usr/lib/x86_64-linux-gnu/ivl/vvp-s.conf': '34cc3cf237ec8a86b3b740dd656a6953bbe3ff681da0dd0c7dde004c2d98dd84', 'usr/lib/x86_64-linux-gnu/ivl/vvp.conf': '6013ffb100e35d3a4656d3a24836be36bb782957c174e527c1c570ffe7aa5b41', 'usr/lib/x86_64-linux-gnu/ivl/vvp.tgt': '9dbabda1a3aa06818d1682361b04c4ba07372adeede64c3ddcba3f72ac597eb5'}

def validate_tool_files():
    for relative, expected in TOOL_SHA256.items():
        path = Path(RUNTIME_ROOT) / relative
        if not path.is_file() or digest(path.read_bytes()) != expected:
            raise WorkerError("Pinned Icarus runtime file changed: " + relative)

def validate_operation(argv, cwd):
    if type(cwd) is not str:
        raise WorkerError("Require a typed absolute isolated execution cwd.")
    if type(argv) is not list or tuple(argv) not in (COMPILE_ARGV, simulation_argv(cwd)):
        raise WorkerError("Only the exact pinned original-job Icarus compile/simulation argv are supported.")
    if (type(cwd) is not str or not cwd.startswith(WORK_ROOT + "/")
            or PurePosixPath(cwd).parent.as_posix() != WORK_ROOT
            or not re.fullmatch(r"original-job-[A-Za-z0-9_-]+", PurePosixPath(cwd).name)
            or ".." in PurePosixPath(cwd).parts or any(ord(c) < 32 for c in cwd)):
        raise WorkerError("Require the exact isolated original-job execution directory.")
    return COMPILE_INPUTS + (("simulation.vvp", *PLUGIN_SHA256) if tuple(argv) == simulation_argv(cwd) else ())

def validate_inputs(request, *, require_fresh=False):
    names = validate_operation(request["argv"], request["cwd"])
    entries = request["input_files"]
    if type(entries) is not dict or set(entries) != set(names):
        raise WorkerError("Require all exact fixed operation input hashes.")
    folder = Path(request["cwd"])
    if folder.resolve() != folder or not folder.is_dir():
        raise WorkerError("Execution directory must exist without symlink redirection.")
    if require_fresh and tuple(request["argv"]) == COMPILE_ARGV and (folder / "simulation.vvp").exists():
        raise WorkerError("Compilation refuses to overwrite an existing simulation.vvp.")
    if require_fresh and tuple(request["argv"]) == simulation_argv(request["cwd"]) and any((folder / name).exists() for name in ("hullcirq-events.tsv", "hullcirq-events-summary.json", "sdf-delay-readback.tsv")):
        raise WorkerError("Simulation refuses to overwrite retained observer outputs.")
    for name in names:
        path, expected = folder / name, entries[name]
        if (type(expected) is not str or not re.fullmatch(r"[0-9a-f]{64}", expected)
                or not path.is_file() or path.resolve().parent != folder
                or digest(path.read_bytes()) != expected):
            raise WorkerError("Frozen input bytes mismatch: " + name)
        if name in PLUGIN_SHA256 and expected != PLUGIN_SHA256[name]:
            raise WorkerError("Only the byte-pinned read-only IOPATH plugin/manifest is supported: " + name)


def boot_identity(proc_root):
    try:
        value = (proc_root / "sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
    except OSError as error:
        raise WorkerError("Cannot establish Linux boot identity.") from error
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", value):
        raise WorkerError("Invalid Linux boot identity.")
    return value


def identity_fields(request, request_sha256, worker_sha256):
    return {"version": VERSION, "argv": request["argv"], "cwd": request["cwd"],
            "request_sha256": request_sha256, "worker_sha256": worker_sha256,
            "input_files": request["input_files"], "configuration_sha256": request["configuration_sha256"]}


def cleanup_saved_group(root, binding, *, proc_root=Path("/proc"), clock=time.monotonic,
                        sleeper=time.sleep, sender=signal_group):
    """A separate host recovery invocation must prove identity before signalling."""
    proof = {**binding, "status": "Failed", "executed": False,
             "whole_process_group_terminated_on_cancel": False, "diagnostics": []}
    try:
        start_raw = (root / "process-start.json").read_bytes()
        start = load_json(start_raw)
        if any(canonical(start.get(key)) != canonical(value) for key, value in binding.items()):
            raise WorkerError("Process-start request/source identity differs from the frozen launch.")
        pgid, birth = start["process_group"], start["leader_starttime"]
        if type(pgid) is not int or pgid <= 1 or type(birth) is not int or birth <= 0:
            raise WorkerError("Invalid process-group birth identity.")
        if start["boot_id"] != boot_identity(proc_root):
            raise WorkerError("Linux restarted; the recorded process-group identity is stale.")
        members = live_group_members(pgid, proc_root)
        leader = read_process(pgid, proc_root)
        if leader is not None and (leader["starttime"] != birth or leader["process_group"] != pgid or leader["session"] != pgid):
            raise WorkerError("The recorded group leader PID was reused or changed identity.")
        if any(member["session"] != pgid or member["starttime"] < birth for member in members):
            raise WorkerError("A live group member has an incompatible session/birth identity.")
        if leader is None and members:
            checkpoint = load_json((root / "process-group.json").read_bytes())
            if checkpoint["process_start_sha256"] != digest(start_raw):
                raise WorkerError("The membership checkpoint belongs to another process start.")
            def member_identity(member):
                values = [member["pid"], member["starttime"], member["session"]]
                if any(type(value) is not int or value <= 0 for value in values):
                    raise WorkerError("A membership checkpoint has an invalid typed identity.")
                return canonical(values)
            observed = {member_identity(member) for member in checkpoint["members"]}
            if not any(member_identity(member) in observed for member in members):
                raise WorkerError("Leader exited and no previously observed live member anchors this group.")
        proof["process_start_sha256"] = digest(start_raw)
        proof["process_group"] = pgid
        proof["termination"] = terminate_group(pgid, proc_root=proc_root, clock=clock, sleeper=sleeper, sender=sender)
        proof["executed"] = True
        proof["whole_process_group_terminated_on_cancel"] = proof["termination"]["verified_terminated"]
        proof["status"] = "Cancelled" if proof["whole_process_group_terminated_on_cancel"] else "Failed"
    except (WorkerError, OSError, ValueError, KeyError, TypeError) as error:
        proof["diagnostics"].append(str(error))
    atomic_json(root / "cleanup-result.json", proof)
    return proof


def run_request(request_path, expected_request_sha256, expected_worker_sha256, *,
                worker_source_path=None, proc_root=Path("/proc"), clock=time.monotonic,
                sleeper=time.sleep, popen_factory=subprocess.Popen, sender=signal_group):
    request_path = Path(request_path).resolve()
    worker_source_path = Path(worker_source_path or __file__).resolve()
    request = frozen_request(request_path, expected_request_sha256, expected_worker_sha256, worker_source_path)
    root = request_path.parent
    if any((root / name).exists() for name in ("process-start.json", "process-result.json", "stdout.log", "stderr.log")):
        raise WorkerError("A worker launch requires a fresh directory; prior evidence is immutable.")
    binding = identity_fields(request, expected_request_sha256, expected_worker_sha256)
    result = {**binding, "status": "Failed", "executed": False, "exit_code": None,
              "process_group": None, "leader_starttime": None, "elapsed_seconds": 0.0,
              "whole_process_group_terminated_on_cancel": False, "whole_process_group_terminated": False, "termination": None,
              "supervisor_cwd": os.getcwd(), "observed_child_cwd": None, "diagnostics": []}
    started = clock()
    process = None
    try:
        boot_id = boot_identity(proc_root)
        with (root / "stdout.log").open("xb") as stdout, (root / "stderr.log").open("xb") as stderr:
            process = popen_factory(request["argv"], cwd=request["cwd"], stdout=stdout, stderr=stderr,
                                    start_new_session=True, shell=False)
            result["executed"], result["process_group"] = True, process.pid
            leader = read_process(process.pid, proc_root)
            if leader is None or leader["process_group"] != process.pid or leader["session"] != process.pid:
                raise WorkerError("Could not verify the newly isolated Linux process group.")
            result["leader_starttime"] = leader["starttime"]
            try:
                result["observed_child_cwd"] = os.readlink(proc_root / str(process.pid) / "cwd")
            except OSError:
                pass  # Popen's exact cwd remains recorded even for a fast exit.
            if result["observed_child_cwd"] not in (None, request["cwd"]):
                raise WorkerError("Actual child cwd differs from the frozen execution cwd.")
            start = {**binding, "process_group": process.pid, "leader_starttime": leader["starttime"],
                     "boot_id": boot_id, "observed_child_cwd": result["observed_child_cwd"]}
            atomic_json(root / "process-start.json", start)
            start_hash = digest((root / "process-start.json").read_bytes())
            result["process_start_sha256"] = start_hash
            previous_members = None
            while True:
                members = live_group_members(process.pid, proc_root)
                if members != previous_members:
                    atomic_json(root / "process-group.json", {"version": VERSION, "process_start_sha256": start_hash, "members": members})
                    previous_members = members
                cancelled = (root / "cancel.request").exists()
                timed_out = clock() - started >= request["timeout_seconds"]
                if cancelled or timed_out:
                    result["status"] = "Cancelled" if cancelled else "Timeout"
                    result["termination"] = terminate_group(process.pid, proc_root=proc_root, clock=clock, sleeper=sleeper, sender=sender)
                    result["whole_process_group_terminated_on_cancel"] = result["termination"]["verified_terminated"]
                    result["whole_process_group_terminated"] = result["termination"]["verified_terminated"]
                    if not result["whole_process_group_terminated_on_cancel"]:
                        result["status"] = "Failed"
                        result["diagnostics"].append("Process-group termination could not be verified.")
                    break
                if process.poll() is not None:
                    # poll may reap a leader that was live at the earlier scan.
                    # Only a fresh scan can establish remaining descendants.
                    if live_group_members(process.pid, proc_root):
                        result["termination"] = terminate_group(process.pid, proc_root=proc_root, clock=clock, sleeper=sleeper, sender=sender)
                        result["whole_process_group_terminated"] = result["termination"]["verified_terminated"]
                        result["diagnostics"].append("Leader exited with live process-group descendants; cleaned up instead of accepting completion.")
                    else:
                        result["status"] = "Completed"
                        result["whole_process_group_terminated"] = True
                    break
                sleeper(POLL_SECONDS)
            try:
                process.wait(timeout=POLL_SECONDS)
            except subprocess.TimeoutExpired:
                result["status"] = "Failed"
                result["diagnostics"].append("The group leader did not become waitable after bounded cleanup.")
            result["exit_code"] = process.returncode
    except (WorkerError, OSError, ValueError, KeyError, TypeError) as error:
        result["status"] = "Failed"
        result["diagnostics"].append(str(error))
        if process is not None:
            result["termination"] = terminate_group(process.pid, proc_root=proc_root, clock=clock, sleeper=sleeper, sender=sender)
            result["whole_process_group_terminated"] = result["termination"]["verified_terminated"]
            try:
                process.wait(timeout=POLL_SECONDS)
            except subprocess.TimeoutExpired:
                pass
            result["exit_code"] = process.returncode
    result["elapsed_seconds"] = clock() - started
    for name, path, expected in (("request", request_path, expected_request_sha256), ("worker", worker_source_path, expected_worker_sha256)):
        try:
            unchanged = digest(path.read_bytes()) == expected
        except OSError:
            unchanged = False
        result[name + "_unchanged_at_completion"] = unchanged
        if not unchanged:
            result["status"] = "Failed"
            result["diagnostics"].append("Frozen " + name + " bytes changed or disappeared during execution.")
    try:
        validate_inputs(request)
        validate_tool_files()
        result["inputs_unchanged_at_completion"] = True
        result["runtime_unchanged_at_completion"] = True
    except (WorkerError, OSError) as error:
        result["status"] = "Failed"
        result["inputs_unchanged_at_completion"] = False
        result["runtime_unchanged_at_completion"] = False
        result["diagnostics"].append(str(error))
    atomic_json(root / "process-result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("request", type=Path)
    parser.add_argument("--request-sha256", required=True)
    parser.add_argument("--worker-sha256", required=True)
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    request_path, source_path = args.request.resolve(), Path(__file__).resolve()
    try:
        if args.cleanup:
            request = frozen_request(request_path, args.request_sha256, args.worker_sha256, source_path)
            result = cleanup_saved_group(request_path.parent, identity_fields(request, args.request_sha256, args.worker_sha256))
            return 0 if result["whole_process_group_terminated_on_cancel"] else 1
        run_request(request_path, args.request_sha256, args.worker_sha256, worker_source_path=source_path)
        return 0  # The retained actual tool/group result determines acceptance.
    except (WorkerError, OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, "postlayout worker rejected launch: " + str(error) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
