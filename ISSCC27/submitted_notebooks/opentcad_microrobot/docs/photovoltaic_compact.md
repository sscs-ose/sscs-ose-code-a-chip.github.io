# Reduced photovoltaic terminal models

`opentcad.device.compact.SingleDiodePV` represents a prescribed photocurrent
and ideal diode, with matched cells in series. It supports numerical IV,
open-circuit voltage, maximum-power-point calculation, current scaling,
three-parameter fitting and optional SPICE subcircuit text export. No external
simulator is a Python dependency.

All electrical quantities are SI. Irradiance is W/m² and temperature K.
Delivering current is positive:

```
I(V,E) = Iph_ref*(E/Eref) - I0*expm1(V/(Ns*n*k*T/q))
```

`n` is per-cell ideality and `Ns` the number of matched series cells. Current
through the series string is not multiplied by Ns. Identical-area scaling
multiplies I0 and Iph together, preserving Voc. This assumes edge, optical
and contact effects do not change. It does not validate a different geometry.

```python
from opentcad.device.compact import SingleDiodePV, fit_single_diode

pv = SingleDiodePV(saturation_A=2e-16, ideality=1.3,
                   photocurrent_A=100e-9, series_cells=2)
voltage, current, power = pv.maximum_power_point(1000)
spice = pv.spice_subcircuit("my_pv")
# model, diagnostics = fit_single_diode(V, delivered_I, irradiance,
#     series_cells=2, uncertainty_A=current_uncertainty)
```

Run `python examples/08_pv_compact.py` for a small, synthetic parameter-recovery
and export example. Tests cover analytical limits, power stationarity,
recovery of a known model, an independent illumination prediction and a
real ngspice IV round trip when the optional executable is installed.

## Fitting and supported scope

The fit adjusts log(I0), log(n), log(Iph), with explicit ideality bounds
0.5..4 and positive currents. It requires multiple light levels and a
forward-current region. Optional current uncertainties weight residuals;
the diagnostics do not supply statistical confidence intervals. Raster
points, in particular, are correlated samples of a printed trace.

Series resistance is fixed to zero, shunt resistance to infinity. No
breakdown, carrier storage, junction capacitance, surface recombination,
partial shading, wavelength-dependent quantum efficiency or cell mismatch
is inferred. The fitted temperature is an assumption unless measured.
Changing temperature requires a separately justified parameter set.

A terminal fit is not a unique calibration of TCAD doping, lifetime,
absorption/reflection or process. Keep it separate from conceptual DD
structures and foundry transistor models. The microrobot application fits
Fig. S2E's plotted terminal curves and reports pixel sensitivity without
claiming predictive XT018 process physics.

## SPICE contract

The exported subcircuit uses p/n pins, `illumination` in W/m² and
`area_scale` multiplying both currents. Run at the stated fitted temperature
in Celsius. The diode's `EG=0 XTI=0` suppresses an uncalibrated extrapolation
of saturation current; it does not establish temperature-invariant PV physics.
No capacitance is exported from DC IV; startup storage must be supplied and
identified independently. SPICE and Python agree within numerical/constant
precision, rather than bit-for-bit physical-constant implementations.
