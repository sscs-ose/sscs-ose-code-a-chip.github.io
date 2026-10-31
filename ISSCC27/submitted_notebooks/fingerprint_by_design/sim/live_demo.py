"""Short live demo for the notebook: simulate a few virtual chips at transistor level and
extract their level-ladder fingerprints.

The frame is 66 DAC samples that use every code 5..26 three times on each channel (about
half the length of the 128-sample frame in the main study), so two chips take a few
minutes. Same netlist, PDK models and feature definition as tx_ident.py; only the frame
differs, so the fingerprints are not numerically identical to the main study's.
A second ngspice run simulates the "nominal" chip (typical models, no mismatch): the
design's mismatch-free response. Chip-to-chip differences distinguish devices; their
shared offset from nominal does not.

usage: python live_demo.py [n_chips] [--out DIR]     ->  DIR/live_fingerprints.json
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

import tx_full as tx
from spice import SPINIT, mc_control
from tx_validate import level_fit

LO_CODE, HI_CODE, REPS_PER_CODE = 5, 26, 3


def demo_codes(seed=7):
    rng = np.random.default_rng(seed)
    codes = np.arange(LO_CODE, HI_CODE + 1)
    ci = np.concatenate([rng.permutation(codes) for _ in range(REPS_PER_CODE)])
    cq = np.concatenate([rng.permutation(codes) for _ in range(REPS_PER_CODE)])
    return ci, cq


def netlist(ci, cq, n_chips, temp=27.0):
    """n_chips Monte Carlo chips (seeds 1..n, as in the main study); n_chips=0: the nominal chip."""
    base = tx.netlist(ci, cq, temp=temp, corner="tt_mm" if n_chips else "tt")
    head = base.split("\n.control")[0]
    name = "tx_out_$&seed" if n_chips else "tx_out_nominal"
    body = ("  delete all\n  save v(rfp) v(rfn) v(outp) v(outn) v(lo_i) v(lo_q)\n"
            f"  tran 20p {len(ci) / tx.FS:.4e} 0 20p\n"
            f"  wrdata {name} v(rfp) v(rfn) v(outp) v(outn) v(lo_i) v(lo_q)\n  destroy all\n")
    if not n_chips:
        return head + "\n.control\n" + body + ".endc\n.end\n"
    return head + "\n" + mc_control(n_chips, body, 1) + ".end\n"


def fingerprint(y, ci, cq):
    """level-ladder deviation from a straight line, I and Q, real and imaginary parts."""
    li, lq, _, _ = level_fit(y, ci, cq, LO_CODE, HI_CODE)
    k = np.arange(len(li))
    return {f"{ch}_{part}": (getattr(lev, part) - np.polyval(np.polyfit(k, getattr(lev, part), 1), k)).tolist()
            for ch, lev in (("I", li), ("Q", lq)) for part in ("real", "imag")}


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 2
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else Path.cwd()
    d = out / "live_run"
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy(SPINIT, d / ".spiceinit")
    ci, cq = demo_codes()
    # Never let an incomplete rerun reuse an older successful waveform.
    for tag in ["nominal"] + [str(k) for k in range(1, n + 1)]:
        (d / f"tx_out_{tag}").unlink(missing_ok=True)
    t0, procs = time.time(), []
    for tag, k in (("mc", n), ("nominal", 0)):                # two ngspice processes in parallel
        (d / f"{tag}.sp").write_text(netlist(ci, cq, k))
        procs.append(subprocess.Popen(["ngspice", "-b", f"{tag}.sp"], cwd=d, stdout=open(d / f"{tag}.log", "w"),
                                      stderr=subprocess.STDOUT))
    statuses = [p.wait() for p in procs]
    if any(statuses):
        sys.exit(f"ngspice failed ({statuses}); inspect the logs in {d}")
    secs = time.time() - t0
    ideal = (2 * ci / tx.N_UNITS - 1) + 1j * (2 * cq / tx.N_UNITS - 1)
    chips = {}
    for s in ["nominal"] + [str(k) for k in range(1, n + 1)]:
        f = d / f"tx_out_{s}"
        if not f.exists():
            sys.exit(f"chip {s}: no waveform, see the logs in {d}")
        t, w = tx.load_wr(f)
        if t[-1] < len(ci) / tx.FS * (1 - 1e-6):
            sys.exit(f"chip {s}: incomplete transient; see the logs in {d}")
        y = tx.downconvert(t, w["rfp"] - w["rfn"], len(ci))
        y = y / ((y @ ideal.conj()) / (ideal @ ideal.conj()))
        evm = 100 * np.sqrt(np.mean(np.abs(y - ideal) ** 2) / np.mean(np.abs(ideal) ** 2))
        chips[s] = {"evm_pct": float(evm), "fingerprint": fingerprint(y, ci, cq),
                    "baseband": [y.real.tolist(), y.imag.tolist()]}
        f.unlink()                                        # each waveform is ~25 MB; keep only the result
    res = {"n_chips": n, "codes": list(range(LO_CODE, HI_CODE + 1)), "ci": ci.tolist(), "cq": cq.tolist(),
           "ngspice_seconds": secs, "chips": chips}
    (out / "live_fingerprints.json").write_text(json.dumps(res, indent=1))
    print(f"{n} chips + nominal in {secs / 60:.1f} min; EVM " + ", ".join(f"chip {k}: {v['evm_pct']:.1f}%" for k, v in chips.items()))


if __name__ == "__main__":
    main()
