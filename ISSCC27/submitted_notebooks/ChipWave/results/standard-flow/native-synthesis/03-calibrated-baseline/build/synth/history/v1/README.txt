Run from the repository root:
  python3 -B build/synth/run.py

Fixed Yosys: 0.69+77 (9ff27d29c), built-in read_slang.
Mapped netlist: build/synth/nebula_cpu_npu_top.v
Mapping scripts: build/synth/preflight.py generates synth.ys and abc.constr.
ABC uses area-priority map -a, buffer and 100 ns sizing; no sequential ABC or retiming.
Standalone OpenSTA: /eda/opensource/openroad/26Q3/bin/sta (3.1.0).
Timing script: build/synth/sta.tcl; unmodified frozen SDC; explicit Liberty Small wire-load model.
Pre-layout ideal clock; no extracted RC/SPEF or physical signoff claim.
Result overview and verdict: reports/synthesis/report.json
Metric contract: reports/synthesis/result_summary.json
Full setup/hold paths: reports/synthesis/setup_paths.rpt and hold_paths.rpt
Memory accounting: reports/synthesis/memory_mapping.json
Warning dispositions: reports/synthesis/warnings.json
Input and tool hashes: reports/synthesis/input_audit.json and tool_identity.json
Frozen gate receipts: reports/synthesis/gates.json and summary_gate.log

initial/ preserves the unbuffered experimental mapping and its raw STA evidence.
Only the top-level mapped netlist above is the selected final candidate.
The parent build directory is Git-ignored; stage this authorized directory with git add -f -- build/synth.
