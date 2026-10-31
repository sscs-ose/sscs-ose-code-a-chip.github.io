# Trace the recorded agent contribution

The semantic cut and service contract were supplied by the designers. The planning agent froze task responsibilities and handoffs; the RTL agent implemented the assigned split. This folder preserves the existing evidence for that handoff.

| Step | Saved evidence | What to inspect |
|---|---|---|
| Designer inputs | [Task intent](rtl-intent.txt), [reference RTL](../../reproduction/reference/rtl/lb_feedback.sv), [contract](../../design/spec/contract.md), [folding specification](../../design/folding-spec.json) | Exact ownership, 352-byte payload, 725 functional links, unchanged cycle behavior and write boundaries |
| Historical configuration | [Recipe](recipe.yaml), [RTL attempt](rtl-attempt.json) | Recipe selects the Codex framework and model identifier gpt-6.1-sol; the recorded RTL attempt uses medium reasoning effort and a 1,800-second timeout |
| Planning output | [Frozen briefs](task-briefs.json) | All nine saved task briefs, including independent checking and the conditions for later feedback |
| Implementation output | [Implementation note](physical-change.md), [delivered RTL](../../design/rtl/lb_feedback.sv) | Storage ownership, combinational next-sum return, endpoint cells and the agent's recorded local checks |
| Session and artifact identities | [Historical report](../historical-P0-report-data.json), [attempt record](rtl-attempt.json), [provenance](provenance.json) | Match native_usage.calls to session/attempt IDs and the RTL SHA-256 |

A concrete input was: “No additional pipeline, serialization or reduced MACs.” The saved brief carries that rule into completion criteria and assigns numerical/performance/physical acceptance to downstream tasks. The implementation note then explains how the last tile returns the combinational next sum to the output bank in the original cycle.

The workflow records one planning session and one RTL workflow attempt. Within that attempt, the implementation note records an initial Icarus elaboration error caused by forward references to unpacked arrays and two local RTL revisions. Moving the cut assignments below the declarations resolved the error. The delivered RTL is byte-identical to the RTL used by the packaged performance comparison.

## Re-execution scope

The supplied entry points rerun saved-evidence checks, paired RTL verification/performance measurement and joint timing; follow the package [README](../../README.md) and [dependency instructions](../../DEPENDENCIES.md). The configuration and frozen briefs here let readers inspect the historical generation inputs and decisions. Full assembled prompts, the complete conversation/tool transcript, the original orchestration runtime and a supported generation entry are outside this package. Regenerating the historical candidate would require those pieces and model access.

The model name is an identifier recorded in the historical configuration. The study contains one design trajectory; success-rate and agent-efficiency comparisons remain future work. The recipe is archival configuration and includes tasks and later candidates beyond the executed scope. Execution status is given by the saved report and attempts.

The original implementation note describes its handoff-time checks on 22 October. Final electrical closure is documented separately in [L1 final acceptance](../L1-final-acceptance.md).

## Provenance and license

These bounded configuration, intent, frozen-brief and implementation-note extracts come from the project experiment archive. [provenance.json](provenance.json) identifies the original snapshot, exact JSON selections, delivery and Git commit. The package's Apache-2.0 authorization covers these project materials; the external platform and model service retain their own terms.
