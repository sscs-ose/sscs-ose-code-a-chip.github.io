"""Viaduct relay / hub: runs inside the container, one process per request,
started by the client through `docker exec -i` (or later `ssh host docker exec`).

Reads one request {"tool", "op", "args", "timeout"?, "safe"?} as JSON on stdin and
prints one JSON reply. Hub duties, all inside the container:

  * signing:  HMAC-SHA256 with the tap's token (~/.viaduct/<tool>.token, 0600);
              tokens never leave the container
  * locking:  one writer per GUI tool at a time (flock on ~/.viaduct/<tool>.lock)
  * audit:    every request appended to /foss/designs/viaduct/.viaduct/audit.jsonl
  * safe mode: `eval`-type ops refused when ~/.viaduct/safe exists or "safe": true
  * timeouts: per-request socket timeout; on timeout the tap is asked (read-only)
              which dialogs are open; the outcome is reported as unknown and nothing
              is closed (dialogs are the designer's; see close_dialog)

tools:  klayout (JSON protocol, taps/klayout/viaduct_tap.py)
        xschem  (Tcl protocol,  taps/xschem/viaduct_tap.tcl)
        sim     (batch ngspice, container/ngspice_runner.py)
        em      (batch FastHenry, container/fasthenry_runner.py)
        verify  (batch KLayout DRC with the PDK deck, container/drc_runner.py)
        hub     (status, safe, audit)
"""
import base64
import contextlib
import fcntl
import hashlib
import hmac
import json
import os
import secrets
import socket
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import history  # noqa: E402
import interrupts  # noqa: E402

BASE_STATE = os.path.expanduser("~/.viaduct")
STATE_DIR = BASE_STATE          # set per request from "session" (live: ~/.viaduct, else ~/.viaduct/<session>)
SESSION = "live"
AUDIT = os.path.join(ROOT, ".viaduct", "audit.jsonl")
DEFAULT_TIMEOUT = float(os.environ.get("VIADUCT_TIMEOUT", "60"))
LOCK_WAIT = 30.0
UNSAFE_OPS = {("klayout", "exec_python"), ("xschem", "eval")}


class Timeout(Exception):
    pass


# ---- transport to the taps ---------------------------------------------------

def tap_info(tool):
    with open(os.path.join(STATE_DIR, tool + ".json")) as f:
        port = json.load(f)["port"]
    with open(os.path.join(STATE_DIR, tool + ".token"), "rb") as f:
        token = f.read().strip()
    return port, token


def exchange(port, line, timeout):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout) as s:
            s.sendall(line.encode() + b"\n")
            buf = b""
            while not buf.endswith(b"\n"):
                chunk = s.recv(65536)
                if not chunk:
                    break
                buf += chunk
    except socket.timeout:
        raise Timeout()
    return buf.decode().strip()


@contextlib.contextmanager
def tool_lock(tool):
    """One writer per GUI tool: concurrent agents queue instead of interleaving edits."""
    os.makedirs(STATE_DIR, mode=0o700, exist_ok=True)
    with open(os.path.join(STATE_DIR, tool + ".lock"), "w") as f:
        deadline = time.time() + LOCK_WAIT
        while True:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.time() > deadline:
                    raise RuntimeError("BUSY: another request holds the %s lock" % tool)
                time.sleep(0.1)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def tcl_quote(value):
    """Quote one value as a single Tcl word (lists become Tcl lists)."""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (list, tuple)):
        return tcl_quote(" ".join(tcl_quote(v) for v in value))
    if isinstance(value, dict):
        return tcl_quote(" ".join(tcl_quote(k) + " " + tcl_quote(v) for k, v in value.items()))
    s = str(value)
    if s == "":
        return "{}"
    # Backslash-newline is a line continuation in Tcl, so control characters
    # are written as escapes (\n), not as backslash + literal character.
    esc = {"\n": "\\n", "\t": "\\t", "\r": "\\r"}
    return "".join(esc[c] if c in esc else "\\" + c if c in ' "{}[]$\\;' else c for c in s)


