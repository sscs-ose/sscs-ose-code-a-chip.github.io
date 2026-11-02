# v3: transistor-level reference, physical layout and post-layout verification

This folder adds three things the schematic-level notebook did not have:

1. **A transistor-level nano-power bandgap reference.** It replaces the ideal VREF (1.2 V) and Iref (250 nA) sources.
2. **A complete scripted layout of LDO + POR + bandgap**, with DRC and LVS sign-off.
3. **Parasitic extraction and post-layout re-simulation** of the whole block:
   - load step, small-step damping, Iq and POR thresholds over 45 PVT points
   - loop gain over 72 PVT × load × C_L points
   - PSRR
   - Monte Carlo at three corners

Everything is reproduced by `scripts/run_all.sh`: device cells, placement and routing, DRC/LVS, C extraction, then all simulations. Notebook Section 16 has two code cells:
- one re-plots the stored results and checks them against the specs
- one re-simulates the extracted netlist with the notebook's own ngspice setup (it reproduces the stored tt values exactly)

## Bandgap (`scripts/lib.py`: `bgr_subckt`, `BGR0`)

The bandgap has no op-amp. Its parts:

- a self-biased PTAT core: native 5 V NMOS pair (`nfet_05v0_nvt`, W/L = 1/25 × 6) and vertical PNPs at 1:8
- a self-cascoded PMOS mirror
- a level-shifted PMOS diode, to keep headroom at low VIN in the cold
- start-up sensed through a PNP (release NMOS gate at VREF, source on a VBE)
- VREF = I·R2 + VBE, with a 5-bit trim on R2 (LSB 25 kΩ, about 2 mV)
- a supply-ripple filter **outside the bandgap loop**: 2 MΩ into 5 pF of MIM, between the core output and the LDO's reference input

Why the filter sits behind a resistor:
- With the MIM directly on the core output, the start-up release (which senses VREF) was delayed. The kick then overshot VREF, and at −40 °C the core collapsed into its zero-current state in three post-layout corners.
- Behind 2 MΩ, the core and its start-up see no extra load.
- The LDO's reference input is a MOS gate, so the resistor adds no DC error.

All results below come from power-up transients:

| | Result |
|---|---|
| VREF (tt, 27 °C, 2.5 V) | 1.1996 V; 1.1960 / 1.1996 / 1.2035 V at −40 / 27 / 125 °C (7.5 mV) |
| PVT (5 corners × 3 temperatures × 3 supplies) | 42 / 45 points within ±1 %. Exceptions: ss / 125 °C / 3.3 V (+1.0 %), fs / 125 °C / 3.3 V (+3.3 %), sf / −40 °C / 1.8 V (−5 %, headroom; recovers at 1.85 V) |
| Monte Carlo, untrimmed (200 chips) | σ = 0.86 % (mainly PMOS-mirror mismatch) |
| Monte Carlo, trimmed once at 27 °C / 2.5 V (100 / 100 chips) | −0.61 % … +0.96 % over −40/27/125 °C and 1.8/2.5/3.3 V |
| Supply current (tt, 2.5 V) | 0.44 / 0.63 / 0.96 µA at −40 / 27 / 125 °C |
| Supply rejection at the filtered output (tt) | 34.5 dB at 1 kHz; 21.8–38.6 dB from 10 kHz to 847 kHz (it was −0.4 dB at 100 kHz without the filter) |
| Start-up on a slow ramp (0 → 3.3 V in 10 ms) | VREF is up by VIN = 1.27–1.61 V at −40 / 27 °C and 1.59–2.18 V at 125 °C. The exception is ss / 125 °C at 2.49 V. It releases cleanly at every corner. |

Notes:
- Three trimmed Monte Carlo seeds hit an ngspice "transient solution failed" at t ≈ 0 at −40 °C. `bgr_tran` now retries such a run with the gear integrator and a 10 TΩ node shunt, and all 100 chips complete.
- Resistor mismatch and resistor corners are not modelled (`mc_pr_switch = 0`), so the untrimmed σ is optimistic.

## Layout (`ldo_top.gds`, `ldo_top.png`)

- **Fully scripted.** `scripts/layout.py` reads the same subcircuits the simulations use. It places Magic-generated PDK devices (100 cells) and routes them:
  - metal3 risers from every terminal
  - one metal4 track per net in channels between the rows
  - metal3 trunks
  - 3 µm-wide supply and output nets
