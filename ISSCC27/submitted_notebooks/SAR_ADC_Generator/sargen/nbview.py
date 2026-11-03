"""Display helpers for the notebook: figure style and numbering, result tables, the summary tables, layout
galleries.  Kept here so the notebook's cells show results and the figure code that matters, not plumbing."""

import base64
import json
import math
import re
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from IPython.display import HTML, Image, Markdown, display
from matplotlib.colors import LinearSegmentedColormap
from mpl_toolkits.mplot3d import proj3d

R = Path("results")
INK, NOTE, MUTED, GRID = "#1d2330", "#4b5563", "#6b7280", "#d7dbe0"
BLUE, ORANGE, GREY = "#2a78d6", "#eb6834", "#b9bdc5"
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
BLUES = LinearSegmentedColormap.from_list("blues", ["#e8f1fb", "#9cc3ee", "#2a78d6", "#123f78"])
RAMP = LinearSegmentedColormap.from_list("ramp", ["#9cc3ee", "#2a78d6", "#123f78"])

_UNIT = re.compile(r"(?<=[\d\s\[(/%~-])u(m\^2|m|V|W|A)\b")


def units(text):
    """Plain-ASCII units of the result files as typeset: um -> \u00b5m, um^2 -> \u00b5m\u00b2, uV / uW / uA likewise."""
    return _UNIT.sub(lambda m: "\u00b5" + m.group(1).replace("^2", "\u00b2"), str(text))


# ---------------------------------------------------------------- numbering (stable when a cell is re-run)
_num = {"fig": {}, "tab": {}}


def _n(kind, key):
    d = _num[kind]
    return d.setdefault(key, len(d) + 1)


# ---------------------------------------------------------------- figures
def style3d(ax):
    for a in (ax.xaxis, ax.yaxis, ax.zaxis):
        a.pane.set_facecolor("#f7f8fa")
        a.pane.set_edgecolor(GRID)
        a._axinfo["grid"].update(color=GRID, linewidth=0.6)
    ax.tick_params(labelsize=9.5, colors=INK)


def heading(fig, title, note, y=0.955):
    """Numbered figure title and a one-line note, drawn into the figure."""
    fig.text(0.03, y, f"Fig. {_n('fig', title)}.  {title}", fontsize=15, fontweight="bold", color=INK)
    fig.text(0.03, y - 0.045, note, fontsize=10.5, color=NOTE, va="top")


def pin(fig, ax, x, y, z, text="", dx=0.0, dy=0.0, marker=True, ha="center", va="bottom", **kw):
    """A marker / label that stays in front of 3D surfaces: project the 3D point, then draw in figure coordinates."""
    fig.canvas.draw()
    X, Y, _ = proj3d.proj_transform(x, y, z, ax.get_proj())
    fx, fy = fig.transFigure.inverted().transform(ax.transData.transform((X, Y)))
    if marker:
        fig.add_artist(plt.Line2D([fx], [fy], marker="o", ms=6.5, color=INK, mec="white", mew=1.2))
    if text:
        if dx or dy:
            fig.add_artist(plt.Line2D([fx, fx + dx], [fy, fy + dy], color=MUTED, lw=0.8))
        fig.text(fx + dx, fy + dy, text, ha=ha, va=va, **{"color": INK, **kw})
    return fx, fy


def render(fig):
    """Show a figure as a PNG with a 192-colour palette: flat-colour figures stay sharp at about 1/3 of the size."""
    from PIL import Image as PILImage
    raw, small = BytesIO(), BytesIO()
    fig.savefig(raw, format="png", dpi=100, facecolor="white")
    plt.close(fig)
    PILImage.open(raw).convert("RGB").quantize(colors=192, dither=PILImage.Dither.NONE).save(small, "PNG", optimize=True)
    display(Image(data=small.getvalue()))


