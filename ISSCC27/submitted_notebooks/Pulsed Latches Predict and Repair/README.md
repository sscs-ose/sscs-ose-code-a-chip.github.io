# Pulsed-Latch Pipelines: Timing Repair and Energy Tradeoffs

**Michael Ibrahim, IEEE Member**

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/MichaelIbrahim-GaTech/sscs-ose-code-a-chip.github.io/blob/main/ISSCC27/submitted_notebooks/Pulsed%20Latches%20Predict%20and%20Repair/Pulsed%20Latches%20Predict%20and%20Repair.ipynb)

An interactive Jupyter notebook exploring race-through in pulsed-latch pipelines, two circuit-level timing repairs, and their energy cost relative to flip-flop storage.

## Project overview

The notebook constructs a two-stage, four-bit incrementing pipeline using **IHP SG13G2 standard cells** and simulates it at transistor level with **ngspice**. The required behavior is:

```text
A[n] = input[n]
B[n] = (A[n−1] + 1) mod 16
```

When both latch banks are transparent, new data can propagate through both stages during the same pulse, violating the intended pipeline behavior. The notebook demonstrates this failure and compares two repairs:

- **Delay the data:** insert noninverting delay cells before the second latch bank.
- **Close earlier:** shorten the locally generated clock pulses.

A resettable D flip-flop implementation provides a reference under the same stimulus, output loading, and operating conditions. The comparison includes the energy of storage, logic, clock-pulse generation, drivers, and delay padding.

## Notebook contents

[Pulsed Latches Predict and Repair.ipynb](Pulsed%20Latches%20Predict%20and%20Repair.ipynb)

The notebook includes the circuit diagram, simulation setup, generated SPICE netlists, waveform analysis, transaction checks, and energy comparisons. Readers can change the input history, padding counts, and pulse-generator configuration to explore the tradeoffs.

## Experiments

1. **Observe race-through.** Apply the input sequence `(15, 0, 1)` to the unrepaired pipeline and inspect the incorrect transaction captured by the second bank.
2. **Repair the timing.** Compare delay padding `(2, 1, 1, 1)` against a shorter clock pulse. Inspect loaded pulse width, data departure, and returning glitches.
3. **Compare energy.** Evaluate both repaired pipelines and the DFF reference using the repeated workload `(0, 1, 3, 7, 15, 0, 8, 5)`.

## Results

Default conditions are **TT, 1.2 V, 25 °C, 100 MHz**, with **5 fF per output** and a **10 ps maximum timestep**.

| Implementation | Energy per transaction | Relative to DFF |
| --- | ---: | ---: |
| DFF reference | 378.77 fJ | Reference |
| Latches with delay padding | 504.99 fJ | +33.33% |
| Latches with shorter pulses | 410.16 fJ | +8.29% |

Both repairs pass the supplied transaction checks. Shortening the pulse consumes less energy than adding delay padding, but the DFF reference has the lowest energy in this comparison. The result illustrates why storage and timing-repair circuitry must be evaluated together.

## Validation and measurement

Transaction checks require valid outputs throughout **3–9.9 ns after each clock edge**, using 20% and 80% VDD logic thresholds. Timing analysis measures loaded pulse widths and detects data departures, including glitches that return to their original logic level.

Energy is integrated across all seven external sources: VDD, clock, reset, and four data inputs. Startup is excluded, and successive workload windows are checked for repeatability before a design is included in the energy ranking.

The results describe schematic simulations at the stated operating point. They do not establish correctness across all input histories or PVT corners. Measured data-departure versus gate-closure separation is an event-ordering metric, not a characterized latch hold margin.

## References

- [IHP Open PDK: pinned revision](https://github.com/IHP-GmbH/IHP-Open-PDK/tree/5e6d592e4002946a4616f798c357f0f3c06cf3b6)
- [VA-Models v2.2](https://github.com/dwarning/VA-Models/releases/tag/v2.2)
- [ngspice documentation](https://ngspice.sourceforge.io/docs.html)
- [Paik and Shin, *Pulsed-Latch Circuits to Push the Envelope of ASIC Design*, ISOCC 2010](https://doi.org/10.1109/SOCDC.2010.5682949)

## License

The notebook code, explanations, and diagram are released under the **MIT License**, copyright © 2026 Michael Ibrahim. The full license text is included in the notebook. Third-party cells and models retain their upstream licenses.
