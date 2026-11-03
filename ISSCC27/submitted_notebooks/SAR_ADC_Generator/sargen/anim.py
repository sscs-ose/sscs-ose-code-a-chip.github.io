"""Animated explanation of one SAR conversion: the binary search (left) next to the capacitor array it switches
(right: capacitors, bottom-plate switches between Vin / Vref / GND, the top-plate Vcm switch, comparator, SAR logic)."""

import io
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import FancyBboxPatch, Polygon

from .model import SarModel

INK, MUTED, GRID = "#1d2330", "#6b7280", "#d7dbe0"
COLORS = {"vin": "#2a78d6", "vref": "#eb6834", "gnd": "#8a8f98"}
KEEP, CLEAR, TRY = "#1baf7a", "#d64545", "#555b66"
RAIL_Y = {"vin": 5.2, "vref": 4.4, "gnd": 3.6}
RAIL_NAME = {"vin": "$V_{in}$", "vref": "$V_{ref}$", "gnd": "GND"}


def _frames(model: SarModel, vin: float):
    """Each trial is shown twice: 'try bit = 1' and then the comparator decision."""
    steps = model.trace(vin)
    frames = [dict(steps[0], stage="sample")]
    for s in steps[1:-1]:
        frames.append(dict(s, stage="try"))
        frames.append(dict(s, stage="decide"))
    frames.append(dict(steps[-1], stage="done"))
    return frames, steps[-1]["code"]


def _bit_symbol(f, i):
    """Text for bit i in a frame: decided value, '?' under test, '_' not yet tried."""
    if f["stage"] == "sample":
        return "_"
    if f["stage"] == "done" or i > f["bit"]:
        return str(int(f["ctrl"][i]))
    if i == f["bit"]:
        return "?" if f["stage"] == "try" else str(int(f["decision"]))
    return "_"


def _cap_conn(f, j, n):
    """Bottom-plate connection of capacitor j (n = the dummy) in a frame."""
    if f["stage"] == "sample":
        return "vin"
    if j == n:
        return "gnd"
    if f["stage"] == "decide" and j == f["bit"]:
        return "vref" if f["decision"] else "gnd"
    return "vref" if f["ctrl"][j] else "gnd"


