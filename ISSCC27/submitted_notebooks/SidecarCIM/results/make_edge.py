"""Edge-deployment tables, the predictor figure and their findings.

table_128.{csv,md}: the 32-row macros (ppa.csv) next to the 128-row
layouts of the final SidecarCIM build (merge register, 3-bit S, K = 4)
and dense W4A4 / W6A4, all at 35 ns (ppa_128.csv rows tagged "redo,
35 ns"). The SidecarCIM row is the hold-repair rerun, the only 128-row
run with PL / GRT hold margins 0.2 / 0.15. Dense W8A4 did not route at
128 rows, so only its synthesis area exists. 8-window accuracy comes
from tile_scaling.json and alternatives.json.

table_energy_token.{csv,md}: macro energy per generated token (batch-1
decode) = MVMs per token of the quantized layers (token_ops.json) x
energy per MVM, once compute only (weights resident) and once with one
full weight reload per MVM (load_energy.csv). The two bracket the real
cost; memory, IO, zero-point correction and the FP layers are left out.

fig_predictor.{png,pdf}: gain of SidecarCIM over dense W6A4 for 14
models against two outlier statistics (predictor.json fit.points).

findings(): the findings these files support, for make_tables.
"""
import csv
import math
import os

import plot_common as pc
import ppa_data as pd


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _num(r):
    return {k: (_f(v) if _f(v) is not None else v) for k, v in r.items()}


def ppa128(design, build):
    """The ppa_128.csv row of design whose build tag starts with build."""
    rr = [_num(r) for r in pd.load_csv("ppa_128.csv")
          if r["design"] == design and r["build"].startswith(build)]
    assert len(rr) == 1, (design, build, len(rr))
    return rr[0]


def load_energy():
    return {r["design"]: _num(r) for r in pd.load_csv("load_energy.csv")}


HEAD128 = "SidecarCIM headline (PIPE_MERGE=1, SBITS=3) K=4"
RED = "redo, 35 ns, hold-repair"           # the hold-clean rerun of the final build
# label, 128-row design and build tag, 32-row design, load_energy keys
R128 = [("W4A4", ("dcim W4A4", "redo, 35 ns"), "dcim_core_ff",
         ("dcim_core_ff", "dcim W4A4 128-row 35 ns")),
        ("W6A4", ("dcim W6A4", "redo, 35 ns"), "dcim_w6a4_ff",
         ("dcim_w6a4_ff", "dcim W6A4 128-row 35 ns")),
        ("W8A4", ("dcim W8A4", "first build"), "dcim_w8a4_ff",
         ("dcim_w8a4_ff", None)),
        ("SidecarCIM", (HEAD128, RED), pd.HEAD,
         (pd.HEAD, "sidecar pipe SBITS=3 K=4 (headline) 128-row 35 ns, "
          "hold-repair margins"))]


def _paired_t(a, b):
    d = [x - y for x, y in zip(a, b)]
    n = len(d)
    m = sum(d) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in d) / (n - 1))
    return m / (sd / math.sqrt(n))


def acc128():
    """8-window accuracy (d over FP32) at 32 and 128 rows; paired t of
    the 128-row K=4 sidecar against dense W6A4 (same 8 windows)."""
    ts = pc.load("tile_scaling.json")
    al = pc.load("alternatives.json")
    out = {}
    for m in ("gpt2", "qwen"):
        rows = {(r["R"], r["k"]): r for r in ts["tables"][m]["rows"]}
        arow = {r["scheme"]: r for r in al["tables"][m]["rows"]}
        u_ref = ts["units"][m + "|R32|k2"]["nll"]
        u_alt = al["units"][m + "|SidecarCIM+wclip k2,VB12"]["nll"]
        assert max(abs(x - y) for x, y in zip(u_ref, u_alt)) < 1e-9, m
        w6 = al["units"][m + "|W6A4+mig+wclip"]["nll"]
        k4 = ts["units"][m + "|R128|k4"]["nll"]
        out[m] = {
            "sc32": rows[(32, 2)]["d"], "sc128k2": rows[(128, 2)]["d"],
            "sc128k4": rows[(128, 4)]["d"],
            "w4": arow["W4A4+mig+wclip"]["d"],
            "w6": arow["W6A4+mig+wclip"]["d"],
            "w8": arow["W8A4+mig+wclip"]["d"],
            "t_k4_vs_w6": _paired_t(k4, w6),
            "t_k4_vs_32": rows[(128, 4)]["vs_ref"]["t"]}
    return out


