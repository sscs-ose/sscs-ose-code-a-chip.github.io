# Passive small-signal adsorption diagnostic

**Reviewed and accepted as small-signal held-input startup evidence; nonlinear adsorption and released actuation remain unvalidated.**

Completed the sole **250 µs / 25 ns** held-input diagnostic. The trace starts at zero, reaches exactly 250 µs and contains **14298 × 45 finite values**. Ngspice returns zero with no abort marker in 35.39 s. All declared diagnostic checks pass, including max|eta|/width = **0.00023159449 <0.01** (maximum |eta|≈**18.52756 µV**). Maximum logistic-equilibrium linearization error along the trace is **2.59×10⁻¹³**; reconstructed coverage remains **0.4999999102–0.5000004491**. These small-signal results establish no large-signal adsorption or released actuation.

Final logic / actuator span / midpoint are **1.825978 / 1.842306 / 0.921153 V**. Reset, driver-ready and phase commands remain held zero; the powered reset-clamp error peaks at **1.199848 µV**. Global startup metal-to-midpoint error is **5.733096 mV**. Maximum per-cell DD voltage is **0.460576 V**, and logic peaks at **1.831136 V**.

PV delivery is **16.824316 pJ**, supply-storage increase **4.182720 pJ**, and signed source/load residual **0.003936 pJ (0.0234%)**. Adsorption RC storage change is **2.013596×10⁻²³ J**, resistor heat **3.861604×10⁻²¹ J**, with RC terminal-work residual **1.60×10⁻²⁸ J**. Global solution KCL residual is **5.66×10⁻²² A**; the largest terminal-versus-solution current discrepancy is **1.701 pA**, and integrated electrode charge residual is at most **2.09×10⁻²⁰ C**. That local current discrepancy is reported separately and is not a claim of sub-pA terminal-current precision. Full electrode energy residual is **−1.427×10⁻²⁰ J**, about 0.27% of electrode port work.

The altered passive model completes where the original nonlinear state formulation failed, but this does not identify a unique physical/numerical cause or validate the original large-signal model. No fine, rescue, DC, DD or layout run was added. Only the three adsorption state branches change; all other circuits and output probes remain identical to the frozen passive-clamp deck.

Verified working-electrode parameters are Qmax 260 pC, width 0.08 V, tau 20 ms, offset 0; Pt return Qmax 2600 pC with the same width/tau. Linearizing logistic coverage at eta0=0, theta0=0.5 gives Cads=Qmax/(4width) and Rads=tau/Cads. Each working interface therefore uses **812.5 pF /24.615384615 MΩ**, return **8.125 nF /2.461538462 MΩ**. Rads connects metal to the third node and Cads connects that node to local solution; Cdl and RF remain unchanged. Positive eta charges a positive capacitor voltage and raises reconstructed coverage.

The existing third-node save vectors ta/tb/tr now encode physical capacitor-node potentials. Offline coverage is **0.5+(Vadsnode−Vsolution)/(4width)**. No ideal coverage source, probe change, voltage seed or UIC is introduced. Interpretation requires **max|eta|/width <0.01** over the entire saved trace. This local approximation does not calibrate or qualify large-signal electrochemistry.

Adsorption energy is now physical RC storage change plus nonnegative Rads heat, separately checked against terminal work. It replaces the original model's signed adsorption-work term and is not claimed to reproduce that nonlinear model globally. Cdl, Faradaic, solution, clamp and measured source-load terms remain separate. All checks on an incomplete trace are prefix-only. Held commands remain zero; no released actuation, phase/gait, bending or autonomous-controller validation is made. A changed outcome or trouble equation does not identify a unique cause.

```text
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python -m examples.microrobot.tcad_passive_adsorption
```

Fresh destinations are required. Exact deck/log/diff and executed source are retained; raw data remain local. Previous evidence/defaults are unchanged. No publication, submission, push or fabrication occurred.

Two focused analytical/assembly tests pass in 1.31 s; Ruff passes. They check RC values/time constants, orientation, reference coverage and energy identity, and prove the exact original deck is recovered by reversing only the electrode-model replacement. No save-vector/probe change occurred in this diagnostic. The final source corrects only an inherited measurement-description label; the original executed runner is preserved, and no numerical value/deck/simulation changed after execution.

```text
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python -m pytest tests/integration/test_tcad_passive_adsorption.py -q
.venv/bin/python -m ruff check examples/microrobot/tcad_passive_adsorption.py tests/integration/test_tcad_passive_adsorption.py
```
