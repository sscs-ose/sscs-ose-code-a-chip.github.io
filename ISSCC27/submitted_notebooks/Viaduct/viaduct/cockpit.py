"""The designer's cockpit: one local page with the noVNC desktop on the left and, on the right,
the session state (running / paused / pending interrupts), a box to interrupt the agent, pause
and resume, the agent's plan, and the time scroll with a restore button per step.

    python client.py cockpit [--mode live|headless] [--port 18090]

The server runs on this machine and listens on 127.0.0.1 only. Every action is sent to the hub
as the designer (actor "designer"); the page polls the read-only hub op `cockpit` every 3 s,
which takes no tool lock. Actions need the token embedded in the page, and requests must name
this host, so other web pages cannot drive it.
"""
import json
import os
import re
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import Viaduct

TOOLS = ("xschem", "klayout")


class Cockpit:
    def __init__(self, mode="live", port=18090):
        self.vd = Viaduct.from_env(mode=mode, actor="designer")
        self.mode = mode
        self.port = port
        self.token = secrets.token_urlsafe(24)
        self._cache = (0.0, None)
        self._lock = threading.Lock()

    # ---- hub calls ---------------------------------------------------------------------
    def state(self):
        with self._lock:                       # several open tabs share one poll
            t, data = self._cache
            if data is not None and time.time() - t < 1.5:
                return data
            r = self.vd.interrupts.call("cockpit", n=10, steps=40)
            data = {"ok": r.ok, "error": r.error, "state": r.result if r.ok else None, "mode": self.mode,
                    "t": time.time()}
            self._cache = (time.time(), data)
            return data

    def act(self, action, body):
        it, hist = self.vd.interrupts, self.vd.history
        if action == "interrupt":
            msg = str(body.get("message", "")).strip()
            if not msg and not body.get("pause"):
                return {"ok": False, "error": "empty instruction"}
            r = it.send(msg, pause=bool(body.get("pause")))
        elif action == "resume":
            r = it.resume()
        elif action == "checkpoint":
            r = hist.checkpoint(str(body.get("label", "")).strip() or "designer checkpoint")
        elif action == "restore":
            r = hist.restore(int(body["step"]))
        else:
            return {"ok": False, "error": "unknown action %r" % action}
        self._cache = (0.0, None)
        return {"ok": r.ok, "status": r.status, "error": r.error, "result": r.result}

    def thumb(self, session, step, tool):
        rel = "/".join((".viaduct", "history", session, "steps", "%04d" % step, tool + ".png"))
        path = self.vd.transport.to_local(self.vd.cfg.remote_dir.rstrip("/") + "/" + rel)
        return open(path, "rb").read() if os.path.isfile(path) else None

    # ---- page ----------------------------------------------------------------------------
    def page(self):
        novnc = self.vd.cfg.novnc_url if self.mode == "live" else ""
        return (PAGE.replace("__TOKEN__", self.token).replace("__NOVNC__", json.dumps(novnc))
                .replace("__MODE__", self.mode))

    def serve(self):
        cockpit = self
        hosts = {"127.0.0.1:%d" % self.port, "localhost:%d" % self.port}

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code, body, ctype="application/json; charset=utf-8", cache="no-store"):
                data = body if isinstance(body, bytes) else (
                    body.encode() if isinstance(body, str) else json.dumps(body, default=str).encode())
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", cache)
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(data)

            def _host_ok(self):
                if self.headers.get("Host") not in hosts:      # DNS rebinding: only our own name
                    self._send(403, {"ok": False, "error": "bad host"})
                    return False
                return True

            def do_GET(self):
                if not self._host_ok():
                    return
                path = self.path.split("?")[0]
                if path == "/":
                    return self._send(200, cockpit.page(), "text/html; charset=utf-8")
                if path == "/api/state":
                    try:
                        return self._send(200, cockpit.state())
                    except Exception as e:
                        return self._send(200, {"ok": False, "error": repr(e)})
                m = re.fullmatch(r"/thumb/([A-Za-z0-9_-]+)/(\d+)/(xschem|klayout)\.png", path)
                if m:
                    data = cockpit.thumb(m.group(1), int(m.group(2)), m.group(3))
                    if data is None:
                        return self._send(404, {"ok": False})
                    return self._send(200, data, "image/png", "max-age=86400")
                self._send(404, {"ok": False, "error": "not found"})

            def do_POST(self):
                if not self._host_ok():
                    return
                m = re.fullmatch(r"/api/(interrupt|resume|checkpoint|restore)", self.path)
                if not m:
                    return self._send(404, {"ok": False, "error": "not found"})
                if not secrets.compare_digest(self.headers.get("X-Cockpit-Token", ""), cockpit.token):
                    return self._send(403, {"ok": False, "error": "bad token"})
                try:
                    n = min(int(self.headers.get("Content-Length", 0)), 65536)
                    body = json.loads(self.rfile.read(n) or b"{}")
                    self._send(200, cockpit.act(m.group(1), body))
                except Exception as e:
                    self._send(200, {"ok": False, "error": repr(e)})

        srv = ThreadingHTTPServer(("127.0.0.1", self.port), H)
        print("Viaduct cockpit (%s session): http://127.0.0.1:%d/   Ctrl+C to stop" % (self.mode, self.port), flush=True)
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            srv.server_close()


PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Viaduct cockpit</title>
<style>
:root{--bg:#f3f5f7;--paper:#fff;--ink:#17202a;--muted:#5b6977;--line:#d9e0e7;--soft:#edf2f6;
--accent:#0f6e9c;--good:#0f8a6c;--warn:#a86400;--bad:#b42318;--on:#fff}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0e141a;--paper:#151d25;--ink:#e2e8ee;
--muted:#97a8b8;--line:#2a3743;--soft:#1a252f;--accent:#5bb8e6;--good:#4fc9a3;--warn:#e0a23c;--bad:#f07a6e;--on:#0e141a}}
:root[data-theme="dark"]{--bg:#0e141a;--paper:#151d25;--ink:#e2e8ee;--muted:#97a8b8;--line:#2a3743;--soft:#1a252f;
--accent:#5bb8e6;--good:#4fc9a3;--warn:#e0a23c;--bad:#f07a6e;--on:#0e141a}
*{box-sizing:border-box}
html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,"Microsoft YaHei",sans-serif}
.app{display:grid;grid-template-columns:minmax(0,1fr) 420px;height:100vh}
.desk{position:relative;background:#000;min-width:0}
.desk iframe{border:0;width:100%;height:100%;display:block}
.desk .none{color:#9aabba;padding:24px}
.side{overflow-y:auto;border-left:1px solid var(--line);background:var(--bg);padding:12px 14px 40px}
h1{font-size:16px;margin:0 0 8px;display:flex;gap:8px;align-items:center}
h1 .sess{font-size:12px;font-weight:500;color:var(--muted);border:1px solid var(--line);border-radius:999px;padding:0 8px}
h2{font-size:12.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin:16px 0 6px}
.st{border-radius:8px;padding:8px 10px;margin:6px 0;border-left:4px solid var(--good);background:var(--soft);overflow-wrap:anywhere}
.st.pause{border-color:var(--warn)} .st.irq{border-color:var(--bad)} .st.err{border-color:var(--bad);color:var(--bad)}
.st .sub{color:var(--muted);font-size:12.5px;margin-top:2px}
textarea{width:100%;min-height:74px;resize:vertical;border:1px solid var(--line);border-radius:8px;padding:8px;
background:var(--paper);color:var(--ink);font:inherit}
textarea:focus,input:focus,button:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.row{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px;align-items:center}
button{font:inherit;border:1px solid var(--line);background:var(--paper);color:var(--ink);border-radius:8px;padding:5px 11px;cursor:pointer}
button.pri{background:var(--accent);border-color:var(--accent);color:var(--on)}
button.warn{border-color:var(--warn);color:var(--warn)}
button:disabled{opacity:.5;cursor:default}
input{font:inherit;border:1px solid var(--line);border-radius:8px;padding:5px 8px;background:var(--paper);color:var(--ink);flex:1;min-width:0}
.hint{color:var(--muted);font-size:12px}
.msg{font-size:12.5px;min-height:18px;margin-top:4px}
.msg.bad{color:var(--bad)} .msg.good{color:var(--good)}
.plan ol{margin:0;padding-left:22px} .plan li.done{color:var(--muted);text-decoration:line-through}
.plan li.now{font-weight:700;color:var(--accent)}
.card{background:var(--paper);border:1px solid var(--line);border-left:4px solid var(--line);border-radius:8px;padding:7px 10px;margin:6px 0}
.card.agent{border-left-color:var(--accent)} .card.designer{border-left-color:var(--good)} .card.viaduct{border-left-color:var(--warn)}
.card.head{box-shadow:0 0 0 2px var(--accent)}
.card .hd{display:flex;gap:6px;align-items:baseline;flex-wrap:wrap}
.card .hd b{color:var(--accent)} .card .op{overflow-wrap:anywhere}
.tag{font-size:11.5px;padding:0 7px;border-radius:999px;border:1px solid var(--line);color:var(--muted)}
.card .mt{color:var(--muted);font-size:12px;display:flex;justify-content:space-between;gap:8px;align-items:center;margin-top:2px}
.card .mt button{padding:1px 8px;font-size:12px}
.thumbs{display:flex;gap:6px;margin-top:6px}
.thumbs img{width:calc(50% - 3px);border:1px solid var(--line);border-radius:6px;background:#000;cursor:zoom-in}
.zoom{position:fixed;inset:0;background:rgba(0,0,0,.8);display:none;align-items:center;justify-content:center;z-index:9;cursor:zoom-out}
.zoom img{max-width:94vw;max-height:94vh;border-radius:6px}
code{font-family:ui-monospace,Consolas,monospace;font-size:12.5px}
.app.nodesk{grid-template-columns:minmax(0,760px);justify-content:center}.app.nodesk .desk{display:none}
.app.nodesk .side{border-left:0}
@media (max-width:900px){.app{grid-template-columns:1fr;height:auto}.desk{height:60vh}.side{border-left:0;border-top:1px solid var(--line)}}
</style></head><body>
<div class="app">
  <div class="desk" id="desk"></div>
  <div class="side">
    <h1>Viaduct cockpit <span class="sess">__MODE__</span></h1>
    <div id="status"><div class="st">Connecting&hellip;</div></div>

    <h2>Interrupt the agent</h2>
    <textarea id="msg" placeholder="e.g. Make M5 L = 2 um and keep W/L; then continue."></textarea>
    <div class="hint">What you have selected in xschem / KLayout is attached. Ctrl+Enter sends.
      Edits you make by hand in the windows interrupt the agent by themselves.</div>
    <div class="row">
      <button class="pri" id="send">Send instruction</button>
      <button class="warn" id="pause">Pause agent</button>
      <button id="resume">Resume</button>
    </div>
    <div class="msg" id="actmsg"></div>

    <div id="plan"></div>

    <h2>Time scroll</h2>
    <div class="row"><input id="cplabel" placeholder="checkpoint label"><button id="cp">Checkpoint</button></div>
    <div id="steps"></div>
  </div>
</div>
<div class="zoom" id="zoom"><img alt="step screenshot"></div>
<script>
const TOKEN = "__TOKEN__", NOVNC = __NOVNC__;
const $ = id => document.getElementById(id);
function el(tag, attrs, ...kids){
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) { if (k === "class") e.className = v; else if (k.startsWith("on")) e.addEventListener(k.slice(2), v); else e.setAttribute(k, v); }
  for (const k of kids) if (k != null) e.append(k.nodeType ? k : String(k));
  return e;
}
if (NOVNC) $("desk").append(el("iframe", {src: NOVNC, title: "Design desktop (noVNC)", allow: "clipboard-read; clipboard-write"}));
else document.querySelector(".app").classList.add("nodesk");   // headless: screenshots are in the time scroll

function localTime(t){ const d = new Date(t); return isNaN(d) ? t : d.toLocaleTimeString(); }
function changeText(c){
  if (!c) return "";
  if (c.layout) return "layout changed";
  const out = [];
  for (const [inst, props] of Object.entries(c.changed || {}))
    for (const [k, v] of Object.entries(props)) out.push(Array.isArray(v) ? `${inst} ${k} ${v[0]} → ${v[1]}` : `${inst} ${k}`);
  if ((c.added || []).length) out.push("added " + c.added.join(", "));
  if ((c.removed || []).length) out.push("removed " + c.removed.join(", "));
  if (c.wires && c.wires[0] !== c.wires[1]) out.push(`wires ${c.wires[0]} → ${c.wires[1]}`);
  return out.join("; ");
}
const KIND = {instruction: "Instruction", pause: "Pause", hand_edit: "Your hand edit", designer_edit: "Your edit", restore: "Your restore"};
const ICON = {edit: "●", hand_edit: "✋", checkpoint: "⚑", restore: "↩", before_restore: "↩"};

function renderStatus(s){
  const box = $("status"); box.replaceChildren();
  const irq = s.interrupts, pend = irq.pending || [];
  if (irq.paused) box.append(el("div", {class: "st pause"}, "⏸ Agent paused: its edits are blocked until you press Resume."));
  for (const i of pend) {
    const sel = i.selection ? Object.entries(i.selection).map(([t, n]) => `${t}: ${n.join(", ")}`).join("; ") : "";
    box.append(el("div", {class: "st irq"}, `⚡ #${i.id} ${KIND[i.kind] || i.kind}` + (i.message ? `: ${i.message}` : ""),
      (changeText(i.changes) || sel) ? el("div", {class: "sub"}, [changeText(i.changes), sel && "selection " + sel].filter(Boolean).join(" · ")) : null,
      el("div", {class: "sub"}, "waiting for the agent to acknowledge")));
  }
  if (!irq.paused && !pend.length) {
    const last = (irq.recent || []).slice(-1)[0];
    box.append(el("div", {class: "st"}, "▶ Running: no pending interrupt.",
      last && last.acked ? el("div", {class: "sub"}, `Last: #${last.id} acknowledged` + (last.ack_note ? ` — “${last.ack_note}”` : "")) : null));
  }
}
function renderPlan(p){
  const box = $("plan"); box.replaceChildren();
  if (!p || !(p.steps || []).length) return;
  const done = p.done || 0;
  box.append(el("h2", {}, `Agent plan · ${done} of ${p.steps.length} done`),
    el("div", {class: "plan"}, p.note ? el("div", {class: "hint"}, p.note) : null,
      el("ol", {}, ...p.steps.map((s, k) => el("li", {class: k < done ? "done" : (k === done ? "now" : "")}, s)))));
}
let lastKey = "";
function renderSteps(h){
  const key = h.count + ":" + h.head;
  if (key === lastKey) return; lastKey = key;
  const box = $("steps"); box.replaceChildren();
  if (!h.steps.length) { box.append(el("div", {class: "hint"}, "No steps yet.")); return; }
  for (const e of h.steps.slice().reverse()) {
    const label = e.op || e.label || "";
    const interrupt = e.kind === "checkpoint" && label.startsWith("interrupt");
    const thumbs = el("div", {class: "thumbs"}, ...(e.tools || []).map(t => el("img", {loading: "lazy", alt: `${t} at step ${e.step}`,
      src: `/thumb/${encodeURIComponent(h.session)}/${e.step}/${t}.png`, onclick: ev => zoom(ev.target.src), onerror: ev => ev.target.remove()})));
    box.append(el("div", {class: `card ${e.actor}` + (e.step === h.head ? " head" : "")},
      el("div", {class: "hd"}, interrupt ? "⚡" : (ICON[e.kind] || "●"), el("b", {}, "#" + e.step),
        el("span", {class: "tag"}, e.actor), el("span", {class: "tag"}, interrupt ? "interrupt" : e.kind), el("span", {class: "op"}, label)),
      el("div", {class: "mt"}, el("span", {}, localTime(e.time) + (e.step === h.head ? " · current" : "")),
        el("button", {onclick: () => restore(e.step), title: "Bring this step back into the windows"}, "Restore")),
      thumbs));
  }
}
function zoom(src){ const z = $("zoom"); z.querySelector("img").src = src; z.style.display = "flex"; }
$("zoom").onclick = () => $("zoom").style.display = "none";

async function poll(){
  try {
    const r = await (await fetch("/api/state", {cache: "no-store"})).json();
    if (!r.ok) throw new Error(r.error || "hub error");
    renderStatus(r.state); renderPlan(r.state.interrupts.plan); renderSteps(r.state.history);
  } catch (e) {
    $("status").replaceChildren(el("div", {class: "st err"}, "Cannot reach Viaduct: " + e.message));
  }
}
async function act(action, body, okText){
  const m = $("actmsg"); m.className = "msg"; m.textContent = "Sending…";
  for (const b of document.querySelectorAll("button")) b.disabled = true;
  try {
    const r = await (await fetch("/api/" + action, {method: "POST", headers: {"Content-Type": "application/json", "X-Cockpit-Token": TOKEN},
      body: JSON.stringify(body || {})})).json();
    m.className = "msg " + (r.ok ? "good" : "bad"); m.textContent = r.ok ? okText(r.result || {}) : (r.status || "") + " " + (r.error || "failed");
    return r.ok;
  } catch (e) { m.className = "msg bad"; m.textContent = e.message; return false; }
  finally { for (const b of document.querySelectorAll("button")) b.disabled = false; lastKey = ""; poll(); }
}
async function send(pause){
  const msg = $("msg").value.trim();
  if (!msg && !pause) { $("msg").focus(); return; }
  if (await act("interrupt", {message: msg, pause}, r => `Sent as #${r.id}` + (r.selection ? " with your selection" : "") + (pause ? "; agent paused" : "")))
    $("msg").value = "";
}
async function restore(step){
  if (!confirm(`Restore step #${step} into the windows?\nThe current state is recorded first, and the agent is interrupted.`)) return;
  act("restore", {step}, r => `Restored #${step} as step #${r.new_step}`);
}
$("send").onclick = () => send(false);
$("pause").onclick = () => send(true);
$("resume").onclick = () => act("resume", {}, () => "Agent resumed");
$("cp").onclick = () => act("checkpoint", {label: $("cplabel").value}, r => { $("cplabel").value = ""; return `Checkpoint #${r.step}`; });
$("msg").addEventListener("keydown", e => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) send(false); });
poll(); setInterval(poll, 3000);
</script></body></html>"""
