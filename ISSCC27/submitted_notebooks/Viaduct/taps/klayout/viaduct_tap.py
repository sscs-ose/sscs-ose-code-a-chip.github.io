"""Viaduct KLayout tap: a small RPC server inside the running KLayout GUI.

Loaded automatically by the autorun macro (taps/klayout/viaduct_autorun.lym,
installed into ~/.klayout/pymacros by `viaduct install`), so any KLayout started
on the desktop carries the tap. Manual start:
    klayout -e -rm /foss/designs/viaduct/taps/klayout/viaduct_tap.py

The server runs on KLayout's Qt main thread, so every request executes in the
GUI thread and edits redraw immediately. It listens on 127.0.0.1 only.
Protocol: one JSON object per line, {"nonce","body","mac"}; mac is
HMAC-SHA256(token, nonce + body). body is JSON {"op": name, "args": {...}}.
"""
import hashlib
import hmac
import importlib
import importlib.util
import json
import os
import secrets
import sys
import time
import traceback

import pya

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PORT = int(os.environ.get("VIADUCT_KLAYOUT_PORT", "18765"))
# A headless session (Xvfb) uses its own state dir and port, so it never collides with the live one.
STATE_DIR = os.environ.get("VIADUCT_STATE_DIR", os.path.expanduser("~/.viaduct"))
TOKEN_FILE = os.path.join(STATE_DIR, "klayout.token")
INFO_FILE = os.path.join(STATE_DIR, "klayout.json")
DEVICE_DIRS = {"tcoil": os.path.join(ROOT, "devices", "tcoil")}
LAYER_PROPS = os.path.join(ROOT, "pdk", "sky130A.lyp")
VERSION = "viaduct-klayout-tap-0.4"
PROTO = 2
# Receipts survive `reload`: request id -> {state, started, op, [finished, reply]}.
RECEIPTS = sys._viaduct_receipts = getattr(sys, "_viaduct_receipts", {})
UNTRACKED = {"receipt", "hello", "ping", "dialogs"}


