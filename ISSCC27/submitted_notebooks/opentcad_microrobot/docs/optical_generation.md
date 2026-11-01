# Prescribed optical generation and 2D photovoltaic currents

`opentcad.device.optical.BeerLambert` adds single-pass monochromatic pair
generation to a `MeshField`. `DeviceSolver` reads it when initialized. This
is reusable device physics; the robot workflow in `examples/microrobot/`
is an independent application. There is no application import in the core.

```python
from opentcad.device.optical import BeerLambert, current_from_2d

# mf is an existing triangular silicon MeshField; entrance plane y = 3 um.
light = BeerLambert(wavelength_nm=660, irradiance_W_m2=1000,
                   absorption_cm_inv=3000, reflectance=0.3)
light.apply(mf, surface_y_um=3)
# Construct DeviceSolver AFTER assigning generation, then run iv_sweep.
# v, i_per_cm = solver.iv_sweep("positive", "negative", 0, 0.65, 0.025)
# i_A = current_from_2d(i_per_cm, depth_um=20)
```

The absorption coefficient and reflectance above are demonstration inputs,
not a supplied silicon optical database. Specify their provenance in real
experiments. The caller is responsible for photon energy relative to the
bandgap. One generated pair per absorbed photon is the default; the quantum
yield may be reduced explicitly. Collection efficiency is determined by DD.

For photon energy `E = h*c/lambda` and depth `d` in cm,

```
Phi = irradiance[W/m²] / E[J] * 1e-4              [photons/cm²/s]
G(d) = yield * (1-R) * Phi * alpha * exp(-alpha*d) [pairs/cm³/s]
integral G dd = yield*(1-R)*Phi*(1-exp(-alpha*t))  [pairs/cm²/s]
```

The entrance plane is in the absorber. Light travels in `-y`. Reflection
is a single entrance loss. No shading, thin-film interference, multiple
reflection, scattering or overlayer transmission is calculated. `apply`
replaces the field and records its inputs in `MeshField.metadata`. A custom
optics calculation can instead set nodal point data named
`optical_generation_cm3_s`. Values must be finite and non-negative. Other
materials receive zero when using `apply`; the solver always ignores
generation in insulators. Triangles are currently required.

Generation enters the electron residual as `-qR + qG` and the hole residual
as `+qR - qG`. These opposite signs conserve charge. The old solver used
`-qR` in both residuals; this was corrected along with the hole time-charge
sign. Existing DC results should be rechecked when recombination matters.
The solver still exposes DC/quasi-static analysis; correcting its time-charge
term does not add a public transient solver.

DEVSIM's 2D integrated terminal current is **A/cm of out-of-plane depth**.
The mesh width is already integrated. For a cross-section of width `w_um`
and invariant out-of-plane depth `z_um`, the illuminated footprint is
`w_um*z_um` and physical current is `i_per_cm*z_um*1e-4`. Do not multiply
by the in-plane width again. Positive current enters the positive diode
terminal; a delivering PV has negative terminal current. The helper does
not account for edges of a finite 3D device.

Boundary conditions remain those of the chosen structure: ideal ohmic
contacts fix carrier densities; uncontacted boundaries have natural zero
normal flux. Bulk SRH is supported. **No surface recombination velocity
or interface recombination model is added here.** Ideal ohmic contacts can
lose minority carriers even with long bulk lifetime. Results assuming
passivated sides are an optimistic boundary case, not a fabrication claim.
The silicon material database is not calibrated to XT018 or an open PDK.
Its intrinsic density is presently the supplied 300 K value; changing
`temperature_K` alone is not a validated temperature-dependent PV model.

Run the generic example with `python examples/07_photovoltaic.py`.
`tests/device/test_optical.py` checks the photon budget analytically,
dimensional scaling, invalid inputs, localized-generation collection in a
depleted diode, and terminal-current conservation with significant dark
recombination. The application additionally records mesh, lifetime,
illumination and system-timestep sensitivity. Numerical convergence is
separate from agreement with measured devices.
