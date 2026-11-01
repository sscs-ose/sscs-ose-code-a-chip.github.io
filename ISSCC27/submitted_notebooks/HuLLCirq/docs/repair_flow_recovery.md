# Return from synthesis failure in 05 to RTL repair in 04

2026-10-16. GUI operation and saved-data protection verification record (historical development reference; not included in this curated archive). The GUI is in English.

Update on the same date: [Complete repair instructions, saved requests and the full synthesis console](repair_prompt_console.md). New previews use instruction v4, which adds a specific driver correction. Previously frozen instructions and retries are not rewritten. Consult the latest verification record (historical development reference; not included in this curated archive) for the current candidate and budget. The run IDs and budgets below record an earlier verification checkpoint.

## Which button to press next

| Current screen | Action |
| --- | --- |
| Synthesis failed in 05 | Select **Prepare repairs for all failed nodes** at the top. The individual **Prepare RTL repair** action opens the same repair preview. |
| You returned to 04 by selecting its tab | Select **Preview repairs for N failed nodes** at the top. The **Repair failed synthesis** section immediately below lists the targets, actual diagnostics and common repair instruction. |
| A repair preview is ready in 04 | Use **Read repair instructions** to read the complete instructions. Inspect the targets, original candidates, run IDs and diagnostics in **S05 repair queue**, then select **Start repair batch**. |
| You edited a repair instruction | The previous Start action becomes unavailable. Select **Preview repairs for N failed nodes** to create a new preview. |
| The preview is Blocked | Select **Rebuild repair preview**. Inspect the displayed input, output, context and maximum output allowance for these inputs; select **Open LLM settings** if needed. Settings are not changed automatically. |
| The instruction is empty for an individual manual repair | Select **Edit required correction** to focus the **Required correction** field. Enter the instruction, then use **Context Preview → Repair node RTL**. |
| The new RTL has completed S04 review and adoption | Return to 05 and select **Run synthesis for all nodes**. The new candidate is synthesized again; current valid synthesis results for other nodes are reused. |

A preview does not call the LLM. Only Start begins a new model request. Requests are sent separately to each node in sequence, preserving the complete inputs, responses and results in history. The boundaries remain: S04 checks the external interface, S05 performs synthesis, and S06 performs behavioral verification.

## Paths corrected in this update

Stage 04 also detects the latest S05 failure corresponding to the currently adopted candidate. It does not prioritize regeneration or proceeding to 05 based on the completion or failure of an older generation batch. Older batches remain available in a collapsed view. Only executed child runs superseded by later adopted candidates are removed from the old unresolved count; a Blocked node whose request has not run is not treated as executed.

Both individual and batch repair actions in 05 use the same backend preview with diagnostics. Long synthesis logs are not duplicated in both the frontend instruction and the backend evidence. Editing instructions, changing the latest candidate, or changing an input or profile version prevents an old preview from starting. Explicitly choosing an individual repair clears only an unsent batch preview; it does not overwrite a running batch or one whose start acknowledgement is uncertain.

## Repair-request budgets and evidence

The new `s05-repair-diagnostics-v3` projection sends an excerpt of at most 400 characters, prioritizing specific final-stage diagnostics such as multiple drivers and undriven signals, together with the original run ID, candidate ID, full-record hash and reference location. It explicitly marks omissions and shortens the request while retaining the complete S05 log. The excerpt is neither a complete enumeration of all errors nor proof that the circuit has been repaired. Reconstruction of the existing v2 format and instructions already frozen in previews or retries are preserved.

For Job control at this checkpoint, the old projection required an input budget of 14,356 plus an output allowance of 3,072, totaling 17,428 and exceeding the 16,384 context. The new projection requires input 13,092 plus output 3,072, totaling 16,164, so it can start with the same saved profile. These are HuLLCirq's conservative UTF-8 byte-bound estimates, not the model's actual token usage or its maximum capabilities. If a long user repair instruction or another input causes the budget to be exceeded again, the Blocked state and recovery actions apply.

## Status at the recorded checkpoint

The original eleven-node design had 11/11 adopted S04 results and 10/11 adopted S05 results. S05 run `workflow-aea07c5ee8b045acaa741a28d2139b21`, corresponding to Job control candidate `generation-93296b57c3074486b24e8448e4958950`, was Failed. Its final CHECK reported multiple drivers for `busy`. This work corrected the GUI paths and diagnostic budgets; it did not send the RTL repair request, establish a passing repair, or run and pass synthesis again.
