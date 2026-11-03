"""Self-contained interactive HTML report (report.html).

One file, no server, no external scripts: open it in any browser, attach it to an
issue, or display it inline in a notebook (``IPython.display.HTML``/``IFrame``).
Charts are drawn by a small inline script from the JSON embedded in the page.
"""
from __future__ import annotations

import html
import json
import time

from . import __version__

_TITLE_MAX = 60


def build_report_data(res, whatif=None, groups=None, files=(), optimize=None):
    T, D, C = res["totals"], res["design"], res["counts"]
    A = res.get("attribution") or {}
    lib = res.get("_libcell", {})
    gsp, shap, gci, local = A.get("single", {}), A.get("shapley", {}), res.get("gci", {}), res.get("local", {})
    names = set(gsp) | set(sorted(local, key=lambda c: -local[c])[:300]) | set(sorted(gci, key=lambda c: -gci[c])[:100])
    Eg = T.get("E_glitch_fJ") or 1.0
    cells = [dict(cell=c, lib=lib.get(c, ""), gsp=gsp.get(c), shapley=shap.get(c), structural=gci.get(c, 0.0),
                  consumed=local.get(c, 0.0) / Eg) for c in names]
    cells.sort(key=lambda r: (-(r["gsp"] if r["gsp"] is not None else -1), -r["consumed"]))
    att = None
    if A:
        att = dict(top=A["top"], joint=A["joint_top"], naive=A["sum_single_top"],
                   greedy=[[c, g] for c, g in A["greedy"]], certified=A.get("certified", True),
                   evaluations=A.get("evaluations"), screened=A.get("screened"),
                   single_greedy=[gsp.get(c, 0.0) for c, _ in A["greedy"]])
    grp = None
    if groups:
        grp = dict(rows=[dict(group=g, size=groups["group_sizes"].get(g, 0), gsp=groups["single"][g],
                              shapley=groups["shapley"].get(g), structural=groups["structural"].get(g, 0.0))
                         for g in sorted(groups["single"], key=lambda g: -groups["single"][g])],
                   top=groups["top"], joint=groups["joint_top"], naive=groups["sum_single_top"],
                   greedy=[[g, v] for g, v in groups["greedy"]], label=groups.get("label", "groups"))
    wi = None
    if whatif:
        wi = dict(rows=whatif["rows"], best=whatif["best"], combined=whatif.get("combined"),
                  recommended=whatif.get("recommended"))
    inputs = [dict(name=n, fj=d["fJ_per_toggle"], rate=d["toggle_rate"], share=d["share"])
              for n, d in list((res.get("data_attribution") or {}).items())[:16]]
    pv = res.get("per_vector", [])
    opt = None
    if optimize:
        rows = []
        for key, label in (("original", "Original"), ("min_register", "Min-register retiming"),
                           ("timing_driven", "Timing-driven retiming"), ("glitch_aware", "GlitchScope (glitch-aware)")):
            r = optimize.get(key)
            if r and r.get("total"):
                rows.append(dict(design=label, flops=r["flops"], period_ps=r["period_ps"], total=r["total"],
                                 glitch=r["glitch"], functional=r["functional"],
                                 registers=r.get("flop_clock", 0) + r.get("flop_data", 0), power_uW=r.get("power_uW"),
                                 chosen=key == "glitch_aware"))
        opt = dict(rows=rows, latency=optimize["latency"], period_ps=optimize["period_ps"],
                   cycles=optimize["sampled_cycles"], measured=len(optimize.get("candidates", [])))
    return dict(design=D, totals=T, counts=C, cells=cells[:400], attribution=att, groups=grp, whatif=wi, optimize=opt,
                inputs=inputs, cycles=dict(fun=[round(v["E_fun"], 3) for v in pv],
                                           glitch=[round(v["E_glitch"], 3) for v in pv]),
                files=list(files), version=__version__, generated=time.strftime("%Y-%m-%d %H:%M"))


def render(data, fragment=False):
    """Full standalone HTML document; ``fragment=True`` returns only the title,
    styles and body content (for hosts that supply their own document skeleton)."""
    top = str(data["design"].get("top", "design"))[:_TITLE_MAX]
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    page = _PAGE.replace("@@TITLE@@", html.escape(f"{top} glitch report")).replace("@@DATA@@", payload)
    if fragment:
        head = page[page.index("<title>"):page.index("</head>")]
        body = page[page.index("<body>") + 6:page.index("</body>")]
        page = head.replace('<meta charset="utf-8">', "") + body
    return page


class inline:
    """Show a report.html inside a notebook cell (Jupyter, Colab, VS Code):
    ``inline("out/report.html")`` as the last line of a cell."""

    def __init__(self, path, height=1000):
        from pathlib import Path
        self.page, self.height = Path(path).read_text(encoding="utf-8"), int(height)

    def _repr_html_(self):
        return (f'<iframe srcdoc="{html.escape(self.page, quote=True)}" style="width:100%;height:{self.height}px;'
                f'border:1px solid rgba(0,0,0,.1);border-radius:8px" loading="lazy"></iframe>')