- **Matched bandgap devices** (`MATCH` in `layout.py`):
  - **PNPs** in one row: dummy · Q2 Q2 Q2 Q2 · **Q1** · Q2 Q2 Q2 Q2 · Q3 · dummy. Q1 sits at the centroid of the eight Q2 units.
  - **PMOS mirror:** all branches side by side in one row with dummy units at both ends, and the self-cascode devices in one row beside them.
  - The dummies are in the netlist, so LVS checks them.
  - This is a 1-D common-centroid arrangement. A 2-D array with interdigitated mirror fingers would need a custom cell generator.
- **Size:** 391 × 522 µm.
  - Wide mirror and pass devices are split into ≤ 20 µm fingers, so rows stay short and the risers that couple VIN into VOUT stay short.
  - VIN–VOUT coupling is about 0.5 pF, down from 1.5 pF in the first placement.
  - The block is routing-dominated and not area-optimised.
- **Trim:** bits are hard-wired to code 16 (a metal option; fuses in a product).

**Verification** (`scripts/verify.sh`):

| Check | Result |
|---|---|
| KLayout, official `sky130A_mr.drc` deck (FEOL + BEOL + off-grid) | **0 violations** |
| Magic DRC on the flattened final GDS | **0 errors** |
| Netgen LVS (`reports/lvs_report.txt`) | **Circuits match uniquely**, 79 devices / 46 nets, no property errors |

Notes:
- The PDK resistor generator draws URPM only 0.75 µm wide around a 0.35 µm poly resistor (rule urpm.1a needs 1.27 µm). Mask hints widen it to ≥ 1.27 µm, so the final GDS is clean.
- Magic's hierarchical check on the `.mag` view still reports RPM that it regenerates at cell interactions. That RPM is not in the GDS.

## Post-layout simulation (`scripts/postlayout.py`, `por_check.py`, `pl_loop.py`, `pl_mc.py`)

**Extraction.**
- Magic C extraction with coupling capacitance: 1,991 parasitic capacitors (`reports/ldo_top_pexC.spice`).
- Every transient run is a power-up of the whole block (VIN ramps from 0 V in 1 ms). The bandgap start-up and the POR are therefore exercised as on a harvested tag.

**PVT: 5 corners × −40 / 27 / 125 °C × VIN 1.8 / 2.5 / 3.3 V = 45 points** (`reports/postlayout_pvt_pex.csv`):

| | Spec | Post-layout result |
|---|---|---|
| 0 → 1 mA load step, 100 ns edge: undershoot | ≤ 300 mV | **≤ 277 mV** (worst at 125 °C; 210 mV at −40 °C, 239 mV at 27 °C) |
| 1 → 0 mA: overshoot | ≤ 300 mV | ≤ 179 mV |
| Small-step (10 µA) recovery overshoot | | ≤ 17.2 %, except fs / −40 °C / ≥ 2.5 V: 24–25 % (VREF still settling, see open points) |
| Iq, LDO + bandgap + POR (4 ms after power-up) | | 7.2 µA at tt / 27 °C; worst 12.9 µA (sf / −40 °C / 2.5 V); ≤ 11.5 µA at 125 °C |
| VOUT 4 ms after power-up, ±3 % | 1.164–1.236 V | 1.186–1.235 V at 43 / 45 points. **FAIL at fs / −40 °C / ≥ 2.5 V: 1.245–1.246 V (+3.8 %)**; it is 1.205 V at 8 ms |
| POR release V_on / hysteresis (15 corner × temperature points, `reports/postlayout_por_pex.csv`) | 2.0 V ± 10 % / ≥ 150 mV | **1.894–2.192 V / ≥ 244 mV** |

**Loop gain from the extracted netlist** (`scripts/pl_loop.py`, `reports/postlayout_loop_pex.csv`):
- **Method.**
  - In a copy of the extracted netlist, the gate of the error-amplifier input transistor gets its own port. A MOS gate draws no current, so a plain voltage injection there is exact.
  - Each point first runs the power-up transient. Every node voltage at the end becomes a `.nodeset`, so the operating point is the running state of the real bandgap.
  - Then op + AC with a 1 GH DC path.
- **Points:** 72 = 5 corners × 3 temperatures × {0, 1 mA} × {10, 100 pF} at 2.5 V, plus 12 points at 1.8 V.

