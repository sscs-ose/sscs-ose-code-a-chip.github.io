# Stable nonlinear adsorption correction

**Reviewed and accepted as failed stable nonlinear-formulation evidence; native startup and end-to-end actuation remain unvalidated.**

The sole 250 µs / 25 ns request aborts at **151.541154 µs**. The saved prefix has **8515 × 45 finite values**. Ngspice returns zero but reports `TRAN: Timestep too small; time = 0.000151541, timestep = 3.125e-20: trouble with node "vreturn#branch"`, then aborts. Native syntax parsed and executed, but complete startup failed. The trouble equation or changed abort time is not an established cause.

Actual endpoint pins are `logic` **1.636831 V**, `act` **1.842303 V**, `mid` **0.921151 V**, `reset_n` **+0.960200 mV**, `driver_ready` **−0.697933 µV**, and `pa`/`pb` **−230.502 µV**. Commands remain fixed zero. Coverage stays **0.4999999415–0.5000002924** and max|eta|/width is **0.0002315953**. Passing domain, held-input, clamp, coverage, small-signal and electrical-bookkeeping checks apply only to this prefix; no completed nonlinear startup or released operation is established.

Decimal 80-digit reference checks pass for **684 cases**, including zero, both crossover sides, large inputs, nonzero offsets and common modes. Maximum tested current error is **1.94×10⁻²² A**, voltage/offset partial error **4.91×10⁻²³ A/V**, and tau-partial error **9.68×10⁻²¹ A/s**. The uniform analytic polynomial-remainder bounds are **2.1870×10⁻²⁹** for c and **1.9683×10⁻²⁵** for c′ on |z|≤10⁻³. These bound exact-polynomial truncation; finite floating errors are separately measured on the stated grid. The crossover float gaps are **1.78×10⁻²⁰** in c and **6.12×10⁻¹⁸** in c′, not claimed zero.

Peak local terminal-versus-solution current discrepancy is **0.241794 pA**, global solution KCL residual **4.88×10⁻²² A**, and integrated electrode charge residual at most **6.08×10⁻²¹ C**; numerical conservation is not exact. Prefix signed adsorption work is **2.864327×10⁻²¹ J**. The normalized state-capacitor quantity changes by **8.537243×10⁻²⁴ J** and the signed behavioral-branch work is **2.855790×10⁻²¹ J**; neither is claimed calibrated chemical energy or resistor heat. No repeat, fine, rescue, DC, DD or layout run is added.

Starting from accepted linear B, only its adsorption current expression and one explicit `.func` change. With g=Qmax/(4width·tau), the law is **Ia=g·[V(metal,state)−offset+2width·c(z)]**, **z=(V(metal,solution)−offset)/(2width)**. Outside |z|<10⁻³, c=tanh(z)−z; inside it uses **−z³/3+2z⁵/15−17z⁷/315**. This bounded approximation avoids forming the near-equal linear terms in the principal metal-to-state current; it is not claimed exact. Ca, Cdl, RF and all surrounding circuitry/probes/timing are unchanged.

Offline Decimal 80-digit checks cover crossover neighbors on both sides, zero, large eta, theta 0/0.5/1, nonzero offsets and common modes. Current and metal/solution/state/offset/tau partials are compared with the original logistic-state reference. Taylor remainder bounds follow the derivative recurrence P(n+1)=(1−t²)P'n and |tanh(z)|≤|z|; offline_checks.json records bounds and floating error separately. Native automatic derivatives are not separately instrumented. The sole startup run is the only native syntax/execution check.

Signed adsorption terminal work is retained. Normalized 0.5Ca·u² is not chemical energy, and signed behavioral-branch work is not resistor heat. Coverage is recovered offline from physical state-to-solution voltage. Current discrepancies remain explicit; no exact numerical-conservation claim is made. Incomplete traces support prefix checks only. No released actuation, phase, bending, large-signal electrochemical or autonomous validation follows, and changed execution does not establish a unique cause.

```text
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python -m examples.microrobot.tcad_stable_adsorption
```

Fresh destinations are required. Exact deck/diff/log, precision checks and executed runner are retained; raw data remain local. Prior evidence/defaults are unchanged. No submission, publication, push or fabrication occurred.

Two focused tests pass in 1.46 s; Ruff passes. They check the bounded high-precision current/partial/remainder audit and exact restoration of every source-deck line by reversing only the B expression and function insertion. Boundary-grid sign checks include a documented 10⁻²¹ A tolerance for floating construction of physical nodes. No native derivative instrumentation, extra simulation or future framework work was added.

```text
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python -m pytest tests/integration/test_tcad_stable_adsorption.py -q
.venv/bin/python -m ruff check examples/microrobot/tcad_stable_adsorption.py tests/integration/test_tcad_stable_adsorption.py
```
