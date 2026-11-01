# Inspect repair instructions and the complete synthesis console

2026-10-16. Operations in the English GUI. Investigation of actual history and GUI verification (historical development reference; not included in this curated archive).

## Read repair instructions

- **Instructions for the next request:** Create a repair preview in 04, then select **Read repair instructions** at the top. Each node's **Complete repair instruction** displays the entire program-prepared instruction and any additional instruction. The original candidate and S05 run are shown alongside it. Use **Read the full first request** to inspect the complete system/user and other messages of the first request. This is a preview; it has not been sent yet.
- **An already saved request:** In **Generation evidence** in 04, select **Read this job’s LLM request** or the **LLM request** tab. Inspect the selected job's frozen instruction and all messages. When viewing an older job, the GUI identifies it as historical and offers **Show latest node request**. **Download request text** and the existing context JSON download are also available.
- To change the instruction, edit **Additional instruction for these repairs** and create a new preview. Do not alter only the displayed text and make it disagree with the request to be sent. Start continues to enforce the existing source, candidate, profile and budget checks.

For previews covering multiple nodes, inspect each node's repair instruction and the first request. Later requests may include conversation from preceding nodes obtained during execution. Inspect the complete messages actually sent in each saved job's **LLM request** view. A preview is not finalized transmission content containing subsequent conversation that does not yet exist. Verification-only jobs indicate that no model request was sent.

## Read the full console

**Full saved tool console** is always available in **Execution evidence** in 05/06. It displays every saved command, completion state and exit code, and each command's stdout/stderr without omission. Older runs that contain only aggregated output are also displayed.

The console can be scrolled, but its content is not truncated. **Jump to start / Jump to end** move to either end. Use **Download full console / Download stdout / Download stderr** to save it. Because the interleaved timing of stdout and stderr was not recorded, they are displayed as separate streams rather than a fabricated chronological sequence. Short diagnostic excerpts and full saved logs remain separate.

## Why the same error persisted, and how the instruction changed

The three most recent Job control repairs at this checkpoint had received the correct original candidate and synthesis diagnostics, including the multiple drivers for `busy`. However, the returned RTL retained both procedural `busy <= ...` assignments and `assign busy = ...` to the same signal. The second response was identical in full; the third only removed comments. This did not establish that the requests had failed to arrive. Instead, the generic repair instruction had not led to the required structural correction.

New instruction v4 identifies the target signal and assignment lines from the original final CHECK diagnostic and a limited lexical match against the RTL. For the candidate's `busy` signal, it identifies procedural assignments on lines 42/50/60/78 and a continuous assignment on line 85, instructing the model to give the output a single driver. If the required output wire is retained, it must be driven by one assign from an internal reg, with no procedural assignment to that wire. A different representation may be chosen only if it remains compatible with the header requirements. This lexical matching is neither a complete Verilog parser nor functional proof; it does not invent instructions for structures it cannot recognize.

Old v2/v3 diagnostics, saved instructions and retries are not rewritten. The complete original logs are retained, while diagnostic excerpts sent to the LLM remain bounded. Being able to read a full log in the GUI does not mean the entire log is supplied to the local LLM. A new preview for the candidate fits within input 13,071 plus output 3,072, totaling 16,143 within a context of 16,384. This is a conservative input-budget estimate, not actual token usage.

The change does not guarantee that the model will return correct RTL. A new repair candidate still needs the S04 external-interface check and S05 synthesis again; behavioral verification takes place in S06.