def _draw_cdac(ax, f, model, vin):
    """The capacitor array as a schematic, switched as in frame f."""
    n = model.bits
    caps = list(model.caps) + [model.c_dummy]
    order = list(range(n - 1, -1, -1)) + [n]                   # MSB on the left, the dummy last
    x0, x1, top = 1.4, 10.4, 8.85
    dx = (x1 - x0) / len(order)
    cmax = max(caps)
    ax.set_xlim(0, 14.2)
    ax.set_ylim(2.9, 10.5)
    ax.axis("off")
    line = lambda xs, ys, **kw: ax.plot(xs, ys, solid_capstyle="round", **{"color": INK, "lw": 1.4, **kw})  # noqa: E731
    dot = lambda x, y, c=INK, s=4.5: ax.plot([x], [y], "o", color=c, ms=s, zorder=5)                      # noqa: E731

    # rails
    for r, y in RAIL_Y.items():
        line([x0 - 0.5, x1 + 0.1], [y, y], color=COLORS[r], lw=2)
        ax.text(x0 - 0.6, y, RAIL_NAME[r], ha="right", va="center", fontsize=11, color=COLORS[r])
    # top plate and its voltage
    sample = f["stage"] == "sample"
    vx = model.vcm + (0.0 if sample else float(model.vx_minus_vcm(vin, _ctrl_shown(f, n))))
    line([x0 - 0.5, 11.55], [top, top], lw=2.4)
    ax.text(x0 - 0.5, 10.0, f"top plate  $V_x$ = {vx:.3f} V", fontsize=11.5, color=INK, va="bottom", fontweight="bold")

    for k, j in enumerate(order):
        xc = x0 + (k + 0.5) * dx
        conn = _cap_conn(f, j, n)
        under_test = f["stage"] in ("try", "decide") and j == f.get("bit")
        if under_test:
            col = KEEP if f["stage"] == "decide" and f["decision"] else CLEAR if f["stage"] == "decide" else "#f2b33d"
            ax.add_patch(FancyBboxPatch((xc - 0.47 * dx, 3.25), 0.94 * dx, 5.35, boxstyle="round,pad=0.02",
                                        fc=col, ec="none", alpha=0.16, zorder=0))
        # capacitor: plate width follows its weight
        hw = 0.12 + 0.3 * caps[j] / cmax
        line([xc, xc], [top, 7.95])
        line([xc - hw, xc + hw], [7.95, 7.95], lw=3)
        line([xc - hw, xc + hw], [7.6, 7.6], lw=3)
        line([xc, xc], [7.6, 6.45])
        dot(xc, top)
        label = f"{2 ** j}C" if j < n else "1C"
        if dx > 1.2:
            ax.text(xc + hw + 0.08, 7.78, label, fontsize=9.5, va="center", color=INK)
        else:                                                   # 7-8 bit: no room beside the plate, label below it
            ax.text(xc, 7.15, label, fontsize=8.5, ha="center", va="center", color=INK,
                    bbox=dict(fc="white", ec="none", pad=0.6), zorder=4)
        ax.text(xc, 9.15, f"b{j}" if j < n else "dummy", ha="center", fontsize=10, color=MUTED)
        # switch: three contacts (Vin, Vref, GND) reached by stubs from their rails; the arm picks one
        cx = {"vin": xc - 0.28, "vref": xc, "gnd": xc + 0.28}
        for r, xr in cx.items():
            line([xr, xr], [RAIL_Y[r], 5.75], lw=1, color=COLORS[r] if r == conn else GRID)
            dot(xr, RAIL_Y[r], COLORS[r] if r == conn else GRID, 3.5)
            ax.plot([xr], [5.75], "o", mfc="white", mec=COLORS[r] if r == conn else MUTED, ms=5, zorder=6)
        line([xc, cx[conn]], [6.45, 5.82], lw=2.6, color=COLORS[conn])
        dot(xc, 6.45, INK, 5)

    # top-plate switch to Vcm (closed while sampling), comparator, SAR logic
    xs = 10.95
    line([xs, xs], [top, 8.35])
    dot(xs, top)
    if sample:
        line([xs, xs], [8.35, 7.75], lw=2.6, color=COLORS["vin"])
    else:
        line([xs, xs + 0.3], [8.35, 7.85], lw=2.2, color=MUTED)
    ax.plot([xs], [7.75], "o", mfc="white", mec=INK, ms=5, zorder=6)
    line([xs, 11.55], [7.75, 7.75])
    line([xs, xs], [7.75, 7.2])
    ax.text(xs, 7.05, "$V_{cm}$", ha="center", va="top", fontsize=11)
    ax.text(xs - 0.15, 8.1, "φ$_t$", ha="right", fontsize=10, color=MUTED)
    ax.add_patch(Polygon([(11.55, 9.3), (11.55, 7.35), (13.05, 8.32)], closed=True, fc="white", ec=INK, lw=1.6))
    ax.text(11.68, 8.85, "+", fontsize=12, va="center")
    ax.text(11.68, 7.75, "−", fontsize=12, va="center")
    decided = f["stage"] == "decide"
    qcol = (KEEP if f["decision"] else CLEAR) if decided else MUTED
    line([13.05, 13.6], [8.32, 8.32], color=qcol, lw=2)
    line([13.6, 13.6], [8.32, 6.35], color=qcol, lw=2)
    ax.annotate("", (13.6, 6.25), (13.6, 6.6), arrowprops=dict(arrowstyle="-|>", color=qcol, lw=2))
    if decided:
        ax.text(13.7, 7.4, "keep" if f["decision"] else "clear", color=qcol, fontsize=11, fontweight="bold",
                rotation=90, va="center")
    ax.add_patch(FancyBboxPatch((11.6, 3.4), 2.4, 2.75, boxstyle="round,pad=0.05", fc="#f7f8fa", ec=INK, lw=1.2))
    ax.text(12.8, 5.75, "SAR logic", ha="center", fontsize=11, fontweight="bold")
    bits = " ".join(_bit_symbol(f, i) for i in range(n - 1, -1, -1))
    ax.text(12.8, 4.65, bits, ha="center", fontsize=14 if n <= 6 else 10, family="monospace", fontweight="bold")
    ax.text(12.8, 3.85, "MSB → LSB", ha="center", fontsize=9, color=MUTED)


def _ctrl_shown(f, n):
    """Bottom-plate controls as drawn in the frame (the bit under test at its trial / decided value)."""
    c = f["ctrl"].copy()
    if f["stage"] == "decide":
        c[f["bit"]] = float(f["decision"])
    return c


def _layout(figsize=(14, 5.9)):
    """Figure with the staircase (left), the switched array (right) and an explanation line (bottom)."""
    fig = plt.figure(figsize=figsize)
    gs = fig.add_gridspec(2, 2, height_ratios=[3.6, 0.7], width_ratios=[1, 1.55], left=0.05, right=0.99,
                          top=0.87, bottom=0.01, wspace=0.08, hspace=0.18)
    return fig, (fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, :]))


