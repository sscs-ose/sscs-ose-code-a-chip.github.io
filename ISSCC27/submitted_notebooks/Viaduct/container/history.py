"""Time scroll: every design state as a step that can be listed, compared and restored.

After each successful edit of a GUI tool (any op that is not read-only) the relay asks the
tap to write the design as it is in memory (schematic or layout) into a new step, plus a
small screenshot. Designers add steps with `checkpoint`. `restore` brings any step back
into the open windows; it first records the state it replaces and the restored state
becomes a new step whose parent is the step it came from, so nothing is ever lost and
the history is a tree.

Layout on disk, per session (live / headless):
    <repo>/.viaduct/history/<session>/
        index.jsonl         one JSON line per step
        head.json           {"step": N}  the step the windows currently show
        steps/NNNN/         schematic.sch, layout.oas, xschem.png, klayout.png, meta.json
"""
import contextlib
import fcntl
import hashlib
import html
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HIST_ROOT = os.path.join(ROOT, ".viaduct", "history")
TOOLS = ("xschem", "klayout")
FILES = {"xschem": "schematic.sch", "klayout": "layout.oas"}   # OASIS keeps the string "name" property of instances

# Ops that do not change the design: no step.
READ_ONLY = {
    "common": {"ping", "hello", "receipt", "dialogs", "close_dialog", "dismiss_dialogs", "snapshot", "selection",
               "screenshot", "zoom_fit", "reload", "stop", "describe", "save", "history_snapshot",
               "history_restore", "fingerprint"},
    "xschem": {"pins", "connectivity", "check", "netlist"},
    "klayout": {"windows", "hierarchy", "show_markers"},
}


def is_edit(tool, op):
    return tool in TOOLS and op not in READ_ONLY["common"] and op not in READ_ONLY.get(tool, set())


