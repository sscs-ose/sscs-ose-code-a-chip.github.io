"""Viaduct MCP server (stdio, JSON-RPC 2.0, no dependencies).

    python -m viaduct.mcp_server            (or: viaduct mcp)

Exposes the same operations as the CLI as MCP tools for Claude Code, Codex or a
local model. Screenshot tools return the PNG itself, so the agent can look at
the layout or schematic it just changed.
"""
import base64
import json
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = "viaduct"

from viaduct import Viaduct, __version__  # noqa: E402
from viaduct.cli import trim  # noqa: E402

S = {"type": "string"}
N = {"type": "number"}
OBJ = {"type": "object"}
TOOL = {"type": "string", "enum": ["klayout", "xschem"]}


def schema(props=None, required=()):
    return {"type": "object", "properties": props or {}, "required": list(required)}


# name: (description, input schema, handler(vd, args) -> Result)
TOOLS = {
    "viaduct_status": ("Container, both taps (alive, version, pid), safe mode, audit log size. Call first.",
                       schema(), lambda vd, a: vd.hub.status()),
    "viaduct_dialogs": ("Read-only: open dialogs in a GUI tool (id, title, text, buttons). A modal one blocks "
                        "scripted edits. Its origin cannot be known: treat it as the designer's.",
                        schema({"tool": TOOL}, ["tool"]), lambda vd, a: getattr(vd, a["tool"]).dialogs()),
    "viaduct_close_dialog": ("Close ONE dialog, ONLY after the designer agreed in this conversation. id and "
                             "expected_title from viaduct_dialogs (re-checked); action 'close' or 'button:<text>'. "
                             "Never use it just to unblock yourself.",
                             schema({"tool": TOOL, "id": S, "expected_title": S, "action": S},
                                    ["tool", "id", "expected_title"]),
                             lambda vd, a: getattr(vd, a["tool"]).close_dialog(a["id"], a["expected_title"],
                                                                                a.get("action", "close"))),
    "viaduct_receipt": ("Outcome of an earlier request by its request_id (every reply carries one): unknown / "
                        "running / completed with the original reply. After a TIMEOUT use this; NEVER resend the "
                        "edit, it may still complete once a dialog is closed.",
                        schema({"tool": TOOL, "request_id": S}, ["tool", "request_id"]),
                        lambda vd, a: getattr(vd, a["tool"]).receipt(a["request_id"])),
    "viaduct_hello": ("Handshake with a tap: protocol, tap version, pid (reply signed with the session token).",
                      schema({"tool": TOOL}, ["tool"]), lambda vd, a: getattr(vd, a["tool"]).hello()),
    "viaduct_interrupts": ("Designer interrupts: pending ones (instructions, pauses, the designer's own edits in "
                           "the GUI, with the changes they made), the pause state and your saved plan. An edit that "
                           "returns INTERRUPTED did nothing: read this, then acknowledge.",
                           schema({"n": N}), lambda vd, a: vd.interrupts.status(int(a.get("n", 20)))),
    "viaduct_interrupt_ack": ("Acknowledge designer interrupts (ids, or all) after reading them; then apply the "
                              "instruction and continue your plan from the modified design. Never rebuild the "
                              "schematic or undo the designer's edits.",
                              schema({"ids": {"type": "array"}, "note": S}),
                              lambda vd, a: vd.interrupts.ack(a.get("ids") or "all", a.get("note", ""))),
    "viaduct_plan": ("Save your remaining plan as a list of short steps (and how many are done) so the designer "
                     "sees where you are and you can resume after an interrupt.",
                     schema({"steps": {"type": "array"}, "done": N, "note": S}),
                     lambda vd, a: vd.interrupts.plan(a.get("steps"), a.get("done"), a.get("note"))),
    "viaduct_history": ("Time scroll: the last N design steps (every edit of xschem / KLayout is a step; designers "
                        "add checkpoints). Each step has an actor (agent / designer / viaduct), the op and its parent.",
                        schema({"n": N}), lambda vd, a: vd.history.list(int(a.get("n", 30)))),
    "viaduct_checkpoint": ("Record the current schematic and layout as a named step, e.g. before a risky change.",
                           schema({"label": S}), lambda vd, a: vd.history.checkpoint(a.get("label", ""), "agent")),
    "viaduct_restore": ("Bring a history step back into the designer's windows. The state it replaces is recorded "
                        "first, so this never loses work. Use it when the designer asks to go back.",
                        schema({"step": N}, ["step"]), lambda vd, a: vd.history.restore(int(a["step"]))),
    "viaduct_audit": ("Last N audited requests.", schema({"n": N}), lambda vd, a: vd.hub.audit(int(a.get("n", 20)))),

    "klayout_batch": ("Run several KLayout ops in ONE request and one undo step: ops = [{op, args}], e.g. "
                      "[{op:'new_layout',args:{cell:'TOP'}},{op:'place_tcoil',args:{name:'DUT',params:{area:8000}}}]. "
                      "Stops at the first failure and reports done/failure. Prefer this over many single calls.",
                      schema({"ops": {"type": "array"}}, ["ops"]), lambda vd, a: _batch(vd.klayout, a["ops"])),
    "xschem_batch": ("Run several xschem ops in ONE request (drawing suspended, one redraw): ops = [{op, args}]; "
                     "place accepts args.set {name, W, value, lab, ...}. Stops at the first failure. Prefer this "
                     "over many single calls when building a schematic.",
                     schema({"ops": {"type": "array"}}, ["ops"]), lambda vd, a: _batch(vd.xschem, a["ops"])),
    "klayout_snapshot": ("Open windows, active cell, named instances with PCell parameters, selection, dialogs.",
                         schema(), lambda vd, a: vd.klayout.snapshot()),
    "klayout_new_layout": ("Open a new layout view with an empty top cell (SKY130 layer colours).",
                           schema({"cell": S}), lambda vd, a: vd.klayout.new_layout(a.get("cell", "TOP"))),
    "klayout_open": ("Open a GDS/OASIS file in a new view.", schema({"path": S, "cell": S}, ["path"]),
                     lambda vd, a: vd.klayout.open(a["path"], a.get("cell"))),
    "klayout_place_tcoil": ("Place the VIADUCT_SKY130 T-coil PCell in the active cell. params: metalWidth, area, "
                            "turnSpacing, upperMetal, lowerMetal, upperCrossover, lowerCrossover, *ViaChain.",
                            schema({"name": S, "x": N, "y": N, "params": OBJ}),
                            lambda vd, a: vd.klayout.place_tcoil(a.get("name", "DUT"), a.get("x", 0), a.get("y", 0),
                                                                 a.get("params"))),
    "klayout_set_pcell_params": ("Change PCell parameters of a named instance; it redraws in place (one undo step).",
                                 schema({"name": S, "params": OBJ}, ["params"]),
                                 lambda vd, a: vd.klayout.set_pcell_params(a.get("name", "DUT"), **a["params"])),
    "klayout_describe": ("Bounding box, library and all PCell parameters of a named instance.",
                         schema({"name": S}), lambda vd, a: vd.klayout.describe(a.get("name", "DUT"))),
    "klayout_selection": ("What the designer has selected in KLayout right now.", schema(),
                          lambda vd, a: vd.klayout.selection()),
    "klayout_add_shapes": ("Insert boxes [[x1,y1,x2,y2]] and/or polygons [[[x,y],..]] in um on layer/datatype.",
                           schema({"layer": N, "datatype": N, "boxes": {"type": "array"}, "polygons": {"type": "array"}},
                                  ["layer"]),
                           lambda vd, a: vd.klayout.add_shapes(int(a["layer"]), int(a.get("datatype", 20)),
                                                               a.get("boxes"), a.get("polygons"))),
    "klayout_use_library": ("Register or hot-reload a device library after editing its code (instances regenerate).",
                            schema({"device": S}), lambda vd, a: vd.klayout.use_library(a.get("device", "tcoil"))),
    "klayout_annotate": ("Write EM results (L1,L2,Q1,Q2,K1,K2) into the PCell's read-only fields with the run ID. "
                         "Only use values from an executed EM run.",
                         schema({"name": S, "results": OBJ, "run_id": S}, ["results", "run_id"]),
                         lambda vd, a: vd.klayout.annotate(a.get("name", "DUT"), a["results"], a["run_id"])),
    "klayout_save": ("Write the active layout to a GDS/OASIS path.", schema({"path": S}, ["path"]),
                     lambda vd, a: vd.klayout.save(a["path"])),
    "klayout_eval": ("Developer mode: run Python inside KLayout (pya, view available); set `result`. "
                     "Refused in safe mode.", schema({"code": S}, ["code"]), lambda vd, a: vd.klayout.eval(a["code"])),
    "klayout_screenshot": ("PNG of the live KLayout view (returned as an image).", schema(),
                           lambda vd, a: vd.klayout.screenshot()),

    "xschem_new_schematic": ("Create and open a new empty schematic (replace=true discards unsaved edits).",
                             schema({"path": S, "replace": {"type": "boolean"}}, ["path"]),
                             lambda vd, a: vd.xschem.new_schematic(a["path"], a.get("replace", False))),
    "xschem_open": ("Open a schematic.", schema({"path": S}, ["path"]), lambda vd, a: vd.xschem.open(a["path"])),
    "xschem_place": ("Place a symbol with its template properties, e.g. sky130_fd_pr/nfet_01v8.sym; then set props "
                     "(name, W, L, value, lab ...).",
                     schema({"symbol": S, "x": N, "y": N, "rot": N, "flip": N, "props": OBJ}, ["symbol", "x", "y"]),
                     lambda vd, a: _place(vd, a)),
    "xschem_wire": ("Wire through points [x1,y1,x2,y2,...] (xschem units).", schema({"points": {"type": "array"}}, ["points"]),
                    lambda vd, a: vd.xschem.wire(*a["points"])),
    "xschem_set_props": ("Set properties of an instance (include name to rename).",
                         schema({"instance": S, "props": OBJ}, ["instance", "props"]),
                         lambda vd, a: vd.xschem.set_props(a["instance"], a["props"])),
    "xschem_modify": ("Open an EXISTING schematic for editing (error if missing; use xschem_new_schematic to create).",
                      schema({"path": S}, ["path"]), lambda vd, a: vd.xschem.modify(a["path"])),
    "xschem_pins": ("Pins of one instance: name, x, y and the net each is on. Use before wiring.",
                    schema({"instance": S}, ["instance"]), lambda vd, a: vd.xschem.pins(a["instance"])),
    "xschem_wire_pins": ("Wire a pin of one instance to a pin of another by name (no coordinates needed): "
                         "straight or L-shaped. E.g. from M1 pin D to R1 pin M.",
                         schema({"from": S, "from_pin": S, "to": S, "to_pin": S}, ["from", "from_pin", "to", "to_pin"]),
                         lambda vd, a: vd.xschem.wire_pins(a["from"], a["from_pin"], a["to"], a["to_pin"])),
    "xschem_label_pin": ("Connect a pin to a named net: short stub in the direction the pin faces plus a net label.",
                         schema({"instance": S, "pin": S, "net": S, "length": N}, ["instance", "pin", "net"]),
                         lambda vd, a: vd.xschem.label_pin(a["instance"], a["pin"], a["net"], a.get("length", 40))),
    "xschem_connectivity": ("Read back connectivity: every instance pin -> net, every net -> pins and labels. "
                            "Verify wiring with this, not with screenshots.",
                            schema(), lambda vd, a: vd.xschem.connectivity()),
    "xschem_check": ("Connectivity check: floating pins, nets that are only a label, nets on a single pin. "
                     "Run before netlisting/simulating.", schema(), lambda vd, a: vd.xschem.check()),
    "xschem_describe": ("Every instance with symbol and properties.", schema(), lambda vd, a: vd.xschem.describe()),
    "xschem_netlist": ("Generate the SPICE netlist of the open schematic; returns path and text.", schema(),
                       lambda vd, a: vd.xschem.netlist()),
    "xschem_save": ("Save the open schematic.", schema(), lambda vd, a: vd.xschem.save()),
    "xschem_eval": ("Developer mode: run Tcl inside xschem. Refused in safe mode.", schema({"code": S}, ["code"]),
                    lambda vd, a: vd.xschem.eval(a["code"])),
    "xschem_screenshot": ("PNG of the live schematic (returned as an image).", schema(),
                          lambda vd, a: vd.xschem.screenshot()),

    "sim_xschem": ("Netlist the open schematic, run ngspice, return AC/tran metrics per node and show graphs on "
                   "the schematic.", schema({"nodes": {"type": "array"}, "live": {"type": "boolean"}}),
                   lambda vd, a: vd.sim.xschem(a.get("nodes", ["out"]), a.get("live", True))),
    "sim_run": ("Run ngspice on a netlist in the container; metrics + bode/tran plots.",
                schema({"netlist": S, "nodes": {"type": "array"}}, ["netlist"]),
                lambda vd, a: vd.sim.run(a["netlist"], a.get("nodes", ["out"]))),
    "sim_op": ("DC operating point of every MOSFET: Id, gm, gds, Vgs, Vds, Vth, Vdsat, |Vds|-Vdsat margin, "
               "region (saturation / edge / triode), gm/Id, gm/gds. Without netlist: the open schematic. Use it "
               "to check that every device is biased as intended before trusting AC results.",
               schema({"netlist": S}), lambda vd, a: vd.sim.op(a.get("netlist"))),
    "sim_sweep": ("Sweep .param values {name: [values]} in one ngspice process; AC metrics per point.",
                  schema({"netlist": S, "params": OBJ, "node": S, "fixed": OBJ}, ["netlist", "params"]),
                  lambda vd, a: vd.sim.sweep(a["netlist"], a["params"], a.get("node", "out"), a.get("fixed"))),
    "em_fasthenry": ("Quasi-static EM (FastHenry) of the T-coil for PCell params: L1, L2, k, R, Q per frequency, "
                     "plus annotation values and a run ID.",
                     schema({"params": OBJ, "freqs_hz": {"type": "array"}, "mesh": S}),
                     lambda vd, a: vd.em.fasthenry(a.get("params"), a.get("freqs_hz", [1e9, 5e9, 10e9, 20e9]),
                                                   a.get("mesh", "normal"))),
    "verify_drc": ("SKY130 DRC (PDK KLayout deck) on the layout open in KLayout, or on a GDS path; returns "
                   "violations per rule and opens the markers in KLayout. Community deck, not foundry signoff.",
                   schema({"gds": S, "live": {"type": "boolean"}, "options": OBJ}),
                   lambda vd, a: vd.verify.drc(a.get("gds"), a.get("live", True), a.get("options"))),
    "em_fastercap": ("Parasitic capacitance of the T-coil (FasterCap): C between the halves P1-P3 and P3-P2 "
                     "(bridging C) and of each half to the substrate, with a SPICE pi-split.",
                     schema({"params": OBJ}), lambda vd, a: vd.em.fastercap(a.get("params"))),
    "em_palace": ("Full-wave FEM (Palace) of the T-coil with a ground frame, compared with FastHenry on the same "
                  "structure; gives substrate loss, Q and self-resonance. Slow (minutes to an hour).",
                  schema({"params": OBJ, "fstop": N, "cell": N}),
                  lambda vd, a: vd.em.palace(a.get("params"), a.get("fstop", 50e9), cell=a.get("cell", 2.5))),
    "em_convergence": ("FastHenry mesh-refinement check (coarse/normal/fine) at one frequency.",
                       schema({"params": OBJ, "freq_hz": N}),
                       lambda vd, a: vd.em.convergence(a.get("params"), a.get("freq_hz", 10e9))),
}