def figure(path, caption, width=None):
    """A PNG produced by the flow, with a numbered caption under it."""
    p = Path(path)
    if not p.exists():
        print(f"({p} not generated yet)")
        return
    display(Image(filename=str(p), width=width) if width else Image(filename=str(p)))
    display(Markdown(f"**Fig. {_n('fig', caption)}.** {units(caption)}"))


def insight(text):
    display(Markdown(f"**Key insight:** {units(text)}"))


def animation(path, caption, width=760):
    """The GIF as an inline <img> (renders in Jupyter, Colab, GitHub and HTML exports alike), with a caption."""
    p = Path(path)
    if p.exists():
        b64 = base64.b64encode(p.read_bytes()).decode()
        display(HTML(f'<img src="data:image/gif;base64,{b64}" width="{width}" alt="SAR conversion animation">'))
        display(Markdown(f"**Fig. {_n('fig', caption)}.** {units(caption)}"))


# ---------------------------------------------------------------- tables
HEAD = {"enob": "ENOB [bit]", "ideal_enob": "ENOB, ideal quantizer", "sndr": "SNDR [dB]", "sndr_db": "SNDR [dB]",
        "sfdr_db": "SFDR [dB]", "dnl": "max DNL [LSB]", "inl": "max INL [LSB]", "dnl_t": "max DNL [LSB]",
        "inl_t": "max INL [LSB]", "missing": "missing codes", "offset": "offset [LSB]", "offset_lsb": "offset [LSB]",
        "gain_lsb": "gain error [LSB]", "p_uw": "power [µW]", "e_pj": "energy / conv. [pJ]",
        "fom_fj": "Walden FoM [fJ/step]", "ctot_ff": "C_total [fF]", "cu_ff": "C_unit [fF]", "w_in": "W input pair [µm]",
        "mc_dnl_p99": "MC DNL, 99th pct. [LSB]", "runtime_min": "run time [min]", "fs": "f_s [MS/s]", "bits": "bits",
        "point": "condition", "power [uW]": "power [µW]", "size [um]": "size [µm]", "area [um^2]": "area [µm²]"}
DROP = {"corner", "temp", "vdd", "f_in", "dnl_max", "inl_max"}     # repeated in the row label / the other DNL column


def _num_fmt(c):
    """Numbers to a readable precision; tiny round-off to 0; nan to a dash."""
    s = c.strip()
    try:
        v = float(s)
    except ValueError:
        return c
    if s.lower() in ("nan", "+nan", "-nan") or math.isnan(v):
        return "–"
    if s.isdigit() or (s.startswith(("+", "-")) and s[1:].isdigit()):
        return s
    sign = "+" if s.startswith("+") else ""
    a = abs(v)
    if a < 5e-4:
        return "0"
    out = f"{v:.0f}" if a >= 100 else f"{v:.1f}" if a >= 10 else f"{v:.2f}" if a >= 1 else f"{v:.3f}"
    return sign + out if v >= 0 else out


def _rows(text):
    """Header and rows of every markdown table line in `text`, with the notes (non-table lines) kept apart."""
    head, rows, notes = None, [], []
    for ln in text.splitlines():
        if ln.startswith("|"):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if head is None:
                head = cells
            elif not set("".join(cells)) <= set("-: "):
                rows.append(cells)
        elif ln.strip() and not ln.startswith("#"):
            notes.append(ln.strip())
    return head, rows, notes


def table(src, caption=None, cols=None, fold="auto", fmt=True):
    """Result table(s) from a markdown file or text, with readable headers and numbers and a numbered caption.
    A file with several tables shows each (a '### title' line above a table becomes its caption).
    cols: header names (raw or readable) to keep, in order; fold: True / False / "auto" (collapsed if > 12 rows)."""
    if isinstance(src, Path) or (isinstance(src, str) and src.endswith(".md") and "\n" not in src):
        if not Path(src).exists():
            print(f"({src} not generated yet)")
            return
        src = Path(src).read_text()
    blocks, cur, title = [], [], None
    for ln in str(src).splitlines() + [""]:
        if ln.startswith("#"):
            title = ln.lstrip("#").strip()
        elif ln.strip():
            cur.append(ln)
        elif cur:
            blocks.append((title, "\n".join(cur)))
            cur, title = [], None
    first = True
    for t, text in blocks:
        head, rows, notes = _rows(text)
        if head is None:                          # a note between tables
            display(Markdown(units(text)))
            continue
        cap = caption if first and caption else t
        first = False
        _one_table(head, rows, notes, cap, cols, fold, fmt)


