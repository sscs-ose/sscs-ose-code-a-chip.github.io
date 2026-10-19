"""r20 (DC part): effective current skew of a nominal +/-4% width skew under the SKY130 binned models.

One NMOS pair per width (W(1 +/- 0.04), L 0.15, drain = gate sweep 0.6-1.0 V at Vd 0.9 V, 27 C).
Effective skew = (I+ - I-) / (I+ + I-); an ideal (bin-neutral) device gives 0.040 at every W and Vg.
  python -B r20_dc_skew.py   ->  out/r20/eff_skew.json  {"<device>|<corner>|<W>": [skew at Vg 0.6 .. 1.0]}
"""
import json
import subprocess

import r3_mismatch_mc  # noqa: F401  (puts the desktop root on sys.path)
from comparator_atlas.spice import ROOT
from r20_offset_mechanism import OUT

PDK = ROOT / ".deps" / "sky130_fd_pr"
NGSPICE = ROOT / ".tools" / "ngspice" / "Spice64" / "bin" / "ngspice_con.exe"
WIDTHS = (2, 3, 4, 6, 7, 12, 24)
SKEW = 0.04
VG = (0.6, 0.7, 0.8, 0.9, 1.0)


def deck(device: str, corner: str, data) -> str:
    cell = PDK / "cells" / device
    lines = ["dc", ".option scale=1u",
             f'.include "{PDK / "models" / "parameters" / "lod.spice"}"',
             f'.include "{cell / f"sky130_fd_pr__{device}__mismatch.corner.spice"}"',
             f'.include "{cell / f"sky130_fd_pr__{device}__{corner}.corner.spice"}"',
             ".temp 27", "Vg g 0 0.9", "Vd dd 0 0.9"]
    k = 0
    for w in WIDTHS:
        for s in (1 + SKEW, 1 - SKEW):
            ww = w * s
            lines += [f"X{k} d{k} g 0 0 sky130_fd_pr__{device} w={ww:.4f} l=0.15 ad={ww * 0.29:.4f} "
                      f"as={ww * 0.29:.4f} pd={2 * (ww + 0.29):.4f} ps={2 * (ww + 0.29):.4f}", f"V{k} dd d{k} 0"]
            k += 1
    lines += [".control", "dc Vg 0.6 1.0 0.1",
              f"wrdata {data} " + " ".join(f"i(V{i})" for i in range(k)), "quit 0", ".endc", ".end"]
    return "\n".join(lines) + "\n"


def main() -> dict:
    folder = OUT / "dc"
    folder.mkdir(parents=True, exist_ok=True)
    out = {}
    for device in ("nfet_01v8_lvt", "nfet_01v8"):
        for corner in ("tt", "sf"):
            data = folder / f"{device}_{corner}.tsv"
            cir = folder / f"{device}_{corner}.cir"
            cir.write_text(deck(device, corner, data))
            subprocess.run([str(NGSPICE), "-b", str(cir)], check=True, capture_output=True, timeout=600)
            rows = [[float(x) for x in line.split()[1::2]] for line in data.read_text().splitlines() if line.strip()]
            if len(rows) != len(VG):
                raise RuntimeError(f"{device} {corner}: expected {len(VG)} sweep points")
            for i, w in enumerate(WIDTHS):
                out[f"{device}|{corner}|{w}"] = [(r[2 * i] - r[2 * i + 1]) / (r[2 * i] + r[2 * i + 1]) for r in rows]
    (OUT / "eff_skew.json").write_text(json.dumps(out, indent=1) + "\n")
    return out


if __name__ == "__main__":
    for key, values in main().items():
        print(f"{key:22s} " + " ".join(f"{v:.3f}" for v in values))