PROTO = 2
IMPOSTOR = ("reply signature mismatch: something other than this session's tap answered on port %s "
            "(another process on the port, or a tap started with a different token); not trusting it")


def _mac(token, *parts):
    return hmac.new(token, "".join(parts).encode(), hashlib.sha256).hexdigest()


def _klayout(op, args, timeout, rid=""):
    port, token = tap_info("klayout")
    body = json.dumps({"op": op, "args": args, "request_id": rid, "proto": PROTO})
    nonce = secrets.token_hex(16)
    line = exchange(port, json.dumps({"nonce": nonce, "body": body, "mac": _mac(token, nonce, body)}), timeout)
    obj = json.loads(line)
    if "reply" not in obj:
        # unsigned: the tap could not authenticate the request (or is an old/foreign tap)
        return {"status": "DENIED", "error": "unsigned reply: %s" % obj.get("error", line[:200])}
    if not hmac.compare_digest(_mac(token, nonce, obj["reply"]), obj.get("mac", "")):
        return {"status": "DENIED", "error": IMPOSTOR % port}
    return json.loads(obj["reply"])


def _xschem_decode(kind, text, structured):
    if kind == "DENIED":
        return {"status": "DENIED", "error": text}
    if kind == "ERR":
        return {"status": "ERROR", "error": text}
    if kind != "OK":
        return {"status": "ERROR", "error": "bad reply kind %r" % kind}
    return {"status": "SUCCESS", "result": json.loads(text) if structured else text}


def _xschem(op, args, timeout, rid=""):
    port, token = tap_info("xschem")
    if op == "eval":
        script, structured = args["code"], False
    else:
        script, structured = "viaduct::op::%s %s" % (op, tcl_quote(args)), True
    raw = script.encode()
    nonce = secrets.token_hex(16)
    rid_field = rid or "-"
    mac = hmac.new(token, (nonce + rid_field + str(PROTO)).encode() + raw, hashlib.sha256).hexdigest()
    reply = exchange(port, "%s %s %s %s %d" % (nonce, mac, base64.b64encode(raw).decode(), rid_field, PROTO), timeout)
    parts = reply.split(" ")
    if len(parts) != 3:
        # unsigned DENIED (bad request signature / old protocol) or garbage
        return {"status": "DENIED", "error": "unsigned reply: %s" % reply[:200]}
    kind, payload, rmac = parts
    if not hmac.compare_digest(_mac(token, nonce, kind, payload), rmac):
        return {"status": "DENIED", "error": IMPOSTOR % port}
    text = base64.b64decode(payload).decode() if payload else ""
    result = _xschem_decode(kind, text, structured)
    if op == "receipt" and result["status"] == "SUCCESS" and result["result"].get("state") == "completed":
        rec = result["result"]
        orig = base64.b64decode(rec.pop("payload_b64", "") or "").decode()
        rec["reply"] = _xschem_decode(rec.pop("kind", "OK"), orig, rec.get("script", "").startswith("viaduct::op::"))
    return result


GUI = {"klayout": _klayout, "xschem": _xschem}


def _history():
    return history.History(SESSION, GUI, STATE_DIR)


def _interrupts():
    return interrupts.Interrupts(STATE_DIR, GUI, _history())


def _rebuilds(op, args):
    """Schematic paths an edit would rebuild from scratch (new_schematic replace=True)."""
    calls = [{"op": op, "args": args}] + (list(args.get("ops") or []) if op == "batch" else [])
    return [c["args"].get("path") for c in calls
            if c.get("op") == "new_schematic" and (c.get("args") or {}).get("replace")
            and not (c.get("args") or {}).get("force_rebuild") and not args.get("force_rebuild")]


def _brief(items):
    return [{k: i.get(k) for k in ("id", "kind", "time", "message", "selection", "changes", "step", "tool", "target") if i.get(k) is not None}
            for i in items]


@contextlib.contextmanager
def all_tool_locks():
    """Both GUI tools, always in the same order: checkpoints and restores see a quiet design."""
    with tool_lock("xschem"):
        with tool_lock("klayout"):
            yield


