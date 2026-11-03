# GlitchScope B8DQ — four-resistor-domain factorial diagnostic

**Status:** execution complete / diagnostic only. No M2 authorization.

## Reproduction authority
- Schematic max |delay/slew| delta: 0 / 0 ps
- Full A1Y1P1G1 PEX max |delay/slew| delta: 0 / 0 ps

## Mean signed factorial effects (ps)

| Effect | Delay | Slew |
|---|---:|---:|
| A | 0.82812 | 0.127781 |
| Y | 1.6631 | 5.12333 |
| P | 15.0548 | 19.7401 |
| G | 5.49588 | 6.24978 |
| AxY | 0.000776389 | 0.000689306 |
| AxP | -0.00721528 | 0.00121069 |
| AxG | -0.00419028 | -0.000554861 |
| YxP | -0.0389736 | -0.0346924 |
| YxG | -0.00429861 | 0.089566 |
| PxG | 0.0048375 | -6.04167e-05 |
| AxYxP | 0.000886111 | -0.00162472 |
| AxYxG | -0.000163889 | -0.000250278 |
| AxPxG | 0.000219444 | 0.000445833 |
| YxPxG | 0.00153611 | 0.000175278 |
| AxYxPxG | 0.00265 | 0.000632778 |

These are preregistered matched finite-difference contrasts of the frozen extracted model.
They do not prove that any single resistor domain was responsible for the historical Liberty data.

## Interpretation limits
- C=1 and the translated diode=1 are fixed in every domain arm.
- Factor-off means ideal topology-checked contraction to that domain's named external net.
- A/Y/VPWR/VGND interactions are reported even if numerically small.
- Case 7 remains in the 18-case descriptive results.
- No arm is promoted as a new golden reference.
- Original Liberty qualification remains unchanged; PEX provenance remains unproven; M2 remains blocked.

## Machine-readable outputs
`b8dq_all_arms_timing.csv`, `b8dq_factorial_effects_per_case.csv`,
`b8dq_conditional_domain_effects_per_case.csv`, `b8dq_factorial_effects_stratified.csv`,
`b8dq_arms_stratified_errors.csv`, `b8dq_arm_structure_manifest.csv`.