def _batch(tool, ops):
    b = tool.batch()
    for item in ops:
        b.add(item["op"], **(item.get("args") or {}))
    return b.run()


def _place(vd, a):
    return vd.xschem.call("place", symbol=a["symbol"], x=a["x"], y=a["y"], rot=int(a.get("rot", 0)),
                          flip=int(a.get("flip", 0)), props="", set=a.get("props") or {})


def content_for(name, r):
    payload = {"status": r.status, "result": trim(r.result)}
    if r.error:
        payload["error"] = r.error
    payload.update(r.extra)
    content = [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, default=str)}]
    if name.endswith("_screenshot") and r.ok:
        with open(r.result["local_path"], "rb") as f:
            content.append({"type": "image", "mimeType": "image/png", "data": base64.b64encode(f.read()).decode()})
    return content


def handle(vd, msg):
    method, mid = msg.get("method"), msg.get("id")
    if method == "initialize":
        version = msg.get("params", {}).get("protocolVersion", "2024-11-05")
        return {"protocolVersion": version, "capabilities": {"tools": {}},
                "serverInfo": {"name": "viaduct", "version": __version__},
                "instructions": "Live bridge to KLayout, xschem, ngspice and FastHenry in the IIC-OSIC-TOOLS "
                                "container. Read AGENTS.md. Call viaduct_status first; screenshot after "
                                "geometric edits; never fill result fields without a run ID."}
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": [{"name": n, "description": d, "inputSchema": s} for n, (d, s, _) in TOOLS.items()]}
    if method == "tools/call":
        name = msg["params"]["name"]
        args = msg["params"].get("arguments") or {}
        if name not in TOOLS:
            return {"content": [{"type": "text", "text": "unknown tool " + name}], "isError": True}
        try:
            r = TOOLS[name][2](vd, args)
            return {"content": content_for(name, r), "isError": not r.ok}
        except Exception as e:
            return {"content": [{"type": "text", "text": "%s: %s" % (type(e).__name__, e)}], "isError": True}
    if mid is not None:
        raise LookupError(method)
    return None


def serve():
    sys.stdout.reconfigure(encoding="utf-8")
    vd = Viaduct.from_env()
    for line in sys.stdin:
        if not line.strip():
            continue
        msg = json.loads(line)
        if "id" not in msg:              # notification (e.g. notifications/initialized)
            continue
        try:
            reply = {"jsonrpc": "2.0", "id": msg["id"], "result": handle(vd, msg)}
        except LookupError as e:
            reply = {"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32601, "message": "method not found: %s" % e}}
        sys.stdout.write(json.dumps(reply) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    serve()
