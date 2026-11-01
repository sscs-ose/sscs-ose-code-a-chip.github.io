HuLLCirq combines an English browser GUI, local-LLM RTL proposals, independent
verification contracts and open-source EDA. It preserves specifications, expected
values, generated candidates, repairs and adopted-source lineage through fourteen
stages. The main worked example is an eleven-block explicit 2x2 signed NPU; separate
Counter, FIFO-to-XOR and shared-definition lane examples document the generic path.

The notebook includes the NPU input matrices and independently calculated results,
logical architecture, measured S06/S10/S14 waveforms and actual saved-source replay
results. The exact adopted Counter RTL and generic synthesized netlist each replay
the unchanged fourteen-cycle, forty-two-output contract without LLM regeneration.
The local GUI demonstrations and development-assistant repair guidance are disclosed
separately; no autonomous first-attempt success or human-usability study is claimed.

Start with `HuLLCirq.ipynb` or its static reading copy `HuLLCirq.html`.
`docs/submission_guide.md` describes setup and distinct reproduction routes;
`docs/saved_rtl_replay.md` gives the concrete saved-source commands.
`python scripts/verify_submission.py` checks the complete per-file manifest.

The physical result uses routed-netlist functional verification plus extracted STA,
not dynamic SDF or foundry/tapeout signoff. Finite verification scope, retained NPU
LVS feedback, failed attempts and remaining environment conditions are stated.
Original software/documentation use Apache-2.0 with third-party notices retained.
Tool/PDK installations, model weights, private host data and standalone restricted
AI branding artwork are excluded. All submission files belong to
`ISSCC27/submitted_notebooks/HuLLCirq/`.

Author and representative: Ryotaro Kawashima, Department of Biomedical Engineering,
Graduate School of Biomedical Engineering, Tohoku University.