def table128():
    p32, le = pd.ppa(), load_energy()
    w6_32 = p32["dcim_w6a4_ff"]
    w6_128 = ppa128("dcim W6A4", "redo, 35 ns")
    rows = []
    for lab, (d128, b128), k32, (l32, l128) in R128:
        r, q = ppa128(d128, b128), p32[k32]
        routed = r.get("energy_per_mvm_pj_est") not in (None, "")
        rows.append(dict(
            circuit=lab, k128=int(r["k"]) if r["k"] not in ("", None) else 0,
            area32_um2=q["area_um2"], energy32_pj=q["energy_per_dot_pj_est"],
            reload32_pj=le[l32]["energy_per_reload_pj"],
            area128_um2=r["area_um2"],
            energy128_pj=r["energy_per_mvm_pj_est"] if routed else None,
            reload128_pj=le[l128]["energy_per_reload_pj"] if l128 else None,
            clock128_ns=r["clock_period_ns"],
            wns128_ns=r["wns_ns"] if routed else None,
            setup_vio128=r["setup_vio"] if routed else None,
            hold_vio128=r["hold_vio"] if routed else None,
            area_vs_w6_32=q["area_um2"] / w6_32["area_um2"],
            area_vs_w6_128=r["area_um2"] / w6_128["area_um2"],
            energy_vs_w6_32=(q["energy_per_dot_pj_est"] /
                             w6_32["energy_per_dot_pj_est"]),
            energy_vs_w6_128=(r["energy_per_mvm_pj_est"] /
                              w6_128["energy_per_mvm_pj_est"])
            if routed else None,
            note="did not route: synthesis area only" if not routed
            else ("hold-repair margins PL 0.2 / GRT 0.15"
                  if lab == "SidecarCIM" else "default settings")))
    return rows


def energy_per_token():
    """uJ per generated token, quantized layers only: compute only and
    with one full weight reload per MVM."""
    tok = pc.load("token_ops.json")["models"]
    t = {r["circuit"]: r for r in table128()}
    p32 = pd.ppa()
    cols = [(c, (t[c]["energy32_pj"], t[c]["reload32_pj"]),
             (t[c]["energy128_pj"], t[c]["reload128_pj"]))
            for c in ("W4A4", "W6A4", "SidecarCIM", "W8A4")]
    cols.append(("W8A8", (p32["dcim_8bit_ff"]["energy_per_dot_pj_est"],
                          None), (None, None)))
    out = []
    for key, name in (("gpt2", "GPT-2 (124M)"),
                      ("qwen2.5-0.5b", "Qwen2.5-0.5B")):
        m = tok[key]
        qz, al = m["quantized"], m["all_linear"]
        for R, mv in ((32, qz["mvm_32x8"]), (128, qz["mvm_128x8"])):
            r = dict(model=name, rows=R, layers=", ".join(
                m["quantized_layers"]), mvm_per_token=mv,
                quantized_mac_share_pct=100.0 * qz["macs"] / al["macs"])
            for c, e32, e128 in cols:
                e, ld = e32 if R == 32 else e128
                r[c + "_uJ"] = None if e is None else mv * e * 1e-6
                r[c + "_reload_uJ"] = (None if e is None or ld is None
                                       else mv * (e + ld) * 1e-6)
            out.append(r)
    return out