| | Spec | Post-layout |
|---|---|---|
| Phase margin (global loop) | ≥ 45° | **≥ 95.0°** at 68 / 72 points (worst: fs / 125 °C, 0 mA, 100 pF); 4 cold points: see below |
| Gain margin | | ≥ 16.7 dB (68 points) |
| Unity-gain frequency | | 69 kHz … 2.6 MHz |
| DC loop gain | | 62.7 … 84.9 dB |

**Low-frequency doublet at four points** (tt and ff, −40 °C, 1 mA, 10 and 100 pF; `doublet` column):
- The loop gain shows a sharp pole-zero doublet near 250 Hz (peak ≈ 100 dB), and the unwrapped phase turns +360° through it.
- Read modulo 360°, the margins there are 100–116° and ≥ 25 dB, but a Bode margin is not a clean measure in that case.
- The step response was checked directly (`scripts/pl_ss_cold.py`): at those points, a 1 → 1.1 mA step 16 ms after power-up (start-up settled) overshoots 4.6–6.5 %, against 3.6 % at 27 °C. So the closed loop stays well damped.
- The origin of the doublet is not identified.

This is the global loop only. The notebook (Section 9.2) explains why the global-loop margin overstates the damping: the class-AB current-buffer path forms a faster inner loop. The small-step overshoot (≤ 17 % here) is the damping check for that inner loop.

**Spec status with the real bandgap, after layout.** The notebook's "18 PASS, 0 FAIL" (Section 13) is the schematic-level result with the ideal reference. After layout, with the bandgap:
- **Load step, POR, phase margin: PASS.**
- **PSRR at 1 kHz: FAIL**, 24.7 dB against ≥ 30 dB.
- **VOUT ±3 % at 4 ms: FAIL** at fs / −40 °C / ≥ 2.5 V (+3.8 %; it passes by 8 ms).
- **Quiescent current:** the ≤ 10 µA spec was for the LDO alone. The whole block (LDO + bandgap + POR) draws 7.2 µA at tt and up to 12.9 µA in the cold.
- **Usable VIN:** the POR keeps the core in reset below its release threshold (1.89–2.19 V over PVT), so RST_N stays low at VIN = 1.8 V by design.

**Before vs after layout** (tt, 27 °C, 2.5 V; the same netlist without parasitics vs with them):

| | Pre-layout | Post-layout |
|---|---|---|
| Load-step undershoot / overshoot | 201 / 133 mV | 230 / 143 mV |
| Iq | 7.27 µA | 7.24 µA |
| PSRR at 1 kHz | 34.9 dB | 24.7 dB |
| PSRR at 100 kHz | 18.6 dB | 22.1 dB |
| PSRR at 847 kHz (NFC subcarrier) | 18.0 dB | 19.1 dB |
| VOUT | 1.2014 V | 1.1929 V |

Notes on the table:
- PSRR in the table is the ripple fitted at the test frequency, so slow drift is not counted.
- With the ideal reference, the notebook's PSRR was −0.4 dB at 100 kHz (v1) and 8.7 dB (v2).
- **VOUT −8.5 mV:** the extracted bandgap gives 1.191 V instead of 1.199 V (meandered high-resistance poly vs the schematic value). This is about 4 trim LSBs, well inside the trim range.

**Where the 1 kHz PSRR goes** (`scripts/pl_psrr_diag.py`): the same extracted netlist was re-simulated with groups of parasitic capacitors removed.

| Extracted netlist variant | PSRR at 1 kHz (tt) |
|---|---|
| All parasitic capacitors (as extracted) | 24.8 dB |
| No parasitic capacitors | 32.7 dB |
| Only the capacitors that touch VIN | 31.9 dB |
| All except the capacitors that touch VIN | 25.1 dB |
| Bandgap routing capacitors removed | 29.2 dB |
| LDO / POR routing capacitors removed | 25.0 / 24.8 dB |
| Capacitors of a single bandgap net removed (pg, ng, pd, ncas, st) | 24.8–27.6 dB |

So the loss is not coupling from VIN (< 1 dB), and not a single node. It is the bandgap's own capacitance to ground, spread over its nA-biased internal nodes (routing about 4 dB, device-internal the rest). These nodes have MΩ-range impedance, so their poles move down toward 1 kHz, and the core's line rejection falls there.

A lower filter corner was tried: 40 MΩ and 20 pF (≈ 200 Hz), with a PMOS bypass whose gate is the mirror node. It was not adopted. The bypass only conducts during the short kick, so the filtered VREF was still 16 mV low at 4 ms. A working version needs a bypass held on by a slower power-good signal, or more bias current in the core.