class History:
    def __init__(self, session, gui, state_dir):
        self.session = session or "live"
        self.dir = os.path.join(HIST_ROOT, self.session)
        self.gui = gui                       # {"xschem": fn(op, args, timeout, rid), "klayout": ...}
        self.cfg_file = os.path.join(state_dir, "history.json")

    # ---- configuration ------------------------------------------------------------
    def config(self, enabled=None, thumbs=None):
        cfg = {"enabled": True, "thumbs": True}
        if os.path.exists(self.cfg_file):
            cfg.update(json.load(open(self.cfg_file)))
        if enabled is not None or thumbs is not None:
            if enabled is not None:
                cfg["enabled"] = bool(enabled)
            if thumbs is not None:
                cfg["thumbs"] = bool(thumbs)
            os.makedirs(os.path.dirname(self.cfg_file), exist_ok=True)
            json.dump(cfg, open(self.cfg_file, "w"))
        return cfg

    # ---- storage --------------------------------------------------------------------
    @contextlib.contextmanager
    def _locked(self):
        os.makedirs(self.dir, exist_ok=True)
        with open(os.path.join(self.dir, ".lock"), "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def entries(self):
        path = os.path.join(self.dir, "index.jsonl")
        if not os.path.exists(path):
            return []
        return [json.loads(l) for l in open(path) if l.strip()]

    def head(self):
        path = os.path.join(self.dir, "head.json")
        return json.load(open(path))["step"] if os.path.exists(path) else None

    def _entry(self, step):
        for e in self.entries():
            if e["step"] == step:
                return e
        raise ValueError("no history step %s in session %s" % (step, self.session))

    def _append(self, entry):
        with open(os.path.join(self.dir, "index.jsonl"), "a") as f:
            f.write(json.dumps(entry) + "\n")
        json.dump({"step": entry["step"]}, open(os.path.join(self.dir, "head.json"), "w"))

    # ---- recording ------------------------------------------------------------------
    def record(self, tools, actor, kind, op=None, request_id="", label="", parent=None, state=None):
        """Snapshot `tools` into a new step; tools not snapshotted keep their state from the parent."""
        cfg = self.config()
        with self._locked():
            entries = self.entries()
            step = (entries[-1]["step"] + 1) if entries else 0
            parent = self.head() if parent is None else parent
            prev = next((e for e in entries if e["step"] == parent), None)
            new_state = dict(state if state is not None else (prev["state"] if prev else {}))
            sdir = os.path.join(self.dir, "steps", "%04d" % step)
            os.makedirs(sdir, exist_ok=True)
            info, errors = {}, {}
            for tool in tools:
                fpath = os.path.join(sdir, FILES[tool])
                try:
                    r = self.gui[tool]("history_snapshot", {"path": fpath}, 30, "")
                except Exception as e:                       # tool not running: keep the old state
                    errors[tool] = repr(e)
                    continue
                if r.get("status") != "SUCCESS":
                    errors[tool] = r.get("error")
                    continue
                res = r.get("result") or {}
                if tool == "klayout" and not res.get("layout"):
                    continue                                 # no layout open
                digest = hashlib.sha256(open(fpath, "rb").read()).hexdigest()[:16]
                new_state[tool] = {"step": step, "file": os.path.relpath(fpath, self.dir), "sha": digest,
                                   "name": res.get("schematic") or res.get("file") or "",
                                   "cell": res.get("cell"), "instances": res.get("instances")}
                info[tool] = new_state[tool]
                if cfg["thumbs"]:
                    try:
                        self.gui[tool]("screenshot", {"path": os.path.join(sdir, tool + ".png"),
                                                      "width": 640, "height": 400}, 30, "")
                    except Exception:
                        pass
            entry = {"step": step, "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "t": round(time.time(), 3),
                     "actor": actor, "kind": kind, "op": op, "request_id": request_id, "label": label,
                     "parent": parent, "tools": sorted(info), "state": new_state}
            if errors:
                entry["errors"] = errors
            json.dump(entry, open(os.path.join(sdir, "meta.json"), "w"), indent=2)
            self._append(entry)
        self.timeline_default()
        return entry

    def after_edit(self, tool, op, request_id, actor="agent"):
        """Called by the relay, under the tool's lock, after a successful edit."""
        if not self.config()["enabled"]:
            return None
        e = self.record([tool], actor=actor, kind="edit", op="%s.%s" % (tool, op), request_id=request_id)
        return {"step": e["step"], "parent": e["parent"]}

    def checkpoint(self, label="", actor="designer"):
        return self.record(list(TOOLS), actor=actor, kind="checkpoint", label=label)

    def restore(self, step, tools=None):
        """Bring step `step` back into the windows. The current state is recorded first."""
        target = self._entry(step)
        before = self.record(list(TOOLS), actor="viaduct", kind="before_restore", label="state before restore to %d" % step)
        restored, errors = [], {}
        for tool in (tools or TOOLS):
            st = target["state"].get(tool)
            if not st:
                continue
            src = os.path.join(self.dir, st["file"])
            args = {"src": src}
            if tool == "xschem" and st.get("name"):
                args["target"] = st["name"]
            if tool == "klayout" and st.get("cell"):
                args["cell"] = st["cell"]
            r = self.gui[tool]("history_restore", args, 60, "")
            if r.get("status") == "SUCCESS":
                restored.append(tool)
            else:
                errors[tool] = r.get("error")
        after = self.record([], actor="viaduct", kind="restore", label="restored step %d" % step,
                            parent=step, state=target["state"])
        out = {"restored_step": step, "tools": restored, "saved_previous_as": before["step"], "new_step": after["step"]}
        if errors:
            out["errors"] = errors
        return out

    # ---- views ----------------------------------------------------------------------
    def listing(self, n=50):
        es = self.entries()
        return {"session": self.session, "dir": self.dir, "head": self.head(), "count": len(es),
                "steps": [{k: e.get(k) for k in ("step", "time", "actor", "kind", "op", "label", "parent", "tools")}
                          for e in es[-int(n):]]}

    def timeline_default(self):
        """Regenerate runs/timeline_<session>.html (called after every step and interrupt)."""
        try:
            return self.timeline(os.path.join(ROOT, "runs", "timeline_%s.html" % self.session))
        except Exception:
            return None

    def timeline(self, out_path, last=80):
        """Self-refreshing HTML page: session status (pause, pending designer interrupts, the
        agent's plan) and one card per step, newest first, with screenshots."""
        es = self.entries()
        head = self.head()
        state_dir = os.path.dirname(self.cfg_file)
        irq = json.load(open(os.path.join(state_dir, "interrupts.json"))) if os.path.exists(os.path.join(state_dir, "interrupts.json")) else {}
        plan = json.load(open(os.path.join(state_dir, "plan.json"))) if os.path.exists(os.path.join(state_dir, "plan.json")) else None
        rel = os.path.relpath(self.dir, os.path.dirname(out_path))
        esc = html.escape

        pending = [x for x in irq.get("items", []) if not x.get("acked")]
        status = []
        if irq.get("paused"):
            status.append('<div class="st pause">&#9208; Paused by the designer: the agent cannot edit until <code>resume</code>.</div>')
        for x in pending:
            what = x.get("message") or ""
            if x.get("changes"):
                what += " " + json.dumps(x["changes"])[:300]
            sel = x.get("selection")
            status.append('<div class="st irq">&#9889; Interrupt #%d (%s)%s: %s</div>' % (
                x["id"], esc(x["kind"]), (" on " + esc(json.dumps(sel))) if sel else "", esc(what)))
        if not status:
            status.append('<div class="st ok">&#9654; Running: no pending interrupt.</div>')
        plan_html = ""
        if plan and plan.get("steps"):
            done = plan.get("done", 0)
            items = "".join('<li class="%s">%s</li>' % ("done" if k < done else ("now" if k == done else ""), esc(s))
                            for k, s in enumerate(plan["steps"]))
            plan_html = '<div class="plan"><b>Agent plan</b> (%d of %d done)%s<ol>%s</ol></div>' % (
                done, len(plan["steps"]), (" &middot; " + esc(plan["note"])) if plan.get("note") else "", items)

        icon = {"edit": "&#9679;", "hand_edit": "&#9995;", "checkpoint": "&#9873;", "restore": "&#8617;",
                "before_restore": "&#8617;"}
        cards = []
        for e in reversed(es[-last:]):
            label = e.get("op") or e.get("label") or ""
            kind = e["kind"]
            if kind == "checkpoint" and label.startswith("interrupt"):
                ic, cls_k = "&#9889;", "interrupt"
            else:
                ic, cls_k = icon.get(kind, "&#9679;"), kind
            imgs = "".join('<img src="%s/steps/%04d/%s.png" alt="%s step %d">' % (rel, e["step"], tl, tl, e["step"])
                           for tl in e.get("tools", []))
            cards.append('<div class="card a-%s%s"><div class="hd"><span class="ic">%s</span><b>#%d</b> '
                         '<span class="k">%s</span> %s</div><div class="mt">%s &middot; %s &middot; parent %s%s</div>'
                         '<div class="im">%s</div></div>' % (
                             esc(e["actor"]), " head" if e["step"] == head else "", ic, e["step"], esc(cls_k), esc(label),
                             esc(e["time"]), esc(e["actor"]), e.get("parent"),
                             (" &middot; " + esc(e["request_id"][:8])) if e.get("request_id") else "", imgs))
        page = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="3"><title>Viaduct timeline</title><style>
:root{--bg:#f5f6f8;--paper:#fff;--ink:#18202a;--muted:#5d6b79;--line:#dde3ea;--accent:#0f6e9c;--good:#0f8a6c;--warn:#a86400;--bad:#b42318;--soft:#eef3f7}
@media (prefers-color-scheme:dark){:root{--bg:#0f151b;--paper:#151d25;--ink:#e3e9ee;--muted:#9aabba;--line:#2a3743;--accent:#5bb8e6;--good:#4fc9a3;--warn:#e0a23c;--bad:#f07a6e;--soft:#1b2630}}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 system-ui,"Microsoft YaHei",sans-serif}
main{max-width:1100px;margin:0 auto;padding:16px}
h1{font-size:20px;margin:4px 0 10px}
.st{border-radius:8px;padding:8px 12px;margin:6px 0;border-left:4px solid var(--good);background:var(--soft);overflow-wrap:anywhere}
.st.pause{border-color:var(--warn)} .st.irq{border-color:var(--bad)}
.plan{background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:8px 12px;margin:8px 0}
.plan ol{margin:4px 0 0;padding-left:22px} .plan li.done{color:var(--muted);text-decoration:line-through} .plan li.now{font-weight:700;color:var(--accent)}
.card{background:var(--paper);border:1px solid var(--line);border-left:4px solid var(--line);border-radius:8px;padding:8px 12px;margin:8px 0}
.card.a-agent{border-left-color:var(--accent)} .card.a-designer{border-left-color:var(--good)} .card.a-viaduct{border-left-color:var(--warn)}
.card.head{box-shadow:0 0 0 2px var(--accent)}
.ic{display:inline-block;width:20px} .hd b{color:var(--accent)} .mt{color:var(--muted);font-size:12px}
.k{font-size:11.5px;padding:0 7px;border-radius:999px;border:1px solid var(--line)}
.im{display:flex;gap:8px;flex-wrap:wrap;margin-top:6px} .im img{max-width:100%;width:300px;border:1px solid var(--line);border-radius:6px;background:#000}
</style></head><body><main><h1>Viaduct timeline &middot; """ + esc(self.session) + """</h1>
<div class="mt">""" + "%d steps, head #%s (showing the last %d). Restore a step: <code>python client.py restore STEP</code>. Refreshes every 3 s." % (
            len(es), head, min(last, len(es))) + "</div>" + "".join(status) + plan_html + "".join(cards) + "</main></body></html>"
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        tmp = out_path + ".tmp"
        with open(tmp, "w") as f:
            f.write(page)
        os.replace(tmp, out_path)
        return {"path": out_path, "steps": len(es), "head": head}
