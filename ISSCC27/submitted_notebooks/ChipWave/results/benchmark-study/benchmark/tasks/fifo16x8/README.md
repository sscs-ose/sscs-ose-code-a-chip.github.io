# fifo16x8

`agent/` is the only task material exposed to an evaluated agent. `grader/`
contains the independent reference, held-out vectors and deliberate mutants.
CSIR checks the typed interface/contract attachment. Actual behavior is checked
by the executable acceptance scoreboard; no complete CSIR-to-RTL lowering is claimed.

Build another task with:
`python scripts/build_benchmark.py --family fifo --output NEW_DIRECTORY`.
Qualify this task with `python scripts/qualify_benchmark.py --task THIS_DIRECTORY`.
Physical qualification and area calibration are separate from these local checks.
