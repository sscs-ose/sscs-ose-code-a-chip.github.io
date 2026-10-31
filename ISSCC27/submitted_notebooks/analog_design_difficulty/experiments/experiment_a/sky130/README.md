# SKY130 transistor-level experiment — sample-and-hold front end

A two-stage Miller-compensated amplifier in unity-gain feedback drives a 1 pF hold capacitor through a CMOS transmission gate. The parent function is a single-ended sample-and-hold that must preserve a 0.6–1.2 V input with 10-bit-equivalent accuracy (`DESIGN_BRIEF.md`). All active devices use public SKY130 models; the simulator is ngspice.

## Records

| File | Role |
|---|---|
| `DESIGN_BRIEF.md` | authoritative definition: parent function, accuracy requirement and error budget, circuit, operating points, tests, metrics, readings |
| `DRIVER_DESIGN.md` | driver topology selection and sizing |
| `ENVIRONMENT.md` | simulator, PDK revision, smoke test |
| `SWITCH_WIDTH_STUDY.md` | connected acquisition at half and double switch width: definition and result |
| `SMALL_STEP_PORT_COMPARISON.md` | input step against output-port disturbance at 10–20 mV: definition and result |
| `HOLD_ERROR_DESIGN_RESPONSE.md` | held-sample error, one architectural response (dummy-switch compensation), and the width ladder: definition and result |
| `RESULTS.md` | all results, read against the brief |

Each study record states its definition and acceptance criteria, followed by its result.

## Netlists

| File | Role |
|---|---|
| `netlists/source_two_stage.spice` | the driver subcircuit (`src2`; file names keep the earlier word *source*) |
| `netlists/source_two_stage_2x.spice` | conditional variation: second stage at 200 µA |
| `netlists/tb_smoke_mos.spice` | MOS operating-point smoke test |
| `netlists/tb_dc.spice`, `tb_ac.spice` | driver bring-up: DC tracking, loop gain, input-to-output response (`Gcmd`), `Zout` |
| `netlists/tb_t0_command.spice` | test (a): input step with 1 pF at the driver output |
| `netlists/tb_t3_interface_model.spice` | test (b): charged `Cs` connected through an ideal switch and `R_if` |
| `netlists/tb_t1_connected.spice` | test (c): charged `Cs` connected through the transmission gate (gate size set by tokens) |
| `netlists/tb_t2_matched.spice` | test (m): input step with the gate already closed |
| `netlists/tb_switch_ron.spice`, `tb_switch_ron_narrow.spice` | transmission-gate DC on-resistance versus level |
| `netlists/tb_t4_hold.spice` | hold step when the gate opens |
| `netlists/tb_s1_input_step_rif.spice` … `tb_s4_connected_tg.spice` | small-step port comparison |
| `netlists/tb_t5_connected_dummy.spice`, `tb_t6_hold_dummy.spice` | test (c) and the hold step with dummy-switch compensation |

Netlists are plain SPICE. The only placeholders are the PDK library path, corner, temperature, and case parameters (`@VPREV@`, `@VCMD0@`, …); `spice_runner.py` writes the resolved netlists to `results/generated/sky130/<case>/` (not part of the package).

## Reproduce

From the folder root, with ngspice and a SKY130A installation (default `~/.volare/sky130A`; otherwise set `PDK_ROOT`):

```bash
uv run python experiments/experiment_a/sky130/run_sky130.py     # brief, tests, checks, switch width
uv run python experiments/experiment_a/sky130/run_followup.py   # small-step and held-sample studies
```

`run_followup.py` reads `results/data/sky130_summary.json`, so it runs second. Together they take about 12 minutes on 12 threads (each ngspice process spends most of its time loading the SKY130 library). `SKY130_REUSE=1` reuses completed cases whose resolved netlists are unchanged, which is useful for regenerating figures only.

Outputs: `results/data/sky130_*.{csv,json}` and `results/figures/figure_sky130_*.{png,svg}`. In the JSON files tests are keyed `a`, `b`, `c`, `m` and operating points `target/previous` (for example `0.6/1.2`).

## Scope and limitations

- Ideal `Cc`, `Rz`, `Cs`, `Cchar`, and bias reference; no layout, extraction, or mismatch; 27 °C, with `ss`/`ff` only for the full-scale transitions.
- The circuit is a public teaching vehicle sized from textbook relations, not optimized, and not derived from any private design.
- SKY130 is the reproducibility vehicle; the engineering lessons are not process-specific.
