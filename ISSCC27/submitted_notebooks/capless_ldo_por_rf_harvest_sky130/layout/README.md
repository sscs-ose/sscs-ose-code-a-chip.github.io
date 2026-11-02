# v3: transistor-level reference and physical layout (added 1–2 Nov 2026, after the deadline)

This folder adds two things the schematic-level notebook did not have:

1. **A transistor-level nano-power bandgap reference.** It replaces the ideal VREF (1.2 V) and Iref (250 nA) sources.
2. **A complete scripted layout of LDO + POR + bandgap**, with DRC and LVS sign-off.

## Bandgap (`scripts/lib.py`: `bgr_subckt`, `BGR0`)

The bandgap has no op-amp. Its parts:

- a self-biased PTAT core: native 5 V NMOS pair (`nfet_05v0_nvt`, W/L = 1/25 × 6) and vertical PNPs at 1:8
- a self-cascoded PMOS mirror
- a level-shifted PMOS diode, to keep headroom at low VIN in the cold
- start-up sensed through a PNP
- VREF = I·R2 + VBE, with a 5-bit trim on R2 (LSB 25 kΩ, about 2 mV)

All results below come from power-up transients:

| | Result |
|---|---|
| VREF (tt, 27 °C, 2.5 V) | 1.198 V; temperature drift 4–9 mV over −40…125 °C |
| PVT (5 corners × 3 temperatures × 3 supplies) | 43 / 45 points within ±1 %. Exceptions: sf / −40 °C / 1.8 V (headroom; recovers at 1.85 V) and fs / 125 °C / 3.3 V (+1.0 %) |
| Monte Carlo, untrimmed (200 chips) | σ = 0.92 % (mainly PMOS-mirror mismatch) |
| Monte Carlo, trimmed once at 27 °C / 2.5 V (100 chips) | −0.61 % … +0.96 % over −40/27/125 °C and 1.8/2.5/3.3 V |
| Supply current | 0.68 µA (tt, 27 °C) |

LDO with this bandgap (tt, schematic):

| | Result |
|---|---|
| VOUT | 1.2012 V |
| Iq (LDO + bandgap) | 4.4 / 6.2 / 9.5 µA at −40 / 27 / 125 °C |
| 0↔1 mA load step, 100 ns edges | −217 / +134 mV |
| Phase margin | 95–129° |

## Layout (`ldo_top.gds`, `ldo_top.png`)

- **Fully scripted.** `scripts/layout.py` reads the same subcircuits the simulations use. It places Magic-generated PDK devices (91 cells) and routes them:
  - metal3 risers from every terminal
  - one metal4 track per net in channels between the rows
  - metal3 trunks
  - 3 µm-wide supply and output nets
- **Size:** 390 × 716 µm. It is not area-optimised; tall stacked mirror devices set the row height.
- **Trim:** bits are hard-wired to code 16 (a metal option; fuses in a product).

**Verification** (run with `scripts/verify.sh`):

| Check | Result |
|---|---|
| KLayout, official `sky130A_mr.drc` deck (FEOL + BEOL + off-grid) | **0 violations** |
| Magic DRC on the flattened final GDS | **0 errors** |
| Netgen LVS (`reports/lvs_report.txt`) | **Circuits match uniquely**, 75 devices / 45 nets, no property errors |

Notes:
- The PDK resistor generator draws URPM only 0.75 µm wide around a 0.35 µm poly resistor (rule urpm.1a needs 1.27 µm). Mask hints widen it to ≥ 1.27 µm, so the final GDS is clean.
- Magic's hierarchical check on the `.mag` view still reports RPM that it regenerates at cell interactions. That RPM is not in the GDS.

## Not done yet (stated plainly)

- **Parasitic extraction and post-layout re-simulation.** RC extraction runs (about 6,700 parasitic resistors), but `ext2spice` does not yet write the coupling capacitances. Post-layout load-step, stability and PSRR margins are therefore **not verified**. The load-step margin was only tens of mV at the worst corner, so this matters.
- The notebook sections 1–14 still use the ideal reference. The bandgap results above come from the scripts in `bandgap/` and `scripts/`.
- The POR has not been re-simulated together with the bandgap.