def write_html_report(path, data):
    from pathlib import Path
    Path(path).write_text(render(data), encoding="utf-8")


_PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>@@TITLE@@</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@500;600&display=swap">
<style>
/* Layout: a bench-instrument readout. Identity strip, one summary band, then
   single-column sections (where -> how -> evidence), data in tabular mono. */
:root {
  --bg: #f6f7f8; --surface: #fcfcfb; --ink: #0b0b0b; --ink-2: #52514e; --muted: #7b7a75;
  --grid: #e1e0d9; --axis: #c3c2b7; --ring: rgba(11,11,11,0.10);
  --accent: #2a78d6; --fun: #2a78d6; --glitch: #eb6834; --filtered: #1baf7a;
  --good: #0ca30c; --good-ink: #006300; --warn: #fab219; --bad: #d03b3b;
  --font-display: "IBM Plex Sans Condensed", "Arial Narrow", "Roboto Condensed", system-ui, sans-serif;
  --font-body: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --font-data: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #0f0f0f; --surface: #1a1a19; --ink: #ffffff; --ink-2: #c3c2b7; --muted: #95938c;
  --grid: #2c2c2a; --axis: #383835; --ring: rgba(255,255,255,0.10);
  --accent: #3987e5; --fun: #3987e5; --glitch: #d95926; --filtered: #199e70;
  --good: #0ca30c; --good-ink: #0ca30c; --warn: #fab219; --bad: #e66767; color-scheme: dark; } }
:root[data-theme="dark"] {
  --bg: #0f0f0f; --surface: #1a1a19; --ink: #ffffff; --ink-2: #c3c2b7; --muted: #95938c;
  --grid: #2c2c2a; --axis: #383835; --ring: rgba(255,255,255,0.10);
  --accent: #3987e5; --fun: #3987e5; --glitch: #d95926; --filtered: #199e70;
  --good: #0ca30c; --good-ink: #0ca30c; --warn: #fab219; --bad: #e66767; color-scheme: dark; }
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 15px/1.55 var(--font-body); }
.wrap { max-width: 1080px; margin: 0 auto; padding-inline: 20px; padding-block: 28px 64px; display: grid; gap: 40px; }
header.id { display: grid; gap: 10px; }
.eyebrow { font: 500 12px/1 var(--font-data); letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
h1 { font: 600 clamp(28px, 4.2vw, 40px)/1.1 var(--font-display); margin: 0; text-wrap: balance; letter-spacing: -.01em; }
h2 { font: 600 22px/1.2 var(--font-display); margin: 0; text-wrap: balance; }
h3 { font: 600 15px/1.3 var(--font-body); margin: 0; }
p { margin: 0; max-width: 68ch; color: var(--ink-2); }
.tags { display: flex; flex-wrap: wrap; gap: 6px 14px; font: 13px/1.4 var(--font-data); color: var(--ink-2); }
.tags b { color: var(--ink); font-weight: 500; }
.chip { display: inline-flex; align-items: center; gap: 6px; font: 500 12px/1 var(--font-body); padding: 5px 9px;
  border-radius: 999px; border: 1px solid var(--ring); background: var(--surface); color: var(--ink); white-space: nowrap; }
.chip i { width: 8px; height: 8px; border-radius: 50%; display: inline-block; font-style: normal; }
section { display: grid; gap: 16px; min-width: 0; }
.lede { display: grid; gap: 6px; }
.band { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 2fr); gap: 28px; align-items: center;
  background: var(--surface); border: 1px solid var(--ring); border-radius: 10px; padding: 22px; }
.hero-num { font: 600 64px/1 var(--font-display); letter-spacing: -.02em; font-variant-numeric: tabular-nums; }
.hero-num small { font-size: 24px; color: var(--ink-2); margin-left: 2px; }
.hero-cap { font-size: 13px; color: var(--ink-2); margin-top: 6px; }
.kv { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px 18px; }
.kv div { display: grid; gap: 2px; min-width: 0; }
.kv span { font-size: 12px; color: var(--muted); }
.kv b { font: 500 17px/1.2 var(--font-data); font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.panel { background: var(--surface); border: 1px solid var(--ring); border-radius: 10px; padding: 18px; min-width: 0; display: grid; gap: 12px; align-content: start; }
.chart { width: 100%; min-width: 0; }
.chart svg { display: block; width: 100%; height: auto; overflow: visible; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 13px; color: var(--ink-2); }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.legend i { width: 12px; height: 12px; border-radius: 3px; display: inline-block; }
.legend i.dash { height: 0; border-top: 2px dashed var(--muted); border-radius: 0; width: 16px; }
.legend i.line { height: 0; border-top: 2px solid var(--accent); border-radius: 0; width: 16px; }
.split { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; align-items: start; }
.tbl { overflow-x: auto; border: 1px solid var(--ring); border-radius: 10px; background: var(--surface); }
table { border-collapse: collapse; width: 100%; font-size: 13.5px; }
th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--grid); white-space: nowrap; }
tr:last-child td { border-bottom: 0; }
th { font: 500 12px/1.3 var(--font-body); color: var(--muted); letter-spacing: .02em; position: sticky; top: 0; background: var(--surface); }
th[data-k] { cursor: pointer; user-select: none; }
th[data-k]:hover, th[data-k]:focus-visible { color: var(--ink); }
th .arr { opacity: .7; margin-left: 4px; }
td.num, th.num { text-align: right; font-family: var(--font-data); font-variant-numeric: tabular-nums; }
td.mono { font-family: var(--font-data); }
td.textwrap { white-space: normal; min-width: 22ch; max-width: 46ch; }
.bar { display: inline-block; vertical-align: middle; height: 8px; border-radius: 0 4px 4px 0; background: var(--accent); margin-right: 8px; }
.bar.neg { background: var(--muted); }
.tools { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
input[type=search] { font: 14px var(--font-body); padding: 8px 10px; border-radius: 8px; border: 1px solid var(--axis);
  background: var(--surface); color: var(--ink); min-width: 0; width: min(320px, 100%); }
input[type=search]:focus-visible, button:focus-visible, th[data-k]:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
button.tab { font: 500 13px var(--font-body); padding: 7px 12px; border-radius: 8px; border: 1px solid var(--ring);
  background: transparent; color: var(--ink-2); cursor: pointer; }
button.tab[aria-pressed="true"] { background: var(--surface); color: var(--ink); border-color: var(--axis); }
.note { font-size: 13px; color: var(--muted); max-width: 80ch; }
.muted { color: var(--muted); font-size: 12px; }
.callout { border-left: 3px solid var(--accent); padding: 4px 0 4px 14px; display: grid; gap: 4px; }
.callout b { font-family: var(--font-data); font-weight: 500; }
.files { font: 13px/1.8 var(--font-data); color: var(--ink-2); columns: 2 260px; }
#tip { position: fixed; pointer-events: none; z-index: 10; background: var(--surface); color: var(--ink);
  border: 1px solid var(--ring); border-radius: 8px; padding: 8px 10px; font: 12.5px/1.45 var(--font-body);
  box-shadow: 0 6px 24px rgba(0,0,0,.14); max-width: 280px; }
