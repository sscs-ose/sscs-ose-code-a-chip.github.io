# Full-wave cross-check of the T-coil (13 Oct 2026)

Coil: VIADUCT_SKY130 TCoil, metalWidth 4 um, area 8000 um^2 (the closed-loop choice).
Fixture (both solvers, identical): met1 ground frame 15 um from the coil (6 um wide), met1
fingers under P1, P2 and the tap P3, vertical ports (met1->met4 at P1/P2, met1->met5 at P3).
Quantity: two-port P1/P2 with P3 shorted to the frame, i.e. P1-P3 and P2-P3 through the
fixture's return path. These L/K values include the fixture and are not the coil-only `em` values.

Palace: gds2palace + AWS Palace (FEM, 2nd order), SKY130 BEOL from the Magic tech file,
SiO2 er 4.1, passivation er 7, 150 um substrate at 10 ohm*cm (assumed), ABC boundaries,
adaptive sweep 1-50 GHz. Runs 20261013_200657_5222 (2.5 um mesh, 215k unknowns, 21 min, 3.0 GB) and
20261013_203447_3fe0 (2.2 um, 257k unknowns, 49 min, ~4.2 GB). FastHenry: quasi-static, same structure.

Columns: Palace 2.5 um / Palace 2.2 um / **FastHenry**.

| GHz | L1 (nH) | L2 (nH) | Q1 | K1 |
|---|---|---|---|---|
| 1 | 0.3126 / 0.3131 / **0.2867** | 0.2104 / 0.2109 / **0.1950** | 0.38 / 0.38 / **0.29** | 0.046 / 0.047 / **0.059** |
| 5 | 0.2736 / 0.2740 / **0.2825** | 0.1856 / 0.1859 / **0.1926** | 1.48 / 1.48 / **1.39** | 0.057 / 0.058 / **0.070** |
| 10 | 0.2671 / 0.2675 / **0.2789** | 0.1803 / 0.1806 / **0.1906** | 2.72 / 2.72 / **2.65** | 0.060 / 0.061 / **0.077** |
| 20 | 0.2705 / 0.2709 / **0.2754** | 0.1795 / 0.1798 / **0.1883** | 4.89 / 4.90 / **4.88** | 0.050 / 0.052 / **0.080** |
| 30 | 0.2830 / 0.2834 / **0.2732** | 0.1826 / 0.1830 / **0.1869** | 6.58 / 6.59 / **6.84** | 0.031 / 0.033 / **0.080** |
| 40 | 0.3056 / 0.3058 / **0.2718** | 0.1889 / 0.1893 / **0.1858** | 7.72 / 7.74 / **8.61** | 0.002 / 0.004 / **0.080** |
| 50 | 0.3438 / 0.3438 / **0.2706** | 0.1993 / 0.1996 / **0.1850** | 8.21 / 8.24 / **10.25** | -0.043 / -0.040 / **0.080** |

Findings
- Mesh: 2.5 -> 2.2 um changes L by <= 0.2 %, Q by <= 0.4 % (a modest 1.19x refinement).
- 5-25 GHz: FastHenry and Palace agree within 2-6 % on L and ~4 % on Q; the lossy substrate
  adds no visible loss below ~25 GHz for this coil (loss is dominated by metal, here
  including the thin met1 fixture).
- Above ~25 GHz Palace L rises (+4 % at 30 GHz, +12 % at 40, +27 % at 50 vs FastHenry) and Q
  falls below FastHenry (-20 % at 50 GHz): capacitance (self-resonance above 50 GHz) and
  dielectric/substrate effects that a quasi-static solver cannot see. The T-coil's -3 dB
  points (27-35 GHz) sit at the start of this region, which is why the FasterCap
  parasitics matter.
- K in this configuration is a small difference quantity (fixture return path is shared);
  it agrees to ~0.01-0.02 absolute below 10 GHz and drifts apart above 20 GHz.
- 1 GHz: Palace reads ~9 % higher L1, but Q = 0.3 there (reactance << resistance); FEM
  low-frequency accuracy is limited, do not use points below ~3 GHz.

Not covered: substrate resistivity sensitivity, a coil-only (de-embedded) Palace extraction,
mesh refinement beyond 2.2 um (memory-limited at 7 GB WSL).