# ---------------------------------------------------------------- figure
NAMES = {"tinystories-1m": "TS-1M", "tinystories-3m": "TS-3M",
         "tinystories-8m": "TS-8M", "tinystories-33m": "TS-33M",
         "gpt2": "GPT-2", "smollm2-135m": "SmolLM2-135M",
         "smollm2-360m": "SmolLM2-360M", "qwen2.5-0.5b": "Qwen2.5-0.5B",
         "smollm2-1.7b": "SmolLM2-1.7B*", "opt-125m": "OPT-125M",
         "opt-350m": "OPT-350M", "pythia-160m": "Pythia-160M",
         "pythia-410m": "Pythia-410M", "pythia-1b": "Pythia-1B",
         "gpt2-medium": "GPT-2-M", "gpt2-large": "GPT-2-L",
         "bloom-1b1": "BLOOM-1B1", "qwen2.5-1.5b": "Qwen2.5-1.5B"}
# label offsets in points (dx, dy) per panel, chosen so labels clear
# each other and the CI bars at print size
OFF = {"act": {"TS-1M": (6, 0), "TS-3M": (6, 0), "TS-8M": (0, -12),
               "TS-33M": (6, -6), "OPT-350M": (-8, 3),
               "Pythia-410M": (0, -14), "Pythia-160M": (4, -30, 1),
               "Pythia-1B": (-5, 8), "SmolLM2-135M": (6, -6),
               "OPT-125M": (-8, 3), "GPT-2": (-6, 7),
               "SmolLM2-360M": (6, 5), "Qwen2.5-0.5B": (6, 6),
               "SmolLM2-1.7B*": (6, 0), "GPT-2-M": (6, -7),
               "GPT-2-L": (-2, 10), "BLOOM-1B1": (-9, 0),
               "Qwen2.5-1.5B": (7, -4)},
       "kurt": {"TS-1M": (6, 0), "TS-3M": (6, 0), "TS-8M": (6, -5),
                "TS-33M": (5, 6), "OPT-350M": (0, -13),
                "Pythia-410M": (0, -12), "Pythia-160M": (6, -9),
                "Pythia-1B": (-6, 7), "SmolLM2-135M": (6, -10),
                "OPT-125M": (-8, -6), "GPT-2": (-8, 7),
                "SmolLM2-360M": (6, 9), "Qwen2.5-0.5B": (9, 7),
                "SmolLM2-1.7B*": (-6, 0), "GPT-2-M": (7, -7),
                "GPT-2-L": (0, -11), "BLOOM-1B1": (-9, 7),
                "Qwen2.5-1.5B": (9, -6)}}


def predictor_points():
    p = pc.load("predictor.json")["fit"]
    return p["points"], p["stats"]


def fig_predictor():
    """One panel: gain over W6A4 against the migrated-weight kurtosis, with
    the split. IEEE single-column size; model names live in TABLE V."""
    import matplotlib.pyplot as plt
    pc.style()
    fs = 8.0
    pts, st = predictor_points()
    pos, neg, ns = pc.ACC, "black", "#8a8a8a"
    key = "w_kurtosis_mig"
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    for q in pts:
        g, (lo, hi) = q["gain_over_W6A4_ppl"], q["gain_ci90"]
        sig = q["p"] < 0.05
        col = (pos if g > 0 else neg) if sig else ns
        mk = ("^" if g > 0 else "v") if sig else "o"
        x = q[key]
        ax.errorbar([x], [g], yerr=[[g - lo], [hi - g]], fmt=mk, color=col,
                    ms=5, mew=0.9, capsize=1.5, elinewidth=0.7, zorder=4)
        if q.get("prospective"):        # predicted before evaluation
            ax.plot([x], [g], "o", ms=10, mfc="none", mec="black", mew=0.7,
                    zorder=5)
    thr = st[key]["threshold"]
    ax.axvline(thr, color="black", ls="--", lw=0.8, zorder=1)
    ax.axhline(0, color="black", lw=0.6, zorder=2)
    ax.text(thr * 1.15, -5, "use SidecarCIM", fontsize=fs, ha="left",
            va="center", color=pos)
    ax.text(thr / 1.15, -5, "use W6A4", fontsize=fs, ha="right",
            va="center")
    ax.set_xscale("log")
    ax.set_yscale("symlog", linthresh=0.5, linscale=1.0)
    ax.set_yticks([-8, -2, -0.5, 0, 0.5, 2, 8])
    ax.set_yticklabels(["$-8$", "$-2$", "$-0.5$", "0", "0.5", "2", "8"])
    ax.set_ylim(-12, 12)
    ax.set_xlim(0.12, 150)
    ax.set_xlabel("Excess kurtosis of migrated weights")
    ax.set_ylabel("Gain over W6A4 (ppl)")
    h = [plt.Line2D([], [], marker="^", color=pos, ls="", label="gain"),
         plt.Line2D([], [], marker="v", color=neg, ls="", label="loss"),
         plt.Line2D([], [], marker="o", color=ns, ls="",
                    label="no difference"),
         plt.Line2D([], [], marker="o", color="black", mfc="none", ms=8,
                    ls="", label="predicted first")]
    ax.legend(handles=h, loc="upper left", fontsize=fs - 1,
              handletextpad=0.2, borderpad=0.4, labelspacing=0.3)
    fig.tight_layout()
    pc.save(fig, "fig_predictor")


