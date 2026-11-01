# Linear behavioral adsorption-current control

**Reviewed and accepted as linear behavioral-source held-input startup evidence; nonlinear and released actuation remain unvalidated.**

Completed the sole **250 µs / 25 ns** held-input startup. The trace starts at zero, reaches exactly 250 µs, and saves **14138 × 45 finite values**. Ngspice returns zero with no abort marker in 35.42 s. All declared diagnostic checks pass, including max|eta|/width **0.0002315932 <0.01**. Coverage remains **0.4999999102–0.5000004491**.

Actual endpoint nodes are `logic` **1.825979 V**, `act` **1.842306 V**, `mid` **0.921153 V**, `reset_n` **7.6879 nV**, `driver_ready` **0.61185 nV**, and `pa`/`pb` **47.399 nV**. The input commands remain zero throughout. The powered reset-clamp error peaks at **1.201118 µV**; global startup metal-to-midpoint error is **5.733097 mV**. Maximum per-cell DD voltage is **0.460576 V**, and logic peaks at **1.831136 V**. These held-input checks do not validate released actuation.

Peak local terminal-versus-solution current discrepancy is **0.209280 pA**, global solution KCL residual **4.55×10⁻²² A**, and integrated electrode charge residual at most **3.62×10⁻²⁰ C**; no exact numerical-conservation claim is made. PV delivery is **16.824303 pJ**, storage increase **4.182721 pJ**, and source/load residual **0.003987 pJ (0.0237%)**. Equivalent adsorption branch dissipation is **3.861562×10⁻²¹ J**, capacitor storage change **2.013573×10⁻²³ J**, and terminal-work balance residual **1.64×10⁻²⁸ J**.

A linear behavioral realization completes in this bench, whereas the tested nonlinear series expression did not. This narrows further checks toward expression/conditioning; it does not identify a unique cause or prove a simulator defect. No fine, rescue, DC, DD or layout run is added.

The passed passive-adsorption deck changes exactly one line: `Rads metal adsnode {tau*4*width/qmax}` becomes `Bads_linear metal adsnode I={qmax/(4*width*tau)*v(metal,adsnode)}`. Thus the native expression uses the direct metal-to-state voltage and has no nonlinear term or common-mode subtraction. The terminal law is exactly I=V/Rads, with identical model parameters, Cads/Cdl/RF, surrounding circuits, probes, held commands, ramp, storage and solver. The test reverses the single substitution to recover the source deck byte for byte.

Energy uses equivalent RC bookkeeping: the linear behavioral branch gives nonnegative V·I=V²/R, with capacitor storage and terminal work reported separately. This mathematical equivalence is not a claim of a separately calibrated physical heat device or chemical energy. Local current discrepancies remain explicit. Checks on an incomplete trace are prefix-only; no released actuation, phase, bending or autonomous operation is validated. Neither a changed outcome nor a reported trouble equation establishes a unique cause or simulator defect.

```text
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python -m examples.microrobot.tcad_linear_bads
```

Fresh destinations are required. Exact diff/deck/log and executed source are retained; raw data remain local. Previous evidence/defaults are unchanged. No publication, submission, push or fabrication occurred.

Two focused tests pass in 1.24 s; Ruff passes. They prove the single-line transformation reverses to the exact source deck and check I=V/R with nonnegative equivalent branch work over ±2 V. No additional simulation or source/physical characterization was run.

```text
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python -m pytest tests/integration/test_tcad_linear_bads.py -q
.venv/bin/python -m ruff check examples/microrobot/tcad_linear_bads.py tests/integration/test_tcad_linear_bads.py
```