#tip b { font-family: var(--font-data); font-weight: 500; }
.axis text, .lab { fill: var(--muted); font: 11px var(--font-data); }
.lab.ink { fill: var(--ink-2); }
footer { font-size: 12.5px; color: var(--muted); display: grid; gap: 6px; border-top: 1px solid var(--grid); padding-top: 18px; }
@media (max-width: 760px) {
  .band, .split { grid-template-columns: minmax(0, 1fr); }
  .kv { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .hero-num { font-size: 52px; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>
</head>
<body>
<div class="wrap" id="app"></div>
<div id="tip" hidden></div>
<script id="gs-data" type="application/json">@@DATA@@</script>
<script>
(function () {
"use strict";
const D = JSON.parse(document.getElementById("gs-data").textContent);
const $ = (s, el) => (el || document).querySelector(s);
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const pct = (v, d) => v == null ? "–" : (100 * v).toFixed(d == null ? (Math.abs(v) < 0.01 && v !== 0 ? 2 : 1) : d) + " %";
const spct = (v, d) => v == null ? "–" : (v >= 0 ? "+" : "−") + Math.abs(v).toFixed(d == null ? 2 : d) + " %";
const fj = v => v >= 1e4 ? (v / 1e3).toFixed(1) + " pJ" : v.toFixed(1) + " fJ";
const T = D.totals, G = D.design, n = Math.max(1, G.cycles || D.cycles.fun.length);
const tip = $("#tip");
function showTip(e, h) { tip.innerHTML = h; tip.hidden = false; moveTip(e); }
function moveTip(e) { const w = tip.offsetWidth, h = tip.offsetHeight;
  let x = e.clientX + 14, y = e.clientY + 14;
  if (x + w > innerWidth - 8) x = e.clientX - w - 14; if (y + h > innerHeight - 8) y = e.clientY - h - 14;
  tip.style.left = Math.max(8, x) + "px"; tip.style.top = Math.max(8, y) + "px"; }
function hideTip() { tip.hidden = true; }
function hoverable(el, html) { el.addEventListener("mouseenter", e => showTip(e, html)); el.addEventListener("mousemove", moveTip);
  el.addEventListener("mouseleave", hideTip); }
const svgNS = "http://www.w3.org/2000/svg";
function S(tag, attrs, parent) { const e = document.createElementNS(svgNS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
function niceMax(v) { if (v <= 0) return 1; const p = Math.pow(10, Math.floor(Math.log10(v))); const m = v / p;
  return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10) * p; }

/* ---------- page skeleton ---------- */
const app = $("#app");
const oc = G.output_check || {};
const ocChip = oc.checked ? (oc.mismatches === 0
  ? `<span class="chip"><i style="background:var(--good)"></i>Outputs match testbench · ${oc.checked}/${oc.checked}</span>`
  : `<span class="chip"><i style="background:var(--bad)"></i>${oc.mismatches} output mismatches of ${oc.checked}</span>`) : "";
const unc = Object.keys(G.uncalibrated_cells || {}), prox = Object.keys(G.proxy_calibrated_cells || {});
app.insertAdjacentHTML("beforeend", `
<header class="id">
  <div class="eyebrow">GlitchScope ${esc(D.version)} · glitch power report</div>
  <h1>${esc(G.top)}</h1>
  <div class="tags"><span><b>${G.cells}</b> cells</span><span><b>${G.flops || 0}</b> flops</span>
    <span><b>${n}</b> ${G.flops ? "clock cycles" : "vectors"}</span>
    ${G.clock_period_ps ? `<span>period <b>${(+G.clock_period_ps).toFixed(0)} ps</b></span>` : ""}
    <span>pulse model <b>${esc(G.model)}</b></span><span>SKY130 HD · TT 25 °C 1.80 V</span></div>
  <div class="tools">${ocChip}${unc.length ? `<span class="chip"><i style="background:var(--warn)"></i>${unc.length} cell types without pulse calibration</span>` : ""}</div>
</header>
<section class="band" aria-label="Summary">
  <div><div class="hero-num">${(100 * T.glitch_fraction).toFixed(1)}<small>%</small></div>
    <div class="hero-cap">of dynamic energy is spent on glitches</div></div>
  <div class="kv">
    <div><span>Glitch energy / ${G.flops ? "cycle" : "vector"}</span><b>${fj(T.E_glitch_fJ / n)}</b></div>
    <div><span>Functional energy / ${G.flops ? "cycle" : "vector"}</span><b>${fj(T.E_functional_fJ / n)}</b></div>
    <div><span>Glitch transitions</span><b>${(D.counts.glitch_transitions || 0).toLocaleString()}</b></div>
    <div><span>Generated · propagated</span><b>${(D.counts.GENERATED || 0).toLocaleString()} · ${(D.counts.PROPAGATED || 0).toLocaleString()}</b></div>
    <div><span>Merged · filtered</span><b>${(D.counts.MERGED || 0).toLocaleString()} · ${(D.counts.FILTERED || 0).toLocaleString()}</b></div>
    <div><span>Filtered-pulse energy</span><b>${pct(T.E_glitch_filtered_fJ / (T.E_glitch_fJ || 1))} of glitch</b></div>
  </div>
</section>`);

/* ---------- energy per cycle ---------- */
const secE = document.createElement("section");
secE.innerHTML = `<div class="lede"><h2>Energy per ${G.flops ? "clock cycle" : "vector"}</h2>
  <p>Functional transitions are the ones the logic needs. Everything above them is glitch energy: extra transitions and pulses that the gates filtered but still paid for.</p></div>
  <div class="panel"><div class="legend"><span><i style="background:var(--fun)"></i>Functional</span><span><i style="background:var(--glitch)"></i>Glitch</span></div>
  <div class="chart" id="c-cycles"></div></div>`;
app.appendChild(secE);

function drawCycles() {
  const el = $("#c-cycles"); el.innerHTML = "";
  let F = D.cycles.fun, Gl = D.cycles.glitch, step = 1;
  const W = Math.max(300, el.clientWidth), H = 220, m = {l: 54, r: 8, t: 8, b: 26};
  const maxBars = Math.floor((W - m.l - m.r) / 3);
  if (F.length > maxBars) { step = Math.ceil(F.length / maxBars);
    const agg = a => { const o = []; for (let i = 0; i < a.length; i += step) { let s = 0, c = 0;
      for (let j = i; j < Math.min(a.length, i + step); j++) { s += a[j]; c++; } o.push(s / c); } return o; };
    F = agg(F); Gl = agg(Gl); }
  const N = F.length, ymax = niceMax(Math.max(1e-9, ...F.map((f, i) => f + Gl[i])));
  const svg = S("svg", {viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Functional and glitch energy per step"}, el);
  const iw = W - m.l - m.r, ih = H - m.t - m.b, bw = iw / N, gap = bw > 4 ? 1 : 0;
  const ax = S("g", {class: "axis"}, svg);
  for (let k = 0; k <= 4; k++) { const v = ymax * k / 4, y = m.t + ih - ih * k / 4;
    S("line", {x1: m.l, x2: W - m.r, y1: y, y2: y, stroke: k ? "var(--grid)" : "var(--axis)", "stroke-width": 1}, ax);
    S("text", {x: m.l - 8, y: y + 4, "text-anchor": "end"}, ax).textContent = v >= 1000 ? (v / 1000).toFixed(1) + " pJ" : v.toFixed(0) + " fJ"; }
  const ticks = Math.min(6, N);
  for (let k = 0; k < ticks; k++) { const i = Math.round(k * (N - 1) / Math.max(1, ticks - 1));
    S("text", {x: m.l + (i + .5) * bw, y: H - 8, "text-anchor": "middle"}, ax).textContent = (i * step + 1); }
  for (let i = 0; i < N; i++) {
    const x = m.l + i * bw, hf = ih * F[i] / ymax, hg = ih * Gl[i] / ymax, w = Math.max(.6, bw - gap);
    const g = S("g", {}, svg);
    S("rect", {x, y: m.t + ih - hf, width: w, height: hf, fill: "var(--fun)"}, g);
    S("rect", {x, y: m.t + ih - hf - hg, width: w, height: Math.max(0, hg - (hg > 2 && bw > 4 ? 1 : 0)), fill: "var(--glitch)"}, g);
    const hit = S("rect", {x: x - 1, y: m.t, width: bw + 2, height: ih, fill: "transparent"}, g);
    const lab = step > 1 ? `${G.flops ? "Cycles" : "Vectors"} ${i * step + 1}–${Math.min(D.cycles.fun.length, (i + 1) * step)} (mean)` : `${G.flops ? "Cycle" : "Vector"} ${i + 1}`;
    hoverable(hit, `${lab}<br>Functional <b>${fj(F[i])}</b><br>Glitch <b>${fj(Gl[i])}</b> · ${pct(Gl[i] / Math.max(1e-12, F[i] + Gl[i]))}`);
  }
}

/* ---------- where to fix ---------- */
const A = D.attribution;
function drawJoint(el, R, unitWord) {
  // cumulative saving of the greedy fix set vs the naive sum of single savings
  el.innerHTML = "";
  const W = Math.max(280, el.clientWidth), H = 220, m = {l: 44, r: 12, t: 12, b: 30};
  const k = R.greedy.length, act = [0, ...R.greedy.map(g => g[1])];
  const naive = [0]; R.single_greedy.forEach((v, i) => naive.push(naive[i] + v));
  const ymax = niceMax(Math.max(...act, ...naive, 0.01));
  const svg = S("svg", {viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Joint saving versus naive sum"}, el);
  const iw = W - m.l - m.r, ih = H - m.t - m.b, X = i => m.l + iw * i / Math.max(1, k), Y = v => m.t + ih - ih * v / ymax;
  const ax = S("g", {class: "axis"}, svg);
  for (let t = 0; t <= 4; t++) { const v = ymax * t / 4;
    S("line", {x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), stroke: t ? "var(--grid)" : "var(--axis)"}, ax);
    S("text", {x: m.l - 6, y: Y(v) + 4, "text-anchor": "end"}, ax).textContent = (+(100 * v).toFixed(1)) + "%"; }
  for (let i = 0; i <= k; i++) S("text", {x: X(i), y: H - 10, "text-anchor": "middle"}, ax).textContent = i;
  const path = a => a.map((v, i) => (i ? "L" : "M") + X(i).toFixed(1) + " " + Y(v).toFixed(1)).join(" ");
  S("path", {d: path(naive), fill: "none", stroke: "var(--muted)", "stroke-width": 2, "stroke-dasharray": "5 4"}, svg);
  S("path", {d: path(act), fill: "none", stroke: "var(--accent)", "stroke-width": 2}, svg);
  act.forEach((v, i) => { if (!i) return;
    const c = S("circle", {cx: X(i), cy: Y(v), r: 4.5, fill: "var(--accent)", stroke: "var(--surface)", "stroke-width": 2}, svg);
    const hit = S("circle", {cx: X(i), cy: Y(v), r: 12, fill: "transparent"}, svg);
    hoverable(hit, `Fix ${i} ${unitWord}${i > 1 ? "s" : ""} (+ <b>${esc(R.greedy[i - 1][0])}</b>)<br>Joint saving <b>${pct(v)}</b><br>Naive sum would claim ${pct(naive[i])}`); });
  S("text", {x: X(k) - 4, y: Y(act[k]) - 10, "text-anchor": "end", class: "lab ink"}, svg).textContent = pct(act[k]) + " joint";
  if (Math.abs(Y(naive[k]) - Y(act[k])) > 14)
    S("text", {x: X(k) - 4, y: Y(naive[k]) - 8, "text-anchor": "end", class: "lab"}, svg).textContent = pct(naive[k]) + " naive";
}

function sortableTable(cols, rows, opts) {
  opts = opts || {};
  const wrap = document.createElement("div"); wrap.className = "tbl";
  const t = document.createElement("table"); wrap.appendChild(t);
  let key = opts.sort || null, dir = opts.dir || -1, filter = "";
  function render() {
    let rs = rows.filter(r => !filter || cols.some(c => c.search && String(r[c.k] || "").toLowerCase().includes(filter)));
    if (key) rs = rs.slice().sort((a, b) => { const x = a[key], y = b[key];
      if (x == null && y == null) return 0; if (x == null) return 1; if (y == null) return -1;
      return (typeof x === "string" ? x.localeCompare(y) : x - y) * dir; });
    const lim = opts.limit || 1e9;
    t.innerHTML = "<thead><tr>" + cols.map(c => `<th ${c.sort !== false ? `data-k="${c.k}" tabindex="0"` : ""} class="${c.num ? "num" : ""}" scope="col">${esc(c.label)}${key === c.k ? `<span class="arr">${dir < 0 ? "↓" : "↑"}</span>` : ""}</th>`).join("") + "</tr></thead><tbody>" +
      rs.slice(0, lim).map(r => "<tr>" + cols.map(c => `<td class="${c.num ? "num" : c.cls || ""}">${c.fmt ? c.fmt(r[c.k], r) : esc(r[c.k] == null ? "–" : r[c.k])}</td>`).join("") + "</tr>").join("") +
      (rs.length > lim ? `<tr><td colspan="${cols.length}" class="note">${rs.length - lim} more rows — refine the search to see them</td></tr>` : "") +
      (rs.length ? "" : `<tr><td colspan="${cols.length}" class="note">No rows match.</td></tr>`) + "</tbody>";
    t.querySelectorAll("th[data-k]").forEach(th => { const go = () => { const k = th.dataset.k; dir = key === k ? -dir : -1; key = k; render(); };
      th.addEventListener("click", go); th.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } }); });
  }
  render();
  return {el: wrap, setFilter: f => { filter = f.trim().toLowerCase(); render(); }};
}
const barCell = (max) => (v) => v == null ? "–" : `<span class="bar ${v < 0 ? "neg" : ""}" style="width:${Math.max(1, 64 * Math.abs(v) / max).toFixed(1)}px"></span>${pct(v)}`;

if (A || D.groups) {
  const sec = document.createElement("section");
  const R = A;
  let lede = `<div class="lede"><h2>Where to fix</h2><p>Suppression potential is measured, not traced: GlitchScope re-simulates the design with a gate made glitch-free (it switches once, straight to its final value) and reports how much glitch energy disappears. Fixes interact, so the saving of a set is measured as a set.</p></div>`;
  sec.innerHTML = lede;
  if (D.groups) {
    const Gr = D.groups, mx = Math.max(...Gr.rows.map(r => Math.abs(r.gsp)), 1e-9);
    const p = document.createElement("div"); p.className = "split";
    p.innerHTML = `<div class="panel"><h3>Groups: best joint fix set</h3><div class="legend"><span><i class="line"></i>Measured joint saving</span><span><i class="dash"></i>Naive sum of single savings</span></div><div class="chart" id="c-gjoint"></div>
      <p class="note" id="n-gjoint"></p></div>`;
    const tb = sortableTable([
      {k: "group", label: "Group", cls: "mono", search: true},
      {k: "size", label: "Cells", num: true},
      {k: "gsp", label: "Suppression potential", num: true, fmt: barCell(mx)},
      {k: "structural", label: "Traced credit", num: true, fmt: v => pct(v)}], Gr.rows, {sort: "gsp", limit: 24});
    const box = document.createElement("div"); box.className = "panel"; box.innerHTML = "<h3>All groups</h3>"; box.appendChild(tb.el);
    p.appendChild(box); sec.appendChild(p);
    Gr.single_greedy = Gr.greedy.map(g => (Gr.rows.find(r => r.group === g[0]) || {}).gsp || 0);
    p.querySelector("#n-gjoint").innerHTML = `${esc(Gr.label)}. Best joint set: ${Gr.greedy.map(g => esc(g[0])).join(" → ")} removes <b>${pct(Gr.greedy[Gr.greedy.length - 1][1])}</b> of glitch energy; adding their single savings would claim ${pct(Gr.single_greedy.reduce((a, b) => a + b, 0))}.`;
  }
  if (R) {
    const p = document.createElement("div"); p.className = "split";
    p.innerHTML = `<div class="panel"><h3>Cells: best joint fix set</h3><div class="legend"><span><i class="line"></i>Measured joint saving</span><span><i class="dash"></i>Naive sum of single savings</span></div><div class="chart" id="c-joint"></div>
      <p class="note">Best joint set: ${R.greedy.map(g => esc(g[0])).join(" → ")} removes <b>${pct(R.greedy.length ? R.greedy[R.greedy.length - 1][1] : 0)}</b> of glitch energy; their single savings add up to ${pct(R.single_greedy.reduce((a, b) => a + b, 0))}.${R.certified ? "" : " Large design: the search evaluated the " + R.screened + " most promising cells, so the ranking is not guaranteed exhaustive."}</p></div>
      <div class="panel"><h3>What the numbers mean</h3>
      <div class="callout"><b>Suppression potential</b><span>Glitch energy removed if this gate alone were glitch-free. Ranks where to fix.</span></div>
      <div class="callout"><b>Shapley share</b><span>Fair split of the joint saving of the top cells, interactions included. Shares add up to the joint saving.</span></div>
      <div class="callout"><b>Traced credit</b><span>Shown for comparison only: the usual trace-and-sum method, crediting each glitch back to the gate that started it. It can miss gates that would be the best fixes.</span></div>
      <div class="callout"><b>Energy consumed</b><span>Glitch energy burnt at the gate's own output. Where the power goes, not where to fix it.</span></div></div>`;
    sec.appendChild(p);
  }
  const mx = Math.max(...D.cells.map(r => Math.abs(r.gsp || 0)), 1e-9);
  const tb = sortableTable([
    {k: "cell", label: "Cell", cls: "mono", search: true},
    {k: "lib", label: "Library cell", cls: "mono", search: true, fmt: v => esc((v || "").replace("sky130_fd_sc_hd__", ""))},
    {k: "gsp", label: "Suppression potential", num: true, fmt: barCell(mx)},
    {k: "shapley", label: "Shapley share", num: true, fmt: v => pct(v)},
    {k: "structural", label: "Traced credit", num: true, fmt: v => pct(v)},
    {k: "consumed", label: "Energy consumed", num: true, fmt: v => pct(v)}], D.cells, {sort: R ? "gsp" : "consumed", limit: 30});
  const box = document.createElement("div"); box.className = "panel";
  box.innerHTML = `<div class="tools" style="justify-content:space-between"><h3>Cells</h3><input type="search" id="q-cells" placeholder="Filter by cell or library cell" aria-label="Filter cells"></div>`;
  box.appendChild(tb.el); sec.appendChild(box);
  app.appendChild(sec);
  box.querySelector("#q-cells").addEventListener("input", e => tb.setFilter(e.target.value));
}

/* ---------- how to fix ---------- */
if (D.whatif) {
  const Wf = D.whatif, sec = document.createElement("section");
  const rec = Wf.recommended, comb = Wf.combined;
  const status = r => r.dE_total_fJ < 0
    ? (r.settle_after_ps <= r.settle_before_ps + 1e-6 ? `<span class="chip"><i style="background:var(--good)"></i>Saves energy</span>`
                                                       : `<span class="chip"><i style="background:var(--warn)"></i>Saves energy, slower</span>`)
    : `<span class="chip"><i style="background:var(--bad)"></i>Costs energy</span>`;
  sec.innerHTML = `<div class="lede"><h2>How to fix</h2><p>Each edit keeps the logic function and is measured by re-simulating every ${G.flops ? "cycle" : "vector"} it can affect: resizing the gate, swapping its symmetric input pins, or resizing the gates that drive it. Settling time is the latest transition seen after the ${G.flops ? "clock edge" : "input change"}, a timing hint rather than sign-off STA.</p></div>`;
  if (rec) {
    const c = rec, together = rec.recommended_as === "combined";
    const interf = !together && comb ? `<p class="note">Applying the best edit of every cell together was also measured (${spct(comb.dE_total_pct)} total): the edits interfere, so the single best edit is recommended.</p>` : "";
    sec.insertAdjacentHTML("beforeend", `<div class="panel"><h3>${together ? "Recommended edits, applied together" : "Recommended edit"}</h3>
      <div class="kv"><div><span>Total dynamic energy</span><b>${spct(c.dE_total_pct)}</b></div>
      <div><span>Glitch energy</span><b>${spct(c.dE_glitch_pct)}</b></div>
      <div><span>Worst settling time</span><b>${c.settle_before_ps.toFixed(0)} → ${c.settle_after_ps.toFixed(0)} ps</b></div></div>
      <p class="note">${together ? "" : "For cell " + esc(c.cell) + ": "}${esc(c.edit)}</p>${interf}</div>`);
  } else {
    sec.insertAdjacentHTML("beforeend", `<div class="panel"><h3>No local edit pays off</h3><p class="note">None of the evaluated resizes or pin swaps lowered total energy without slowing the design. The glitches here come from path structure; see the joint fix sets above.</p></div>`);
  }
  const tb = sortableTable([
    {k: "cell", label: "For cell", cls: "mono", search: true},
    {k: "edit", label: "Edit", cls: "textwrap", search: true},
    {k: "dE_total_pct", label: "Δ total energy", num: true, fmt: v => spct(v)},
    {k: "dE_glitch_pct", label: "Δ glitch energy", num: true, fmt: v => spct(v)},
    {k: "settle_after_ps", label: "Settling (ps)", num: true, fmt: (v, r) => `${r.settle_before_ps.toFixed(0)} → ${v.toFixed(0)}`},
    {k: "steps_resimulated", label: G.flops ? "Cycles re-run" : "Vectors re-run", num: true},
    {k: "dE_total_fJ", label: "Verdict", sort: false, fmt: (v, r) => status(r)}], Wf.rows, {sort: "dE_total_pct", dir: 1, limit: 40});
  const box = document.createElement("div"); box.className = "panel";
  box.innerHTML = `<div class="tools" style="justify-content:space-between"><h3>All evaluated edits</h3><input type="search" id="q-edits" placeholder="Filter by cell or edit" aria-label="Filter edits"></div>`;
  box.appendChild(tb.el); sec.appendChild(box); app.appendChild(sec);
  box.querySelector("#q-edits").addEventListener("input", e => tb.setFilter(e.target.value));
}

/* ---------- reduce it: register placement ---------- */
if (D.optimize && D.optimize.rows.length) {
  const O = D.optimize, sec = document.createElement("section");
  const o = O.rows[0], g = O.rows.find(r => r.chosen);
  sec.innerHTML = `<div class="lede"><h2>Reduce it: register placement</h2><p>The registers are moved${O.latency ? ` (and ${O.latency} pipeline stage${O.latency > 1 ? "s" : ""} added)` : ""} so that they stop glitches where they cost most, keeping the clock period. Every candidate netlist is re-simulated with the same stimulus, its outputs checked against the original on every cycle, and its total energy measured: logic, glitches, and the flip-flops with their share of the clock tree. ${O.measured} placements were measured.</p></div>`;
  if (g) {
    sec.insertAdjacentHTML("beforeend", `<div class="panel"><h3>Written to optimized.v</h3>
      <div class="kv"><div><span>Total energy per cycle</span><b>${spct(100 * (g.total / o.total - 1), 1)}</b></div>
      <div><span>Glitch energy</span><b>${o.glitch.toFixed(0)} → ${g.glitch.toFixed(0)} fJ</b></div>
      <div><span>Flip-flops</span><b>${o.flops} → ${g.flops}</b></div></div>
      <p class="note">Same function and ${O.latency ? `+${O.latency} cycle` : "the same"} latency, verified cycle by cycle. Confirm timing and power after place and route.</p></div>`);
  } else {
    sec.insertAdjacentHTML("beforeend", `<div class="panel"><h3>Keep the registers where they are</h3><p class="note">No measured placement lowered total energy: the extra flip-flops would cost more than the glitches they remove.</p></div>`);
  }
  const tb = sortableTable([
    {k: "design", label: "Register placement"},
    {k: "total", label: "Total (fJ/cycle)", num: true, fmt: (v, r) => `${v.toFixed(0)} <span class="muted">${r === o ? "" : spct(100 * (v / o.total - 1), 1)}</span>`},
    {k: "glitch", label: "Glitch", num: true, fmt: v => v.toFixed(0)},
    {k: "functional", label: "Functional", num: true, fmt: v => v.toFixed(0)},
    {k: "registers", label: "Flip-flops + clock", num: true, fmt: v => v.toFixed(0)},
    {k: "flops", label: "Flip-flops", num: true},
    {k: "period_ps", label: "Critical path (ps)", num: true, fmt: v => v.toFixed(0)}], O.rows, {sort: "total", dir: 1});
  const box = document.createElement("div"); box.className = "panel"; box.appendChild(tb.el); sec.appendChild(box);
  app.appendChild(sec);
}

/* ---------- inputs ---------- */
if (D.inputs && D.inputs.length) {
  const sec = document.createElement("section");
  sec.innerHTML = `<div class="lede"><h2>Which input bits trigger glitches</h2><p>A least-squares fit of each ${G.flops ? "cycle" : "vector"}'s glitch energy on which inputs and register bits toggled. Useful for data-dependent power: operand gating, encoding, or reordering.</p></div>`;
  const mx = Math.max(...D.inputs.map(r => Math.abs(r.fj)), 1e-9);
  const tb = sortableTable([
    {k: "name", label: "Input or state bit", cls: "mono", search: true},
    {k: "fj", label: "Glitch energy per toggle", num: true, fmt: v => `<span class="bar ${v < 0 ? "neg" : ""}" style="width:${Math.max(1, 64 * Math.abs(v) / mx).toFixed(1)}px"></span>${v.toFixed(1)} fJ`},
    {k: "rate", label: "Toggle rate", num: true, fmt: v => pct(v, 0)},
    {k: "share", label: "Share of glitch energy", num: true, fmt: v => pct(v)}], D.inputs, {sort: "share"});
  sec.appendChild(tb.el); app.appendChild(sec);
}

/* ---------- footer ---------- */
app.insertAdjacentHTML("beforeend", `<footer>
  ${D.files.length ? `<div><b>Files written next to this report</b><div class="files">${D.files.map(esc).join("<br>")}</div></div>` : ""}
  <div>Event-driven simulation with Liberty NLDM timing; pulse filtering by the SPICE-calibrated M2 model (ngspice + SKY130A); energy from Liberty internal power plus ½CV², scaled per cell to SPICE where calibrated.${prox.length ? " Drive-strength variants without their own calibration use the same function's calibration: " + esc(prox.join(", ")) + "." : ""} Generated ${esc(D.generated)}.</div>
</footer>`);

function drawAll() { drawCycles(); if (A) drawJoint($("#c-joint"), A, "cell"); if (D.groups) drawJoint($("#c-gjoint"), D.groups, "group"); }
drawAll();
let rt; addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(drawAll, 120); });
})();
</script>
</body>
</html>
"""