def call_gui(tool, op, args, timeout=None, rid="", actor="agent"):
    timeout = timeout or DEFAULT_TIMEOUT
    try:
        if op in ("dialogs", "close_dialog", "dismiss_dialogs", "ping", "hello", "receipt"):
            # Never queue behind a stuck request: these are how a stuck tool is diagnosed.
            return GUI[tool](op, args, timeout, rid)
        with tool_lock(tool):
            edit = history.is_edit(tool, op)
            irq = _interrupts()
            pending, paused = [], False
            if actor == "agent":
                # Designer interrupts come first: a hand edit in the GUI since Viaduct's last
                # edit is detected here; while anything is unacknowledged, edits are refused.
                try:
                    irq.detect([tool])
                    pending, paused = irq.pending()
                except Exception as e:
                    pending, paused = [], False
                    sys.stderr.write("interrupt check failed: %r\n" % e)
                if edit and (pending or paused):
                    return {"status": "INTERRUPTED",
                            "error": ("the designer has paused the session" if paused and not pending else
                                      "the designer has %d unacknowledged interrupt(s); nothing was changed" % len(pending)),
                            "interrupts": _brief(pending), "paused": paused, "plan": irq.plan(),
                            "hint": ("read the changes, acknowledge with `interrupt-ack` (MCP viaduct_interrupt_ack), "
                                     "apply the designer's instruction, then continue your plan from the modified "
                                     "design. Do not rebuild the schematic, do not undo the designer's edits."
                                     + (" The session is paused: wait for the designer's `resume`." if paused else ""))}
                if edit and tool == "xschem":
                    for path in _rebuilds(op, args):
                        steps = irq.designer_edited(path)
                        if steps:
                            return {"status": "DENIED",
                                    "error": "the designer edited %s (history steps %s); rebuilding it with "
                                             "new_schematic replace=true would erase their work" % (path, steps),
                                    "hint": "change the open schematic with set_props / place / wire instead; "
                                            "rebuild only if the designer agrees (force_rebuild=true)"}
            reply = GUI[tool](op, args, timeout, rid)
            if reply.get("status") == "SUCCESS" and edit:
                # Time scroll: the edited design becomes a new step (under the same lock).
                step = None
                try:
                    step = _history().after_edit(tool, op, rid, actor)
                    if step:
                        reply["history_step"] = step["step"]
                except Exception as e:
                    reply["history_error"] = repr(e)
                try:
                    item = irq.after_edit(tool, actor, step["step"] if step else None)
                    if item:
                        reply["interrupt_raised"] = item["id"]
                except Exception as e:
                    reply["interrupt_error"] = repr(e)
            if actor == "agent" and (pending or paused):
                reply["interrupts_pending"] = _brief(pending)
                reply["paused"] = paused
            return reply
    except Timeout:
        reply = {"status": "TIMEOUT",
                 "error": "%s did not answer %r within %gs" % (tool, op, timeout)}
        if rid:
            reply["request_id"] = rid
            reply["receipt_hint"] = "query the outcome later: receipt -t %s %s (never resend it)" % (tool, rid)
        try:
            dialogs = GUI[tool]("dialogs", {}, 5, "")
            reply["dialogs"] = dialogs.get("result")
            if dialogs.get("result"):
                reply["hint"] = ("a dialog is open and may be the designer's; show it to them. Close it only "
                                 "with their agreement: close-dialog -t %s ID --title TITLE [--action button:TEXT]" % tool)
                reply["outcome"] = "unknown: the request may still run once the dialog is closed; do not resend"
        except Exception as e:
            reply["dialogs"] = "tap not answering either: %r" % e
        return reply
    except (OSError, ValueError) as e:
        return {"status": "NO_TAP", "error": "%s tap not reachable: %s" % (tool, e)}


# ---- batch tools -------------------------------------------------------------------

