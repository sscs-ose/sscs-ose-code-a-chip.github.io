# PrecisionFit -- Yosys synthesis script (guide section 4.2).
#
# Purpose: the open-source equivalent of a Genus "quick synth" pass. Given one
# generated RTL file, elaborate it, run the generic synthesis flow, map to
# Yosys's built-in cmos2 gate set, and write a JSON cell-count report. Used
# across hundreds of sweep candidates, so it is deliberately fast and
# target-independent; Week 4's real SKY130 numbers come from the OpenLane flow
# (`sky130.tcl` / `openlane_config.json`) instead.
#
# Usage:
#   yosys -c synth/yosys_synth.tcl -- <rtl_file> <top_module> <report_out.json>
#
# Licensed under the Apache License, Version 2.0. See the repo LICENSE file.

yosys -import

set rtl_file    [lindex $argv 0]
set top_module  [lindex $argv 1]
set report_file [lindex $argv 2]

if {$rtl_file eq "" || $top_module eq "" || $report_file eq ""} {
    puts "usage: yosys -c yosys_synth.tcl -- <rtl_file> <top_module> <report_out.json>"
    exit 1
}

read_verilog -sv $rtl_file
hierarchy -check -top $top_module

# generic, target-independent synthesis
synth -top $top_module
# technology mapping to the built-in cmos2 gate set (relative area comparisons)
abc -g cmos2

# `tee -o` writes the report to a file; a bare `> file` shell redirect is not
# a Tcl construct and silently does nothing inside a -c script.
tee -o $report_file stat -json
