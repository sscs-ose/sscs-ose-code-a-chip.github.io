# Research Question — FINAL / FROZEN

## Primary research question

> **Under a fixed and reproducible open-source backend implementation flow, how faithfully does a cycle-level GEMM accelerator model preserve the relative latency ordering and hardware-selection decisions among parameterized systolic-array configurations after RTL verification and post-route timing analysis?**

## Neutral hypothesis

Architecture-level cycle-count ordering may or may not be preserved after configuration-specific post-route timing is included. The experiment will measure preservation and margin transformation without presuming disagreement.

## What this project is not trying to prove

The project does not start from any of these conclusions:

- architecture simulators are wrong;
- larger arrays necessarily lose because of timing;
- 8×8 must lose to 4×4;
- a ranking reversal must exist;
- SKY130 behavior generalizes to modern advanced nodes;
- OpenLane/OpenROAD output equals measured silicon behavior.

## Main analytical questions

For each pre-registered workload:

1. Does the architecture model match the implemented RTL cycle semantics?
2. Which array configuration has the lowest architecture-level cycle count?
3. After using the frozen post-route timing result for each configuration, which configuration has the lowest implementation-aware latency?
4. Is the top-1 selection preserved?
5. For each pair of configurations, is the pairwise ordering preserved?
6. Does physical timing widen, narrow, or reverse the architecture-level decision margin?
7. What physical implementation evidence helps explain any observed changes?

## Contribution framing

The strongest defensible framing is a **decision-centric, fully reproducible audit** rather than a claim that cross-layer modeling itself is unprecedented.

Prior full-stack accelerator research already links architectural evaluation to implementation metrics. Model2GDS instead makes the hardware-selection decision and its evidence chain the explicit object of audit in a compact, open, notebook-reproducible experiment.