def _sim_reply(result):
    if result["status"] == "COMPLETE":
        return {"status": "SUCCESS", "result": result}
    why = (result.get("errors") or [])[:3]
    if not why and not result.get("raw_files"):
        why = ["no .raw file was written: add `write <name>.raw` to the .control block"]
    if not why:
        why = ["ngspice exit code %s" % result.get("exit_code")]
    return {"status": "ERROR", "error": "; ".join(why) + " (log: %s/ngspice.log)" % result["run_dir"], "result": result}


def call_sim(op, args, timeout=None):
    import ngspice_runner
    nodes = args.get("nodes") or ["out"]
    pdk = args.get("pdk", "sky130A")
    if op == "run":
        result = ngspice_runner.run(args["netlist"], nodes=nodes, pdk=pdk)
        return _sim_reply(result)
    if op == "xschem":
        # Live mode: netlist the schematic open in xschem, simulate, then show the
        # waveforms in graphs on that same schematic.
        nl = call_gui("xschem", "netlist", {})
        if nl.get("status") != "SUCCESS":
            return nl
        result = ngspice_runner.run(nl["result"]["path"], nodes=nodes, pdk=pdk)
        reply = {"status": "SUCCESS" if result["status"] == "COMPLETE" else "ERROR", "result": result}
        if result["status"] == "COMPLETE" and args.get("live", True):
            graphs = ngspice_runner.graph_records(result, nodes, args.get("graph_box", [600, -500, 800, 360]))
            if graphs:
                raw, kind, text = graphs
                reply["xschem"] = call_gui("xschem", "show_waveforms", {"raw": raw, "type": kind, "graphs": text})
        return reply
    if op == "op":
        # Without a netlist: the schematic open in xschem, netlisted now.
        netlist = args.get("netlist")
        if not netlist:
            nl = call_gui("xschem", "netlist", {})
            if nl.get("status") != "SUCCESS":
                return nl
            netlist = nl["result"]["path"]
        result = ngspice_runner.op(netlist, pdk=pdk)
        return {"status": "SUCCESS" if result["status"] == "COMPLETE" else "ERROR", "result": result}
    if op == "sweep":
        result = ngspice_runner.sweep(args["netlist"], args.get("params"), args.get("node", "out"),
                                      pdk=pdk, fixed=args.get("fixed", {}), cases=args.get("cases"),
                                      ac=args.get("ac", "dec 40 1e8 2e11"))
        return {"status": "SUCCESS" if result["status"] == "COMPLETE" else "ERROR", "result": result}
    return {"status": "ERROR", "error": "unknown sim op %r" % op}


def call_em(op, args, timeout=None):
    import fasthenry_runner
    if op == "fasthenry":
        result = fasthenry_runner.run(args.get("params", {}), args.get("freqs_hz") or [1e9, 5e9, 10e9, 20e9],
                                      pdk=args.get("pdk", "sky130A"), mesh=args.get("mesh", "normal"))
        return {"status": "SUCCESS" if result["status"] == "COMPLETE" else "ERROR", "result": result}
    if op == "fastercap":
        import fastercap_runner
        result = fastercap_runner.run(args.get("params", {}), pdk=args.get("pdk", "sky130A"),
                                      accuracy=args.get("accuracy", 0.01))
        return {"status": "SUCCESS" if result["status"] == "COMPLETE" else "ERROR", "result": result}
    if op == "palace":
        import palace_runner
        result = palace_runner.run(args.get("params", {}), pdk=args.get("pdk", "sky130A"),
                                   fstop=args.get("fstop", 50e9), fstep=args.get("fstep", 1e9),
                                   refined_cellsize=args.get("cell", 2.5), order=args.get("order", 2),
                                   np=args.get("np", 8), substrate_ohm_cm=args.get("substrate_ohm_cm", 10.0))
        return {"status": "SUCCESS" if result["status"] == "COMPLETE" else "ERROR", "result": result}
    if op == "convergence":
        result = fasthenry_runner.convergence(args.get("params", {}), args.get("freq_hz", 10e9),
                                              pdk=args.get("pdk", "sky130A"))
        return {"status": "SUCCESS" if result["status"] == "COMPLETE" else "ERROR", "result": result}
    return {"status": "ERROR", "error": "unknown em op %r" % op}


