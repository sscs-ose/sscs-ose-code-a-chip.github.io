# Reproduce the paired throughput measurement

Run commands from the package root using Python 3.12. The recorded simulator was Icarus Verilog 13.0. Install iverilog and vvp; paths can be selected using IVERILOG_EXE and VVP_EXE. The RTL includes the endpoint buffer simulation models.

## Inspect the inputs first

```sh
python reproduction/reproduce_performance.py
```

This checks all source-file hashes, regenerates the performance testbench from design/verif/tb_lb.sv in memory, reconstructs nine vectors, and computes the original workload digest in the original order. Both archived records must match these identities.

- Reference RTL: reproduction/reference/rtl/lb_feedback.sv.
- Two-tier RTL: design/rtl/lb_feedback.sv.
- Original generated checker: reproduction/tb_folding_perf.sv.
- Original measurement source: reproduction/original/logic_folding_performance.py.
- Portable copy: reproduction/performance.py. Only platform command/logging helpers were replaced with standard-library functions; measurement, stimuli and comparison logic are retained.
- Fixed input schedules: reproduction/stimulus/.
- Recorded arithmetic vectors: reproduction/vectors/.

## Explicit full regeneration

```sh
python reproduction/reproduce_performance.py --run build/paired-reproduction
```

The output directory must be new. Both runs use the same checker and event files. The runner compiles each RTL and executes 162 scenarios per design, with four workers and a 600-second per-case timeout. It writes reference/performance.json, two-tier/performance.json, simulator logs, receipts and comparison.json under the chosen output directory. A tool failure or missing pass marker stops acceptance. New counters are compared with all archived metrics, including maximum latency.

In v4, the portable entry completed all 324 RTL simulations in a fresh archive extraction, standard-library Python environment and minimal subprocess environment on the same host, using the recorded installed Icarus tools. All scenario keys, counters, maximum latency and input digests match the archived experiment. See ../portability/result.json and the complete logs/receipts in ../portability/paired/. Source-build instructions cover obtaining the fixed tools elsewhere; another operating-system build remains a separate check.

## Measurement contract

Each scenario accepts 1,100 jobs. The first 100 warm up the circuit. Completion intervals span final output acceptance of job 99 to job 1099; supply intervals span the last memory response of those same jobs. Useful bytes count jobs 100–1099, giving 1000 × 8 × K bytes. Maximum latency is the largest command-acceptance-to-output-completion interval among those 1,000 jobs.

The matrix is K = 4/16/64 × three repair mappings × seeds 11/23/37 × fast/jitter/burst service × always-ready/periodically-stalled output = 162 scenarios. Ready events use a fixed cycle schedule; response latency uses lane and request ordinal. Arithmetic payloads are fixed per seed and job length. The testbench checks arithmetic, ordering, request totals and useful response totals before printing its pass marker.

All elapsed cycle totals, useful bytes and latency values remain available per scenario. The plotted group summaries preserve the complete underlying records.

Fixed public dependency sources and build instructions: [DEPENDENCIES](../DEPENDENCIES.md).

Recorded full-campaign runtime: 86.9 minutes with four workers on the recorded host.

v5 reuses the completed campaign and adds GDS export/illustration only.