def _token():
    os.makedirs(STATE_DIR, mode=0o700, exist_ok=True)
    if not os.path.exists(TOKEN_FILE):
        fd = os.open(TOKEN_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(secrets.token_hex(32))
    with open(TOKEN_FILE, "rb") as f:
        return f.read().strip()


# Registry lives on sys so `reload` can replace ops without restarting the server.
OPS = sys._viaduct_ops = getattr(sys, "_viaduct_ops", {})


def op(fn):
    OPS[fn.__name__.rstrip("_")] = fn     # trailing _ avoids shadowing builtins (open_)
    return fn


def _mw():
    return pya.MainWindow.instance()


def _view(required=True):
    view = pya.LayoutView.current()
    if view is None and required:
        raise RuntimeError("No layout view is open; call new_layout or open first")
    return view


def _cellview():
    view = _view()
    cv = view.active_cellview()
    if not cv.is_valid():
        raise RuntimeError("No valid active cellview")
    return view, cv


def _show_all(view):
    if getattr(sys, "_viaduct_batch_open", False):
        sys._viaduct_batch_redraw = True       # done once when the batch ends
        return
    view.add_missing_layers()
    view.max_hier()
    view.zoom_fit()


class _txn:
    """One undo step per op; inside a batch the whole batch is one undo step."""
    def __init__(self, view, label):
        self.view, self.label = view, label

    def __enter__(self):
        self.own = not getattr(sys, "_viaduct_batch_open", False)
        if self.own:
            self.view.transaction(self.label)
        elif getattr(sys, "_viaduct_batch_view", None) is None:
            # First edit of a batch: open the batch's single undo step on the view being
            # edited (a batch may start with new_layout, before any view exists).
            self.view.transaction(sys._viaduct_batch_label)
            sys._viaduct_batch_view = self.view
        return self

    def __exit__(self, *exc):
        if self.own:
            self.view.commit()
        return False


def _later(ms, fn):
    """Run fn on the GUI thread after the current reply has been sent."""
    timer = pya.QTimer()
    timer.setSingleShot(True)
    timer.timeout += fn
    timer.start(ms)
    sys._viaduct_timers = getattr(sys, "_viaduct_timers", []) + [timer]


# ---- session ---------------------------------------------------------------------

@op
def ping():
    return {"tap": VERSION, "klayout": pya.Application.instance().version(), "pid": os.getpid(),
            "views": _mw().views(), "root": ROOT}


@op
def windows():
    mw = _mw()
    out = []
    for i in range(mw.views()):
        v = mw.view(i)
        cvs = []
        for j in range(v.cellviews()):
            cv = v.cellview(j)
            cvs.append({"index": j, "file": cv.filename(), "dirty": cv.is_dirty(),
                        "cell": cv.cell.name if cv.cell else None})
        out.append({"index": i, "title": v.title, "cellviews": cvs})
    return {"current": mw.current_view_index, "views": out}


@op
def exec_python(code):
    """Developer mode: the analogue of SKILL evalstring. Set `result`."""
    env = {"pya": pya, "view": _view(False), "result": None}
    exec(code, env)
    return env["result"]


@op
def screenshot(path, width=1400, height=900):
    view = _view()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    view.save_image(path, width, height)
    return {"path": path, "width": width, "height": height}


@op
def zoom_fit():
    _view().zoom_fit()
    return True


@op
def reload():
    """Re-execute this file: refreshes every op; the running server is kept."""
    path = os.path.abspath(__file__)
    with open(path, encoding="utf-8") as f:
        exec(compile(f.read(), path, "exec"), {"__file__": path, "__name__": "viaduct_tap"})
    return {"tap": VERSION, "ops": sorted(sys._viaduct_ops)}


def _modal_widgets():
    out = []
    for w in pya.QApplication.topLevelWidgets():
        if w.isVisible() and (w.isModal() or isinstance(w, pya.QDialog)) and not isinstance(w, pya.QMainWindow):
            out.append(w)
    return out


# Dialogs created inside Qt (QMessageBox::question etc.) reach Python as *_Native wrapper
# types that fail isinstance checks against pya.QMessageBox / pya.QAbstractButton, so
# buttons are found by capability, not by type.
def _is_button(c):
    return hasattr(c, "click") and hasattr(c, "text") and "Button" in type(c).__name__


def _buttons(w):
    if hasattr(w, "buttons") and callable(w.buttons):
        try:
            found = list(w.buttons())
            if found:
                return found
        except Exception:
            pass
    found, stack = [], list(w.children())
    while stack:
        c = stack.pop()
        if _is_button(c):
            found.append(c)
        elif hasattr(c, "children"):
            stack.extend(c.children())
    return found


def _btext(b):
    return b.text.replace("&", "")


def _dialog_info(w):
    item = {"id": str(int(w.winId())), "class": type(w).__name__.replace("_Native", ""),
            "title": w.windowTitle, "modal": w.isModal(), "buttons": [_btext(b) for b in _buttons(w)]}
    if "MessageBox" in type(w).__name__:
        item["text"] = w.text
    return item


@op
def dialogs():
    """Read-only: visible dialogs. A modal one blocks scripted edits until it is closed.
    Their origin (designer or script) cannot be told apart; nothing is changed here."""
    return [_dialog_info(w) for w in _modal_widgets()]


@op
def close_dialog(id, expected_title, action="close"):
    """Close ONE dialog the designer agreed to close. id and expected_title come from
    dialogs() and are re-checked here; action is "close" (window close, usually = Cancel)
    or "button:<text>" to press one named button."""
    target = next((w for w in _modal_widgets() if str(int(w.winId())) == str(id)), None)
    if target is None:
        raise RuntimeError("no open dialog with id %s (already closed?)" % id)
    info = _dialog_info(target)
    if target.windowTitle != expected_title:
        raise RuntimeError("dialog %s is now titled %r, not %r; inspect again" % (id, target.windowTitle, expected_title))
    if action == "close":
        target.close()
    elif action.startswith("button:"):
        label = action[len("button:"):]
        btn = next((b for b in _buttons(target) if _btext(b) == label), None)
        if btn is None:
            raise RuntimeError("dialog %s has no button %r (buttons: %s)" % (id, label, info["buttons"]))
        btn.click()
    else:
        raise ValueError('action must be "close" or "button:<text>"')
    return {"requested": action, "dialog": info}


@op
def dismiss_dialogs(confirm_all=False):
    """Legacy bulk close of EVERY visible dialog, including the designer's own. Refused
    unless confirm_all=True; prefer dialogs() + close_dialog()."""
    if not confirm_all:
        raise RuntimeError("bulk dismissal closes the designer's dialogs too; pass confirm_all=True "
                           "only when told to, or use close_dialog(id, expected_title, action)")
    closed = dialogs()
    for w in _modal_widgets():
        w.close()
    return {"closed": closed}


@op
def stop(force=False):
    """Quit KLayout. Refuses while layouts have unsaved edits unless force."""
    dirty = [v for v in windows()["views"] for c in v["cellviews"] if c["dirty"]]
    if dirty and not force:
        raise RuntimeError("unsaved layouts %s; save them or pass force" % [v["title"] for v in dirty])
    _later(200, lambda: pya.Application.instance().exit(0))
    return {"stopping": True, "discarded": [v["title"] for v in dirty]}


# ---- layout ----------------------------------------------------------------------

@op
def new_layout(cell="TOP", dbu=0.001):
    mw = _mw()
    cv = mw.create_layout(1)          # mode 1: new view
    layout = cv.layout()
    layout.dbu = dbu
    cv.cell = layout.create_cell(cell)
    if os.path.exists(LAYER_PROPS):
        mw.current_view().load_layer_props(LAYER_PROPS)
    _show_all(mw.current_view())
    return {"cell": cell, "view": mw.current_view_index}


@op
def open_(path, cell=None):
    mw = _mw()
    cv = mw.load_layout(path, 1)
    if cell:
        cv.cell = cv.layout().cell(cell)
    if os.path.exists(LAYER_PROPS):
        mw.current_view().load_layer_props(LAYER_PROPS)
    _show_all(mw.current_view())
    return {"file": path, "cell": cv.cell.name if cv.cell else None, "view": mw.current_view_index}


@op
def save(path):
    _, cv = _cellview()
    cv.layout().write(path)
    return {"path": path}


@op
def history_snapshot(path):
    """Write the active layout as it is in memory to `path`. Use OASIS: it keeps PCells
    (context info) and the string "viaduct_name" property that names instances, which GDS
    drops. The view, its file name and its undo history are untouched."""
    view = _view(required=False)
    if view is None or not view.active_cellview().is_valid():
        return {"layout": None}
    cv = view.active_cellview()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cv.layout().write(path)
    return {"layout": path, "cell": cv.cell.name if cv.cell else None, "file": cv.filename()}


@op
def fingerprint():
    """A hash of what the active layout contains (top-cell instances with their placement,
    PCell parameters and names; shape counts per layer; bounding box), not of how it is
    shown. The relay compares it with the value after its own last edit."""
    view = _view(required=False)
    if view is None or not view.active_cellview().is_valid() or view.active_cellview().cell is None:
        return {"layout": None}
    cv = view.active_cellview()
    ly, top = cv.layout(), cv.cell
    h = hashlib.sha256()
    for inst in top.each_inst():
        pc = inst.pcell_parameters_by_name() if inst.is_pcell() else None
        h.update(repr((inst.cell.name if inst.cell else "", str(inst.dcplx_trans), sorted(pc.items()) if pc else None,
                       inst.property("viaduct_name"))).encode())
    for li in ly.layer_indexes():
        h.update(("%s:%d;" % (ly.get_info(li), top.shapes(li).size())).encode())
    h.update(str(top.dbbox()).encode())
    return {"layout": cv.filename() or top.name, "cell": top.name, "sha": h.hexdigest()[:16]}


@op
def history_restore(src, cell=None):
    """Replace the active layout's content with the snapshot `src`, in place: same view,
    same file name (nothing is written to disk; the caller snapshots what it replaces)."""
    view, cv = _cellview()
    ly = cv.layout()
    name = cell or (cv.cell.name if cv.cell else None)
    view.clear_transactions()
    ly.clear()
    ly.read(src)
    target = ly.cell(name) if name and ly.cell(name) else ly.top_cell()
    cv.cell = target
    view.add_missing_layers()
    view.max_hier()
    view.zoom_fit()
    return {"cell": target.name if target else None, "file": cv.filename(), "shapes_layers": ly.layers()}


@op
def add_shapes(layer, datatype=20, boxes=None, polygons=None):
    """Insert boxes [[x1,y1,x2,y2],...] and polygons [[[x,y],...],...] (um) in the active cell."""
    view, cv = _cellview()
    layout = cv.layout()
    shapes = cv.cell.shapes(layout.layer(int(layer), int(datatype)))
    with _txn(view, "viaduct add_shapes"):
        for b in boxes or []:
            shapes.insert(pya.DBox(*b))
        for pts in polygons or []:
            shapes.insert(pya.DPolygon([pya.DPoint(x, y) for x, y in pts]))
    view.add_missing_layers()
    return {"boxes": len(boxes or []), "polygons": len(polygons or [])}


@op
def add_label(text, x, y, layer, datatype=5):
    view, cv = _cellview()
    with _txn(view, "viaduct add_label"):
        cv.cell.shapes(cv.layout().layer(int(layer), int(datatype))).insert(pya.DText(text, pya.DTrans(x, y)))
    return True


# ---- devices / PCells ----------------------------------------------------------------

def _device(name="tcoil", reload_code=False):
    """The device's PCell module, loaded by path under a unique name (no clash with
    other packages' klayout_pcell/tcoil_core); reload_code re-executes it from disk."""
    key = "viaduct_%s_pcell" % name
    if reload_code or key not in sys.modules:
        spec = importlib.util.spec_from_file_location(key, os.path.join(DEVICE_DIRS[name], "klayout_pcell.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[key] = mod
        spec.loader.exec_module(mod)
    return sys.modules[key]


@op
def use_library(device="tcoil", reload_code=True):
    """Register (or hot-reload) a device library; existing instances regenerate."""
    mod = _device(device, reload_code)
    lib = mod.register(force=reload_code)
    refreshed = False
    try:
        lib.refresh()           # KLayout >= 0.27.10: re-generate PCells using this library
        refreshed = True
    except Exception:
        pass
    view = _view(False)
    if view:
        view.add_missing_layers()
    return {"library": mod.LIBRARY, "cell": mod.CELL, "reloaded": reload_code, "instances_refreshed": refreshed}


def _find_instance(cell, name):
    for inst in cell.each_inst():
        if inst.property("viaduct_name") == name:
            return inst
    raise RuntimeError("No instance named %r in %s" % (name, cell.name))


def _describe(inst):
    box = inst.dbbox()
    out = {"name": inst.property("viaduct_name"), "cell": inst.cell.name,
           "bbox_um": [[box.left, box.bottom], [box.right, box.top]]}
    if inst.is_pcell():
        out["pcell"] = inst.pcell_declaration().name()
        out["library"] = inst.cell.library().name() if inst.cell.library() else None
        out["params"] = {k: v for k, v in inst.pcell_parameters_by_name().items() if k != "emKey"}
    return out


@op
def place_tcoil(name="DUT", x=0.0, y=0.0, params=None):
    mod = _device("tcoil")
    view, cv = _cellview()
    with _txn(view, "viaduct place_tcoil"):
        variant = mod.create_variant(cv.layout(), params or {})
        inst = cv.cell.insert(pya.DCellInstArray(variant.cell_index(), pya.DTrans(x, y)))
        inst.set_property("viaduct_name", name)
    _show_all(view)
    return _describe(inst)


def _change_params(name, params, label):
    view, cv = _cellview()
    inst = _find_instance(cv.cell, name)
    decl = inst.pcell_declaration()
    current = inst.pcell_parameters_by_name()
    current.update(params or {})
    specs = decl.get_parameters()
    # Coerce like the GUI Properties dialog does, so read-only fields refresh
    # and invalid combinations are rejected before the geometry changes.
    values = decl.coerce_parameters(cv.layout(), [current.get(p.name, p.default) for p in specs])
    with _txn(view, label):
        inst.change_pcell_parameters({p.name: v for p, v in zip(specs, values)})
    _show_all(view)
    return _describe(_find_instance(cv.cell, name))


@op
def set_pcell_params(name="DUT", params=None):
    return _change_params(name, params, "viaduct set_pcell_params")


@op
def annotate(name="DUT", results=None, run_id=""):
    """Write EM results into the read-only RF fields, bound to the current geometry."""
    mod = _device("tcoil")
    _, cv = _cellview()
    inst = _find_instance(cv.cell, name)
    current = inst.pcell_parameters_by_name()
    geometry = {k: current[k] for k in mod.Parameters.__dataclass_fields__}
    fields = {k: str(v) for k, v in (results or {}).items() if k in mod.RF_FIELDS}
    fields.update(resultStatus=run_id or "EM", emKey=mod.geometry_key(geometry))
    return _change_params(name, fields, "viaduct annotate")


@op
def describe(name="DUT"):
    _, cv = _cellview()
    return _describe(_find_instance(cv.cell, name))


# ---- batch ---------------------------------------------------------------------------

_NOT_IN_BATCH = {"batch", "exec_python", "reload", "stop", "dismiss_dialogs", "close_dialog"}


@op
def batch(ops, label="viaduct batch"):
    """Run [{"op": name, "args": {...}}, ...] in one request and one undo step.
    Stops at the first failing op; the reply says how many ops completed."""
    results, failure = [], None
    sys._viaduct_batch_open = True
    sys._viaduct_batch_redraw = False
    sys._viaduct_batch_view = None
    sys._viaduct_batch_label = label
    try:
        try:
            for i, item in enumerate(ops):
                name = item.get("op")
                fn = sys._viaduct_ops.get(name)
                if fn is None or name in _NOT_IN_BATCH:
                    failure = {"index": i, "op": name, "error": "op not allowed in a batch or unknown"}
                    break
                try:
                    results.append(fn(**(item.get("args") or {})))
                except Exception as e:
                    failure = {"index": i, "op": name, "error": repr(e)}
                    break
        finally:
            if sys._viaduct_batch_view is not None:
                sys._viaduct_batch_view.commit()
    finally:
        sys._viaduct_batch_open = False
        sys._viaduct_batch_view = None
    view = _view(False)                      # new_layout inside the batch may have opened one
    if view and sys._viaduct_batch_redraw:
        _show_all(view)
    out = {"ok": failure is None, "done": len(results), "total": len(ops), "results": results}
    if failure:
        out["failure"] = failure
    return out


# ---- verification overlay ------------------------------------------------------------

@op
def show_markers(path):
    """Load a report database (.lyrdb) into the current view and open the Marker Browser."""
    view = _view()
    for i in reversed(range(view.num_rdbs())):
        if view.rdb(i).filename() == path:
            view.remove_rdb(i)
    rdb = pya.ReportDatabase("")
    rdb.load(path)
    index = view.add_rdb(rdb)
    view.show_rdb(index, view.active_cellview_index)
    return {"rdb_index": index, "items": rdb.num_items(), "categories": rdb.num_categories()
            if hasattr(rdb, "num_categories") else None}


# ---- readback ---------------------------------------------------------------------

@op
def selection():
    view = _view()
    out = []
    for path in view.each_object_selected():
        if path.is_cell_inst():
            out.append(dict(kind="instance", **_describe(path.inst())))
        else:
            s = path.shape
            box = s.dbbox()
            info = path.layout().get_info(path.layer)
            out.append({"kind": "shape", "type": s.to_s().split("(")[0], "layer": [info.layer, info.datatype],
                        "bbox_um": [[box.left, box.bottom], [box.right, box.top]]})
    return out


@op
def hierarchy(depth=3):
    _, cv = _cellview()
    layout = cv.layout()

    def walk(cell, d):
        node = {"cell": cell.name, "pcell": cell.is_pcell_variant()}
        if d > 0:
            node["children"] = [walk(layout.cell(ci), d - 1) for ci in cell.each_child_cell()]
        return node
    return [walk(layout.cell(t), depth) for t in layout.each_top_cell()]


@op
def snapshot():
    """One-call summary: windows, active cell, named instances with parameters, selection."""
    out = {"windows": windows(), "dialogs": dialogs()}
    view = _view(False)
    if view and view.active_cellview().is_valid():
        cv = view.active_cellview()
        out["active_cell"] = cv.cell.name
        out["instances"] = [_describe(i) for i in cv.cell.each_inst() if i.property("viaduct_name")]
        out["selection"] = selection()
    return out


# ---- server --------------------------------------------------------------------------

class Tap:
    def __init__(self, port):
        self.token = _token()
        self.seen = {}
        self.clients = []
        self.server = pya.QTcpServer()
        self.server.newConnection += self._accept
        self.listening = self.server.listen(pya.QHostAddress("127.0.0.1"), port)
        if not self.listening:
            # Another KLayout already owns the tap port; this one stays a plain KLayout.
            print("[viaduct] tap not started, 127.0.0.1:%d busy: %s" % (port, self.server.errorString()))
            return
        with open(INFO_FILE, "w") as f:
            json.dump({"port": port, "pid": os.getpid(), "tap": VERSION, "started": time.time()}, f)
        print("[viaduct] tap listening on 127.0.0.1:%d" % port)

    def _accept(self):
        while self.server.hasPendingConnections():
            sock = self.server.nextPendingConnection()
            buf = bytearray()

            def ready(sock=sock, buf=buf):
                buf.extend(bytes(sock.readAll()))
                while b"\n" in buf:
                    line, _, rest = bytes(buf).partition(b"\n")
                    buf[:] = rest
                    reply = json.dumps(self._handle(line), default=str) + "\n"
                    sock.write(reply.encode())
                    sock.flush()

            def gone(sock=sock):
                if sock in self.clients:
                    self.clients.remove(sock)

            sock.readyRead += ready
            sock.disconnected += gone
            self.clients.append(sock)

    def _handle(self, line):
        """Protocol v2. Request {nonce, body, mac}; body {op, args, request_id, proto};
        mac = HMAC(token, nonce + body). Reply {reply, mac}: reply is the JSON result,
        mac = HMAC(token, nonce + reply), so the relay can tell this tap from anything
        else answering on the port. Every request id gets a receipt (running/completed
        + reply) that can be queried after a timeout; a reused id is refused."""
        start = time.time()
        nonce = ""
        try:
            req = json.loads(line)
            nonce, body = req["nonce"], req["body"]
            mac = hmac.new(self.token, (nonce + body).encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(mac, req.get("mac", "")):
                return {"status": "DENIED", "error": "bad signature"}
            now = time.time()
            self.seen = {n: t for n, t in self.seen.items() if now - t < 900}
            if nonce in self.seen:
                return self._signed(nonce, {"status": "DENIED", "error": "replayed nonce"})
            self.seen[nonce] = now
            body = json.loads(body)
            if body.get("proto") != PROTO:
                return self._signed(nonce, {"status": "DENIED",
                                            "error": "protocol %r, tap speaks %d" % (body.get("proto"), PROTO)})
            op_name, rid = body.get("op"), body.get("request_id")
            track = bool(rid) and op_name not in UNTRACKED
            if track:
                if rid in RECEIPTS:
                    return self._signed(nonce, {"status": "DENIED", "error": "request id %s was already submitted; "
                                                "query its receipt, do not resend" % rid})
                _prune_receipts()
                RECEIPTS[rid] = {"state": "running", "started": now, "op": op_name}
            reply = self._execute(op_name, body.get("args", {}), start)
            if track:
                RECEIPTS[rid].update(state="completed", finished=time.time(), reply=reply)
            return self._signed(nonce, reply)
        except Exception as e:
            return self._signed(nonce, {"status": "ERROR", "error": repr(e), "trace": traceback.format_exc(limit=4)})

    def _execute(self, op_name, args, start):
        ops = sys._viaduct_ops
        fn = ops.get(op_name)
        if fn is None:
            return {"status": "ERROR", "error": "unknown op %r" % op_name, "ops": sorted(ops)}
        try:
            result = fn(**args)
            return {"status": "SUCCESS", "result": result, "ms": round((time.time() - start) * 1000, 1)}
        except Exception as e:
            return {"status": "ERROR", "error": repr(e), "trace": traceback.format_exc(limit=4)}

    def _signed(self, nonce, reply):
        text = json.dumps(reply, default=str)
        return {"reply": text, "mac": hmac.new(self.token, (nonce + text).encode(), hashlib.sha256).hexdigest()}


def _prune_receipts():
    now = time.time()
    for k in [k for k, r in RECEIPTS.items() if r["state"] == "completed" and now - r["finished"] > 3600]:
        del RECEIPTS[k]
    done = sorted((r["finished"], k) for k, r in RECEIPTS.items() if r["state"] == "completed")
    while len(RECEIPTS) > 2000 and done:
        del RECEIPTS[done.pop(0)[1]]


@op
def hello():
    """Handshake: protocol, version, capabilities; changes nothing."""
    return {"proto": PROTO, "tap": VERSION, "pid": os.getpid(), "klayout": pya.Application.instance().version(),
            "receipts": True, "server_time": time.time()}


@op
def receipt(request_id):
    """What happened to an earlier request: unknown | running | completed (+ its reply)."""
    r = RECEIPTS.get(request_id)
    if r is None:
        return {"request_id": request_id, "state": "unknown"}
    return dict(r, request_id=request_id)


# Keep a process-wide reference so the server is not garbage collected
# after the macro's own namespace goes away. Only in the GUI application.
if getattr(sys, "_viaduct_tap", None) is None and pya.Application.instance().main_window() is not None:
    sys._viaduct_tap = Tap(PORT)
elif getattr(sys, "_viaduct_tap", None) is not None:
    # `reload`: the running server keeps its socket and callbacks; its callbacks look up
    # self._handle at call time, so swapping the class switches the protocol code too.
    sys._viaduct_tap.__class__ = Tap
