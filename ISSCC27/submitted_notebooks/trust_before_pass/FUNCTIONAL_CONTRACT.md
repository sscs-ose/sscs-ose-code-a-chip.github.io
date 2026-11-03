# Four separate judgments

Execution describes the recorded simulator process. Measurement validity describes
whether a declared scalar is supported by its required events and artifacts.
`scalar_spec` compares a valid delay with numerical bounds; legacy `verdict` is
an alias for that field, **not** overall circuit compliance. `functional.status`
independently checks an explicitly supplied temporal contract against AVDD and POR.

## Teaching assumption T1

Observe from t = 0. At the first AVDD rising crossing of 3.0 V, require a **new**
POR rising crossing of 0.9 V within 2 ms, including the deadline. AVDD must remain
at or above 3.0 V through that event or the deadline. Samples must be finite,
ordered and separated by no more than 2 us over the required history. A trace
initially above the supply threshold cannot establish the rising trigger.

The source README (`assets/por/README.upstream.md`, POR commit
`db8745ef4d7d85a1852fc60c251ba34c6cebe497`) describes selectable 2.4–3.0 V trip,
roughly 1 ms startup and roughly 50 ms reset assertion. It does **not** establish
T1's exact thresholds/deadline for all operating conditions. T1 uses the upper
nominal trip range and a declared educational response budget. It is a new
evaluation assumption, not an independently established safety requirement or
proof of violation of the original designer's specification.

The original startup template instead measures first oscillator-to-POR rises
after 1.5 ms, with a 0.5–2 ms numerical bound. Those two contracts are not equivalent.
Do not infer power-good timing from an oscillator proxy without further evidence.
`por` rising is active-high reset **assertion**, not reset release.

| Functional status | Meaning |
|---|---|
| PASS | A new post-trigger edge was witnessed under T1 assumptions |
| FAIL | Trigger and deadline observed, supply remained valid, but no required edge |
| NOT_TRIGGERED | No rising supply trigger in the observed interval; no PASS claimed |
| INSUFFICIENT_EVIDENCE | Missing history/deadline, invalid samples, sparse sampling, or supply collapse |
| NOT_EVALUATED | No functional contract supplied |

An early POR high level does not satisfy a requirement for a new post-trigger
edge. That choice is explicit in T1; a different system requirement might instead
ask for a high level at a particular time. Change the contract, not its explanation.
Missing response can yield measurement INVALID and functional FAIL simultaneously.
An early observation cutoff can yield unavailable delay and insufficient functional
evidence without saying anything about the original completed simulation's exit code.

## Standalone use

```python
from evidence import assess_run
from functional import FunctionalContract
r = assess_run('data/runs/tt27_continuous_nanoamp',
               functional_contract=FunctionalContract())
print(r['execution'], r['measurement'], r['scalar_spec'], r['functional'])
```

For an in-memory waveform use `assess_function(t, avdd, por, contract)` with SI
units. Invalid contract settings raise ValueError; malformed or insufficient
waveform evidence returns INSUFFICIENT_EVIDENCE with a reason. The CACE startup
hook remains the existing waveform-validity hook: its Error status is not a
functional FAIL. Feed saved six-column waveforms to this separate API for T1.
The new function is not claimed to be encoded into the native CACE summary.

## Limits and independent oracle

This is first-startup sampled monitoring, not brownout recovery, metastability,
glitch qualification, all-PVT characterization, continuous-time proof or a check
of the full 50 ms pulse. A PASS proves only this narrow sampled property. Sparse
sampling rejection cannot rule out all sub-sample glitches. Supplies that collapse
need a different contract; they are not automatically called circuit failures.

Synthetic tests use analytically specified crossing times, including exact deadline
edges, absent/early/late responses and coverage gaps. Real-case conclusions use
unaltered archived waveforms and their provenance. The upstream HVL correction is
credited to its authors; no new circuit defect or automatic root-cause diagnosis
is claimed. A minimal independent Python baseline is included for comparison.