def _one_table(head, rows, notes, caption, cols, fold, fmt):
    fs_col = head.index("fs") if "fs" in head else None
    keep = [i for i, h in enumerate(head) if h not in DROP]
    if cols:
        keep = [i for c in cols for i, h in enumerate(head) if h == c or HEAD.get(h) == c]
    out_head = [units(HEAD.get(head[i], head[i])) for i in keep]
    body = []
    for r in rows:
        r = r + [""] * (len(head) - len(r))
        if fs_col is not None:
            try:
                r[fs_col] = f"{float(r[fs_col]) / 1e6:g}"
            except ValueError:
                pass
        body.append([units(_num_fmt(r[i]) if fmt else r[i]) for i in keep])
    notes = [units(n) for n in notes]
    caption = units(caption) if caption else caption
    num = f"Table {_n('tab', caption)}." if caption else ""
    if fold is True or (fold == "auto" and len(body) > 12):
        th = "".join(f"<th>{h}</th>" for h in out_head)
        trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in body)
        display(HTML(f"<details><summary><b>{num}</b> {caption or ''} <i>(click to expand: {len(body)} rows)</i>"
                     f"</summary><table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>"
                     + "".join(f"<p>{n}</p>" for n in notes) + "</details>"))
        return
    md = ([f"**{num}** {caption}", ""] if caption else []) + ["| " + " | ".join(out_head) + " |",
                                                               "|" + "---|" * len(out_head)]
    md += ["| " + " | ".join(r) + " |" for r in body]
    md += [""] + notes if notes else []
    display(Markdown("\n".join(md)))


show = table      # (older name)


def md_rows(path):
    """The rows of the first markdown table in a result file, as dicts."""
    head, rows, _ = _rows(Path(path).read_text())
    return [dict(zip(head, r)) for r in rows]


def spec_table(spec):
    """The specification: the two inputs and the targets the sizing rules work to."""
    sp = spec.to_dict()
    table("\n".join([
        "| specification | value | used for |", "|---|---|---|",
        f"| resolution / sample rate | {sp['bits']} bit / {sp['fs'] / 1e6:g} MS/s | everything |",
        f"| supply, reference, common mode | {sp['vdd']} V, {sp['vref']} V, {sp['vcm']} V | "
        f"LSB = {sp['lsb'] * 1e3:.1f} mV |",
        f"| SAR clock | {sp['fclk'] / 1e6:g} MHz ({sp['cycles']} cycles per conversion) | switch and comparator timing |",
        f"| DNL target (3 sigma, capacitor mismatch) | {sp['dnl_3sigma_lsb']} LSB | unit capacitor size |",
        f"| comparator offset target (3 sigma) | {sp['offset_3sigma_lsb']} LSB | input-pair size |",
        f"| comparator noise target | {sp['noise_lsb']} LSB | kT/C and input pair |",
        f"| settling target | {sp['settle_lsb']} LSB | switch and driver widths |",
        f"| sizing condition | {sp['corner']}, {sp['temp']:g} \u00b0C | (corners are checked in section 12) |"]),
        "The specification: two inputs (resolution, sample rate) and the targets every block is sized for.", fmt=False)


# ---------------------------------------------------------------- summary tables (top of the notebook and section 14)
def glance(p, width=950):
    p = Path(p)
    if p.exists():
        display(Image(filename=str(p), width=width))
    else:                       # Colab: the repository folder is opened by the setup cell
        print(f"({p} is in the project folder; run the setup cell first)")


