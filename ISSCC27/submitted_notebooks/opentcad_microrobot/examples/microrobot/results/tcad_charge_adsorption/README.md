# Charge-conserving nonlinear adsorption series branch

**Reviewed and accepted as failed nonlinear adsorption-reformulation evidence; nonlinear startup and end-to-end actuation remain unvalidated.**

The sole 250 µs / 25 ns request aborts at **81.534551 µs**. The trace saves **4577 × 45 finite values**. Ngspice returns zero but reports `TRAN: Timestep too small; time = 8.15346e-05, timestep = 3.125e-20: trouble with node "vreturn#branch"`, then aborts. This equation is not an established cause. Algebraic equivalence passed, but complete startup did not.

Final logic / actuator span / midpoint are **1.577298 / 1.821612 / 0.910804 V**. Reset ends at **−2.391321 mV**, driver-ready **+0.236399 µV**; all numerical commands remain zero. Recovered coverage stays **0.4999999715–0.5000001425**, with max|eta|/width **0.000231595**. These are small excursions in an incomplete held-input trace, not evidence of large-signal or released-actuation validity.

The 451-point offline grid matches the original nonlinear dtheta/dt with maximum absolute difference **1.42×10⁻¹⁴ s⁻¹**. Prefix signed adsorption terminal work is **1.568200×10⁻²¹ J**. The normalized state-capacitor quantity changes by **2.026072×10⁻²⁴ J**; its work/storage residual is **1.12×10⁻²⁹ J**, and signed series-branch work is **1.566174×10⁻²¹ J**. These quantities retain their stated mathematical bookkeeping roles and are not chemical-energy or heat measurements.

Peak local terminal-versus-solution current discrepancy is **0.167141 pA**, global solution KCL residual **4.44×10⁻²² A**, and integrated electrode charge residual at most **4.05×10⁻²¹ C**. Numerical conservation is not exact. Prefix PV delivery is **5.163893 pJ** with supply-balance residual **0.000474 pJ**. Passing energy/domain/clamp/coverage checks apply only to this prefix; failed completion prevents startup acceptance. No fine, rescue, DC, DD or layout run is added.

Starting from accepted passive adsorption, only the adsorption resistor and one explanatory comment change. The replacement current flows metal→state, with **Ia=Ca/tau·[2width·tanh((eta−offset)/(2width))−u]**, **u=V(state,solution)=4width·(theta−0.5)** and **Ca=Qmax/(4width)**. The existing capacitor connects state→local solution; Cdl and RF remain unchanged. Actual offset is 0. This yields **Ia=Qmax·dtheta/dt** and exactly **dtheta/dt=[logistic(eta/width)−theta]/tau**. There is no separate ground-referenced coverage source or duplicate direct adsorption-current branch.

Offline algebra.json checks a grid of eta −2 to +2 V and theta 0 to 1, including boundary signs and finite 20 ms relaxation. Algebraic agreement at large input values is not large-signal physical validation. Startup coverage is reconstructed offline from the unchanged ta/tb/tr output columns, which remain physical state-node potentials. Every other DD source, geometry, extracted clock, native DFF, proxy, transistor driver, passive clamp, electrode/Pt-return element, ramp, storage, tolerance and output probe remains unchanged.

Signed adsorption terminal work is retained in the electrode energy balance. The normalized capacitor quantity **0.5Ca·u² is not physical chemical energy**; its work/storage balance and the signed behavioral-series-branch work are separately identified. That branch work is not resistor heat. Current discrepancies and integrated charge-KCL residuals are reported without claiming exact numerical conservation. All checks on incomplete data are prefix-only.

Held commands remain zero. This diagnostic provides no released actuation, gait, bending, large-signal electrochemical calibration or autonomous-controller acceptance. A changed simulator outcome or trouble equation does not establish a unique cause.

```text
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python -m examples.microrobot.tcad_charge_adsorption
```

Fresh destinations are required. Exact deck/log/diff and executed runner are retained; raw data remain local. Previous defaults/evidence are preserved. No publication, submission, push or fabrication occurred.

Two focused simulator-free tests pass in 1.30 s; Ruff passes. They verify full nonlinear algebra and boundary signs, topology/no duplicate state current, and exact restoration of the original deck by reversing the single branch substitution and comment. No output vectors/probes, native defaults, source characterization or prior evidence changed.

```text
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python -m pytest tests/integration/test_tcad_charge_adsorption.py -q
.venv/bin/python -m ruff check examples/microrobot/tcad_charge_adsorption.py tests/integration/test_tcad_charge_adsorption.py
```
