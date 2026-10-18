> **v0.3 scope:** the native startup hook and previously recorded CLI runs below
> are unchanged historical evidence. The new `functional.py` monitor is an independent
> sidecar API, supplied with AVDD/POR and an explicit teaching contract. It is not
> represented by CACE's Error/Pass status. See `FUNCTIONAL_CONTRACT.md`.

# Full CACE integration: measured scope

The three completed integration checks use **unmodified CACE 2.13.0**, pinned to
`dedb5e0d30f5c286d36a1511b61fc81795bd24cf`, installed in an isolated Python environment.
Every installed CACE Python source was hash-compared against that checkout.

`cace_project.py` creates a current-format 5.2 datasheet and xschem wrappers, then executes:

```text
python -m cace <project>/cace/por.yaml --source schematic --jobs 1 --parallel-parameters 1 --sequential --no-plot --no-progress-bar
```

CACE regenerates the DUT with real xschem, substitutes testbench conditions, generates its
SPICE netlist, launches real ngspice, reads three numeric waveform columns, invokes
`cace_startup_gate.postprocess(results, conditions)`, evaluates the returned scalar, and writes
its own summary. No mocked executable, monkeypatch or modified CACE implementation is used.

| Case | CACE summary | CLI exit | Independent delay | Wall time | Process-tree peak |
|---|---|---:|---:|---:|---:|
| Corrected HVL, nonlinear resistor, 2 ms ramp | Pass | 0 | 1.125921 ms | 48.66 s | 585.75 MiB |
| Older HVL, nonlinear resistor, 2 ms ramp | Error | 1 | No valid delay | 74.80 s | 583.54 MiB |
| Corrected HVL, nonlinear resistor, 4 ms ramp | Pass | 0 | 1.128335 ms | 53.08 s | 587.16 MiB |

All three waveform hashes match the independently simulated archived evidence. These checks
do not increase the count of independent circuits, PVT points or operating scenarios.
Raw three-column files, logs, per-run conditions, CACE summaries, generated project snapshots
and sampled resource records are in `data/cace_integration/`. The snapshots preserve historical
absolute paths for provenance; use the generator to obtain relocatable paths for a new run.

## Validity semantics

The hook requires finite, strictly ordered samples covering the declared stop time and a rising
oscillator edge followed by a rising POR edge after 1.5 ms at 0.9 V. Missing events raise
`ValueError`; they are never replaced with zero or NaN. CACE catches the exception and returns
`ResultType.ERROR`. The old-library log contains `Missing por rising event in declared window`.
CACE Error is a general category: the retained exception supplies the measurement reason.
Valid delay values use seconds internally; the CACE specification expresses 0.5–2 ms.

The hook is waveform-only. It does not inspect solver logs or resource cutoffs and is not the
entire `evidence.py` provenance/log gate. The three recorded full-flow cases establish the
tested success/rejection behavior; they do not certify all CACE error paths or collated runs.
Collation is disabled. A fresh multi-corner sweep and circuit-wide integration are outside scope.

## Why the wrapper is necessary

This CACE version's direct `.spice` template branch is explicitly unimplemented. The generator
therefore uses native `.sch` templates with code blocks containing the pinned public SPICE
body and 24 explicit ports. Supporting subcircuits are emitted outside the DUT. xschem writes
the actual netlists consumed by ngspice. This is a **netlist-body schematic wrapper**, not a
recreated transistor schematic and not a migration of the original project's layout flow.
The source adaptation is validated here by identical measured waveforms, not by an LVS claim.

The local `pdk/sky130A` directory contains startup configuration only; actual device models
come from the bundled pinned source subset. It is not a complete open_pdks installation.
Native xschem 3.4.4 uses `lvs_netlist` to emit a top-level `.subckt`; both this option and the
newer `top_is_subckt` option are set. Absolute symbol references avoid CACE's Unix-style search
path separator on Windows. Raw SPICE code blocks are invisible to xschem's connectivity
checker, so it warns about wrapper pins; successful simulations and matching waveforms are
the validation evidence. Early setup failures are retained locally and listed separately.

The native ngspice executable is copied byte-for-byte into the generated project's `bin/`
under the name CACE expects. This is a real executable, not a behavior-emulating shim.
Configuration and the child xschem user profile remain inside the generated project.

See `REPRODUCIBILITY.md` for exact commands. No upstream PR has been submitted.
Sources: [CACE postprocessing interface](https://github.com/fossi-foundation/cace/blob/dedb5e0d30f5c286d36a1511b61fc81795bd24cf/docs/source/tutorials/custom_scripts.md),
[CACE ngspice implementation](https://github.com/fossi-foundation/cace/blob/dedb5e0d30f5c286d36a1511b61fc81795bd24cf/cace/parameter/parameter_ngspice.py).