def results_table():
    """Area, ENOB (schematic -> extracted layout), linearity, power and FoM of the 4-, 6- and 8-bit cores."""
    rows = ["| resolution | core area | ENOB, schematic → layout | max DNL / INL, layout | power, layout | Walden FoM, layout |",
            "|---|---|---|---|---|---|"]
    x8 = None
    for b in (4, 6, 8):
        pp = R / f"{b}bit/layout/prepost.json"
        if not pp.exists():
            continue
        r = json.loads(pp.read_text())
        s, x = r["schematic"], r["full core from layout"]
        fs = json.loads((R / f"{b}bit/summary.json").read_text())["spec"]["fs"]
        core = next(ln for ln in (R / f"{b}bit/layout/signoff.md").read_text().splitlines() if "core (all blocks" in ln)
        fom = x["p_uw"] * 1e-6 / (2 ** x["enob"] * fs) * 1e15
        nb = "\u00a0"                       # number and unit on one line
        rows.append(f"| {b}{nb}bit | {core.split('|')[3].strip()}{nb}µm² | {s['enob']:.2f} → {x['enob']:.2f} | "
                    f"{x['dnl_t']:.2f} / {x['inl_t']:.2f}{nb}LSB | {x['p_uw']:.0f}{nb}µW | {fom:.0f}{nb}fJ/step |")
        x8 = x if b == 8 else x8
    bo = R / "8bit/layout/sine_backoff.md"
    if bo.exists() and x8:   # the 8-bit full-scale sine clips on the core's offset (section 13)
        r = next(ln for ln in bo.read_text().splitlines() if ln.startswith("| full core"))
        rows.append(f"\n8-bit layout ENOB at -0.5 dBFS (no clipping): **{r.split('|')[3].strip()}** - the full-scale test "
                    f"sine clips on the extracted core's offset of {-x8['offset_lsb']:.1f} LSB (section 13).")
    display(Markdown(f"**Table {_n('tab', 'results')}.** The generated cores, simulated from their extracted layout "
                     "(10 MS/s, 1.8 V, typical corner).\n\n" + "\n".join(rows)))


def spec_check():
    """Each sizing target of section 1 against the simulated result, at 4, 6 and 8 bits."""
    ok = lambda v, t: "✅" if v <= t + 1e-9 else "❌"      # noqa: E731
    rows, lvs = {}, {}
    for b in (4, 6, 8):
        sp = json.loads((R / f"{b}bit/summary.json").read_text())
        spec, lsb_mv = sp["spec"], sp["spec"]["lsb"] * 1e3
        x = json.loads((R / f"{b}bit/layout/prepost.json").read_text())["full core from layout"]
        cmp_ = next(r for r in md_rows(R / f"{b}bit/layout/comparator_layout_ab.md") if r["layout"] == "after")
        sig = float(cmp_["Monte Carlo sigma [mV] (n)"].split()[0])
        noise = next(r for r in md_rows(R / "comparator_noise.md") if r["bits"] == str(b))
        num, den = noise["sigma / LSB"].split("/")
        core = next(ln for ln in (R / f"{b}bit/layout/signoff.md").read_text().splitlines() if "core (all" in ln)
        c = [v.strip() for v in core.strip("|").split("|")]
        lvs[b] = "match ✅" if c[5].startswith("match") else "fail ❌"
        rows[b] = [("missing codes, extracted core", 0, x["missing"], "{:.0f}"),
                   ("max DNL, extracted core [LSB]", spec["dnl_3sigma_lsb"], x["dnl_t"], "{:.2f}"),
                   ("DNL, 99 % of chips (mismatch MC) [LSB]", spec["dnl_3sigma_lsb"], sp["mc"]["dnl_p99"], "{:.2f}"),
                   ("comparator offset 3 sigma, extracted [LSB]", spec["offset_3sigma_lsb"], 3 * sig / lsb_mv, "{:.2f}"),
                   ("comparator noise sigma [LSB]", spec["noise_lsb"], float(num) / float(den), "{:.3f}"),
                   ("DRC errors (KLayout + Magic), core", 0, float(c[3]) + float(c[4]), "{:.0f}")]
    out = [f"**Table {_n('tab', 'spec check')}.** Specification check: each target of section 1 against the simulated "
           "result.", "", "| requirement | target | 4 bit | 6 bit | 8 bit |", "|---|---|---|---|---|"]
    for k, (name, tgt, _, f) in enumerate(rows[4]):
        cells = [f"{f.format(rows[b][k][2])} {ok(rows[b][k][2], rows[b][k][1])}" for b in (4, 6, 8)]
        out.append(f"| {name} | {'0' if tgt == 0 else '<= ' + format(tgt, 'g')} | " + " | ".join(cells) + " |")
    out.append("| LVS, core | match | " + " | ".join(lvs[b] for b in (4, 6, 8)) + " |")
    display(Markdown("\n".join(out)))