def _draw(fig, axes, frames, k, model, vin, code):
    """Draw frame k of one conversion."""
    ax_v, ax_c, ax_t = axes
    n = model.bits
    lsb = model.vref / 2**n
    f = frames[k]
    for ax in axes:
        ax.clear()

    # --- binary search staircase ---
    done = [fr for fr in frames[: k + 1] if fr["stage"] == "try"]
    ax_v.axhline(vin, color=COLORS["vin"], lw=2, label=f"$V_{{in}}$ = {vin:.3f} V")
    for m, fr in enumerate(done):
        last = m == len(done) - 1 and f["stage"] in ("try", "decide")
        keep = fr["decision"] if (not last or f["stage"] == "decide") else None
        color = KEEP if keep else (CLEAR if keep is False else TRY)
        ax_v.plot([m, m + 1], [fr["vdac"]] * 2, color=color, lw=3.5, solid_capstyle="butt")
        ax_v.annotate(f"b{fr['bit']}", (m + 0.5, fr["vdac"]), textcoords="offset points",
                      xytext=(0, 6), ha="center", fontsize=10, color=INK)
    ax_v.set_xlim(0, n)
    ax_v.set_ylim(-0.05 * model.vref, 1.05 * model.vref)
    ax_v.set_xticks(range(n + 1))
    ax_v.set_xlabel("bit-trial cycle")
    ax_v.set_ylabel("DAC level tried [V]")
    ax_v.set_title("binary search: the DAC level against the input", loc="left", fontsize=12, color=INK)
    ax_v.grid(color=GRID, lw=0.6)
    ax_v.spines[["top", "right"]].set_visible(False)
    ax_v.plot([], [], color=KEEP, lw=3.5, label="kept (DAC < $V_{in}$)")
    ax_v.plot([], [], color=CLEAR, lw=3.5, label="cleared")
    ax_v.legend(loc="lower right", fontsize=9.5, frameon=False)

    # --- capacitor array, switched ---
    _draw_cdac(ax_c, f, model, vin)
    ax_c.set_title("the capacitor array and its switches", loc="left", fontsize=12, color=INK)

    # --- explanation text ---
    ax_t.axis("off")
    if f["stage"] == "sample":
        msg = (f"SAMPLE: every bottom plate tracks Vin, the top plate is held at Vcm = {model.vcm:.2f} V.\n"
               f"The array now stores the charge (Vcm - Vin) * Ctot.  LSB = {lsb * 1e3:.1f} mV.")
    elif f["stage"] == "try":
        msg = (f"TRY bit b{f['bit']}: switch its capacitor's bottom plate to Vref -> DAC level {f['vdac']:.3f} V.\n"
               f"The comparator checks the sign of Vx - Vcm: is the DAC level below Vin?")
    elif f["stage"] == "decide":
        ok = f["decision"]
        msg = (f"DECIDE b{f['bit']} = {int(ok)}: DAC {f['vdac']:.3f} V {'<' if ok else '>'} Vin {vin:.3f} V -> "
               f"{'keep it on Vref' if ok else 'return it to GND'}.")
    else:
        msg = (f"DONE: output code {code} (0b{code:0{n}b}); ideal code = floor(Vin / LSB) = "
               f"{int(min(vin / lsb, 2**n - 1))}.")
    ax_t.text(0.01, 0.85, msg, fontsize=12, va="top", family="monospace", color=INK)
    fig.suptitle(f"One {n}-bit SAR conversion, step {k + 1} of {len(frames)}", fontsize=14,
                 fontweight="bold", x=0.05, ha="left", color=INK)


def animate_conversion(model: SarModel, vin: float, path=None, fps: float = 0.8):
    """Build the animation; save it as GIF when `path` is given. Returns the FuncAnimation."""
    frames, code = _frames(model, vin)
    fig, axes = _layout()

    def draw(k):
        _draw(fig, axes, frames, k, model, vin, code)
        return []

    anim = FuncAnimation(fig, draw, frames=len(frames), interval=1000 / fps, blit=False)
    if path:
        anim.save(path, writer=PillowWriter(fps=fps))
    plt.close(fig)
    return anim


def frame_png(bits, vin, step=None, vref=1.8, dpi=80):
    """One frame of a conversion as PNG bytes (step None or past the end: the finished conversion)."""
    model = SarModel(bits, vref)
    frames, code = _frames(model, vin)
    k = len(frames) - 1 if step is None else min(step, len(frames) - 1)
    fig, axes = _layout()
    _draw(fig, axes, frames, k, model, vin, code)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi)
    plt.close(fig)
    return buf.getvalue()


def explorer(vref=1.8, bits=4, vin=1.13):
    """Sliders for the resolution, the input voltage and the conversion step, driving the behavioral model.
    Static runs (no live kernel, SARGEN_STATIC=1, or no ipywidgets) show the finished conversion instead."""
    from IPython.display import Image, display
    try:
        import ipywidgets as w
    except ImportError:
        w = None
    if w is None or os.environ.get("SARGEN_STATIC"):
        display(Image(frame_png(bits, vin, vref=vref)))
        return
    s_bits = w.IntSlider(value=bits, min=4, max=8, description="bits")
    s_vin = w.FloatSlider(value=vin, min=0.0, max=vref, step=0.001, readout_format=".3f", description="Vin [V]",
                          continuous_update=False, layout=w.Layout(width="420px"))
    s_step = w.IntSlider(value=2 * bits + 1, min=0, max=2 * bits + 1, description="step")
    out = w.Output()

    def update(_=None):
        png = frame_png(s_bits.value, s_vin.value, s_step.value, vref)
        with out:
            out.clear_output(wait=True)
            display(Image(png))

    def on_bits(ch):
        s_step.unobserve(update, "value")
        s_step.max = 2 * ch["new"] + 1
        s_step.value = s_step.max                      # jump to the finished conversion
        s_step.observe(update, "value")
        update()

    s_bits.observe(on_bits, "value")
    s_vin.observe(update, "value")
    s_step.observe(update, "value")
    display(w.VBox([w.HBox([s_bits, s_vin, s_step]), out]))
    update()
