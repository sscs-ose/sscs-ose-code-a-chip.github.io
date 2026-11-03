"""viaduct CLI.  python -m viaduct.cli <command> ...   (or: python client.py <command> ...)

Lifecycle      init | install | start | stop [--force] | restart | status
Hub            safe on|off | audit [-n N]
Interrupts     interrupt "INSTRUCTION" [--pause] (designer) | resume (designer) | interrupts |
               interrupt-ack [ID ..] [--note T] (agent) | plan [show | set STEP .. | done N | note TEXT]
               cockpit [--port 18090] (designer's page: desktop, interrupts, plan, time scroll)
History        history [-n N] | checkpoint [LABEL] | restore STEP [--tools xschem klayout] |
               timeline (HTML with a screenshot per step) | history-config [--on|--off] [--thumbs|--no-thumbs]
Any GUI tool   -t klayout|xschem:  batch OPS.json (one request: [{"op":..,"args":{..}},..]) |
               ping | hello | receipt REQUEST_ID (outcome of a timed-out request; never resend) |
               snapshot | selection | dialogs (read-only) |
               close-dialog ID --title TITLE [--action close|button:TEXT] (only with the designer's OK) |
               dismiss-dialog --all (legacy bulk close, the designer's dialogs too) |
               screenshot [--out P] | zoom-fit | reload | eval CODE | load FILE
KLayout        new-layout CELL | open PATH | save PATH | windows | hierarchy |
               use-library [--device tcoil] | tcoil --set k=v.. | set [NAME] --set k=v.. |
               describe [--name N] | annotate --set L1=.. --run-id ID | add-box L D x1 y1 x2 y2 |
               add-label TEXT x y L [D]
xschem         -t xschem new-schematic PATH [--replace] | open PATH | place SYM x y [--props ..] |
               modify PATH | wire x1 y1 x2 y2 .. | set NAME --set k=v.. | describe | netlist | save |
               pins NAME | wire-pins A PIN_A B PIN_B | label-pin NAME PIN NET [--length 40] |
               connectivity | check   (floating pins, label-only / single-pin nets)
ngspice        sim NETLIST [--nodes out ..] | simulate [--nodes ..] [--no-live] |
               sim-op [NETLIST]   (per-MOSFET operating point; default: the open schematic) |
               sweep NETLIST --param NAME=v1,v2,.. [--fixed NAME=v ..] [--node out]
EM             em [--set k=v ..] [--freqs 1e9 1e10 ..] [--mesh coarse|normal|fine] |
               em-convergence [--set ..] [--freq 1e10] | cap [--set k=v ..]   (FasterCap parasitic C) |
               fullwave [--set k=v ..] [--fstop 5e10] [--cell 2.5] [--np 8]   (Palace FEM, slow)
Verify         drc [--gds PATH] [--no-live] [--opt feol=false ..]   (default: the open KLayout layout)
Agents         mcp     (stdio MCP server exposing the same operations)

Use PowerShell or cmd, not Git Bash (Git Bash rewrites /foss/... arguments).
"""
import argparse
import json
import sys
from pathlib import Path

from . import Viaduct, Result
from .transport import Config


def kv(pairs, numeric=True):
    out = {}
    for pair in pairs or []:
        key, _, value = pair.partition("=")
        if numeric:
            try:
                value = float(value)
            except ValueError:
                pass
        out[key] = value
    return out


