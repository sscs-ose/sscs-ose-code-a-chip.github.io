# The voltage-reference controller

This is the third choice in the main lesson. It meets all seven primary sampled
requirements and costs more during ordinary storage. All choices use the same
published flip-flop, 10 fF load, normal write and matched supplies. These are
conventional circuits, not a new reset topology.

## Run the details

After [setup](README.md), use the environment's Python:

    python execute_sequence_notebook.py --reference
    python reproduce_reference.py

The first command runs four notebook cells on saved data, with no new SPICE.
The second checks all 56 saved records and makes ten new selected simulations.
`reference_reproduction_spec.json` declares the subset and expected diagnoses.
It repeats the working storage/analog energy comparisons, cold/hot action and
a cold storage trough. It is not a new full temperature matrix or held-out test.
Incomplete simulations keep their logs and have no functional verdict.

For one case:

    python reference_consumer.py --case hot_shallow --variant reference_supervisor
    python reference_consumer.py --case hot_shallow --variant original
    python reference_consumer.py --case cold_storage --group trough

`reference_circuit.generate(case, variant, max_step, group)` builds the deck and
source waveforms. Variants are `original`, `digital_guard` and
`reference_supervisor`. `group="trough"` replaces no-dip storage with a declared
1.62 V trough. It is a separate storage test. Smaller-step working energy pairs
use 1 us; the selected cold/hot action and trough runs use 2 us.

## How it works

The controller replaces the POR instance and uses the existing 3.3 V analog
rail. A 1:8 SKY130 PNP array and ideal resistors form a self-biased reference.
A startup circuit brings up the loop. Five high-voltage MOS devices compare
the reference with divided DVDD. A high-voltage NMOS interface and low-voltage
inverter drive reset. The complete candidate has no ideal reference, current
bias, comparator or forced internal state.

Separate characterization tests do use ideal currents. Nine samples cover
0.1, 1 and 5 uA nominal at -40, 27 and 125 C. The chosen 1 uA point gives
`K=10.13859221736199`, `R1=54423.78137568827 ohm` and
`R2=551780.5262949636 ohm`. The audit reconstructs this fit from the data.
The opposing temperature trends of VBE and delta-VBE explain the method.
These development samples are not an independent accuracy test.

With startup, the three reference-only traces settle to 1.22893, 1.23321 and
1.23687 V. They meet the chosen 1.20 to 1.26 V band by 15 ms through 20 ms.
Without startup, all three miss that test. This does not prove a stable off
equilibrium. Overshoot reaches 1.633 V, so startup is not precisely regulated.

The 220 kohm / 1 Mohm divider suggests a balance near 1.50 V. It explains a
design target, not a measured switching threshold or hysteresis specification.
The complete circuit traces determine whether reset works.

## Read the state and energy results

At -40 C, the original POR and guard never establish Q=1 in the saved test.
At 125 C, both establish Q=1, then miss reset after the 1.35 V dip.
The reference meets all seven primary requirements and preserves data in three
extra trough tests. All use TT models; they do not qualify a continuous range.

Reset requires both rails above 95% nominal, Q <= 0.36 V and reset-bar >= 1.71 V
within 12 ms after the ramp, with at least 1 ms hold. The prior write must be
measured. Storage instead requires Q >= 1.44 V and reset-bar >= 0.8 times
instantaneous DVDD throughout the post-write interval. These are our application
limits, not upstream guarantees.

The smaller-step 27 C storage comparison uses 40.31% more supplied energy than
the original, or 38.38% more than the guard. The separate analog interruption
uses 19.80% less than the original. Primary 125 C storage costs 157.59% more.
Startup and all four sources are counted. Failed circuits get no energy ranking.
Different histories do not define a lifetime usage mix.

## Evidence and source credit

Four raw archives keep nine characterizations, six reference-only starts and
41 complete-circuit runs. They retain failed results. They also keep the first
adapter's three generation errors and eight jobs not started, separately from
transistor results. [EVIDENCE.md](EVIDENCE.md) maps the files and checks.

The amplifier and startup declarations come from
[2AMLogic/sky130-bandgap](https://github.com/2AMLogic/sky130-bandgap/tree/49b2571054696bee9dd4e6bc074d7d9a47248181)
under Apache-2.0. Their geometry, contacts and multiplicities are retained.
The startup PNP has an explicit grounded fourth substrate terminal.
The source forced-node testbench is excluded. `reference_sources.json` pins the
source snapshot, license and added PNP models. The primitive commit is
`f62031a1be9aefe902d6d54cddd6f59b57627436`.
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) preserves all earlier credits.

Logic and comparator devices keep their documented default geometry; the
credited analog blocks use explicit source geometry. Added passives are ideal
and model leakage defaults are unchanged. Hardware retention, noise, hysteresis,
physical area and full process/voltage/temperature coverage are unverified.
