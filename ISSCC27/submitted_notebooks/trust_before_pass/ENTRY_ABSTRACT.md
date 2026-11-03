# Trust Before Pass: An Evidence-Driven POR Investigation

秦睿遥 · Fudan University · QuRYous111

This open educational notebook asks learners to decide what a simulation result
actually establishes. Using a public SKY130 power-on-reset circuit, it separates
execution status, measurement validity, scalar limits and an explicitly declared
functional response contract. A missing event can make a delay undefined while
also violating a functional deadline; an unfinished observation may support neither
success nor failure.

The seven-act investigation combines recorded SPICE waveforms, prediction and
explanation tasks, selectable observation windows, matched dependency comparisons,
a negative control and an independent slow-supply observation challenge. A known
upstream HVL level-shifter correction restores valid extraction with both resistor
representations. That fix is credited to its authors, not presented as our discovery.

The independent checker exposes its assumptions and evidence, while an existing
CACE postprocessing hook supports the engineering workflow. A minimal Python
baseline agrees on all supported recorded cases; the claimed contribution is
reproducibility, explicit reasoning and teaching structure, not new fault-detection
accuracy. Core replay uses free Python tools without a full EDA installation.

Evidence covers one circuit and limited conditions. The new temporal requirement
is a teaching assumption rather than a proven original design specification.
Independent reader trial materials are prepared, but learner outcomes remain
unvalidated. No automatic diagnosis, research-paper readiness or measured learning benefit is claimed.

The browser interface provides offline, no-code controls with structured predictions, a guarded evidence/explanation sequence, local attempt export and a script-free worksheet. All choices use Python-precomputed checks of real recorded data; no browser-side SPICE or new engineering verdict algorithm is claimed. Independent reader evaluation remains pending.