# ---------------------------------------------------------------- layout galleries
BLOCK_NAMES = {"cdac_unit": "CDAC unit cell", "strongarm": "StrongARM comparator", "topsw": "top-plate switch",
               "sar_logic": "SAR logic (LibreLane)"}


def _crop(img):
    """Trim the white margin of a layout render."""
    a = np.asarray(img)
    ink = np.where((a[..., :3] < 0.97).any(axis=2) if a.dtype != np.uint8 else (a[..., :3] < 247).any(axis=2))
    if not len(ink[0]):
        return a
    y0, y1, x0, x1 = ink[0].min(), ink[0].max(), ink[1].min(), ink[1].max()
    return a[max(0, y0 - 6):y1 + 6, max(0, x0 - 6):x1 + 6]


def layout_gallery(bits, blocks, caption):
    """The generated blocks of one resolution side by side, each titled with its size and signoff."""
    L = R / f"{bits}bit/layout"
    sign = {}
    for ln in (L / "signoff.md").read_text().splitlines()[2:]:
        c = [v.strip() for v in ln.strip("|").split("|")]
        sign[c[0]] = c
    items = []
    for b in blocks:
        p = L / f"{b}.png"
        if not p.exists():
            continue
        name = BLOCK_NAMES.get(b, "CDAC array" if b.startswith("cdacu") else "routed core" if "core" in b else b)
        row = next((c for k, c in sign.items() if (b.startswith("cdacu") and "CDAC (common" in k) or
                    ("core" in b and "core (all" in k) or (b == "cdac_unit" and k.startswith("CDAC unit")) or
                    (b == "strongarm" and k.startswith("StrongARM")) or (b == "topsw" and k.startswith("top-plate")) or
                    (b == "sar_logic" and k.startswith("SAR logic"))), None)
        sub = f"{row[1].replace(' x ', ' × ')} µm · DRC {int(row[3]) + int(row[4])} · LVS {row[5].split()[0]}" if row else ""
        items.append((name, sub, _crop(plt.imread(p))))
    n = len(items)
    cols = 2 if n == 4 else min(n, 3)
    rws = math.ceil(n / cols)
    head_in, cell_w, cell_h = 1.25, 13.8 / cols, 4.3          # heading band and panel size [inch]
    H = head_in + cell_h * rws
    fig, axs = plt.subplots(rws, cols, figsize=(13.8, H), squeeze=False)
    for ax in axs.ravel():
        ax.axis("off")
    for ax, (name, sub, img) in zip(axs.ravel(), items):
        ax.imshow(img, interpolation="lanczos")
        ax.set_title(f"{name}\n{sub}", fontsize=11.5, color=INK, loc="left")
    fig.subplots_adjust(left=0.02, right=0.98, top=1 - head_in / H, bottom=0.01, wspace=0.06, hspace=0.3)
    fig.text(0.03, 1 - 0.3 / H, f"Fig. {_n('fig', caption[0])}.  {caption[0]}", fontsize=15, fontweight="bold",
             color=INK, va="top")
    fig.text(0.03, 1 - 0.68 / H, caption[1], fontsize=10.5, color=NOTE, va="top")
    render(fig)
