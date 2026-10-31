"""C2: does the Python transmitter model predict each chip's fingerprint?
(pre-registered in PLAN.md, 2026-10-02)

For each Monte Carlo chip (tt_mm) and temperature, one ngspice session runs:
  op   -> the chip's 2x31 DAC unit currents (0 V ammeters in series)
  ac   -> RC-CR outputs vi, vq at FLO (LO amplitude/phase imbalance)
  tran -> the full transistor-level transmitter, RF written to a file
Python then extracts the chip's DAC level pattern from the RF output and
compares its chip-specific part with the prediction from the op currents.
"""
import re
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

import tx_full as tx
from spice import mc_control

N_CHIPS = 8
N_SAMPLES = 128
TEMPS = [-40.0, 27.0, 85.0]


def netlist(temp, codes_i, codes_q):
    base = tx.netlist(codes_i, codes_q, temp=temp, corner="tt_mm")
    # put a 0 V ammeter in series with every DAC unit current source
    base = re.sub(r"^XU([iq])(\d+) n([iq])(\d+) ", r"Vm\1\2 n\3\4 m\3\4 0\nXU\1\2 m\3\4 ", base, flags=re.M)
    head = base.split("\n.control")[0]
    prints = "\n".join(f"  print i(Vm{c}{k})" for c in "iq" for k in range(tx.N_UNITS))
    # op/ac keep every vector (single values, cheap). Before the transient, keep only the six
    # waveforms used; afterwards free all stored results. Without this, ngspice kept every
    # node and branch at every 20 ps step for every chip (~1.4 GB per chip, never freed),
    # which ran three parallel runs past 40 GB and froze the machine (2026-10-02).
    body = (f"  delete all\n  op\n{prints}\n"
            f"  ac lin 1 {tx.FLO} {tx.FLO}\n  print vm(vi) vp(vi) vm(vq) vp(vq)\n"
            f"  save v(rfp) v(rfn) v(outp) v(outn) v(lo_i) v(lo_q)\n"
            f"  tran 20p {N_SAMPLES / tx.FS:.4e} 0 20p\n"
            f"  wrdata tx_out_$&seed v(rfp) v(rfn) v(outp) v(outn) v(lo_i) v(lo_q)\n"
            f"  destroy all\n")
    return head + "\n" + mc_control(N_CHIPS, body) + ".end\n"


def run_temp(temp):
    """one ngspice session per temperature; the log is streamed to disk as it runs, so
    finished chips survive an interrupted run."""
    import shutil
    import subprocess
    from spice import SPINIT
    ci, cq, _ = tx.qpsk_codes(N_SAMPLES, seed=1)
    d = tx.WORK / f"validate_T{temp:g}"
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy(SPINIT, d / ".spiceinit")
    (d / "c.sp").write_text(netlist(temp, ci, cq))
    with open(d / "ngspice.log", "w") as log:
        subprocess.run(["ngspice", "-b", "c.sp"], cwd=d, stdout=log, stderr=subprocess.STDOUT, timeout=4 * 3600)
    return temp, str(d)


def parse_op(log):
    chips = {}
    cur = None
    for line in log.splitlines():
        m = re.match(r"@@CHIP (\d+)", line.strip())
        if m:
            cur = int(m.group(1)); chips[cur] = {"u": np.full((2, tx.N_UNITS), np.nan)}
            continue
        if cur is None:
            continue
        m = re.match(r"i\(vm([iq])(\d+)\)\s*=\s*(\S+)", line.strip())
        if m:
            chips[cur]["u"]["iq".index(m.group(1)), int(m.group(2))] = float(m.group(3))
        for k in ("vm(vi)", "vp(vi)", "vm(vq)", "vp(vq)"):
            m = re.match(re.escape(k) + r"\s*=\s*(\S+)", line.strip())
            if m:
                chips[cur][k] = float(m.group(1))
    return chips


def level_fit(y, ci, cq, lo=5, hi=26):
    """one-hot regression -> complex I and Q level vectors over codes lo..hi."""
    keep = (ci >= lo) & (ci <= hi) & (cq >= lo) & (cq <= hi)
    n = hi - lo + 1
    A = np.concatenate([np.eye(n)[ci[keep] - lo], np.eye(n)[cq[keep] - lo][:, 1:]], 1)
    w, *_ = np.linalg.lstsq(A, y[keep], rcond=None)
    seen_i = np.isin(np.arange(lo, hi + 1), ci[keep])
    seen_q = np.isin(np.arange(lo, hi + 1), cq[keep])
    return w[:n], np.concatenate([[0], w[n:]]), seen_i, seen_q


def deviation(levels, seen):
    """real-valued deviation of a level ladder from its best straight line, on seen codes."""
    k = np.arange(len(levels))[seen]
    v = levels[seen]
    v = v * np.exp(-1j * np.angle(np.polyfit(k, v, 1)[0]))          # rotate the ladder onto the real axis
    v = v.real
    return v - np.polyval(np.polyfit(k, v, 1), k), k


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "sim":
        with ProcessPoolExecutor(2) as ex:                    # at most 2 at once
            print(list(ex.map(run_temp, TEMPS)))
        sys.exit()
    ci, cq, _ = tx.qpsk_codes(N_SAMPLES, seed=1)
    out = {}
    for temp in TEMPS:
        d = tx.WORK / f"validate_T{temp:g}"
        chips = parse_op((d / "ngspice.log").read_text())
        pats_t, pats_m = [], []
        for c in sorted(chips):
            t, w = tx.load_wr(d / f"tx_out_{c}")
            y = tx.downconvert(t, w["rfp"] - w["rfn"], N_SAMPLES)
            li, lq, si, sq = level_fit(y, ci, cq)
            u = chips[c]["u"]
            pt, pm = [], []
            for lev, seen, uu in ((li, si, u[0]), (lq, sq, u[1])):
                dev_t, k = deviation(lev, seen)
                cum = np.concatenate([[0], np.cumsum(uu)])[5:27]     # model levels for codes 5..26
                dev_m, _ = deviation(cum.astype(complex), seen)
                pt.append(dev_t / np.std(dev_t + 1e-30)); pm.append(dev_m)
            pats_t.append(np.concatenate(pt)); pats_m.append(np.concatenate(pm))
        Pt, Pm = np.array(pats_t), np.array(pats_m)
        Pt -= Pt.mean(0); Pm -= Pm.mean(0)                           # chip-specific parts only
        r = [np.corrcoef(a, b)[0, 1] for a, b in zip(Pt, Pm)]
        out[temp] = r
        print(f"T={temp:5g}: per-chip correlation (chip-specific DAC pattern, transistor vs model): "
              f"median {np.median(r):.3f}  min {np.min(r):.3f}  all {np.round(r, 2).tolist()}")
    ok = all(np.median(v) >= 0.8 for v in out.values())
    print("pre-registered verdict:", "PASS" if ok else "FAIL")
