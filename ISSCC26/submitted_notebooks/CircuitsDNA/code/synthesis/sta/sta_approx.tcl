# ---- OpenSTA TCL (no -outfile, no redirect) ----

# Env & inputs
if {![info exists ::env(LIB_SYN)]} {
  set ::env(LIB_SYN) "/oscar/home/rqi7/pdk/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu9t5v0/lib/gf180mcu_fd_sc_mcu9t5v0__tt_025C_3v30.lib"
}
set lib $::env(LIB_SYN)

if {![info exists ::env(CLK_PERIOD)]} { set ::env(CLK_PERIOD) 10.0 }
set clock_period $::env(CLK_PERIOD)

set netlist "code/genetic_algorithm/output/netlist_output.sv"
set sdc     "code/synthesis/sta/constraints.sdc"

file mkdir "code/synthesis/sta"

puts "\[INFO] Using liberty: $lib"
puts "\[INFO] Netlist: $netlist"
puts "\[INFO] SDC: $sdc"

# Load design
read_liberty $lib
read_verilog $netlist

link_design approxMult_signed8x8
read_sdc $sdc

# --- Full reports print to stdout ---
puts "\n\[INFO] ----- report_checks (max) -----"
report_checks -path_delay max -fields {slew capacitance} -digits 3 -group_count 5

puts "\n\[INFO] ----- report_checks (min) -----"
report_checks -path_delay min -fields {slew capacitance} -digits 3 -group_count 5

# --- Compute WNS using API ---

set wns_val "NA"
if {[llength [info commands worst_slack]]} {
  # max = setup，min = hold；
  set wns_val [worst_slack -max]
}

set min_clock_period "NA"
if {[string is double -strict $wns_val] && [string is double -strict $clock_period]} {
  set min_clock_period [expr {$clock_period - $wns_val}]
}

if {$min_clock_period ne "NA"} {
  puts "\n\[INFO] WNS=$wns_val  Target_Clock_Period=$clock_period  Min_Clock_Period=$min_clock_period"
} else {
  puts "\n\[INFO] WNS=$wns_val (cannot compute min period; non-numeric clock_period or WNS)"
}

# Pass/Fail
set fail 0
if {$wns_val ne "NA" && $wns_val < 0} {
  puts "\[FAIL] WNS negative (timing NOT met)."
  set fail 1
} else {
  puts "\[PASS] Timing MET (WNS>=0)."
}

puts "\[INFO] STA complete."
if {$fail} { exit 2 }
exit 0
