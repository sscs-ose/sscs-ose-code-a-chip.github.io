# PrecisionFit -- OpenROAD + SKY130 physical implementation (Week 4, OPTIONAL).
#
# This is the "real numbers" flow: Yosys with the actual SKY130 standard-cell
# library, then OpenROAD floorplan -> place -> CTS -> route, then OpenSTA
# timing signoff. It is the open-source equivalent of Innovus + Tempus.
#
# IMPORTANT (guide section 6): final layout is "encouraged but not required"
# for the Code-a-Chip submission. This whole step is optional and is only run
# for the THREE headline configs, never for the full sweep -- the sweep's job
# (finding the frontier) is already done with the generic-cell metric.
#
# Usage (either):
#   # A. Let OpenLane2 drive the whole sequence (recommended -- matched tool
#   #    versions and a wired-up PDK; this is the path that avoids the
#   #    version-mismatch pain the guide warns about):
#   #      openlane synth/openlane_config.json --run-tag <tag>
#   #
#   # B. Drive OpenROAD directly with this script (assumes the PDK env vars
#   #    from OpenLane/OpenROAD-flow-scripts are set):
#   #      openroad -exit synth/sky130.tcl
#
# Licensed under the Apache License, Version 2.0. See the repo LICENSE file.

# ---- configuration ---------------------------------------------------------
set design_name  "fir_best_uniform"          ;# override per headline config
set rtl_file     "../src/verilog/rtl/fir_best_uniform.v"
set top_module   "$design_name"
set liberty_file "$::env(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
set sdc_file     "constraints.sdc"
set report_dir   "../results/pareto"

puts "== PrecisionFit OpenROAD/SKY130 flow: $design_name =="

# ---- 1. synthesis to the real SKY130 library ------------------------------
# OpenLane2 performs this internally; when driving OpenROAD directly, run the
# Yosys mapping first (dfflibmap + abc -liberty against the SKY130 .lib) and
# read the resulting netlist here:
#   yosys -p "read_verilog -sv $rtl_file; synth -top $top_module; \
#             dfflibmap -liberty $liberty_file; abc -liberty $liberty_file; \
#             write_verilog $design_name.sky130.v"
read_liberty $liberty_file
read_verilog "${design_name}.sky130.v"
link_design $top_module
read_sdc $sdc_file

# ---- 2. floorplan -> place -> CTS -> route --------------------------------
# Die area is deliberately generous (500 x 500 um is very roomy for a
# 9-multiplier FIR) so placement is not fighting congestion unrelated to the
# accuracy-vs-area comparison. Tightening it to a "which design fits in a
# smaller die" sub-result is a stretch goal, not core.
initialize_floorplan -die_area {0 0 500 500} -core_area {10 10 490 490} \
    -site unithd
make_tracks
place_pins -random -hor_layers met3 -ver_layers met2
global_placement -density 0.5
detailed_placement
improve_placement
clock_tree_synthesis -buf_list "sky130_fd_sc_hd__clkbuf_4"
detailed_placement
global_route
detailed_route

# ---- 3. timing + area signoff ---------------------------------------------
report_checks -path_delay max -format full_clock_expanded > "$report_dir/${design_name}_timing.rpt"
report_design_area  > "$report_dir/${design_name}_area.rpt"
report_power        > "$report_dir/${design_name}_power.rpt"

# NOTE ON POWER (guide section 6.4): report_power above is NOT a measured
# energy claim. Without switching-activity annotation (a VCD/SAIF from the
# Verilator/Icarus runs on representative signals) the numbers are
# assumptions-only, so the notebook must not claim energy savings from area.
puts "== done: $design_name (see $report_dir) =="