def call_verify(op, args, timeout=None):
    import drc_runner
    if op != "drc":
        return {"status": "ERROR", "error": "unknown verify op %r (available: drc)" % op}
    pdk = args.get("pdk", "sky130A")
    run = drc_runner.new_run()
    gds = args.get("gds")
    if not gds:
        # Live mode: check exactly what is open in KLayout right now.
        cell = call_gui("klayout", "snapshot", {}).get("result", {}).get("active_cell") or "layout"
        gds = os.path.join(run[1], cell + ".gds")
        saved = call_gui("klayout", "save", {"path": gds})
        if saved.get("status") != "SUCCESS":
            return saved
    result = drc_runner.run(gds, pdk=pdk, options=args.get("options"), run=run)
    reply = {"status": "SUCCESS" if result["status"] == "COMPLETE" else "ERROR", "result": result}
    if result["status"] == "COMPLETE" and args.get("live", True) and not args.get("gds"):
        reply["klayout"] = call_gui("klayout", "show_markers", {"path": result["report"]})
    return reply


def call_hub(op, args, timeout=None, actor="agent"):
    safe_flag = os.path.join(STATE_DIR, "safe")
    if op == "safe":
        os.makedirs(STATE_DIR, mode=0o700, exist_ok=True)
        if args.get("on"):
            open(safe_flag, "w").close()
        elif os.path.exists(safe_flag):
            os.remove(safe_flag)
        return {"status": "SUCCESS", "result": {"safe": os.path.exists(safe_flag)}}
    if op == "history":
        return {"status": "SUCCESS", "result": _history().listing(args.get("n", 50))}
    if op == "history_config":
        return {"status": "SUCCESS", "result": _history().config(args.get("enabled"), args.get("thumbs"))}
    if op == "checkpoint":
        with all_tool_locks():
            e = _history().checkpoint(args.get("label", ""), args.get("actor", "designer"))
        return {"status": "SUCCESS", "result": {k: e.get(k) for k in ("step", "parent", "tools", "label", "errors")}}
    if op == "restore":
        with all_tool_locks():
            res = _history().restore(int(args["step"]), args.get("tools"))
            if actor == "designer":                          # the design changed under the agent: tell it
                res["interrupt_raised"] = _interrupts().restored(res["new_step"], int(args["step"]))
            else:
                _interrupts().rebaseline(res["new_step"])    # the agent's own restore is not a hand edit
        _history().timeline_default()
        return {"status": "SUCCESS", "result": res}
    if op == "interrupt":
        with all_tool_locks():
            sel = args.get("selection")
            if sel is None:          # what the designer has selected right now
                sel = {}
                for tool in GUI:
                    try:
                        r = GUI[tool]("selection", {}, 5, "")
                        names = [i.get("name") for i in (r.get("result") or []) if isinstance(i, dict) and i.get("name")]
                        if names:
                            sel[tool] = names
                    except Exception:
                        pass
            item = _interrupts().raise_(args.get("message", ""), bool(args.get("pause")), sel)
        _history().timeline_default()
        return {"status": "SUCCESS", "result": item}
    if op == "cockpit":       # read-only state for the cockpit page: no tool lock, no detection
        irq, h = _interrupts(), _history()
        return {"status": "SUCCESS", "result": {"session": SESSION, "interrupts": irq.status(int(args.get("n", 10))),
                                                "history": h.listing(int(args.get("steps", 40)))}}
    if op == "interrupts":
        with all_tool_locks():
            irq = _interrupts()
            irq.detect()
            return {"status": "SUCCESS", "result": irq.status(int(args.get("n", 20)))}
    if op == "interrupt_ack":
        ids = args.get("ids", "all")
        res = _interrupts().ack(ids if ids == "all" else [int(i) for i in ids], args.get("note", ""))
        _history().timeline_default()
        return {"status": "SUCCESS", "result": res}
    if op == "resume":
        res = _interrupts().resume()
        _history().timeline_default()
        return {"status": "SUCCESS", "result": res}
    if op == "plan":
        res = _interrupts().set_plan(args.get("steps"), args.get("done"), args.get("note")) \
            if any(k in args for k in ("steps", "done", "note")) else _interrupts().plan()
        _history().timeline_default()
        return {"status": "SUCCESS", "result": res}
    if op == "timeline":
        out = args.get("path") or os.path.join(ROOT, "runs", "timeline_%s.html" % SESSION)
        return {"status": "SUCCESS", "result": _history().timeline(out)}
    if op == "audit":
        n = int(args.get("n", 20))
        lines = open(AUDIT).read().splitlines()[-n:] if os.path.exists(AUDIT) else []
        return {"status": "SUCCESS", "result": [json.loads(l) for l in lines]}
    if op == "status":
        taps = {}
        for tool in GUI:
            info_file = os.path.join(STATE_DIR, tool + ".json")
            info = json.load(open(info_file)) if os.path.exists(info_file) else None
            ping = call_gui(tool, "ping", {}, 3) if info else {"status": "NO_TAP"}
            taps[tool] = {"info": info, "alive": ping.get("status") == "SUCCESS",
                          "ping": ping.get("result", ping.get("error"))}
        return {"status": "SUCCESS", "result": {
            "taps": taps, "safe": os.path.exists(safe_flag), "audit_log": AUDIT,
            "audit_entries": sum(1 for _ in open(AUDIT)) if os.path.exists(AUDIT) else 0,
            "pdk_env": os.environ.get("PDK"), "image": os.environ.get("IIC_OSIC_TOOLS_VERSION")}}
    return {"status": "ERROR", "error": "unknown hub op %r" % op}


