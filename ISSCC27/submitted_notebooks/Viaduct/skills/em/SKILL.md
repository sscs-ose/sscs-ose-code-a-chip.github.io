---
name: viaduct-em
description: Extract L1, L2, R, Q and k of the VIADUCT_SKY130 T-coil with FastHenry through Viaduct, check mesh convergence, and write the results into the PCell with the run ID. Use whenever inductance, coupling or Q of the coil is needed.
---

# EM (FastHenry) through Viaduct

The EM model is built from the same geometry code as the layout
(`tcoil_core.em_model`): winding centerlines on both parallel planes, the two
crossovers (winding metals / bridge metals), the 11 inter-plane via sites, the
bridge via stacks and the tap stub, with SKY130 heights, thicknesses and sheet
resistances from `pdk/sky130A.json` (Magic tech file values). Every run writes
`runs/em_<run_id>/` with the FastHenry input per frequency, `Zc.mat`, logs,
`metrics.json` and `model.png` (EM model drawn over the layout - look at it).

## API

| Task | CLI | Python |
|---|---|---|
| L/R/Q/k at frequencies | `python client.py em --set metalWidth=4 area=6400 --freqs 1e9 5e9 1e10 2e10` | `vd.em.fasthenry(params, freqs_hz)` |
| parasitic C (FasterCap) | `python client.py cap --set metalWidth=4 area=8000` | `vd.em.fastercap(params)` |
| mesh convergence | `python client.py em-convergence --set metalWidth=4 area=6400 --freq 1e10` | `vd.em.convergence(params, 10e9)` |
| into the PCell | `python client.py annotate --set L1="0.1769 nH" ... --run-id "FASTHENRY <id>"` | `vd.klayout.annotate("DUT", r["annotation"], "FASTHENRY " + r["run_id"])` |

`params` are the PCell parameters (metalWidth, area, turnSpacing, metals, ...).
A normal-mesh run takes about 5 s per frequency (in parallel across frequencies).

## Conventions

- Port 1 = P1-P3, port 2 = P2-P3 (same as the EMX flow). `L1 = Im Z11/w`,
  `Q1 = Im Z11 / Re Z11`, `K1 = Im Z12 / (w sqrt(L1 L2))`.
- With these port directions a **series-aiding** coil has **K1 < 0**. For SPICE with
  `L1 P1 P3`, `L2 P3 P2`, use `K = -K1` (given as `spice_model.K`).
- `L_series_P1_P2_nH` = inductance from P1 to P2 = L1 + L2 + 2|M|.
- The tap is off-centre: L1 is about 1.8 x L2 for the default geometry.

## Validity (say this with the numbers)

Quasi-static: no substrate loss or eddy currents, no dielectric, **no capacitance**
(no self-resonance, no inter-winding C); via arrays are solid posts. Q is
conductor-loss Q only and is optimistic at high frequency. Reference point
(10-13 Oct 2026): normal -> fine mesh changed L1, L2, K1 by < 0.1 % and R by < 0.6 %;
the generic65 version of the same geometry under EMX gave the same signs and
similar magnitudes (L1 0.153 nH, L2 0.081 nH, K -0.40 at 10 GHz vs FastHenry
SKY130 0.177 / 0.097 / -0.35; different metal stacks).

## Capacitance (FasterCap)

The coil is cut at the tap into half A (P1-P3) and half B (P3-P2); the substrate is a
ground plane; one homogeneous dielectric (`dielectric_er` in the PDK profile).
Returns `C_AB_fF` (built-in bridging C between the halves), `C_A_gnd_fF`,
`C_B_gnd_fF` and `spice_parasitics` (pi split: X gets C_A/2, tap (C_A+C_B)/2, Y C_B/2;
swap A/B if P2 faces the driver). About 50 s. Reference (W=4, area=8000): 13.9 / 27.9 /
19.9 fF. Substrate-as-ground overestimates C to substrate somewhat.

## Full-wave (Palace FEM)

| Task | CLI | Python |
|---|---|---|
| full-wave cross-check | `python client.py fullwave --set metalWidth=4 area=8000` | `vd.em.palace(params)` |

`container/palace_runner.py` writes a SKY130 stackup for gds2palace (Magic-tech BEOL,
SiO2, passivation, 150 um substrate at `substrate_ohm_cm`, default 10 ohm*cm, assumed),
an EM GDS (same `tcoil_core` geometry, EM layer numbers), a measurement fixture
(met1 ground frame 15 um from the coil, met1 fingers under P1, P2, P3, vertical lumped
ports: met1->met4 at the leads because the leads are on both planes, met1->met5 at the
tap), meshes with gmsh, runs `palace -np 8` (not `run_palace`: that nests mpirun) and
`combine_snp`. Result: the two-port with P3 shorted to the frame (Y[0:2,0:2] of the
3-port; the grounded 3-port Z of a floating coil is ill-conditioned), and FastHenry on
the identical coil + frame + fingers + P3 short for comparison, plus
`palace_vs_fasthenry.png`. ~20-45 min, 3-4.5 GB; WSL has 7 GB, so do not refine the
mesh much below 2 um or the OOM killer may hit the GUIs.

Reference (13 Oct 2026, W=4, area=8000, docs/fullwave/): 5-25 GHz FastHenry matches Palace
within 2-6 % on L, ~4 % on Q; above ~25 GHz Palace L rises (+4 % @30, +27 % @50 GHz) and Q
drops (-20 % @50 GHz); self-resonance above 50 GHz; Palace points below ~3 GHz unreliable.
So: FastHenry L is good to ~25 GHz; near/above that, add the FasterCap parasitics.

The fixture's return path is part of the measured loop, so L1/L2/K here are not the
coil-only values from `em`; compare Palace with `fasthenry_same_structure`, not with `em`.
openEMS (FDTD) is impractical for an 80 um coil at GHz (sub-um cells, ~0.4 fs steps).

## Rules

- Only `annotate` with values and run ID from an executed run; geometry changes reset them.
- Check `converged_2pct_LK` before quoting a new geometry family.
