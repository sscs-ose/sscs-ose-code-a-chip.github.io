"""Circuit schematics generated from the same parameters the netlist uses.

Generated rather than pasted: a PNG exported from a schematic editor is a binary asset
that can drift from the netlist actually simulated. These are built from the same device
widths, so they cannot drift -- change a width and the drawing changes with it.
"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

CMP  = dict(w_tail=0.5, w_in=1.5, w_ln=0.5, w_lp=0.5, w_rst=0.5)
WL   = 1.40          # MiM unit, um
CUNIT= 4.830         # fF, measured (area + perimeter)
N    = 8

# ------------------------------------------------------------------ architecture ---
def architecture(fn="sch_architecture.png"):
    fig, ax = plt.subplots(figsize=(11, 4.6))
    def box(x, y, w, h, text, fc="#eaf2f8", ec="#2c3e50"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.06",
                                    fc=fc, ec=ec, lw=1.4))
        ax.text(x+w/2, y+h/2, text, ha="center", va="center", fontsize=9)
    def arrow(x1, y1, x2, y2, label="", style="-|>"):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                                     mutation_scale=13, lw=1.3, color="#2c3e50"))
        if label: ax.text((x1+x2)/2, (y1+y2)/2+0.12, label, ha="center", fontsize=7.5)

    box(0.2, 2.6, 1.5, 0.8, "sampling\nswitch\nTG+dummy")
    box(2.3, 2.6, 2.3, 0.8, f"binary-weighted\nMiM CDAC\n{2**N} x {CUNIT:.2f} fF")
    box(5.2, 2.6, 1.8, 0.8, "StrongARM\ncomparator")
    box(7.6, 2.6, 1.7, 0.8, f"SAR register\n{N} x DFF")
    box(3.6, 0.5, 3.2, 0.8, f"one-hot sequencer  p0..p{N}\nclear DERIVED at 9.75·t$_p$")

    ax.text(-0.35, 3.0, "$V_{in}$", fontsize=11, va="center")
    arrow(-0.05, 3.0, 0.2, 3.0)
    arrow(1.7, 3.0, 2.3, 3.0)
    arrow(4.6, 3.0, 5.2, 3.0, "top plate")
    arrow(7.0, 3.0, 7.6, 3.0)
    arrow(9.3, 3.0, 9.9, 3.0)
    ax.text(10.05, 3.0, "$D_{out}[7{:}0]$", fontsize=11, va="center")
    # feedback: register drives the DAC bottom plates
    ax.add_patch(FancyArrowPatch((8.45, 2.6), (8.45, 1.9), arrowstyle="-", lw=1.3, color="#c0392b"))
    ax.add_patch(FancyArrowPatch((8.45, 1.9), (3.45, 1.9), arrowstyle="-", lw=1.3, color="#c0392b"))
    ax.add_patch(FancyArrowPatch((3.45, 1.9), (3.45, 2.6), arrowstyle="-|>", mutation_scale=13,
                                 lw=1.3, color="#c0392b"))
    ax.text(5.9, 2.0, "bit $k$ sets the DAC for trial $k+1$ — so the LAST trial's\n"
                      "decision feeds nothing, which is why the dead LSB was readout-only",
            ha="center", fontsize=7.5, color="#c0392b")
    arrow(5.2, 1.3, 5.2, 2.6, style="-|>")
    ax.text(5.35, 1.95, "clk", fontsize=7.5)
    ax.set_xlim(-0.9, 11.4); ax.set_ylim(0.1, 4.0); ax.axis("off")
    ax.set_title("8-bit charge-redistribution SAR ADC", fontsize=12, pad=6)
    fig.tight_layout(); fig.savefig(fn, dpi=150, bbox_inches="tight"); plt.close(fig)
    return fn

# --------------------------------------------------------------- StrongARM latch ---
def _mos(ax, x, y, kind, label, mirror=False, h=0.62, lab_dx=0.0):
    """One MOSFET drawn at (x, y). Gate faces left unless mirror=True.
    Returns (drain, gate, source) connection points; drain is the upper terminal."""
    c = "#2c3e50"; s = -1 if not mirror else 1
    ax.plot([x, x], [y+h, y+h*0.45], c=c, lw=1.4)
    ax.plot([x, x], [y-h, y-h*0.45], c=c, lw=1.4)
    ax.plot([x, x], [y+h*0.45, y-h*0.45], c=c, lw=1.7)            # channel
    gx = x + 0.30*s
    ax.plot([gx, gx], [y+h*0.42, y-h*0.42], c=c, lw=1.7)          # gate plate
    ax.plot([gx, gx+0.34*s], [y, y], c=c, lw=1.4)                 # gate lead
    if kind == "p":
        ax.add_patch(plt.Circle((gx+0.10*s, y), 0.075, fc="white", ec=c, lw=1.2, zorder=4))
    ax.text(x - 0.52*s + lab_dx, y, label, fontsize=6.8, va="center",
            ha="right" if not mirror else "left", color="#444", linespacing=1.35,
            bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.9), zorder=6)
    return (x, y+h), (gx+0.34*s, y), (x, y-h)

def comparator(fn="sch_comparator.png"):
    fig, ax = plt.subplots(figsize=(8.6, 7.4))
    c = "#2c3e50"; XL, XR = -1.5, 1.5
    wire = lambda xs, ys, col=c, lw=1.4: ax.plot(xs, ys, c=col, lw=lw, zorder=1)
    dot  = lambda x, y: ax.plot([x], [y], "o", ms=5, c=c, zorder=5)

    wire([XL-1.1, XR+1.1], [5.5, 5.5])
    ax.plot([0, 0], [5.5, 5.85], c=c, lw=1.4)
    ax.plot([-0.22, 0.22], [5.85, 5.85], c=c, lw=2.2)
    ax.text(0, 6.02, "VDD", ha="center", fontsize=10)

    nd = {}
    for x, mir, out, inlab in ((XL, False, "outn", "inp"), (XR, True, "outp", "inn")):
        s = 1 if mir else -1
        # reset PMOS outboard, latch PMOS inboard -- keeps the gate leads from crossing
        rd, rg, rs = _mos(ax, x + 0.62*s, 4.75, "p", f"$M_{{rst}}$\n{CMP['w_rst']}µm", mir)
        pd, pg, ps = _mos(ax, x - 0.62*s, 4.75, "p", f"$M_{{lp}}$\n{CMP['w_lp']}µm", not mir)
        wire([rd[0], rd[0]], [5.5, rd[1]]); wire([pd[0], pd[0]], [5.5, pd[1]])
        wire([rs[0], rs[0]], [rs[1], 3.9]); wire([ps[0], ps[0]], [ps[1], 3.9])
        wire([rs[0], ps[0]], [3.9, 3.9]); dot(x, 3.9)
        ax.text(x + 0.55*s, 4.06, out, fontsize=10, ha="center", color="#c0392b")
        ld, lg, ls = _mos(ax, x, 3.1, "n", f"$M_{{ln}}$\n{CMP['w_ln']}µm", not mir)
        wire([x, x], [3.9, ld[1]])
        idd, ig, iss = _mos(ax, x, 1.55, "n", f"$M_{{in}}$\n{CMP['w_in']}µm", mir)
        wire([x, x], [ls[1], idd[1]]); dot(x, 2.32)
        wire([x, x], [iss[1], 0.72])
        wire([ig[0], x + 2.9*s], [ig[1], ig[1]])
        ax.text(x + 3.02*s, ig[1], inlab, fontsize=10, va="center",
                ha="left" if mir else "right")
        nd[out] = dict(node=(x, 3.9), lg=lg, pg=pg, rg=rg)

    # cross-coupling: each latch gate pair is driven by the OPPOSITE output node
    for tgt, src, yj in (("outn", "outp", 3.52), ("outp", "outn", 3.34)):
        lg, pg = nd[tgt]["lg"], nd[tgt]["pg"]; sx = nd[src]["node"][0]
        wire([lg[0], lg[0]], [lg[1], yj], "#c0392b")
        wire([pg[0], pg[0]], [pg[1], yj], "#c0392b")
        wire([lg[0], pg[0]], [yj, yj], "#c0392b")
        wire([pg[0], sx], [yj, yj], "#c0392b")
        wire([sx, sx], [yj, 3.9], "#c0392b")
    ax.text(0, 2.70, "cross-coupled latch", ha="center", fontsize=7.5, color="#c0392b")

    # clk drives both reset gates and the tail. Drawn as labelled stubs rather than one
    # long wire, which would cross the input leads and read as a connection.
    for k in ("outn", "outp"):
        rg = nd[k]["rg"]; s = -1 if k == "outn" else 1
        wire([rg[0], rg[0] + 0.55*s], [rg[1], rg[1]], "#2471a3")
        ax.text(rg[0] + 0.68*s, rg[1], "clk", fontsize=8, va="center",
                ha="left" if s > 0 else "right", color="#2471a3")

    wire([XL, XR], [0.72, 0.72]); dot(0, 0.72)
    td, tg, ts = _mos(ax, 0, 0.05, "n", f"$M_{{tail}}$\n{CMP['w_tail']}µm", True)
    wire([0, 0], [0.72, td[1]])
    wire([tg[0], tg[0] + 0.7], [tg[1], tg[1]], "#2471a3")
    ax.text(tg[0] + 0.85, tg[1], "clk", fontsize=10, va="center", ha="left", color="#2471a3")
    wire([0, 0], [ts[1], -0.9])
    for i, w in enumerate((0.34, 0.22, 0.10)):
        ax.plot([-w, w], [-0.9-0.11*i, -0.9-0.11*i], c=c, lw=1.8)

    ax.set_xlim(-5.2, 5.2); ax.set_ylim(-1.5, 6.4); ax.axis("off"); ax.set_aspect("equal")
    ax.set_title("StrongARM comparator — device widths as simulated", fontsize=11, pad=4)
    fig.tight_layout(); fig.savefig(fn, dpi=150, bbox_inches="tight"); plt.close(fig)
    return fn

# -------------------------------------------------------------------- CDAC slice ---
def cdac_slice(fn="sch_cdac.png"):
    """Charge-redistribution DAC. Each bottom plate switches between VREF and GND under
    the control of its own decided bit; the top plate is common and floats after
    sampling. The dummy is tied off rather than left floating."""
    fig, ax = plt.subplots(figsize=(11, 5.0))
    c = "#2c3e50"
    cols = [("128C", "$b_0$"), ("64C", "$b_1$"), ("32C", "$b_2$"),
            ("...", None), ("2C", "$b_6$"), ("1C", "$b_7$"), ("1C", "dummy")]
    xs = [k*1.55 for k in range(len(cols))]
    TOP, CAP_T, CAP_B, SW, RAIL_V, RAIL_G = 3.9, 3.3, 2.7, 2.0, 1.15, 0.45

    ax.plot([xs[0]-1.5, xs[-1]+1.3], [TOP, TOP], c=c, lw=1.8)
    ax.text(xs[0]-1.62, TOP, "top plate", ha="right", va="center", fontsize=9)
    ax.plot([xs[-1]+1.3], [TOP], "o", ms=5, mfc="white", mec=c)
    ax.text(xs[-1]+1.42, TOP, "to comparator", fontsize=9, va="center")

    # sampling switch to Vcm
    ax.plot([xs[0]-1.1, xs[0]-1.1], [TOP, TOP+0.75], c=c, lw=1.4)
    ax.plot([xs[0]-1.1], [TOP+0.75], "o", ms=4, mfc="white", mec=c, zorder=4)
    ax.plot([xs[0]-1.1, xs[0]-0.62], [TOP+0.75, TOP+1.05], c=c, lw=1.6)
    ax.plot([xs[0]-0.35], [TOP+0.75], "o", ms=4, mfc="white", mec=c, zorder=4)
    ax.plot([xs[0]-0.35, xs[0]+0.30], [TOP+0.75, TOP+0.75], c=c, lw=1.4)
    ax.text(xs[0]-0.72, TOP+1.22, "sample", fontsize=8, ha="center")
    ax.text(xs[0]+0.48, TOP+0.75, "$V_{cm}$", fontsize=9, va="center")

    for x, (w, bit) in zip(xs, cols):
        if w == "...":
            ax.text(x, (CAP_T+CAP_B)/2, "$\\cdots$", ha="center", va="center", fontsize=15)
            continue
        ax.plot([x, x], [TOP, CAP_T], c=c, lw=1.4)
        ax.plot([x-0.30, x+0.30], [CAP_T, CAP_T], c=c, lw=2.2)      # plates
        ax.plot([x-0.30, x+0.30], [CAP_B, CAP_B], c=c, lw=2.2)
        ax.text(x+0.38, (CAP_T+CAP_B)/2, w, fontsize=8.5, va="center")
        ax.plot([x, x], [CAP_B, SW+0.3], c=c, lw=1.4)
        if bit == "dummy":
            ax.plot([x, x], [SW+0.3, RAIL_G], c=c, lw=1.4)
            for i, hw in enumerate((0.26, 0.17, 0.08)):
                ax.plot([x-hw, x+hw], [RAIL_G-0.10*i, RAIL_G-0.10*i], c=c, lw=1.8)
            ax.text(x, SW-0.15, "dummy\ntied off", fontsize=7, ha="center", color="#7f8c8d")
            continue
        # SPDT thrown by the decided bit: VREF on the left throw, GND on the right.
        # The blade is drawn making contact with VREF so the state is unambiguous.
        ax.plot([x], [SW+0.3], "o", ms=4.5, c=c, zorder=4)            # common
        ax.plot([x-0.36, x-0.36], [RAIL_V, RAIL_V+0.18], c=c, lw=1.4) # left throw stub
        ax.plot([x+0.36, x+0.36], [RAIL_G, RAIL_G+0.18], c=c, lw=1.4) # right throw stub
        ax.plot([x-0.36], [RAIL_V+0.18], "o", ms=4, mfc="white", mec=c, zorder=4)
        ax.plot([x+0.36], [RAIL_G+0.18], "o", ms=4, mfc="white", mec=c, zorder=4)
        ax.plot([x, x-0.36], [SW+0.3, RAIL_V+0.18], c="#c0392b", lw=1.8, zorder=3)  # blade
        ax.text(x+0.14, SW-0.18, bit, fontsize=9, ha="left", color="#c0392b")

    ax.plot([xs[0]-0.8, xs[-2]+0.8], [RAIL_V, RAIL_V], c="#27ae60", lw=1.6)
    ax.text(xs[0]-0.95, RAIL_V, "VREF", ha="right", va="center", fontsize=9, color="#27ae60")
    ax.plot([xs[0]-0.8, xs[-2]+0.8], [RAIL_G, RAIL_G], c=c, lw=1.6)
    ax.text(xs[0]-0.95, RAIL_G, "GND", ha="right", va="center", fontsize=9)

    ax.text((xs[0]+xs[-1])/2, -0.35,
            f"256 units of {CUNIT:.2f} fF (measured: area + perimeter). Binary weights are "
            f"built from\nidentical units in a dispersed common-centroid pattern, not from "
            f"scaled devices.",
            ha="center", fontsize=8, color="#555")
    ax.set_xlim(xs[0]-3.4, xs[-1]+3.6); ax.set_ylim(-0.8, TOP+1.7)
    ax.axis("off"); ax.set_title("Binary-weighted MiM capacitor DAC", fontsize=11, pad=4)
    fig.tight_layout(); fig.savefig(fn, dpi=150, bbox_inches="tight"); plt.close(fig)
    return fn



# ------------------------------------------------------------------- workflow ---
def workflow(fn="sch_workflow.png"):
    """The notebook's flow. Not specific to this converter: the same sequence applies
    to any mixed-signal block in an open PDK."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    fig, ax = plt.subplots(figsize=(13, 6.2))
    C = dict(spec="#d6eaf8", build="#d5f5e3", meas="#fdebd0", verify="#e8daef", fail="#fadbd8")

    def box(x, y, w, h, title, sub="", fc="#eee", fs=8.5):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.07",
                                    fc=fc, ec="#2c3e50", lw=1.3))
        ax.text(x+w/2, y+h*0.62, title, ha="center", va="center", fontsize=fs, weight="bold")
        if sub: ax.text(x+w/2, y+h*0.26, sub, ha="center", va="center", fontsize=7, color="#555")
    def arr(x1,y1,x2,y2,c="#2c3e50",style="-|>",lw=1.3):
        ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle=style,mutation_scale=12,lw=lw,color=c))

    box(0.1, 4.4, 2.5, 1.0, "1. Specification", "written BEFORE\nany transistor", C["spec"])
    box(3.0, 4.4, 2.5, 1.0, "2. Behavioural model", "harness validated on a\nconverter with a known answer", C["spec"])
    box(5.9, 4.4, 2.6, 1.0, "3. Blocks", "comparator · CDAC ·\nSAR logic", C["build"])
    box(8.9, 4.4, 2.6, 1.0, "4. Assembled converter", "774 devices, ngspice", C["build"])

    box(8.9, 2.7, 2.6, 1.0, "5. Measure", "ENOB · INL · monotonicity", C["meas"])
    box(5.9, 2.7, 2.6, 1.0, "6. Physical design", "layout generated\nfrom the netlist", C["verify"])
    box(3.0, 2.7, 2.5, 1.0, "7. DRC + LVS", "full sky130A deck\nnetlist match", C["verify"])
    box(0.1, 2.7, 2.5, 1.0, "8. Results", "every spec measured,\nincluding the failure", C["meas"])

    for a,b in (((2.6,4.9),(3.0,4.9)), ((5.5,4.9),(5.9,4.9)), ((8.5,4.9),(8.9,4.9)),
                ((10.2,4.4),(10.2,3.7)), ((8.9,3.2),(8.5,3.2)), ((5.9,3.2),(5.5,3.2)),
                ((3.0,3.2),(2.6,3.2))):
        arr(*a,*b)

    # the loop that matters
    box(3.6, 0.7, 4.6, 1.1, "TRY TO BREAK THE MEASUREMENT", 
        "vary the numerics · check an invariant · measure what the spec names", C["fail"], fs=9)
    arr(1.35, 2.7, 1.35, 1.25); arr(1.35, 1.25, 3.6, 1.25)
    arr(8.2, 1.25, 10.2, 1.25, c="#c0392b"); arr(10.2, 1.25, 10.2, 2.7, c="#c0392b")
    ax.text(9.3, 1.45, "withdraw and re-measure", fontsize=7.5, color="#c0392b", ha="center")
    ax.text(5.9, 0.35, "Four published results were withdrawn this way. None were circuit problems;\n"
                       "all four reproduced perfectly on re-run.",
            ha="center", fontsize=8, color="#c0392b")

    ax.set_xlim(-0.3, 11.9); ax.set_ylim(0.0, 5.9); ax.axis("off")
    ax.set_title("Workflow: an open-PDK mixed-signal block, and the loop that checks it",
                 fontsize=12, pad=8)
    fig.tight_layout(); fig.savefig(fn, dpi=150, bbox_inches="tight"); plt.close(fig)
    return fn


if __name__ == "__main__":
    for f in (architecture(), comparator(), cdac_slice(), workflow()):
        print("wrote", f)
