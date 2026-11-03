V2 physical implementation of the frozen mapped netlist. Inputs are immutable; no RTL or synthesis is rerun here.
Historical V1, forced-row/core trials and interrupted WIP remain in history/v1-resume/, failures/, initial_geometry/ and geometry_repair/. Their measurements do not qualify V2.

Load the authorized environment in the same shell:
source /tmp/chipnebula-pinned-tools/env.sh
source /opt/rh/gcc-toolset-13/enable

Reproduce (2 threads, explicit authorized OpenROAD binary and native Sky130HD rows/tracks):
python3 -B build/pnr/run.py --rebuild
python3 -B build/pnr/export_and_sta.py
python3 -B build/pnr/check_geometry.py
python3 -B build/pnr/check_external_reset.py
python3 -B build/pnr/equivalence.py
python3 -B build/pnr/run_decks.py
/tmp/chipnebula-pinned-tools/bin/klayout -b -r build/pnr/read_decks.py
python3 -B build/pnr/write_summary.py
/tmp/chipnebula-public-repro-user37/bin/python build/pnr/check_exit_gates.py
python3 -B build/pnr/finalize_reports.py

The delivered RC ECO starts from the preserved electrical baseline, using the same environment above:
NEBULA_ECO_SOURCE=build/pnr/history/electrical-baseline/6_final.odb /tmp/chipnebula-pinned-tools/bin/openroad -no_init -exit -threads 2 build/pnr/prepare_rc_eco.tcl
python3 -B build/pnr/run.py --rebuild --from-stage grt
Then run export_and_sta.py and the remaining checks in the sequence above. reports/pnr/rc-comparison.json and guardband.json bind the measured first-round over-fix; final Liberty thresholds remain unchanged. Mid-route restoration automatically clears ordinary wires/guides before rebuilding GRT, preserving cells, CTS, PDN and diodes; checkpoint_restore_selfcheck.tcl validates that preparation on the preserved baseline into a temporary ODB.

The driver imports the mapped netlist into a new ODB without modifying build/synth, then executes installed ORFS floorplan, placement, CTS, global route, detailed route/diode repair, filler and extraction in that order. No guides from historical geometry are used. Detailed-route via-in-pin, process-node and PDN-via arguments inherit installed platform defaults.
Planned core and native legal-row bbox are independently derived and checked at placement/final export; legal-row equality with planning is not required. Pin layers, stock track phases, spacing, corner clearance and native placement checks remain mandatory.
Final STA export retains all signal-pin or Liberty-modeled instances including antenna diodes; independent STA reload uses the exported netlist, SPEF, SDC and identical TT Liberty. Same-snapshot hashes and raw reports bind all final numbers.
Only two active ODB checkpoint slots exist. checkpoints/latest.json records input/tool/database hashes, metrics and the recovery command. Stage ODBs remain required deliverables, not numbered checkpoint accumulation.

AC-POWER-AREA qualification (preserves the accepted physical snapshot):
python3 -B build/pnr/check_power_area.py
Read reports/pnr/power_area.json and per-workload reports under reports/pnr/power_area/. The source-bound authorized operator experiment is preserved in build/pnr/power_area/operator-evidence/, including commands, checker/model/program/runtime/trace hashes, gzip waveforms and the unselected sampling history. PnR reimports identical frozen Liberty models using Yosys, checks the model hierarchy and actual operands/reference/commit/output comparisons, reruns the supplied primary clock/reset waveform checker, verifies compressed and decoded hashes, and recomputes each workload's power using the authorized OpenROAD/2-thread environment. The clock is measured at 100 ns and 50% duty; power windows start at reset release and end at settled committed tohost completion. There is no weighted aggregate. No Verilator command is executed by this PnR entry point, and no tool permission is expanded. Verilator 5.048 gate replay is adopted from the immutable external experiment after binding. The former unavailable report and evidence remain under reports/pnr/history/power-area-unavailable/; check_power_area_unavailable.py preserves its original audit source. Reported 100% VCD coverage covers only tool-eligible pin classes, excluding sequential internal/hierarchical pins. These are Liberty-model estimates from zero-delay gate activity and extracted RC, not SDF/glitch/silicon-power or matched energy improvement. GDS and whole-project resource/development/evaluator/typed-adapter receipts remain separate.
KLayout 0.30.12 was measured in reports/pnr/klayout_version.log. Make receives that measured version to avoid repeated container launches for version probing; actual stream-out and fixed DRC/LVS decks are executed.
The current captured netlist includes the verifier-owned V2 reset waveform. check_external_reset.py verifies published bytes/hashes, clock/reset/memory-state measurements and formal input/runtime bindings, recording reports/pnr/external_reset_dependency.json. Missing evidence keeps execution failed even when numerical physical checks pass. General chip metal density and foundry/multi-corner/ERC/EM-IR qualifications remain unavailable where the frozen deck/model does not provide them. No tapeout-release claim.
