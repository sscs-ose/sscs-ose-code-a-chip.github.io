# Changelog

## Unreleased

### Numerical behavior change: electron/hole continuity

The device solver now uses opposite electron and hole recombination/generation
source signs and a positive hole time-charge sign. The earlier shared source
sign could violate terminal-current conservation when recombination was active.
This correction can change previously generated dark as well as illuminated
results. Re-run affected drift-diffusion studies; do not combine old and new
results as if they used the same equations. Optical charge-conservation and
analytical regressions cover the corrected convention. Historical results have
not all been recalculated or retrospectively validated.

### Photovoltaic and microrobot experiments

Add prescribed Beer-Lambert generation, explicit 2D current conversion and a
reusable ideal-diode terminal model/fit/SPICE exporter. A separate microrobot
application demonstrates conceptual device physics, paper-derived terminal
fitting, circuit blocks and physical verification of a bias macro. The TCAD
structure is uncalibrated; the complete autonomous controller remains unfinished.
