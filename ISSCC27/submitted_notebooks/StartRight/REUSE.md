# Use the reset check on your circuit

Start with the last code cell in [StartRight.ipynb](StartRight.ipynb). It maps
the new latch trace to a one-output example. It does not run another simulation.

For another circuit, define the state that reset should produce. Use normal
inputs to write a different reachable state. Measure that state before the
supply event. Also test a history with no event, where data should stay stored.

## The monitor interface

`reset_contract.evaluate` takes a time vector and named waveform signals.
The signal names are yours; the monitor does not assume a circuit or file format.

| Input | Meaning |
|---|---|
| `Band("q", upper=.36)` | q must be at most 0.36 V |
| `Band("q", lower=1.44)` | q must be at least 1.44 V |
| `Window(id, start_s, ramp_end_s, stop_s)` | The event and observation interval |
| `state_bands` | Voltage limits for the desired state |
| `release_bands` | Voltage limits for released reset and a ready supply |
| `state_delay_s`, `release_delay_s` | Deadlines after the supply ramp |
| `hold_s` | How long the result must remain valid |
| `precondition_interval`, `prior_bands` | When and how to verify the prior state |
| `alternate_bands` | The different state that reset should change |

Limits are absolute voltages. Convert nominal-voltage fractions in your adapter.
The monitor interpolates each bound before combining results. It checks the
declared supply history and full observation interval. Missing or nonfinite
vectors, repeated time points and incomplete deadline/hold coverage are rejected.
Your adapter must also check the circuit's initialization and normal inputs.

## Read the result correctly

| Field | Meaning |
|---|---|
| `observed_pass` | State and reset-release limits were met |
| `declared_precondition_verified` | The expected prior state was measured |
| `alternate_state_exercised` | The different state was present before the event |
| `sampled_restoration_observed` | The checks support restoration from that state |

A retained-state test can pass with restoration coverage false. An incomplete
simulation is `unresolved`, with `observed_pass=None`. It is never a circuit pass
or failure. A complete simulation can show a valid circuit failure.
`check_reset_contract.py` contains a hand-computed one-node example and rejection
checks. These are software tests, not transistor experiments.

## Count energy fairly

`source_work` takes voltage/current pairs for every independent source.
SPICE current is positive into a source's positive terminal, so supplied power
is `-V*I`. The function keeps delivered energy, returned energy and net work
separate. Zero-volt current probes do no work.

Compare only working circuits with the same load, supply history, prior-state
requirement and observation interval. Count startup and input sources.
`sequence_analysis.explain` compares only the working startup interval before
the write. A failed full RC sequence is not a low-energy design alternative.

## Supported fresh commands

After [setup](README.md), use the environment's Python.

| Command or call | Supported scope |
|---|---|
| `run_sequence(corner="tt", low_V=.9, command=True)` | Three named latch variants; TT or SF, both at 27 C; finite dips from 0 to 1.8 V |
| `python reset_sequence.py --retain-state` | Same latch history without the ordinary write |
| `python external_consumer.py --detector-scale 4` | Published single-rail flip-flop; TT/27 C; finite detector scales 1, 2 or 4 |
| `python por_consumer.py --event digital_zero` | Published dual-rail POR and flip-flop; TT/27 C |
| `python guard_consumer.py --condition half_depth` | Fixed original/guard challenge histories |
| `python reference_consumer.py --case hot_shallow --variant reference_supervisor` | Fixed reference-controller histories |

A changed dip is one new finite test, not proof of a continuous range.
The individual external, POR, guard and reference commands exit 0 when simulation
completes, including a circuit miss, and 2 when it is incomplete. The reproduction
scripts also check their expected outcomes. [EVIDENCE.md](EVIDENCE.md) lists them.

The single-rail adapter uses the same clock pulse with D=0 or D=1, then returns D
to zero. Its no-dip control must keep Q=1. The finite sizing code excludes scales
with missing or failing controls before comparing working energy. It makes the
same choice as a competent conventional script.

For dual-rail tests, `por_circuit.py` defines both supply waveforms and the column
order. `por_spec.json` declares numerical settings and time budget. Both rails
and both input sources are counted. `powered_reset.py` adds a separate 100 ns
powered-reset observation; that teaching check is not a cell timing guarantee
or a necessary condition for every observed restoration.

## Check data and sources

Each fresh run keeps a record, raw waveforms, circuit decks and logs. The record
contains source hashes. `sequence_evidence.py` and the other evidence modules
regenerate saved decks and repeat measurements without SPICE.

The published flip-flop keeps its source schematic's default zero diffusion
geometry and NRD/NRS. The POR uses unchanged typical passive coefficients.
`por_models.py` maps the old `mrdn_hv`/`mrdp_hv` resistor names to foundry models,
following prior Open PDKs work. Their old bulk pin is unused because the current
resistor models have two terminals. Only the POR's final deck-level `.end` is
removed during assembly. Source device declarations stay unchanged.

The guard adds nine MOS devices and ideal passives. The isolated DC adapter
holds the POR input high; it cannot prove full-system reset action.
[APPLICABILITY.md](APPLICABILITY.md) explains those tests.
[REFERENCE.md](REFERENCE.md) gives the reference circuit and source credits.
Gate tunnelling is disabled in the pinned models. None of these interfaces
finds every internal state or proves hardware retention.
