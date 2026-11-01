# Evidence and attribution

Access checked 2026-10-26. The verified Reynolds 2022 DOI is **10.1126/scirobotics.abq2296**.

## Primary evidence retrieved

Reynolds et al., *Microscopic robots with onboard digital control*,
Science Robotics 7, eabq2296 (2022).
[DOI](https://doi.org/10.1126/scirobotics.abq2296),
[Cornell author PDF](https://mceuengroup.lassp.cornell.edu/sites/mceuen/files/publications/scirobotics.abq2296.pdf).
The PDF was downloaded and its Fig. 1 inspected visually. SHA256:
`4e9a538f61d01ddd80d7c45cf117dc9e25f8b49e9e87b07438123e8ad4f6022f`.
The copyrighted paper is not redistributed with this application.

| Published item | Location / extent of disclosure |
|---|---|
| XT018 180 nm CMOS SOI; current reference, relaxation clock, divider, phase shifter and drivers | Fig. 1; Circuit design, pp. 6-7 |
| Two large PVs for actuators and two smaller PVs for IC; large pair tested in series | Fig. 1D/E; Circuit testing, p. 8 |
| Approximately 32 kHz clock; eight phases spaced by 1/8 period | Circuit design, pp. 6-7 |
| Approximately ±0.6 V outputs; about 0.3 A/W responsivity; frequency dependent on illumination | Fig. 1; Circuit testing, p. 8 |
| Exposed Pt ground electrodes in solution | Purcell-bot description, p. 2; Fig. 3 |
| Controller footprint 94 × 55 um; Pt/Ti actuator stack approximately 7/2 nm | pp. 1-2 |
| 660 nm source for Purcell-bot/dogbot, 600 nm for antbot | Operation methods, p. 8 |
| Fabrication sequence described, with full recipe referred to supplement | Fig. 2; Fabrication process section |

These are architectural and approximate measurement anchors, not enough
to reconstruct transistor sizing or calibrate a PV structure.

## Supplement retrieved locally on 2026-10-27

The 13-page supplementary PDF was obtained locally after publisher access had
returned HTTP 403. Its source is
[the publisher supplement](https://www.science.org/doi/suppl/10.1126/scirobotics.abq2296/suppl_file/scirobotics.abq2296_sm.pdf).
An unchanged local copy is retained in the git-ignored `local_references/`.
SHA256: `43138926560d636d64845f7f708ba6026e26446f79df2962cc8e1355ed6b9fd4`.
The text and all six supplementary figures were inspected.

Figure S1B confirms that the logic and actuator PV pairs share their lower
rail. The actuator interface is shown between the actuator pair's midpoint
and an output switched to the upper/lower actuator rails. Combine this
electrical diagram with the exposed Pt/electrolyte return described in the
main paper; the midpoint metal is not an ideal fixed electrolyte potential.
The four-cell logic array in the first conceptual experiment was my
adaptation. The published-data experiment now uses three cells to respect
the controller voltage range; neither arrangement is the paper's logic pair.

Figure S2E supplies approximate published anchors: each large PV has area
540 um²; the two in series have Voc about 1.24 V (0.62 V per cell) and Isc
about 150 nA at 1000 W/m². Both dark and illuminated curves are plotted.
These are caption values, not digitized traces or fitted parameters. S2D's
nominal frequency-selection setting and measured frequency must be kept
distinct. The manufacturing recipe is detailed, but the supplement supplies
block diagrams/CAD images rather than transistor-level schematics, W/L or
timing R/C values, and does not give a calibrated PV doping profile.
Apparent dimensions in micrographs are not treated as device dimensions.

## Historical registry audit: 2026-10-27

The [data DOI printed in the paper](https://doi.org/10.5281/zenodo.7008281)
returned 404 / DOI Not Found during that audit. The
[Zenodo record API](https://zenodo.org/api/records/7008281) returned 404 with
`The persistent identifier is not registered.` The
[DataCite DOI API](https://api.datacite.org/dois/10.5281/zenodo.7008281) also
returned 404. Direct title search in Zenodo and title/related-article-DOI
search in DataCite returned zero records; an Internet Archive availability
lookup found no snapshot for `zenodo.org/record/7008281`.
That audit found no verified replacement link. These results do not establish
whether the paper cites a typo, an unpublished reservation or another issue.
The paper states that its reported data are in the main text and supplement.
The missing archive was not a prerequisite. S2E's plotted dark/illuminated
curves were digitized, fitted and compared, with tick coordinates,
PDF checksum, raster coordinates and pixel-sensitivity assumptions recorded
in `data/` and `results/published/`. This is extracted figure evidence,
not the authors' raw files.

## Measurement CSVs supplied locally on 2026-10-30

The project author supplied a directory named `Reynolds-2022-data`, described
as the Zenodo data. It contains `Fig3_PurcellBot.csv`, `Fig4_PurcellBot.csv`,
`Fig5_Dogbot.csv`, `FigS2_CircuitTesting.csv`, `FigS4_LEGO_purcell.csv` and
`FigS6_DogbotCircuit.csv`. This changes the local data-availability status;
the earlier 404 observations remain a historical audit, not a claim that the
measurement files are still unavailable.

No download URL, README, repository metadata or data license accompanied these
six files. Their claimed Zenodo origin has not been independently verified.
SHA256 hashes identify the exact supplied bytes, not a verified remote record.
Original files remain outside Git and the submission export.

See [the six-file audit](data/reynolds2022_AUDIT.md),
[supplied-file inventory](data/reynolds2022_inventory.json) and
[data handling and comparison instructions](data/README.md). Recorded headers,
units and corresponding paper panels must be checked together: independent
column groups have separate sampling and lengths, and a filename need not
correctly identify the robot in the corresponding paper figure. The new
comparison preserves the previous digitization and terminal model as historical
inputs; it does not silently refit or rerun existing circuit/layout results.
Terminal measurements do not uniquely determine doping, optical loss, lifetime,
electrode kinetics or mechanical properties.

The [direct comparison](results/reynolds2022/README.md) and
[separate effective-model candidate study](results/reynolds2022_fit/README.md)
document subsequent analyses of the supplied files. The candidate study keeps
both main offset hypotheses, uses training-only fits and fixed withheld-voltage
regions, and reports bin-width sensitivity. It does not replace the historical
model or update the circuit/layout evidence. Its assumed 300 K is not a measured
source temperature, and an observation offset is not established device physics.

## Supporting and future sources

Miskin et al., *Electronically integrated, mass-manufactured, microscopic
robots*, Nature 584, 557-561 (2020).
[DOI](https://doi.org/10.1038/s41586-020-2626-9),
[author PDF](https://cohengroup.ccmr.cornell.edu/userfiles/pubs/Miskin_Nature_2020.pdf).
Downloaded SHA256: `00b896c45a2a60dfa87ab3ea7bd3fba4c191a04b2c514e0e6b69bf9443c8e1db`.
Methods distinguish double-layer and adsorption charging; the adsorption
charge scale is approximately 130 uC/cm² = 1.3 C/m². The reported 50 ms
mechanical response belongs to a particular Pt/graphene cantilever geometry.
Neither is a calibrated parameter set for the 2022 Pt/Ti robot legs.
Potentials against Ag/AgCl in actuator characterization must not be identified
with CMOS terminal voltage against an onboard Pt return electrode.

Lassiter et al., *Microscopic Robots That Sense, Think, Act, and Compute*
(2025), [arXiv:2503.23085](https://arxiv.org/abs/2503.23085),
[journal DOI](https://doi.org/10.1126/scirobotics.adu8009).
Only the arXiv abstract/metadata were checked; its processor, memory, sensing
and communication architecture is future work, not the initial design.

## Additional ISSCC 2022 reference supplied on 2026-10-28

Li Xu et al., *A 210 × 340 × 50µm Integrated CMOS System for Micro-Robots
with Energy Harvesting, Sensing, Processing, Communication and Actuation*,
ISSCC 2022, paper 12.1, digest pp. 194–195 plus continuation.
All three supplied pages and Figures 12.1.1–12.1.7 were inspected visually.
The unchanged PDF is retained only in git-ignored
`local_references/xu_isscc2022_micro_robot.pdf` (original filename
`a-210x340-1.pdf`); SHA256 `b553e4c64f39f10131bffe3fa552137166af31c2771da11466a0a8a9e3fbd8f3`.
It is a separate design from Reynolds et al.; the Reynolds 2022 system remains
the initial implementation target. No numerical traces have been digitized or
parameters fitted from this new reference.

| Published disclosure | Location and interpretation |
|---|---|
| 210 × 340 × 50 µm die; 55 nm triple-well DDC process from United Semiconductor Japan | p. 194; custom higher-Vth transistors reduce leakage by approximately 9× relative to the standard option. This is not an available SKY130 model calibration. |
| Opposite-polarity solar cells using N+/P-well, P-well/deep-N-well and deep-N-well/P-sub junctions | p. 194 and Fig. 12.1.3: electrical cross-sections and junction connectivity, not calibrated doping/depth/area data. |
| Negative solar cell ties P-well to P-sub and N+ to deep-N-well; positive cell shorts P-sub to deep-N-well | p. 194 and Fig. 12.1.3. Floating substrate allows stacking around the substrate reference; it is not a negative rail relative to an external earth ground. |
| PMOS N-wells tied to VDD; NMOS P-wells to VSSN and their deep-N-wells to VDD | p. 194 and Fig. 12.1.3. These body/isolation connections are explicit, process-dependent design evidence. |
| More than 0.6 V rail span; no-load rail voltage versus illumination plotted | Fig. 12.1.3; the plot is not a loaded PV I–V curve. Operation/leg actuation demonstrated at 60 klux. |
| Differential actuation between front and rear legs through the solution | Fig. 12.1.3; the paper describes greater than +0.3 V and below −0.3 V relative to solution. This is distinct from the Reynolds dedicated Pt return at the actuator-PV midpoint. |
| Programmable leg period, phase and pulse width | Fig. 12.1.3; time resolution is one system-clock period. On-chip clock uses a leakage-based oscillator or a recovered optical clock. |
| Custom 11-bit processor; 11-bit × 32 instruction memory and 8-bit × 16 data memory | Fig. 12.1.4; memory is implemented with flip-flops. Processor/optical reception remain future application scope. |
| Metal structures and MIM capacitors over active circuits reduce light-induced current by approximately 10× | p. 194; optical exposure can affect controller leakage and timing, not just useful PV generation. |
| Reported system power 75 nW, with a footnote giving measured 15 nW without legs | Fig. 12.1.6. Do not identify the 60 nW difference with calibrated actuator-only dissipation without matching conditions and power accounting. |
| Two-leg test die with identical harvesting/drive circuits shows light-powered actuation | p. 194 and Fig. 12.1.5. The plotted curvature uses arbitrary units; it does not calibrate SI curvature or walking speed. |
| Voltage measurements used 10 MΩ parallel 12 pF oscilloscope probes | p. 194. Comparisons with those waveforms must include measurement loading. |

**What is still missing:** transistor W/L for the oscillator, power-on/reset,
receiver and output stages; complete transistor-level netlists; timing/passive
values; calibrated PV doping and optical spectra; raw loaded I–V data;
electrode areas and a uniquely inferable interface/mechanical parameter set.
The inverter drawing provides well connections, not a complete controller
schematic. The measured actuation demonstration and the full programmed-chip
waveforms should not be collapsed into a claim of measured autonomous walking.

**Implications for this project:** keep the two papers' supply/electrode
networks separate. A future triple-well-PV branch must check the selected PDK's
isolation and substrate constraints, and demonstrate its optical behavior;
this paper alone does not establish that arbitrary series PVs are manufacturable
in SKY130. Lux cannot be converted to my 660 nm W/m² input without a source
spectrum. The existing conceptual PV generation and dark foundry transistor
models do not validate light-induced leakage in the controller. Shielding and
substrate photocarrier collection are additional verification needs, not
performance improvements already simulated. No current circuit parameters or
published-data fits have been changed based on this paper.

## Parameter provenance policy

1. **Published:** values above retain source and approximate precision.
2. **Extracted:** `data/s2e_digitized.csv` contains reconstructed paper traces;
   DD/SPICE metrics are separately labelled simulated results.
3. **Fitted:** the ideal single-diode terminal parameters in
   `results/published/pv_fit.json` use the digitized traces, assumed 300 K,
   zero series resistance and infinite shunt resistance. Pixel-sensitivity
   ranges are not confidence intervals or unique TCAD parameter inference.
4. **Design choice:** all geometry/doping/optics in `pv.py`, all behavioral
   parameters in `system.Parameters`, and all ring W/L/R/C in `spice.py`.
   The new `circuits/starved_clock.spice` dimensions, capacitor geometry,
   three-cell logic allocation, storage capacitors and RTL divider are
   also my choices. The bias is not a reproduction of the paper's PTAT circuit.

PV doping, lifetime, reflection, absorption, sidewall recombination and
contact loss cannot be uniquely inferred from one responsivity and Voc.
Adsorption midpoint, width, rates, leakage, return area and solution resistance
also cannot be uniquely inferred from the reported output waveforms.

My contributions are the OpenTCAD optical field/units support, conservation
correction, terminal fitting/MPP/SPICE export and numerical regressions;
the attributed PV extraction; and the new functional clock, phase RTL and
separate auditable coupling experiment. Attribution for the original microrobot
concepts belongs to the cited
authors; DD, meshing, numerics and circuit models belong respectively to
DEVSIM, Gmsh, NumPy/SciPy and the SKY130/ngspice projects. Repository code
and the notebook use the root Apache-2.0 license; paper and PDK licenses
remain those of their owners.