# ---------------------------------------------------------------- tables
def _write(stem, rows):
    with open(os.path.join(pc.HERE, stem + ".csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def _n(v, fmt):
    return "n/a" if v is None else fmt % v


def main():
    from make_tables import md_table
    t = table128()
    _write("table_128", t)
    a = acc128()
    md = ("# 128-row layouts next to the 32-row macros\n\n"
          "Generated by `results/make_edge.py` from `results/ppa.csv`, "
          "`results/ppa_128.csv`, `results/load_energy.csv`, "
          "`python/out/tile_scaling.json` and "
          "`python/out/alternatives.json`. The 128-row SidecarCIM is the "
          "final build (merge register, 3-bit S) with K = 4 slots per "
          "column, the fewest that hold accuracy at this height. W4A4, "
          "W6A4 and SidecarCIM were laid out at 35 ns and meet setup and "
          "hold at every corner. The SidecarCIM layout is a rerun with "
          "the hold-repair margins raised to 0.2 ns (placement) and "
          "0.15 ns (global routing); that is the only setting that differs "
          "from the other two. Dense W8A4 did not route at 128 rows, so "
          "only its synthesis area exists. Energies are post-layout "
          "estimates from real GPT-2 tiles, per MVM at the clock in the "
          "table; reload = one full weight load of the macro.\n\n")
    md += md_table(
        ["circuit", "area 32 (um^2)", "pJ/MVM 32", "reload 32 (pJ)",
         "area 128 (um^2)", "pJ/MVM 128", "reload 128 (pJ)",
         "WNS 128 (ns)", "area / W6A4 at 32", "at 128",
         "energy / W6A4 at 32", "at 128", "note"],
        [[r["circuit"] + (" K=%d" % r["k128"] if r["k128"] else ""),
          "%.0f" % r["area32_um2"], "%.1f" % r["energy32_pj"],
          "%.1f" % r["reload32_pj"], "%.0f" % r["area128_um2"],
          _n(r["energy128_pj"], "%.1f"), _n(r["reload128_pj"], "%.0f"),
          _n(r["wns128_ns"], "%+.2f"), "%.2fx" % r["area_vs_w6_32"],
          "%.2fx" % r["area_vs_w6_128"], "%.2fx" % r["energy_vs_w6_32"],
          _n(r["energy_vs_w6_128"], "%.2fx"), r["note"]] for r in t])
    md += ("\nAccuracy on 8 windows (perplexity increase over FP32, GPT-2 "
           "/ Qwen): dense W6A4 %+.2f / %+.2f at any height; SidecarCIM at "
           "32 rows with k = 2 %+.2f / %+.2f; at 128 rows with k = 2 %+.2f / "
           "%+.2f and with k = 4 %+.2f / %+.2f (paired t against W6A4 %.2f "
           "/ %.2f, against the 32-row design %.2f / %.2f). These runs used "
           "the 4-bit shift encoder; the 3-bit clamp was checked at 32 "
           "rows.\n" % (
               a["gpt2"]["w6"], a["qwen"]["w6"], a["gpt2"]["sc32"],
               a["qwen"]["sc32"], a["gpt2"]["sc128k2"], a["qwen"]["sc128k2"],
               a["gpt2"]["sc128k4"], a["qwen"]["sc128k4"],
               a["gpt2"]["t_k4_vs_w6"], a["qwen"]["t_k4_vs_w6"],
               a["gpt2"]["t_k4_vs_32"], a["qwen"]["t_k4_vs_32"]))
    with open(os.path.join(pc.HERE, "table_128.md"), "w",
              encoding="utf8") as fh:
        fh.write(md)
    e = energy_per_token()
    _write("table_energy_token", e)
    md = ("# Macro energy per generated token\n\n"
          "Generated by `results/make_edge.py`. MVMs per token of the "
          "quantized layers (`python/out/token_ops.json`, batch-1 decode, "
          "weight-stationary tiles) times the energy per MVM (32 rows: "
          "`ppa.csv`; 128 rows: the 35 ns layouts in `ppa_128.csv`, "
          "SidecarCIM with K = 4). Each cell is compute only / compute "
          "plus one full weight reload per MVM (`load_energy.csv`). The "
          "first assumes every weight stays in its macro, the second "
          "that no weight does, so the two bracket the macro energy. "
          "Memory, IO, zero-point correction and the FP layers are not "
          "counted. W8A4 has no 128-row layout and W8A8 has no reload "
          "measurement. uJ per token.\n\n")
    md += md_table(
        ["model", "rows", "quantized layers", "MVMs/token",
         "share of linear MACs", "W4A4", "W6A4", "SidecarCIM", "W8A4",
         "W8A8"],
        [[r["model"], r["rows"], r["layers"],
          "{:,}".format(r["mvm_per_token"]),
          "%.1f %%" % r["quantized_mac_share_pct"]] +
         ["%s / %s" % (_n(r[c + "_uJ"], "%.0f"),
                       _n(r[c + "_reload_uJ"], "%.0f"))
          for c in ("W4A4", "W6A4", "SidecarCIM", "W8A4", "W8A8")]
         for r in e])
    with open(os.path.join(pc.HERE, "table_energy_token.md"), "w",
              encoding="utf8") as fh:
        fh.write(md)
    fig_predictor()
    print("wrote table_128, table_energy_token, fig_predictor")


def spearman(pts, key):
    """Spearman correlation of pts[key] with the gain (average ranks)."""
    def ranks(v):
        o = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[o[j + 1]] == v[o[i]]:
                j += 1
            for t in range(i, j + 1):
                r[o[t]] = (i + j) / 2.0 + 1
            i = j + 1
        return r
    x = ranks([q[key] for q in pts])
    y = ranks([q["gain_over_W6A4_ppl"] for q in pts])
    mx, my = sum(x) / len(x), sum(y) / len(y)
    num = sum((u - mx) * (w - my) for u, w in zip(x, y))
    return num / math.sqrt(sum((u - mx) ** 2 for u in x) *
                           sum((w - my) ** 2 for w in y))


# ---------------------------------------------------------------- findings
def findings():
    s = pc.load("srange.json")["tables"]
    po = pc.load("pooled.json")["tables"]
    tl = pc.load("tinylm.json")
    L = []

    def row(t, pat):
        return next(r for r in t["rows"] if r["scheme"].endswith(pat))
    s3 = [row(s[m], "S3b/layer") for m in ("gpt2", "qwen")]
    s2 = [row(s[m], "S2b/layer")["vs_sidecar"] for m in ("gpt2", "qwen")]
    L.append(
        "The ideal per-column shift S never exceeds 7 in any column of GPT-2 or Qwen, so S in 0..7 gives the "
        "same encoding in every layer (perplexity difference exactly %g "
        "and %g), and the final build uses it. A 2-bit S with a per-layer base "
        "is also TOST-equivalent (%+.3f and %+.3f ppl, `srange.json`)." % (
            s3[0]["vs_sidecar"]["dppl"], s3[1]["vs_sidecar"]["dppl"],
            s2[0]["dppl"], s2[1]["dppl"]))
    p12 = [row(po[m], "P12,VB12")["vs_sidecar"] for m in ("gpt2", "qwen")]
    p16 = [row(po[m], "P16,VB12")["vs_sidecar"] for m in ("gpt2", "qwen")]
    L.append(
        "When the 8 columns of a tile share a pool of P slots, P = 12, "
        "25%% fewer slots than k = 2 per column, differs from the fixed "
        "slots by %+.3f and %+.3f ppl (p %.2f and %.2f, TOST-equivalent), "
        "and P = 16 is better by %.3f and %.3f. One column can receive "
        "the whole pool, so the hardware would need a column crossbar or "
        "a cap per column, and we did not build it (`pooled.json`)." % (
            p12[0]["dppl"], p12[1]["dppl"], p12[0]["p_two_sided"],
            p12[1]["p_two_sided"], -p16[0]["dppl"], -p16[1]["dppl"]))
    os_ = tl["outlier_stats"]
    sizes = ("1m", "3m", "8m", "33m")
    act = [os_["tinystories-" + z]["summary"]["act_max_over_std_max"]
           for z in sizes]
    win = []
    for z in sizes:
        rr = {r["scheme"]: r for r in tl["tables"][z]["rows"]}
        win.append(rr["W6A4+mig+wclip"]["vs_sidecar"]["dppl"])
    L.append(
        "TinyStories 1M to 33M have near-Gaussian c_fc weights and a largest activation of "
        "%.1f to %.1f standard deviations (GPT-2 %.1f). Dense W6A4 beats "
        "SidecarCIM at every size, by %s ppl from the smallest to the "
        "largest (`tinylm.json`)." % (
            min(act), max(act),
            os_["gpt2"]["summary"]["act_max_over_std_max"],
            ", ".join("%.2f" % -w for w in win)))
    t = {r["circuit"]: r for r in table128()}
    sc, w6 = t["SidecarCIM"], t["W6A4"]
    a = acc128()
    L.append(
        "At 128 rows, with K = 4 slots per column, SidecarCIM needs %.2fx the area and %.2fx the energy per MVM "
        "of W6A4, against %.2fx and %.2fx at 32 rows. All three 128-row "
        "layouts close setup and hold at %.0f ns (SidecarCIM WNS %+.2f "
        "ns, W6A4 %+.2f ns); the SidecarCIM layout needed raised "
        "hold-repair margins (PL 0.2, GRT 0.15). On 8 windows it loses "
        "%+.2f ppl against %+.2f for W6A4 on GPT-2 (paired t %.2f) and "
        "%+.2f against %+.2f on Qwen (t %.2f, not significant). W8A4 did "
        "not route at 128 rows (`table_128.md`)." % (
            sc["area_vs_w6_128"], sc["energy_vs_w6_128"],
            sc["area_vs_w6_32"], sc["energy_vs_w6_32"], sc["clock128_ns"],
            sc["wns128_ns"], w6["wns128_ns"],
            a["gpt2"]["sc128k4"], a["gpt2"]["w6"],
            a["gpt2"]["t_k4_vs_w6"], a["qwen"]["sc128k4"],
            a["qwen"]["w6"], a["qwen"]["t_k4_vs_w6"]))
    e = {(r["model"][:4], r["rows"]): r for r in energy_per_token()}
    g32, q32 = e[("GPT-", 32)], e[("Qwen", 32)]
    g128, q128 = e[("GPT-", 128)], e[("Qwen", 128)]
    L.append(
        "Counting only the quantized MLP input projections, %.0f%% and "
        "%.0f%% of the linear MACs, SidecarCIM "
        "at 32 rows spends %.0f uJ (GPT-2) and %.0f uJ (Qwen) per token "
        "on compute, against %.0f and %.0f for W6A4 and %.0f and %.0f for "
        "W8A4. If every MVM also reloads its weights, the figures become "
        "%.0f and %.0f uJ (W6A4 %.0f and %.0f). At 128 rows SidecarCIM "
        "needs %.0f and %.0f uJ compute only and %.0f and %.0f with "
        "reload, against %.0f / %.0f and %.0f / %.0f for W6A4 "
        "(`table_energy_token.md`). Whether the weights stay in the "
        "macros matters more than the choice of array." % (
            g32["quantized_mac_share_pct"], q32["quantized_mac_share_pct"],
            g32["SidecarCIM_uJ"], q32["SidecarCIM_uJ"], g32["W6A4_uJ"],
            q32["W6A4_uJ"], g32["W8A4_uJ"], q32["W8A4_uJ"],
            g32["SidecarCIM_reload_uJ"], q32["SidecarCIM_reload_uJ"],
            g32["W6A4_reload_uJ"], q32["W6A4_reload_uJ"],
            g128["SidecarCIM_uJ"], q128["SidecarCIM_uJ"],
            g128["SidecarCIM_reload_uJ"], q128["SidecarCIM_reload_uJ"],
            g128["W6A4_uJ"], q128["W6A4_uJ"], g128["W6A4_reload_uJ"],
            q128["W6A4_reload_uJ"]))
    pts, st = predictor_points()
    sig = [q for q in pts if q["p"] < 0.05]
    gp = [q for q in sig if q["gain_over_W6A4_ppl"] > 0]
    gn = [q for q in sig if q["gain_over_W6A4_ppl"] < 0]
    ka, kk = st["act_max_over_std_max"], st["w_kurtosis_mig"]
    act_, kur = "act_max_over_std_max", "w_kurtosis_mig"
    wt = [q for q in pts if not q["dataset"].startswith("TinyStories")]
    sm = next(q for q in pts if q["model"] == "smollm2-1.7b")
    big = [q for q in wt if q["params"] >= 1.2e8]
    thr = kk["threshold"]
    up = [q for q in pts if q[kur] > thr]
    dn = [q for q in pts if q[kur] <= thr]
    psc = pc.load("predictor.json")["prospective_score"]
    tal = psc["tally"]

    def tl(key):
        t_ = tal[key]
        nm = {"hit": "hit", "miss": "miss", "no call": "no call",
              "sign agrees, not significant": "right sign, not significant"}
        return "; ".join("%s %d" % (nm[k_], v_) for k_, v_ in sorted(t_.items()))
    blm = next(q for q in pts if q["model"] == "bloom-1b1")
    L.append(
        "Over %d models (`predictor.json`), %d of them evaluated after their "
        "predictions were frozen (`predictor_prospective.json`, written %s), "
        "the excess kurtosis of the migrated weights splits the sign of the "
        "gain over W6A4 at %.2f with %d error and leave-one-out %s. Of the "
        "%d models above it %d gain significantly and the rest show no "
        "difference; of the %d at or below it %d lose and none gains. On "
        "the unseen models the kurtosis rule scored %s; the activation-ratio "
        "split (gain above 92, loss below 71) scored %s, missing %s, which "
        "gains %.2f ppl (p %.1e) at an activation ratio of %.0f; the joint "
        "rule scored %s. Over all models the activation ratio has Spearman "
        "%.2f with the gain against %.2f for kurtosis, but its best split is "
        "%.0f with %d errors and leave-one-out %s. On the %d WikiText-2 "
        "models alone the Spearman values are %.2f (activation ratio), %.2f "
        "(kurtosis) and %.2f (parameter count); parameter count also has "
        "leave-one-out %s, and of the %d WikiText-2 models of 124M "
        "parameters or more %d gain and %d lose. The lowest gaining "
        "kurtosis, %.1f, belongs to SmolLM2-1.7B with the sink rule, whose "
        "gain over all %d windows is only marginal (p %.3f); without it the "
        "lowest is %.1f." % (
            len(pts), len(psc["models"]), psc["predictions_written"][:16],
            thr, kk["errors"], kk["loo_accuracy"], len(up),
            sum(q["p"] < 0.05 and q["gain_over_W6A4_ppl"] > 0 for q in up),
            len(dn),
            sum(q["p"] < 0.05 and q["gain_over_W6A4_ppl"] < 0 for q in dn),
            tl("prediction_kurtosis_only"), tl("prediction_act_split_71_92"),
            blm["model"], blm["gain_over_W6A4_ppl"], blm["p"], blm[act_],
            tl("prediction"), ka["spearman_gain"], kk["spearman_gain"],
            ka["threshold"], ka["errors"], ka["loo_accuracy"], len(wt),
            spearman(wt, act_), spearman(wt, kur), spearman(wt, "params"),
            st["params"]["loo_accuracy"], len(big),
            sum(q in gp for q in big), sum(q in gn for q in big),
            sm[kur], sm["windows"], sm["p"],
            min(q[kur] for q in gp if q is not sm)))
    sk = pc.load("sizetrend.json")["sink_rule_smollm2_1.7b"]
    cw = sk["clean_windows"]
    sch = sk["schemes"]
    L.append(
        "On SmolLM2-1.7B without a fix, the attention-sink token takes "
        "SidecarCIM to %s ppl and W8A4 %s. With token 0 of each "
        "window kept in FP (exact, because token 0 only attends to "
        "itself), SidecarCIM gives %.2f and W8A4 %.2f. On the %d windows "
        "where no scheme breaks, SidecarCIM is %.2f ppl better than W6A4 "
        "(90%% CI [%.2f, %.2f], p %.1e), and W8A4 is %.2f ppl better than "
        "SidecarCIM (p %.2f, TOST-equivalent) (`sizetrend.json`)." % (
            format(round(sch["SidecarCIM+wclip k2,VB12 (no rule)"]["ppl"]),
                   ","),
            format(round(sch["W8A4+mig+wclip (no rule)"]["ppl"]), ","),
            sch["SidecarCIM+wclip k2,VB12 (sink rule)"]["ppl"],
            sch["W8A4+mig+wclip (sink rule)"]["ppl"], cw["windows"],
            cw["W6A4+mig+wclip"]["vs_sidecar"]["dppl"],
            *cw["W6A4+mig+wclip"]["vs_sidecar"]["ci90_dppl"],
            cw["W6A4+mig+wclip"]["vs_sidecar"]["p_two_sided"],
            -cw["W8A4+mig+wclip"]["vs_sidecar"]["dppl"],
            cw["W8A4+mig+wclip"]["vs_sidecar"]["p_two_sided"]))
    sh = pc.load("sidecar_shift.json")["tables"]

    def srow(k, s_):
        return next(r for r in sh[k]["rows"] if r["scheme"] == s_)
    qd = "qwen|down"
    t3 = srow(qd, "SidecarCIM+T3 k2,VB12")
    L.append(
        "On Qwen down_proj three layers carry the model's largest "
        "activation outliers. Migration pushes them into weights larger "
        "than a 12-bit slot can hold at S = 0, and SidecarCIM collapses "
        "to %s ppl (%d windows). Shifting the "
        "sidecar sum by a per-column T in 0..7, Y = (D << S) + (C << T), "
        "brings it to %.2f, against %.2f for W8A4 and %.2f for W6A4. T is "
        "non-zero in %d of %d down_proj columns. The down projections "
        "still collapse under every 4-bit-activation scheme on GPT-2, and "
        "4-bit activations stay unusable for the whole model. The shift "
        "is an extension that we tested in Python and did not build "
        "(`sidecar_shift.json`)." % (
            format(round(srow(qd, "SidecarCIM+wclip k2,VB12")["ppl"]), ","),
            sh[qd]["windows"],
            t3["ppl"], srow(qd, "W8A4+mig+wclip")["ppl"],
            srow(qd, "W6A4+mig+wclip")["ppl"],
            sum(v for k_, v in t3["layer_stats"]["mlp_down"]["T_hist"].items()
                if k_ != "0"),
            sum(t3["layer_stats"]["mlp_down"]["T_hist"].values())))
    return L


if __name__ == "__main__":
    main()
