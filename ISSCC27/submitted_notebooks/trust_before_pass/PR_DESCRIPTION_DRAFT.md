This submission presents **Trust Before Pass**, an open educational Jupyter notebook by **秦睿遥 (Fudan University; @QuRYous111)**.

Using a public SKY130 power-on-reset circuit and recorded SPICE traces, learners investigate why a completed simulation does not guarantee a meaningful delay measurement. Seven acts and four no-code tasks separate measurement validity, scalar bounds and an explicit functional contract, with predictions, controlled dependency comparisons, explanations and a held-out observation challenge.

The project includes an independently usable Python checker, integration through existing CACE hooks, a simple-script baseline, source/model pins, original licenses, replay instructions and static fallbacks. The default replay requires Python packages but no EDA toolchain.

The known upstream HVL fix is credited to its authors. T1 is a teaching assumption. Evidence covers one circuit and limited conditions; no automatic diagnosis, improved detection accuracy or measured learning benefit is claimed. Independent human reader evaluation has not yet been conducted. AI assistance is disclosed in NOTICE.

All added files are confined to `ISSCC27/submitted_notebooks/trust_before_pass/`. Start with `Trust_Before_Pass.ipynb` or the README. `SUBMISSION_VALIDATION.json` records the final notebook/test replay; historical CACE and browser evidence is labelled separately.