def audit(req, reply, ms, safe):
    os.makedirs(os.path.dirname(AUDIT), exist_ok=True)
    args = json.dumps(req.get("args", {}), sort_keys=True, default=str)
    entry = {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "tool": req.get("tool"), "op": req.get("op"),
             "args_sha256": hashlib.sha256(args.encode()).hexdigest()[:16], "status": reply.get("status"),
             "ms": round(ms, 1), "safe": safe, "session": req.get("session", "live"),
             "request_id": req.get("request_id", ""), "actor": req.get("actor") or "agent"}
    with open(AUDIT, "a") as f:
        f.write(json.dumps(entry) + "\n")


def handle(req):
    tool, op, args = req.get("tool", "klayout"), req.get("op"), req.get("args", {})
    safe = bool(req.get("safe")) or os.path.exists(os.path.join(STATE_DIR, "safe"))
    if safe and (tool, op) in UNSAFE_OPS:
        return {"status": "DENIED", "error": "safe mode: %s %s is disabled (structured ops only)" % (tool, op)}, safe
    try:
        if tool in GUI:
            return call_gui(tool, op, args, req.get("timeout"), req.get("request_id", ""),
                            req.get("actor") or "agent"), safe
        if tool == "hub":
            return call_hub(op, args, req.get("timeout"), req.get("actor") or "agent"), safe
        handler = {"sim": call_sim, "em": call_em, "verify": call_verify}.get(tool)
        if handler is None:
            return {"status": "ERROR", "error": "unknown tool %r" % tool}, safe
        return handler(op, args, req.get("timeout")), safe
    except Exception as e:
        import traceback
        return {"status": "ERROR", "error": repr(e), "trace": traceback.format_exc(limit=5)}, safe


def main():
    global STATE_DIR, SESSION
    req = json.loads(sys.stdin.read())
    session = req.get("session", "live")
    SESSION = session
    STATE_DIR = BASE_STATE if session == "live" else os.path.join(BASE_STATE, session)
    t0 = time.time()
    reply, safe = handle(req)
    if req.get("op") not in ("ping",) and req.get("tool") != "hub":
        try:
            audit(req, reply, (time.time() - t0) * 1000, safe)
        except OSError:
            pass
    print(json.dumps(reply, default=str))


if __name__ == "__main__":
    main()