def build_parser():
    p = argparse.ArgumentParser(prog="viaduct", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-t", "--tool", choices=("klayout", "xschem"), default="klayout")
    p.add_argument("--safe", action="store_true", help="refuse eval-type ops for this call")
    p.add_argument("--full", action="store_true", help="print complete results (logs, vector lists)")
    p.add_argument("--timeout", type=float, help="seconds to wait for a GUI tool (default 60)")
    p.add_argument("--mode", choices=("live", "headless"), default="live",
                   help="live: the noVNC desktop; headless: same tools on an invisible Xvfb display")
    sub = p.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("init")
    for k in ("distro", "container", "remote_dir", "local_dir", "pdk", "novnc_url"):
        q.add_argument("--" + k.replace("_", "-"))
    sub.add_parser("install")
    q = sub.add_parser("start")
    q.add_argument("--tools", nargs="+", default=["klayout", "xschem"])
    q = sub.add_parser("stop")
    q.add_argument("--tools", nargs="+", default=["klayout", "xschem"])
    q.add_argument("--force", action="store_true", help="discard unsaved edits")
    q = sub.add_parser("restart")
    q.add_argument("--tools", nargs="+", default=["klayout", "xschem"])
    q.add_argument("--force", action="store_true")
    sub.add_parser("status")
    sub.add_parser("safe").add_argument("state", choices=("on", "off"))
    sub.add_parser("audit").add_argument("-n", type=int, default=20)
    q = sub.add_parser("interrupt")
    q.add_argument("message")
    q.add_argument("--pause", action="store_true", help="block the agent's edits until resume")
    sub.add_parser("resume")
    sub.add_parser("cockpit").add_argument("--port", type=int, default=18090)
    sub.add_parser("interrupts").add_argument("-n", type=int, default=20)
    q = sub.add_parser("interrupt-ack")
    q.add_argument("ids", nargs="*", type=int)
    q.add_argument("--note", default="")
    q = sub.add_parser("plan")
    q.add_argument("action", nargs="?", default="show", choices=("show", "set", "done", "note"))
    q.add_argument("values", nargs="*")
    sub.add_parser("history").add_argument("-n", type=int, default=50)
    sub.add_parser("checkpoint").add_argument("label", nargs="?", default="")
    q = sub.add_parser("restore")
    q.add_argument("step", type=int)
    q.add_argument("--tools", nargs="+", choices=("xschem", "klayout"))
    sub.add_parser("timeline")
    q = sub.add_parser("history-config")
    q.add_argument("--on", dest="enabled", action="store_true", default=None)
    q.add_argument("--off", dest="enabled", action="store_false")
    q.add_argument("--thumbs", dest="thumbs", action="store_true", default=None)
    q.add_argument("--no-thumbs", dest="thumbs", action="store_false")
    q = sub.add_parser("close-dialog")
    q.add_argument("id")
    q.add_argument("--title", required=True, help="exact current title, from `dialogs`")
    q.add_argument("--action", default="close", help='"close" or "button:<text>"')
    q = sub.add_parser("dismiss-dialog")
    q.add_argument("--all", action="store_true", help="really close every dialog, including the designer's")
    sub.add_parser("receipt").add_argument("request_id")
    sub.add_parser("modify").add_argument("path")
    sub.add_parser("pins").add_argument("name")
    q = sub.add_parser("wire-pins")
    for a in ("a", "pin_a", "b", "pin_b"):
        q.add_argument(a)
    q = sub.add_parser("label-pin")
    for a in ("name", "pin", "net"):
        q.add_argument(a)
    q.add_argument("--length", type=float, default=40)
    for name in ("ping", "hello", "snapshot", "selection", "dialogs", "zoom-fit", "reload",
                 "windows", "hierarchy", "netlist", "connectivity", "check"):
        sub.add_parser(name)
    sub.add_parser("eval").add_argument("code")
    sub.add_parser("load").add_argument("file", type=Path)
    sub.add_parser("screenshot").add_argument("--out")
    sub.add_parser("new-layout").add_argument("cell", nargs="?", default="TOP")
    sub.add_parser("open").add_argument("path")
    sub.add_parser("save").add_argument("path", nargs="?")
    sub.add_parser("use-library").add_argument("--device", default="tcoil")
    q = sub.add_parser("tcoil")
    q.add_argument("--name", default="DUT")
    q.add_argument("--set", nargs="*", metavar="KEY=VALUE")
    q = sub.add_parser("set")
    q.add_argument("name", nargs="?", default="DUT")
    q.add_argument("--set", nargs="*", metavar="KEY=VALUE")
    sub.add_parser("describe").add_argument("--name", default="DUT")
    q = sub.add_parser("annotate")
    q.add_argument("--name", default="DUT")
    q.add_argument("--set", nargs="*", metavar="L1=..")
    q.add_argument("--run-id", default="")
    q = sub.add_parser("add-box")
    for a in ("layer", "datatype"):
        q.add_argument(a, type=int)
    for a in ("x1", "y1", "x2", "y2"):
        q.add_argument(a, type=float)
    q = sub.add_parser("add-label")
    q.add_argument("text")
    q.add_argument("x", type=float)
    q.add_argument("y", type=float)
    q.add_argument("layer", type=int)
    q.add_argument("datatype", type=int, nargs="?", default=5)
    q = sub.add_parser("new-schematic")
    q.add_argument("path")
    q.add_argument("--replace", action="store_true")
    q = sub.add_parser("place")
    q.add_argument("symbol")
    q.add_argument("x", type=float)
    q.add_argument("y", type=float)
    q.add_argument("--rot", type=int, default=0)
    q.add_argument("--flip", type=int, default=0)
    q.add_argument("--props", default="")
    sub.add_parser("wire").add_argument("points", type=float, nargs="+")
    q = sub.add_parser("sim")
    q.add_argument("netlist")
    q.add_argument("--nodes", nargs="+", default=["out"])
    q = sub.add_parser("simulate")
    q.add_argument("--nodes", nargs="+", default=["out"])
    q.add_argument("--no-live", action="store_true")
    sub.add_parser("sim-op").add_argument("netlist", nargs="?", help="default: the schematic open in xschem")
    q = sub.add_parser("sweep")
    q.add_argument("netlist")
    q.add_argument("--param", nargs="+", required=True, metavar="NAME=v1,v2,..")
    q.add_argument("--fixed", nargs="*", metavar="NAME=v")
    q.add_argument("--node", default="out")
    q = sub.add_parser("em")
    q.add_argument("--set", nargs="*", metavar="KEY=VALUE")
    q.add_argument("--freqs", nargs="+", type=float, default=[1e9, 5e9, 10e9, 20e9])
    q.add_argument("--mesh", choices=("coarse", "normal", "fine"), default="normal")
    q = sub.add_parser("em-convergence")
    q.add_argument("--set", nargs="*", metavar="KEY=VALUE")
    q.add_argument("--freq", type=float, default=10e9)
    q = sub.add_parser("drc")
    q.add_argument("--gds")
    q.add_argument("--no-live", action="store_true")
    q.add_argument("--opt", nargs="*", metavar="NAME=VALUE")
    q = sub.add_parser("cap")
    q.add_argument("--set", nargs="*", metavar="KEY=VALUE")
    q.add_argument("--accuracy", type=float, default=0.01)
    q = sub.add_parser("fullwave")
    q.add_argument("--set", nargs="*", metavar="KEY=VALUE")
    q.add_argument("--fstop", type=float, default=50e9)
    q.add_argument("--fstep", type=float, default=1e9)
    q.add_argument("--cell", type=float, default=2.5)
    q.add_argument("--order", type=int, default=2)
    q.add_argument("--np", type=int, default=8)
    q.add_argument("--substrate-ohm-cm", type=float, default=10.0)
    sub.add_parser("batch").add_argument("file", type=Path, help='JSON list [{"op": name, "args": {...}}, ...]')
    sub.add_parser("mcp")
    return p


def run(a, vd):
    t = getattr(vd, a.tool)
    xs = a.tool == "xschem"
    c = a.cmd
    if c == "init":
        cfg = Config.load()
        for k in ("distro", "container", "remote_dir", "local_dir", "pdk", "novnc_url"):
            if getattr(a, k):
                setattr(cfg, k, getattr(a, k))
        return Result("SUCCESS", result={"config": str(cfg.save()), **cfg.__dict__})
    if c == "install":
        return vd.install()
    if c == "start":
        return vd.start(a.tools)
    if c == "stop":
        return vd.stop(a.tools, a.force)
    if c == "restart":
        vd.stop(a.tools, a.force)
        import time
        time.sleep(3)
        return vd.start(a.tools)
    if c == "status":
        state = vd.transport.docker(["ps", "-a", "--filter", "name=^/%s$" % vd.cfg.container,
                                     "--format", "{{.Status}}"]).stdout.strip()
        r = vd.hub.status()
        if r.ok:
            r.result["container"] = state or "missing"
            r.result["novnc"] = vd.cfg.novnc_url
        return r
    if c == "safe":
        return vd.hub.safe(a.state == "on")
    if c == "audit":
        return vd.hub.audit(a.n)
    if c == "interrupt":
        vd.actor = vd.actor or "designer"
        return vd.interrupts.send(a.message, a.pause)
    if c == "resume":
        vd.actor = vd.actor or "designer"
        return vd.interrupts.resume()
    if c == "interrupts":
        return vd.interrupts.status(a.n)
    if c == "interrupt-ack":
        return vd.interrupts.ack(a.ids or "all", a.note)
    if c == "plan":
        if a.action == "set":
            return vd.interrupts.plan(steps=a.values)
        if a.action == "done":
            return vd.interrupts.plan(done=int(a.values[0]))
        if a.action == "note":
            return vd.interrupts.plan(note=" ".join(a.values))
        return vd.interrupts.plan()
    if c == "history":
        return vd.history.list(a.n)
    if c == "checkpoint":
        return vd.history.checkpoint(a.label)
    if c == "restore":
        return vd.history.restore(a.step, a.tools)
    if c == "timeline":
        return vd.history.timeline()
    if c == "history-config":
        return vd.history.config(a.enabled, a.thumbs)
    if c == "close-dialog":
        return t.close_dialog(a.id, a.title, a.action)
    if c == "dismiss-dialog":
        return t.dismiss_dialogs(confirm_all=a.all)
    if c in ("ping", "hello", "snapshot", "selection", "dialogs", "reload", "windows", "hierarchy", "netlist",
             "connectivity", "check"):
        return t.call(c)
    if c == "receipt":
        return t.receipt(a.request_id)
    if c == "modify":
        return vd.xschem.modify(a.path)
    if c == "pins":
        return vd.xschem.pins(a.name)
    if c == "wire-pins":
        return vd.xschem.wire_pins(a.a, a.pin_a, a.b, a.pin_b)
    if c == "label-pin":
        return vd.xschem.label_pin(a.name, a.pin, a.net, a.length)
    if c == "zoom-fit":
        return t.zoom_fit()
    if c == "eval":
        return t.eval(a.code)
    if c == "load":
        return t.eval(a.file.read_text(encoding="utf-8"))
    if c == "screenshot":
        return t.screenshot(a.out)
    if c == "new-layout":
        return vd.klayout.new_layout(a.cell)
    if c == "open":
        return t.open(a.path)
    if c == "save":
        return vd.xschem.save() if xs else vd.klayout.save(a.path)
    if c == "use-library":
        return vd.klayout.use_library(a.device)
    if c == "tcoil":
        return vd.klayout.place_tcoil(a.name, params=kv(a.set))
    if c == "set":
        return vd.xschem.set_props(a.name, kv(a.set, False)) if xs else vd.klayout.set_pcell_params(a.name, **kv(a.set))
    if c == "describe":
        return vd.xschem.describe() if xs else vd.klayout.describe(a.name)
    if c == "annotate":
        return vd.klayout.annotate(a.name, kv(a.set, False), a.run_id)
    if c == "add-box":
        return vd.klayout.add_shapes(a.layer, a.datatype, boxes=[[a.x1, a.y1, a.x2, a.y2]])
    if c == "add-label":
        return vd.klayout.add_label(a.text, a.x, a.y, a.layer, a.datatype)
    if c == "new-schematic":
        return vd.xschem.new_schematic(a.path, a.replace)
    if c == "place":
        return vd.xschem.place(a.symbol, a.x, a.y, a.rot, a.flip, a.props)
    if c == "wire":
        return vd.xschem.wire(*a.points)
    if c == "sim":
        return vd.sim.run(a.netlist, a.nodes)
    if c == "simulate":
        return vd.sim.xschem(a.nodes, live=not a.no_live)
    if c == "sim-op":
        return vd.sim.op(a.netlist)
    if c == "sweep":
        params = {}
        for spec in a.param:
            name, _, values = spec.partition("=")
            params[name] = [float(v) for v in values.split(",")]
        return vd.sim.sweep(a.netlist, params, a.node, kv(a.fixed))
    if c == "em":
        return vd.em.fasthenry(kv(a.set), a.freqs, a.mesh)
    if c == "em-convergence":
        return vd.em.convergence(kv(a.set), a.freq)
    if c == "cap":
        r = vd.em.fastercap(kv(a.set), a.accuracy)
        if isinstance(r.result, dict):
            r.result.pop("matrix_F", None)
        return r
    if c == "fullwave":
        r = vd.em.palace(kv(a.set), a.fstop, a.fstep, a.cell, a.order, a.np, a.substrate_ohm_cm)
        if isinstance(r.result, dict) and not a.full:
            for k in ("palace", "fasthenry_same_structure"):
                r.result.pop(k, None)
        return r
    if c == "batch":
        b = t.batch()
        for item in json.loads(a.file.read_text(encoding="utf-8")):
            b.add(item["op"], **(item.get("args") or {}))
        return b.run()
    if c == "drc":
        return vd.verify.drc(a.gds, not a.no_live, kv(a.opt, False))
    raise SystemExit("unknown command %s" % c)


def trim(result):
    """Default CLI output drops bulky fields; --full keeps everything."""
    if isinstance(result, dict):
        result = {k: trim(v) for k, v in result.items() if k not in ("log_tail", "vectors", "netlist_text")}
    elif isinstance(result, list):
        result = [trim(v) for v in result]
    return result


def main(argv=None):
    a = build_parser().parse_args(argv)
    if a.cmd == "mcp":
        from .mcp_server import serve
        return serve()
    if a.cmd == "cockpit":
        from .cockpit import Cockpit
        return Cockpit(mode=a.mode, port=a.port).serve()
    vd = Viaduct.from_env(mode=a.mode, safe=a.safe)
    vd.timeout = a.timeout
    r = run(a, vd)
    out = {"status": r.status, "result": r.result if a.full else trim(r.result)}
    if r.error:
        out["error"] = r.error
    out.update(r.extra)
    out["ms"] = r.ms
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    sys.exit(0 if r.ok else 1)


if __name__ == "__main__":
    main()