**Post-layout Monte Carlo** (`scripts/pl_mc.py`, `reports/postlayout_mc_pex_*.csv`): process corner plus local mismatch on every device of the extracted netlist, untrimmed, power-up then the load step.

| | tt, 27 °C, 2.5 V (100) | tt, 125 °C, 1.8 V (60) | ss, 125 °C, 1.8 V (60) | fs, −40 °C, 2.5 V (60) |
|---|---|---|---|---|
| Start-up | 100 / 100 | 60 / 60 | 60 / 60 | 60 / 60 |
| VOUT mean / σ | 1.1939 V / 12.1 mV | 1.1953 V / 13.9 mV | 1.2019 V / 14.0 mV | 1.2533 V / 13.1 mV (4 ms; still settling) |
| Untrimmed chips outside ±3 % | 3 / 100 | 2 / 60 | 1 / 60 | (settling) |
| Load-step undershoot / overshoot, worst | 236 / 151 mV | 279 / 175 mV | **283** / 186 mV | 199 / 120 mV |
| Iq, mean / worst | 7.26 / 7.68 µA | 9.98 / 10.45 µA | 9.87 / 10.34 µA | 9.38 / 10.16 µA |
| RST_N released | 100 / 100 | 0 / 60 (below V_on, as designed) | 0 / 60 (as designed) | 60 / 60 |

- The load step stays inside 300 mV with mismatch at the worst corner (ss / 125 °C / 1.8 V).
- The untrimmed VOUT σ is about 1.0–1.2 %, set mostly by the bandgap (σ 0.86 % alone). The one-time trim at 27 °C brings the reference to −0.61 … +0.96 % over temperature and supply.
- The `load_reg` column in these files is the VOUT shift inside the 40 µs load pulse. It is a transient value, not the DC load regulation of the notebook (2.43 mV/mA, Section 9.1).

## Open points (measured, not hidden)

- **Start-up settling in the cold (worst at fs / −40 °C, VIN ≥ 2.5 V).**
  - The start-up kick overshoots VREF to 1.67 V. It relaxes to 1.243 V at 4 ms, 1.205 V at 8 ms and 1.193 V at 16 ms.
  - The other cold corners settle faster, but are not fully settled at 4 ms either (ss / −40 °C reads +2.8 %). Their Iq at 4 ms (11–12.9 µA at 2.5 V) still contains start-up current.
  - Cause: the release NMOS (gate VREF, source on a VBE) has only VREF − VBE ≈ 0.45 V of drive at −40 °C. Making it stronger brings back the 125 °C slow-ramp start failure.
  - Alternatives tried (`scripts/bgr_slow.py`, `scripts/pl_swap.py`), none adopted:
    - **Release from a copy of the core current:** the cold start VIN rises to 1.8–2.2 V.
    - **Release NMOS source to ground:** it releases in the cold low-current state (VREF ≈ VBE), so the cold slow-ramp start goes to 2.2–3.4 V.
    - **Release NMOS gate on the mirror-diode drain `pd`:** best on the schematic (start ≤ 1.34 V at every corner, clean cold release). But `pd` also rises during the kick itself. After layout the core then never latched at 15 of 45 PVT points, so it was rejected.
    - **Native release NMOS:** the 125 °C slow-ramp start rises to 3.7 V.
    - **Weaker kick transistor:** less overshoot, but VOUT is still out of range at 4 ms.
  - The POR does not wait for VREF to settle. A product should add a ≈ 10 ms delay or a VREF-good comparator.
- **ss / 125 °C, slow ramp:**
  - The stand-alone bandgap is up only at VIN = 2.49 V.
  - In the full-block POR test, RST_N releases at 2.19 V at that corner.
  - So VREF may not be fully settled when reset releases there. This is not verified, and the same POR delay would cover it.
- **PSRR at 1 kHz drops 10 dB after layout** (34.9 → 24.7 dB), below the 30 dB spec. The cause is located (the bandgap's distributed node capacitance; table above) but not fixed.
- **Not done:**
  - RC extraction is not in the simulations. Resistance extraction runs, but `extresist` fails on 37 native-device nodes.
  - No resistor mismatch or resistor corners.
  - No ESD, no antenna model, no rectifier model beyond a current source.
  - Sections 1–14 of the notebook still use the ideal reference. The bandgap and post-layout results are in this folder and in Section 16.
