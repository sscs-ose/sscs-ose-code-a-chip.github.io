# What is added over a small script?

The strongest relevant baseline is ordinary CACE plus a short Python event check.
We include `simple_baseline.py` and actually run it on the same five existing
recorded conditions. `data/v03_baseline.json` preserves the categorical results,
source hash and measured local timings. All supported-case results agree: **no
extra fault detection or accuracy gain is demonstrated**.

| Approach | Inputs / setup | What it supplies | Limits |
|---|---|---|---|
| Native CACE numeric evaluator | Existing exported delay and bounds | PASS/FAIL against scalar limits; already fails negative startup export | Does not by itself certify that failed `.meas` produced a meaningful scalar or evaluate T1 |
| Minimal Python baseline | Six-column waveform; fixed 3 V / 0.9 V / 2 ms constants | Required edge check, scalar bound, narrow T1 result | Rejects inputs outside monotone, complete, finely sampled startup; no log/provenance audit or learner workflow |
| This package | Same waveform plus optional recorded logs/artifacts; explicit functional contract | Same verdicts plus reasons, trigger/deadline/witness, source/coverage, independent state dimensions; reusable journal and plots | More files and configuration; still sampled, narrow first-startup monitoring |

The numeric CACE evidence was recorded earlier with the actual pinned evaluator,
and three earlier CLI runs are retained in `data/cace_integration`. It is not fair
to score CACE as failing to implement a new property it was never configured to
check. Its normal Python hook is a suitable place for custom checks. The unchanged
startup hook retains its existing validity-only role; `assess_run(...,
functional_contract=...)` supplies a separate T1 sidecar result.

The simple baseline deliberately uses independent scalar Python loops for event
interpolation, not calls into our monitor. On its supported input domain it is a
credible alternative for a one-off check. Unsupported inputs raise ValueError.
Tests compare it to the main implementation on the real records; analytic
synthetic cases separately check deadline and evidence semantics in the monitor.

Current timing fields are transparent cost observations, **not speedup numbers**:
the simple function is timed on an already loaded array (minimum of five calls);
the package call includes disk I/O, hashing and original artifact audit (one call).
Their workloads differ. No human diagnosis-time, maintenance-time or learning
benefit has been measured. Configuration effort is described above rather than
invented as a quantitative score. A future user study or equivalent-work benchmark
would be needed for those claims.

Prefer the small script when its domain and fixed rules fit the job. Prefer the
package when reusable explicit contracts, provenance and a guided investigation
are useful. Use existing temporal monitoring tools for richer specifications;
do not turn this example into a general temporal-logic framework by default.
