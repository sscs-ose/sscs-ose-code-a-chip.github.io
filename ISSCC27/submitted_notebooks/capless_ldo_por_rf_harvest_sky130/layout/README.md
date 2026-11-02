# v3: transistor-level reference, physical layout and post-layout verification

This folder adds three things the schematic-level notebook did not have:

1. **A transistor-level nano-power bandgap reference.** It replaces the ideal VREF (1.2 V) and Iref (250 nA) sources.
2. **A complete scripted layout of LDO + POR + bandgap**, with DRC and LVS sign-off.
3. **Parasitic extraction and post-layout re-simulation** of the whole block over 45 PVT points: load step, small-step damping, Iq, POR thresholds and PSRR.

Everything is reproduced by `scripts/run_all.sh`: device cells, placement and routing, DRC/LVS, C extraction, then all simulations.

## Bandgap (`scripts/lib.py`: `bgr_subckt`, `BGR0`)

The bandgap has no op-amp. Its parts:

- a self-biased PTAT core: native 5 V NMOS pair (`nfet_05v0_nvt`, W/L = 1/25 × 6) and vertical PNPs at 1:8
- a self-cascoded PMOS mirror
- a level-shifted PMOS diode, to keep headroom at low VIN in the cold
- start-up sensed through a PNP (release NMOS gate at VREF, source on a VBE)
- VREF = I·R2 + VBE, with a 5-bit trim on R2 (LSB 25 kΩ, about 2 mV)
- a supply-ripple filter **outside the bandgap loop**: 2 MΩ into 5 pF of MIM, between the core output and the LDO's reference input

The filter sits behind a resistor on purpose. With the MIM directly on the core output, the start-up release (which senses VREF) was delayed. The kick then overshot VREF, and at −40 °C the core collapsed into its zero-current state in three post-layout corners. Behind 2 MΩ the core and its start-up see no extra load. The LDO's reference input is a MOS gate, so the resistor adds no DC error.

All results below come from power-up transients:

| | Result |
|---|---|
| VREF (tt, 27 °C, 2.5 V) | 1.1996 V; 1.1960 / 1.1996 / 1.2035 V at −40 / 27 / 125 °C (7.5 mV) |
| PVT (5 corners × 3 temperatures × 3 supplies) | 42 / 45 points within ±1 %. Exceptions: ss / 125 °C / 3.3 V (+1.0 %), fs / 125 °C / 3.3 V (+3.3 %), sf / −40 °C / 1.8 V (−5 %, headroom; recovers at 1.85 V) |
| Monte Carlo, untrimmed (200 chips) | σ = 0.86 % (mainly PMOS-mirror mismatch) |
| Monte Carlo, trimmed once at 27 °C / 2.5 V (100 chips) | −0.61 % … +0.96 % over −40/27/125 °C and 1.8/2.5/3.3 V |
| Supply current (tt, 2.5 V) | 0.44 / 0.63 / 0.96 µA at −40 / 27 / 125 °C |
| Supply rejection at the filtered output (tt) | 34.5 dB at 1 kHz; 21.8–38.6 dB from 10 kHz to 847 kHz (it was −0.4 dB at 100 kHz without the filter) |
| Start-up on a slow ramp (0 → 3.3 V in 10 ms) | VREF is up by VIN = 1.27–1.61 V at −40 / 27 °C and 1.59–2.18 V at 125 °C. The exception is ss / 125 °C at 2.49 V. It releases cleanly at every corner. |

## Layout (`ldo_top.gds`, `ldo_top.png`)

- **Fully scripted.** `scripts/layout.py` reads the same subcircuits the simulations use. It places Magic-generated PDK devices (96 cells) and routes them:
  - metal3 risers from every terminal
  - one metal4 track per net in channels between the rows
  - metal3 trunks
  - 3 µm-wide supply and output nets
- **Size:** 390 × 524 µm.
  - Wide mirror and pass devices are split into ≤ 20 µm fingers, so rows stay short and the risers that couple VIN into VOUT stay short.
  - VIN–VOUT coupling: 0.49 pF, down from 1.5 pF in the first placement.
- **Trim:** bits are hard-wired to code 16 (a metal option; fuses in a product).

**Verification** (`scripts/verify.sh`):

| Check | Result |
|---|---|
| KLayout, official `sky130A_mr.drc` deck (FEOL + BEOL + off-grid) | **0 violations** |
| Magic DRC on the flattened final GDS | **0 errors** |
| Netgen LVS (`reports/lvs_report.txt`) | **Circuits match uniquely**, 77 devices / 46 nets, no property errors |

Notes:
- The PDK resistor generator draws URPM only 0.75 µm wide around a 0.35 µm poly resistor (rule urpm.1a needs 1.27 µm). Mask hints widen it to ≥ 1.27 µm, so the final GDS is clean.
- Magic's hierarchical check on the `.mag` view still reports RPM that it regenerates at cell interactions. That RPM is not in the GDS.

## Post-layout simulation (`scripts/postlayout.py`, `scripts/por_check.py`)

**Extraction.**
- Magic C extraction with coupling capacitance: 1,992 parasitic capacitors (`reports/ldo_top_pexC.spice`).
- Every run is a power-up transient of the whole block (VIN ramps from 0 V in 1 ms). The bandgap start-up and the POR are therefore exercised as on a harvested tag.

