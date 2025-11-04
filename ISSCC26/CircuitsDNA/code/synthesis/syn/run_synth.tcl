# ----------------------------------------------------------------------
# Yosys-in-Tcl synthesis wrapper (no external CLK_PERIOD required)
# ----------------------------------------------------------------------
yosys -import

# Design / paths
set ::env(DESIGN_NAME) "mult_8bits"
set ::env(RESULTS_DIR) "syn/"
file mkdir $::env(RESULTS_DIR)
set ::env(REPORTS_DIR) "$::env(RESULTS_DIR)/reports"
file mkdir $::env(REPORTS_DIR)
set ::env(PYTHON_EXE) "python3"
set ::env(SDC_FILE) "syn/mult_8bits.sdc"

# Fixed clock period here (ns). Change this value if needed.
set ::clock_period_ns 10.0
set ::clock_period_ps [expr {int($::clock_period_ns * 1000.0)}]
puts "INFO: Using fixed clock period = $::clock_period_ns ns ($::clock_period_ps ps)"

# Library / mapping (GF180). LIB_SYN must be provided by the caller.
if { ![info exists ::env(LIB_SYN)] } {
  puts {[WARN] LIB_SYN not provided via environment; quitting.}
  exit 1
}
set ::env(DFF_LIB_FILE) $::env(LIB_SYN)

# Cells for hilomap / buffering
set ::env(TIEHI_CELL_AND_PORT) {gf180mcu_fd_sc_mcu9t5v0__tieh_1 Z}
set ::env(TIELO_CELL_AND_PORT) {gf180mcu_fd_sc_mcu9t5v0__tiel_1 Z}
set ::env(MIN_BUF_CELL_AND_PORTS) {gf180mcu_fd_sc_mcu9t5v0__buf_1 A Z}

# Optional toggles (kept for compatibility)
set ::env(SYNTH_MEMORY_MAX_BITS) 0
set ::env(SYNTH_ARGS) ""
set ::env(SYNTH_OPERATIONS_ARGS) ""
set ::env(SYNTH_OPT_HIER) ""
set ::env(SYNTH_HIERARCHICAL) 0
set ::env(DONT_USE_CELLS) {}
set ::env(ADDER_MAP_FILE) ""
set ::env(LATCH_MAP_FILE) ""
set ::env(SYNTH_GUT) 0

# Helpers (light shims for upstream-style scripts)
proc env_var_exists_and_non_empty {name} {
  return [expr {[info exists ::env($name)] && $::env($name) ne ""}]
}
proc env_var_equals {name value} {
  if {![info exists ::env($name)]} { return 0 }
  return [expr {$::env($name) eq $value}]
}
proc env_var_or_empty {name} {
  if {[info exists ::env($name)]} { return $::env($name) } { return "" }
}
proc log_cmd {args} { puts "LOG_CMD: $args" ; eval $args }
proc convert_liberty_areas {} { }
proc keep_hierarchy {{args {}}} { }
proc extract_fa {} { }
proc env_var_exists {name} { return [info exists ::env($name)] }

# Read RTL (path relative to where this script is invoked)
read_verilog -sv ./verilog/modules/mult_8bits.sv
hierarchy -check -top $::env(DESIGN_NAME)

# ABC script with timing target
set abc_path $::env(RESULTS_DIR)/abc.script
set fh [open $abc_path w]

# Logic restructuring, retiming, delay-driven mapping and sizing
puts $fh "read_lib -X \"*aoi*\" -X \"*oai*\" -X \"*mux*\" -X \"*nor*\" \
        -X \"*and2_2*\" -X \"*and2_4*\" -X \"*and3*\" -X \"*and4*\" \
        -X \"*nand2_2*\" -X \"*nand2_4*\" -X \"*nand3*\" -X \"*nand4*\" \
        -X \"*or2_2*\" -X \"*or2_4*\" -X \"*or3*\" -X \"*or4*\" \
        -X \"*xor2_2*\" -X \"*xor2_4*\" -X \"*xor3*\" \
        -X \"*xnor2_2*\" -X \"*xnor2_4*\" -X \"*xnor3*\" \
        -X \"*inv_2*\" -X \"*inv_3*\" -X \"*inv_4*\" \
        -X \"*clk*\" \
        $::env(DFF_LIB_FILE)"
puts $fh "strash"
puts $fh "balance"
puts $fh "rewrite"
puts $fh "refactor"
puts $fh "rewrite -z"
puts $fh "balance"
puts $fh "dc2"
puts $fh "dch"
puts $fh "retime -D $::clock_period_ps"
puts $fh "dch"
puts $fh "map -D $::clock_period_ps"
puts $fh "topo"
puts $fh "stime -c"
puts $fh "upsize -c"
puts $fh "stime -c"
puts $fh "dnsize -c"
puts $fh "stime -c"

close $fh

# Minimal synth flow
proc run_simple_synth {} {
  synth -flatten -top $::env(DESIGN_NAME)
  dfflibmap -liberty $::env(DFF_LIB_FILE)

  # ABC with fixed timing target
  set abc_args [list -liberty $::env(DFF_LIB_FILE) -D $::clock_period_ps]
  abc -script $::env(RESULTS_DIR)/abc.script {*}$abc_args

  opt_clean -purge
  stat -liberty $::env(DFF_LIB_FILE)

  write_verilog -nohex -nodec $::env(RESULTS_DIR)/mult_8bits.syn.v
}

run_simple_synth
puts "INFO: Synthesis completed. Output: $::env(RESULTS_DIR)/mult_8bits.syn.v"
