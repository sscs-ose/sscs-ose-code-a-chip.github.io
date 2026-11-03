#!/usr/bin/env python3
"""Comparator input-referred noise of the sized StrongARM at each resolution (sargen/noise.py): analytic estimate
from the simulated gm and integration time, and the probability method with that noise injected.
Writes results/comparator_noise.md.  Run inside IIC-OSIC-TOOLS:  python3 studies/comparator_noise.py [bits ...]
(~15 min per resolution at 300 decisions per input level).
"""
import json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sargen import SarSpec, noise


def snr_loss_db(sigma, lsb):
    """SNR loss from comparator noise next to quantization noise LSB^2/12 (both white, independent)."""
    return 10 * math.log10(1 + sigma ** 2 / (lsb ** 2 / 12))


def main(bits=(4, 6, 8), n_cycles=300):
    rows = []
    for b in bits:
        d = json.loads(Path(f"build/{b}bit/design.json").read_text())
        r = noise.measure(SarSpec(bits=b), d, Path(f"build/{b}bit/studies/noise"), n_cycles=n_cycles)
        rows.append((b, r))
        print(f"{b} bit: sigma est {r['sigma_est'] * 1e6:.0f} uV, measured {r['sigma_meas'] * 1e6:.0f} uV, "
              f"LSB {r['lsb'] * 1e3:.2f} mV", flush=True)
    md = ["| bits | W/L input pair [um] | gm [mS] | T_int [ps] | sigma, estimate [uV] | sigma, simulated [uV] "
          "| LSB [mV] | sigma / LSB | SNR loss [dB] |",
          "|---|---|---|---|---|---|---|---|---|"]
    for b, r in rows:
        c = json.loads(Path(f"build/{b}bit/design.json").read_text())["cmp"]
        s = r["sigma_meas"]
        md.append(f"| {b} | {c['w_in']:.1f}/{c['l_in']:.2f} | {r['gm'] * 1e3:.2f} | {r['t_int'] * 1e12:.0f} "
                  f"| {r['sigma_est'] * 1e6:.0f} | {s * 1e6:.0f} | {r['lsb'] * 1e3:.2f} | 1/{r['lsb'] / s:.0f} "
                  f"| {snr_loss_db(s, r['lsb']):.3f} |")
    md.append(f"\nInput pair thermal noise (gamma = {noise.GAMMA:g}) injected as an equivalent TRNOISE source; "
              f"{n_cycles} decisions per input level, probit fit (Razavi, SSC Magazine 2020).")
    out = Path("results/comparator_noise.md")
    out.write_text("\n".join(md) + "\n")
    print(out.read_text())


if __name__ == "__main__":
    main(tuple(int(a) for a in sys.argv[1:]) or (4, 6, 8))