**PVT: 5 corners × −40 / 27 / 125 °C × VIN 1.8 / 2.5 / 3.3 V = 45 points** (`reports/postlayout_pvt_pex.csv`):

| | Spec | Post-layout result |
|---|---|---|
| 0 → 1 mA load step, 100 ns edge: undershoot | ≤ 300 mV | **≤ 279 mV** (worst at 125 °C; 209 mV at −40 °C, 240 mV at 27 °C) |
| 1 → 0 mA: overshoot | | ≤ 180 mV |
| Small-step (10 µA) recovery overshoot | | ≤ 17 %, except fs / −40 °C / ≥ 2.5 V: 24–26 % (VREF still settling, see below) |
| Iq, LDO + bandgap + POR (4 ms after power-up) | | 7.2 µA at tt / 27 °C; worst 12.8 µA (sf / −40 °C / 2.5 V); ≤ 11.5 µA at 125 °C |
| VOUT 4 ms after power-up, ±3 % | 1.164–1.236 V | 1.186–1.234 V at 43 / 45 points. **FAIL at fs / −40 °C / ≥ 2.5 V: 1.244 V (+3.7 %)**; it is 1.205 V at 8 ms |
| POR release V_on / hysteresis (15 corner × temperature points, `reports/postlayout_por_pex.csv`) | 2.0 V ± 10 % / ≥ 150 mV | **1.894–2.192 V / ≥ 244 mV** |

**Spec status with the real bandgap, after layout.** The notebook's "18 PASS, 0 FAIL" (Section 13) is the schematic-level result with the ideal reference. After layout, with the bandgap:
- **Load step, POR, stability: PASS.**
- **PSRR at 1 kHz: FAIL**, 24.8 dB against ≥ 30 dB.
- **VOUT ±3 % at 4 ms: FAIL** at fs / −40 °C / ≥ 2.5 V (+3.7 %; it passes by 8 ms).
- **Quiescent current:** the ≤ 10 µA spec was for the LDO alone. The whole block (LDO + bandgap + POR) draws 7.2 µA at tt and up to 12.8 µA in the cold.
- **Usable VIN:** the POR keeps the core in reset below its release threshold (1.89–2.19 V over PVT), so RST_N stays low at VIN = 1.8 V by design.

**Post-layout PSRR at 1 kHz fails the notebook's 30 dB spec: 24.8 dB at tt** (34.9 dB before layout). The cause is not found; see the open points.

**Before vs after layout** (tt, 27 °C, 2.5 V; the same netlist without parasitics vs with them):

| | Pre-layout | Post-layout |
|---|---|---|
| Load-step undershoot / overshoot | 201 / 133 mV | 231 / 143 mV |
| Iq | 7.27 µA | 7.24 µA |
| PSRR at 1 kHz | 34.9 dB | 24.8 dB |
| PSRR at 100 kHz | 18.6 dB | 21.3 dB |
| PSRR at 847 kHz (NFC subcarrier) | 18.0 dB | 19.1 dB |
| VOUT | 1.2014 V | 1.1929 V |

Notes on the table:
- PSRR in the table is the ripple fitted at the test frequency, so slow drift is not counted.
- With the ideal reference, the notebook's PSRR was −0.4 dB at 100 kHz (v1) and 8.7 dB (v2).
- **VOUT −8.5 mV:** the extracted bandgap gives 1.191 V instead of 1.199 V (meandered high-resistance poly vs the schematic value). This is about 4 trim LSBs, well inside the trim range.

## Open points (measured, not hidden)

- **Start-up settling at fs / −40 °C, VIN ≥ 2.5 V.**
  - The start-up kick overshoots VREF to 1.67 V. It relaxes to 1.243 V at 4 ms, 1.205 V at 8 ms and 1.193 V at 16 ms.
  - Measured at 4 ms, this corner reads VOUT = 1.243 V and a 25 % small-step overshoot (the drift contaminates the step).
  - Cause: the release NMOS (gate VREF, source on a VBE) is weak in the cold, and making it stronger brings back the 125 °C slow-ramp start failure. A release driven by a copy of the core current would remove the trade-off. I tried one, but it raised the cold start VIN to 1.8–2.2 V.
  - The POR does not wait for VREF to settle. A product should add a ≈ 10 ms delay or a VREF-good comparator.
- **ss / 125 °C, slow ramp:**
  - The stand-alone bandgap is up only at VIN = 2.49 V.
  - In the full-block POR test, RST_N releases at 2.19 V at that corner.
  - So VREF may not be fully settled when reset releases there. This is not verified, and the same POR delay would cover it.
- **PSRR at 1 kHz drops 10 dB after layout** (34.9 → 24.8 dB), below the 30 dB spec. The cause is not identified yet. At 1 kHz the extracted capacitances alone should not matter, so the next step is to find which device geometry change (extracted vs schematic) costs the gain.
- **Not done:**
  - RC extraction is not in the simulations. Resistance extraction runs, but `extresist` fails on 37 native-device nodes.
  - No ESD, no antenna model, no rectifier model beyond a current source.
  - Sections 1–14 of the notebook still use the ideal reference. The bandgap and post-layout results are in this folder.
