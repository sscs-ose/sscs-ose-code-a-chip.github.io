"""Figures for the SAR ADC report (all saved as PNG), in the notebook's figure style: a bold title and a one-line
note above the plot, the notebook's palette, light grids and no top / right frame."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import textwrap

import numpy as np

INK, NOTE, MUTED, GRID = "#1d2330", "#4b5563", "#6b7280", "#d7dbe0"
BLUE, ORANGE, GREEN, AMBER = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
STYLE = {"font.size": 10.5, "axes.titlesize": 11, "axes.titlelocation": "left", "axes.titlecolor": INK,
         "axes.labelcolor": INK, "axes.edgecolor": MUTED, "axes.spines.top": False, "axes.spines.right": False,
         "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "xtick.color": INK, "ytick.color": INK,
         "legend.frameon": False, "legend.fontsize": 9.5, "figure.facecolor": "white"}


def _fig(w, h, title, note, **kw):
    """Figure with a bold title and a wrapped note above the plot area (top margin sized to fit them)."""
    note = textwrap.fill(note, int(w * 13.5))
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(w, h), **kw)
    fig.text(0.012, 1 - 0.12 / h, title, fontsize=13, fontweight="bold", color=INK, va="top")
    fig.text(0.012, 1 - 0.45 / h, note, fontsize=10, color=NOTE, va="top", linespacing=1.3)
    fig._top = 1 - (0.62 + 0.2 * note.count("\n") + 0.15) / h
    return fig, ax


def _save(fig, path, top=None):
    with plt.rc_context(STYLE):
        fig.tight_layout(rect=(0, 0, 1, getattr(fig, "_top", top)))
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def _style(*axes):
    for a in np.ravel(axes):
        a.set_axisbelow(True)
        a.spines[["top", "right"]].set_visible(False)
        a.grid(color=GRID, lw=0.6)


def waveforms(w, timing, spec, path):
    """Transient of a few conversions: top plate vs vcm, comparator clock/output, bits."""
    t = w["time"] * 1e9
    n = spec.bits
    fig, ax = _fig(10, 7.6, "One conversion at transistor level: the binary search in the circuit",
                   f"{n}-bit SAR, three conversions of a DC input. The top plate jumps with every bit trial and is pulled "
                   "back towards Vcm; the comparator decides once per trial.", nrows=3, sharex=True,
                   gridspec_kw=dict(height_ratios=[2.2, 1, 1.6]))
    _style(ax)
    for i in range(n):
        ax[0].plot(t, w[f"bot_{i}"], lw=0.8, alpha=0.45, color=plt.cm.Greys(0.35 + 0.5 * i / max(1, n - 1)))
    ax[0].plot(t, w["top"], color=BLUE, lw=1.8, label="top plate $V_x$")
    ax[0].axhline(spec.vcm, color=ORANGE, ls="--", lw=1.2, label="$V_{cm}$")
    ax[0].plot([], [], color="#9ca3af", lw=0.8, label="bottom plates")
    ax[0].set_ylabel("voltage [V]")
    ax[0].legend(ncol=3, loc="lower right", bbox_to_anchor=(1, 1.0))     # above the traces
    ax[0].set_title("capacitor array (CDAC)", loc="left", fontsize=11, color=INK)
    ax[1].plot(t, w["phit"], color=MUTED, lw=1, label="sample phase")
    ax[1].plot(t, w["clk"], color=BLUE, lw=1, label="comparator clock")
    ax[1].plot(t, w["qp"], color=ORANGE, lw=1.3, label="decision (1 = keep bit)")
    ax[1].legend(ncol=3, loc="lower right", bbox_to_anchor=(1, 1.0))
    ax[1].set_ylabel("[V]")
    ax[1].set_title("comparator", loc="left", fontsize=11, color=INK)
    for i in range(n):
        ax[2].plot(t, w[f"bo_{i}"] / spec.vdd * 0.8 + i, color=BLUE if i % 2 else INK, lw=1.2)
        ax[2].text(t[0] - 0.01 * t[-1], i + 0.25, f"b{i}", fontsize=9, ha="right", color=INK)
    ax[2].set_yticks([])
    ax[2].set_xlabel("time [ns]")
    ax[2].set_title("output bits", loc="left", fontsize=11, color=INK)
    for k in range(1, int(t[-1] * 1e-9 / timing.tconv) + 1):
        for a in ax:
            a.axvline(k * timing.tconv * 1e9, color=MUTED, lw=0.6, ls=":")
    return _save(fig, path, 0.9)


def transfer(vin, codes, spec, path):
    fig, ax = _fig(8, 4.8, f"{spec.bits}-bit transfer characteristic",
                   "Slow input ramp at transistor level; dashed: an ideal quantizer.")
    _style(ax)
    ideal = np.clip(np.floor(vin / spec.lsb), 0, 2**spec.bits - 1)
    ax.plot(vin, ideal, "--", color=MUTED, lw=1.2, label="ideal")
    ax.step(vin, codes, where="post", color=BLUE, lw=1.6, label="simulated (SPICE)")
    ax.set_xlabel("input voltage [V]")
    ax.set_ylabel("output code")
    ax.legend(loc="upper left")
    return _save(fig, path, 0.86)


def inl_dnl(hist_res, spec, path, title="code-density test"):
    fig, ax = _fig(9, 6.6, f"Static linearity from the {title}",
                   f"Hits per code of a slow ramp (top); DNL = hits / mean - 1 (middle); INL = running sum, end-point "
                   f"fit (bottom). Max |DNL| {hist_res['dnl_max']:.2f} LSB, max |INL| {hist_res['inl_max']:.2f} LSB.",
                   nrows=3, sharex=True)
    _style(ax)
    codes = np.arange(2**spec.bits)
    ax[0].bar(codes, hist_res["hist"], color=BLUE, width=0.8)
    ax[0].set_ylabel("hits")
    ax[1].bar(hist_res["codes"], hist_res["dnl"], color=ORANGE, width=0.8)
    ax[1].axhline(0, color=INK, lw=0.6)
    ax[1].set_ylabel("DNL [LSB]")
    ax[2].plot(hist_res["codes"], hist_res["inl"], "o-", color=GREEN, ms=4, lw=1.4)
    ax[2].axhline(0, color=INK, lw=0.6)
    ax[2].set_ylabel("INL [LSB]")
    ax[2].set_xlabel("output code")
    return _save(fig, path, 0.86)


def spectrum(fft_res, spec, path):
    fig, ax = _fig(9, 4.8, f"Output spectrum: ENOB {fft_res['enob']:.2f} bit",
                   f"Coherent FFT of a near-full-scale sine. SNDR {fft_res['sndr_db']:.1f} dB, SFDR "
                   f"{fft_res['sfdr_db']:.1f} dB (ideal quantizer: {fft_res['ideal_sqnr_db']:.1f} dB); x: harmonics.")
    _style(ax)
    f = fft_res["freq_bins"] * spec.fs / 1e6
    # bins with no power at all (the fs/2 bin of a half-wave-symmetric coherent record is exactly 0) would dive
    # to the log floor (-300 dB): leave them out
    db = np.where(fft_res["spectrum_dbfs"] < -250, np.nan, fft_res["spectrum_dbfs"])
    ax.plot(f[1:], db[1:], lw=1.2, color=BLUE)
    for k in fft_res["harmonic_bins"]:
        if np.isfinite(db[k]):
            ax.plot(f[k], db[k], "x", color=ORANGE, ms=8, mew=2)
    ax.set_xlabel("frequency [MHz]")
    ax.set_ylabel("power [dBc]")
    return _save(fig, path, 0.84)


def time_samples(vin, codes, spec, path):
    fig, ax = _fig(9, 3.8, "Sine input and output codes", "The input in LSB (dots) and the converter's output code.")
    _style(ax)
    ax.plot(vin / spec.lsb, ".", color=MUTED, ms=4, label="input / LSB")
    ax.step(np.arange(len(codes)), codes, where="mid", color=BLUE, lw=1.3, label="output code")
    ax.set_xlabel("sample")
    ax.set_ylabel("[LSB]")
    ax.legend(loc="upper right", ncol=2)
    return _save(fig, path, 0.8)


def offset_hist(off, spec, path):
    off = np.asarray(off) * 1e3
    s = off.std(ddof=1)
    fig, ax = _fig(8, 4.4, "Comparator offset over SKY130 mismatch",
                   f"{len(off)} StrongARM instances: mean {off.mean():.2f} mV, sigma {s:.2f} mV; "
                   f"one LSB is {spec.lsb * 1e3:.1f} mV.")
    _style(ax)
    ax.hist(off, bins=20, color=BLUE, edgecolor="white")
    for k in (-3, 3):
        ax.axvline(off.mean() + k * s, color=ORANGE, ls="--", lw=1.2)
    ax.text(off.mean() + 3 * s, ax.get_ylim()[1] * 0.92, "  3 sigma", color=ORANGE, fontsize=9.5)
    ax.set_xlabel("input-referred offset [mV]")
    ax.set_ylabel("instances")
    return _save(fig, path, 0.84)


def mc_linearity(dnl_max, inl_max, spec, path):
    fig, ax = _fig(10, 4.4, f"Linearity over {len(dnl_max)} simulated chips",
                   f"{spec.bits}-bit behavioral SAR with the PDK's capacitor mismatch and the measured comparator offset; "
                   "dashed: 99th percentile.", ncols=2)
    _style(ax)
    for a, v, col, name in ((ax[0], dnl_max, ORANGE, "max |DNL| [LSB]"), (ax[1], inl_max, GREEN, "max |INL| [LSB]")):
        a.hist(v, bins=30, color=col, edgecolor="white")
        p = np.percentile(v, 99)
        a.axvline(p, color=INK, ls="--", lw=1)
        a.text(p, a.get_ylim()[1] * 0.92, f" 99 %: {p:.2f}", fontsize=9.5, color=INK)
        a.set_xlabel(name)
        a.set_ylabel("chips")
    return _save(fig, path, 0.84)


def transition_inl_dnl(tr, spec, path):
    """INL/DNL from measured code-transition voltages; also shows absolute INL (offset + gain)."""
    k = np.arange(1, 2**spec.bits)
    inl = np.asarray(tr["inl"])
    inl_ep = inl - np.linspace(inl[0], inl[-1], len(inl))
    fig, ax = _fig(9, 5.4, "Static linearity from the code-transition levels",
                   f"Where each code starts on a fine ramp. Max |DNL| {tr['dnl_max']:.2f} LSB, max |INL| "
                   f"{tr['inl_max']:.2f} LSB (end-point); grey: including offset and gain error.", nrows=2, sharex=True)
    _style(ax)
    ax[0].bar(k[:-1] + 0.5, tr["dnl"], color=ORANGE, width=0.8)
    ax[0].axhline(0, color=INK, lw=0.6)
    ax[0].set_ylabel("DNL [LSB]")
    ax[1].plot(k, inl, ".--", color=MUTED, lw=1, label="absolute (offset and gain included)")
    ax[1].plot(k, inl_ep, "o-", color=GREEN, ms=4, lw=1.4, label="end-point fit")
    ax[1].set_ylabel("INL [LSB]")
    ax[1].set_xlabel("code transition")
    ax[1].legend(loc="best")
    return _save(fig, path, 0.84)
