# Repeated generic physical correction through the GUI

Updated: 2026-10-28. Generic closure v1 remains the exact executed first-correction
recipe. A separate v2 adds explicitly requested subsequent attempts; it does
not reinterpret earlier failures or promise that a design will close.

## Eligible failures

Open the editable original project with its saved generic cycle-vector plan.
The complete RTL, independent expected values, clock/reset, original signoff
SDC and all nine final timing/electrical corners remain fixed.

An additional correction requires either:

- The latest current **S11** execution of the preceding prepared generic profile,
  completed with actual fresh mapping/routing and only electrical checks failed.
- The latest current **S14** execution with only electrical checks failed,
  bound to the exact currently adopted S11/S12/S13 chain and preceding profile.

Failed launches, uncertain process cleanup, missing reports, stale sources,
software fixtures, failed timing/routing/function, and an adopted failed result
are not eligible. Full saved native proofs and immutable predecessor bundles
are rechecked; a label, zero process exit or model statement is not a pass.

## Explicit prepare, then separate execution

1. For a first eligible S14 failure, use **Prepare fixed physical correction**
   as before. That is the preserved v1 fresh generic correction.
2. If that correction's S11 or later source-bound S14 fails only its electrical
   checks, choose **Prepare next generic physical correction** in that stage.
3. Preparation saves a new immutable numbered bundle. It lowers core utilization
   by five percentage points from the previous recorded value, with a minimum
   of 10%. This is a placement assumption, not a change to the original circuit
   requirements or signoff limits. At the minimum, further explicit attempts
   retain 10%; do not interpret another attempt as a new optimization strategy.
4. Inspect the prepared profile, attempt number, source IDs and core utilization.
   Preparation starts no EDA/model process and adopts nothing.
5. Separately choose **Run physical layout**. Every v2 run performs fresh
   synthesis, technology mapping, placement, CTS, routing, extraction and checks;
   no predecessor checkpoint or earlier mapping is reused.
6. Review/adopt only a fully Passed current result. Run and review new S12 DRC,
   S13 LVS and S14 for that new layout. A new layout never inherits those passes.
   Select the actual **Review operator** before recording explicit adoption.

There is no automatic retry. Each request requires a user action, and history
is bounded to 256 subsequent preparation attempts per original preparation.
Block-region placement is deliberately rejected rather than silently removed;
the cancelled block-region approach is not restarted by this feature.

## Reconnect and preservation

If a preparation response is lost, use **Reconnect without resending** or
**Refresh saved post-layout runs** / **Refresh saved layout runs** first.
Preparation and execution remain blocked while the outcome is unknown.
Saved profiles are restored only after their entire predecessor/source chain
and retained artifacts validate. Missing, rehashed or altered bundles fail
closed, remain on disk, and are not overwritten or silently skipped.

All prior run/review bodies, original v1 recipes and original inputs remain
unchanged. New numbered bundle publication is atomic and refuses an existing
destination. Viewing a stage, profile or history starts no tool and saves no
design. Only explicit preparation changes the active execution profile; that
may make downstream evidence historical while retaining its original bytes.

## Verification boundary

The implementation has isolated builder, source-admission, three-attempt
prepare/restore, publication, controller and lost-response tests. These use
explicit software/native-proof mocks where stated; they are not actual native
EDA executions. The task's completion ledger (historical development reference; not included in this curated archive)
records the exact current GUI/native verification status and intervention times.
This path does not add dynamic SDF, formal equivalence, analog or fabrication
qualification. See the [generic project guide](generic_digital_projects.md).
