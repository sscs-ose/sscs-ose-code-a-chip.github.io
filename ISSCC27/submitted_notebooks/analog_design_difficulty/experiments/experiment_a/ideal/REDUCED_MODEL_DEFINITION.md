# Reduced-model study — definition

Date: 2026-10-29 JST; reader-facing text 2026-10-30 JST

Model: the two-state closed-loop driver of `../REDUCED_MODEL_ANALYSIS.md` (`model.py`), with an ideal switch. The values represent a small on-chip closed-loop source driving a switched-capacitive load. They are illustrative values for a qualitative mechanism model (a counterexample), not a fit to the SKY130 driver; no parameter is tuned toward a particular pass or fail result.

| Parameter | Value | Rationale |
|---|---:|---|
| `Ae` | 9 | about 20 dB of low-frequency error correction; a modest rather than high-gain amplifier |
| `τd` | 20 ns | an internal pole in the single-digit-MHz range, plausible for a compact generic on-chip source |
| `Rout` | 2.0 kΩ | finite output-path resistance; with `Ae` = 9 the low-frequency closed-loop output impedance is about 200 Ω |
| `Co` | 0.50 pF | output-node capacitance of devices and interconnect |
| `Cs` | 1.00 pF | a small sampling capacitor |
| switch | ideal | no charge injection, clock feedthrough, or added time constant |

The post-event output capacitance is `Co + Cs` = 1.50 pF in both tests, and `Rout (Co + Cs)` = 3.0 ns.

Voltages: target 0.9 V; a source range of 0.2–1.6 V for this demonstration; a common error limit of 2 mV (about 0.14 % of that range). These are the reduced model's own illustrative values, separate from the SKY130 brief.

Cases (all on the same time axis, 0 at the event):

- **input step** with `Cchar = Cs` connected: input 0.60 → 0.90 V, read at 80 ns;
- **zero-charge control**: the connection with `Vprev = Vtarget`, read at 30 ns;
- **connection of a charged capacitor**: `Vprev = Vtarget − 0.30 V`, read at 30 ns;
- **matched comparison** (Figure 3.3 of the notebook): the input step and the connection, with the input step chosen so that the initial output error equals the connection's initial output error (200 mV), the same 1.50 pF, and the same time axis; the metric is the largest difference of the output errors, each normalized to its initial error, over 0–40 ns;
- **acquisition times** 5–100 ns for the connection, reported descriptively;
- a local ±20 % check of each parameter, used as a sanity check, not as a tuning procedure.

No random search or optimizer is used. A pass or fail at any point is not a condition for keeping these values.
