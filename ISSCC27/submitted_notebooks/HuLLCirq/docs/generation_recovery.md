# S04 — Recovery from generation failure

## Eligibility and operation

When the request selected in Local RTL Generation is Failed, Cancelled or Interrupted, Generation evidence shows **Recover this request**. Recovery creates a new request using the same saved specification, starting from the original record that remains failed. It does not append text to a partial answer or adopt reasoning as RTL.

1. Read the short guidance for the error and inspect Context / input estimate / max output.
2. As indicated by the guidance, adjust **Retry output limit (tokens)**, **Thinking control** and **Retry timeout (seconds)**. No save is needed when no setting changes.
3. Only if settings changed, use **Save recovery settings** to save a new provider-profile version. Changes are limited to the output cap, thinking control and timeout; the model, destination, context limit and other settings are retained. Saving does not perform inference.
4. Use **Prepare retry with saved settings** to restore the original operation, repair source and instruction. This operation does not perform inference either.
5. Use **Context Preview** to inspect the request with the new profile.
6. Use **Retry node RTL** to explicitly start new generation. **Start new request** removes the retry association.

## Limits and deciding what to change

The output field shows the range allowed for that request. The upper limit is `min(65,536, context window − 1, context window − input estimate)`. The input count prioritizes a conservative estimate of the transmitted format recorded by the service and is distinguished from actual tokenizer usage. If the input estimate is unavailable, the remaining budget is Unknown; prepare a retry with the saved settings and inspect Context Preview.

For example, the collector in this checkpoint had context 16,384 and an input estimate of 8,829, so its configurable output range was **1–7,555 tokens**. The timeout range was **0.05–3,600 seconds**. This output cap is HuLLCirq's request budget, not a measurement of the model's own maximum output capacity. Increasing the profile's context value alone does not enlarge the running LLM's context.

| Error | First action |
| --- | --- |
| stream_incomplete | A normal completion notification was not received. Prepare a retry with the same settings; do not conclude that the output cap or timeout was reached |
| output_truncated | If an increased cap fits the budget, use the proposal button to update the field and save it. If only reasoning was returned, disabling thinking is also proposed |
| timeout | Inspect whether the partial answer was useful ongoing generation or repetition. Extend the timeout only when needed |
| Setting outside the allowed range | Correct it to the displayed range or use **Reset to saved settings** |

The fields start with the saved values. Proposal buttons change only the draft, without automatically saving or retrying. If there is no room to increase the output cap, the UI does not suggest that increasing the same request's output budget will solve the problem. Instead, consider a new request with shorter instructions or inputs. Changing the instruction is not treated as a retry of the original request.

Usage, answer/reasoning character counts, finish reason, earlier settings and the saved explanatory text remain under the collapsed **Request details**. If failures recur, inspect the raw answer and server logs. Thinking-control support was checked with the prepared Ollama/Qwen environment; other providers may differ.

## Preservation and rejection conditions

A new job stores `retry_of_job_id`, which is also included in the preview context hash. The original job's text, reasoning, error, context and profile remain unchanged. No migration adds new fields to old jobs; old context hashes are preserved.

A parent must be a failed, cancelled or interrupted request with a recorded end time. A retry uses the same node, saved revision, input hash, operation, repair source, instruction, exact messages and prompt template. A change to the specification or instruction is a new request whose preview is built from current inputs. A retry may be prepared even if there is no partial RTL, while preserving the existing requirement that a repair source must contain an inspectable RTL candidate.

Recovery actions are restricted for an unsaved design or provider draft, stale source, read-only state, storage error, active job, pending communication and similar conditions. Delayed responses from profile updates, previews and other operations are not applied to a project/system that has already been switched. There is no automatic retry, automatic limit increase or fallback to an external provider.

## Scope of acceptance checks

Even when regenerated output reaches Completed, the S04 external-port check and saved adoption policy still apply. S05 handles syntax and synthesizability; S06 handles circuit behavior against the original specification. See stage responsibilities at this checkpoint (historical development reference; not included in this curated archive). Receiving output is not substituted for a Passed behavior-verification result. An HTTP 409 caused by insufficient verification is not misreported as a project connection conflict.

At this checkpoint, Job control and Operand buffer in the new 11-node NPU had behavioral checkers corresponding to their original specifications and inputs. Support for other nodes or later stages was not claimed complete; inspect the required support in S06.

For execution evidence and operation screens, see recovery verification (historical development reference; not included in this curated archive).

For the short guidance, per-request limits and actual GUI boundary checks from 2026-10-14, see the recovery-guidance improvement record (historical development reference; not included in this curated archive). The collector request was inspected through preview with the same saved settings; actual regeneration was not performed.
