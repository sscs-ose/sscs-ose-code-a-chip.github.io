# Frozen Phase 2 post-route fixed-layout STA-derived frequency methodology.
# This script reports raw timing only; Python performs the frequency derivation.
proc fail {message} {
    puts stderr "PHASE2_R2R_STA_FAIL $message"
    exit 1
}
foreach variable {PHASE2_STA_ENV PHASE2_NETLIST PHASE2_SPEF PHASE2_SDC PHASE2_DESIGN PHASE2_RUN_PREFIX} {
    if {![info exists ::env($variable)]} { fail "missing $variable" }
}
set saved_env $::env(PHASE2_STA_ENV)
set expected_netlist $::env(PHASE2_NETLIST)
set expected_spef $::env(PHASE2_SPEF)
set expected_sdc $::env(PHASE2_SDC)
set expected_design $::env(PHASE2_DESIGN)
set run_prefix $::env(PHASE2_RUN_PREFIX)
foreach artifact [list $saved_env $expected_netlist $expected_spef $expected_sdc] {
    if {![file isfile $artifact]} { fail "missing artifact $artifact" }
    if {[string first "$run_prefix/" $artifact] != 0} { fail "artifact from another run: $artifact" }
}
if {[string first "openroad-stapostpnr" $saved_env] < 0} { fail "environment is not post-route STA" }
if {[string first "openroad-rcx" $expected_spef] < 0} { fail "parasitics are not final route extraction" }
source $saved_env
set corner max_ss_100C_1v60
if {$::env(DESIGN_NAME) ne $expected_design} { fail "design identity mismatch" }
if {$::env(CLOCK_PORT) ne "clk" || $::env(CLOCK_PERIOD) != 20.0} { fail "clock recipe mismatch" }
if {$::env(CURRENT_NETLIST) ne $expected_netlist} { fail "final netlist environment mismatch" }
if {[dict get $::env(CURRENT_SPEF) max_*] ne $expected_spef} { fail "SPEF environment mismatch" }
# SAVE_SDC is an intended output name and need not exist. Use the actual SDC
# view carried by the final state, alongside the final fill-insertion netlist.
set netlist_sdc [string range $expected_netlist 0 end-5].sdc
if {$expected_sdc ne $netlist_sdc} { fail "SDC does not accompany final routed netlist" }
if {$::env(OPENLANE_SDC_IDEAL_CLOCKS) != 0} { fail "saved timing environment has ideal clocks" }
if {[string first "/$corner/" $saved_env] < 0} { fail "wrong saved environment corner" }
set_cmd_units -time ns -capacitance pF -current mA -voltage V -resistance kOhm -distance um
set sta_report_default_digits 6
define_corners $corner
foreach lib [dict get $::env(LIB) *_ss_100C_1v60] {
    if {![file isfile $lib]} { fail "missing Liberty $lib" }
    read_liberty -corner $corner $lib
    puts "PHASE2_STA_LIBRARY $lib"
}
read_verilog $expected_netlist
link_design $expected_design
read_sdc $expected_sdc
read_spef -corner $corner $expected_spef
set clocks [get_clocks clk]
if {[llength $clocks] != 1} { fail "missing or ambiguous clk" }
set period [get_property [lindex $clocks 0] period]
if {$period != 20.0} { fail "SDC clock period mismatch" }
puts "PHASE2_STA_ENV $saved_env"
puts "PHASE2_STA_NETLIST $expected_netlist"
puts "PHASE2_STA_SPEF $expected_spef"
puts "PHASE2_STA_SDC $expected_sdc"
puts "PHASE2_STA_DESIGN $expected_design"
puts "PHASE2_R2R_CORNER $corner"
puts "PHASE2_R2R_CLOCK_PERIOD_NS $period"
set starts [all_registers -clock_pins]
set ends [all_registers -data_pins]
if {[llength $starts] == 0 || [llength $ends] == 0} { fail "no internal sequential endpoints" }
set paths [find_timing_paths -from $starts -to $ends -path_delay max -sort_by_slack \
    -group_count 1000 -endpoint_count 1 -corner $corner]
if {[llength $paths] == 0} { fail "no internal register-to-register setup paths" }
set worst 1.0e99
foreach path $paths {
    set slack [get_property $path slack]
    if {![string is double -strict $slack] || [regexp -nocase {nan|inf} $slack]} { fail "nonfinite setup slack" }
    if {$slack < $worst} { set worst $slack }
}
report_checks -from $starts -to $ends -path_delay max -sort_by_slack \
    -group_count 1000 -endpoint_count 1 -fields {slew cap input nets fanout} \
    -format full_clock_expanded -corner $corner
puts "PHASE2_R2R_PATH_COUNT [llength $paths]"
puts "PHASE2_R2R_SETUP_WS_NS $worst"
if {20.0 - $worst <= 0.0} { fail "nonpositive estimated period" }
puts "PHASE2_R2R_STA_PASS"
exit
