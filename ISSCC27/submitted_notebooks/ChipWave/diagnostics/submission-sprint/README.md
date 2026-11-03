# Submission-sprint runtime preflight (diagnostic only)

The one authorized preflight used three independent role contexts and five native
invocations. It completed the initial implementation, verification, a deliberately
failed physical substitute and a feedback repair, then stopped during verification
at the shared Token ceiling. The second physical substitute did not run. Thus the
preflight failed and **no new design comparison was admitted**.

The limit was 500,000 logical input-plus-output Tokens; observed usage was 515,131,
including 15,131 in-flight excess. Cached input is included. Excess is reported,
not credited as budget-admissible source. There were zero real physical attempts.
This is preparation work, not a chip-design sample or evidence of workflow superiority.

After installing the submission's public runtime, from the submission root:

```bash
python diagnostics/submission-sprint/scripts/capacity_accounting_replay.py \
  --packet diagnostics/submission-sprint/preflight/native-accounting.json \
  --runtime diagnostics/submission-sprint/preflight/runtime
```

This checks filtered native accounting and captured source association offline.
It does not verify provider invoices or reconstruct removed private transcript
bytes. Model account homes and authentication are excluded. Runtime sources here
are captured diagnostic sources, not permission to launch an unqualified study.
