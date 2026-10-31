# Reduced-model analysis: when are an input step and an output-port disturbance the same test?

Date: 2026-10-29 JST (analysis); reader-facing text 2026-10-30 JST

This note derives, without simulation, why an input-step test of a driver and the connection of a charged sampling capacitor are the same test for a one-state driver model and different tests for the smallest closed-loop model with an internal state. The numerical study of the reduced model is in `ideal/REDUCED_MODEL_DEFINITION.md` (definition) and `ideal/REDUCED_MODEL_RESULT.md` (result).

## 1. One-state driver: the two tests coincide

Model the driver as an ideal voltage source behind `Rout`, driving one capacitor `C`. For `t ≥ 0`,

```text
C dV/dt = (Vtarget − V) / Rout,     V(t) = Vtarget + (Vprev − Vtarget) exp[−t / (Rout C)].
```

- **Input step.** The capacitor is connected throughout; the source steps from `Vprev` to `Vtarget`. The capacitor starts at `Vprev` and follows the equation above.
- **Connection of a charged capacitor.** The source is already at `Vtarget`; a capacitor holding `Vprev` is connected through the same `Rout`. It starts at `Vprev` and follows exactly the same equation.

For equal capacitance and equal initial difference, the two waveforms are identical up to the time origin and the evaluation time. A fixed series switch resistance only replaces `Rout` by `Rout + Rsw`. With this model, a block test that passes while the connected test fails can only come from giving the two tests different time allowances.

## 2. Smallest model that separates them

Keep the switched sampling capacitor, and replace the one-state source by a generic closed-loop voltage source with one internal drive state `Vd` and one output node `Vout`:

```text
τd dVd/dt   = Vin + Ae (Vin − Vout) − Vd
C_T dVout/dt = (Vd − Vout) / Rout − Idist
```

`Ae` is a dimensionless error gain, `τd` the time constant of the internal state, `Rout` the output-path resistance, `C_T` the capacitance at the output node, and `Idist` a current drawn from the output port by the load. In the input-step test `C_T = Co + Cchar`; after the switch closes in the connected test `C_T = Co + Cs`; with `Cchar = Cs` the post-event capacitance is the same, so the distinction below does not come from a larger capacitance.

## 3. Two transfer paths with the same poles

Linearized about the settled target, with `C_T` fixed after the event, the common denominator is

```text
D(s) = (τd s + 1)(Rout C_T s + 1) + Ae.
```

- Input to output (`Idist = 0`): `Gin(s) = Vout/Vin = (1 + Ae) / D(s)`. The excitation enters the internal-state equation. (Code and data call this `Gcmd`.)
- Output-port disturbance to output (input held): `Zout(s) = −Vout/Idist = Rout (τd s + 1) / D(s)`. The excitation enters the output-node equation directly.

The poles are shared; the numerators, `(1 + Ae)` and `Rout (τd s + 1)`, are not. No time shift or change of allowed interval turns one response into the other.

## 4. How the sampling capacitor excites the output port

Before the switch closes in the connected test, `Vin = Vtarget`, `Vd` has settled, `Vout = Vtarget`, and `Cs` holds `Vprev`. With an ideal switch, charge sharing gives

```text
Vout(0+) = (Co Vtarget + Cs Vprev) / (Co + Cs),     Vd(0+) = Vd(0−).
```

The connection is an output-port charge disturbance applied while the internal state is settled. This is the intended sampling charge of `Vprev ≠ Vtarget`, not MOS charge injection or clock feedthrough. In the input-step test, the internal state and the output both start displaced. In target-referenced coordinates:

```text
input step:   [ΔVd, ΔVout] = [nonzero, nonzero]
connection:   [ΔVd, ΔVout] = [0, nonzero]
```

Even with the external voltage excursion matched, the two events excite different combinations of the driver's states.

## 5. Conclusion

For the one-state model the two tests are the same equation. For the two-state closed-loop model they are different tests: they enter at different ports, they have different transfer numerators, and they start from different internal states. The model adds only finite internal closed-loop dynamics, a finite output node, and finite output drive; it needs no switch charge injection, clock feedthrough, parasitics, mismatch, or particular transistor topology. Whether the difference matters numerically for a given circuit has to be measured: `ideal/REDUCED_MODEL_RESULT.md` for the reduced model, `sky130/RESULTS.md` for the SKY130 driver.
