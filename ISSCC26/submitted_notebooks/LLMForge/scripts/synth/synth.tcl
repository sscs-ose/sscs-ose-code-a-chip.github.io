source $::env(SCRIPTS_DIR)/synth_preamble.tcl

# set buffering $::env(SYNTH_BUFFERING)
# set sizing $::env(SYNTH_SIZING)

set buffering 1
set sizing 1

# input pin cap of IN_3VX8
# set max_FO $::env(MAX_FANOUT_CONSTRAINT)
# set max_TR 0
# if { [info exist ::env(MAX_TRANSITION_CONSTRAINT)]} {
#     set max_TR [expr {$::env(MAX_TRANSITION_CONSTRAINT) * 1000}]; # ns -> ps
# }

set max_FO 10
set max_TR 0

# Generic synthesis
set final_synth_args $::env(SYNTH_ARGS)
# if {[info exists ::env(SYNTH_HIERARCHICAL)] && $::env(SYNTH_HIERARCHICAL) != 1} {
#   puts "Flattening the hierarchy."
#   append final_synth_args " -flatten"
# }
# Check if hierarchical synthesis is enabled

hierarchy -check -top $::env(DESIGN_NAME)

if {[info exists ::env(SYNTH_HIERARCHICAL)] && $::env(SYNTH_HIERARCHICAL) == 1} {
    puts "Performing hierarchical synthesis."
    append final_synth_args " -hier"
    synth  -top $::env(DESIGN_NAME)
} else {
    puts "Flattening the hierarchy."
    append final_synth_args " -flatten"
    synth  -top $::env(DESIGN_NAME) -flatten

}

# synth  -top $::env(DESIGN_NAME) {*}$final_synth_args
# synth  -top $::env(DESIGN_NAME) -hier


if { [info exists ::env(USE_LSORACLE)] } {
    set lso_script [open $::env(OBJECTS_DIR)/lso.script w]
    puts $lso_script "ps -a"
    puts $lso_script "oracle --config $::env(LSORACLE_KAHYPAR_CONFIG)"
    puts $lso_script "ps -m"
    puts $lso_script "crit_path_stats"
    puts $lso_script "ntk_stats"
    close $lso_script

    # LSOracle synthesis
    lsoracle -script $::env(OBJECTS_DIR)/lso.script -lso_exe $::env(LSORACLE_CMD)
    techmap
}

# Optimize the design
opt -purge

# Technology mapping of adders
if {[info exist ::env(ADDER_MAP_FILE)] && [file isfile $::env(ADDER_MAP_FILE)]} {
  # extract the full adders
  extract_fa
  # map full adders
  techmap -map $::env(ADDER_MAP_FILE)
  techmap
  # Quick optimization
  opt -fast -purge
}

# Technology mapping of latches
if {[info exist ::env(LATCH_MAP_FILE)]} {
  techmap -map $::env(LATCH_MAP_FILE)
}

# Technology mapping of flip-flops
# dfflibmap only supports one liberty file
if {[info exist ::env(DFF_LIB_FILE)]} {
  dfflibmap -liberty $::env(DFF_LIB_FILE)
} else {
  dfflibmap -liberty $::env(DONT_USE_SC_LIB)
}
opt

set constr [open $::env(OBJECTS_DIR)/abc.constr w]
puts $constr "set_driving_cell $::env(ABC_DRIVER_CELL)"
puts $constr "set_load $::env(ABC_LOAD_IN_FF)"
close $constr

# # Mapping parameters
# set A_factor  0.00
# set B_factor  0.88
# set F_factor  0.00

# # Assemble Scripts (By Strategy)
# set abc_rs_K    "resub -K "
# set abc_rs      "resub"
# set abc_rsz     "resub -z"
# set abc_rf      "drf -l"
# set abc_rfz     "drf -l -z"
# set abc_rw      "drw -l"
# set abc_rwz     "drw -l -z"
# set abc_rw_K    "drw -l -K"
# # if { $::env(SYNTH_ABC_LEGACY_REFACTOR) == "1" } {
# #     set abc_rf      "refactor"
# #     set abc_rfz     "refactor -z"
# # }
# # if { $::env(SYNTH_ABC_LEGACY_REWRITE) == "1" } {
# #     set abc_rw      "rewrite"
# #     set abc_rwz     "rewrite -z"
# #     set abc_rw_K    "rewrite -K"
# # }
# set abc_b       "balance"

# set abc_resyn2        "${abc_b}; ${abc_rw}; ${abc_rf}; ${abc_b}; ${abc_rw}; ${abc_rwz}; ${abc_b}; ${abc_rfz}; ${abc_rwz}; ${abc_b}"
# set abc_share         "strash; multi -m; ${abc_resyn2}"
# set abc_resyn2a       "${abc_b};${abc_rw};${abc_b};${abc_rw};${abc_rwz};${abc_b};${abc_rwz};${abc_b}"
# set abc_resyn3        "balance;resub;resub -K 6;balance;resub -z;resub -z -K 6;balance;resub -z -K 5;balance"
# set abc_resyn2rs      "${abc_b};${abc_rs_K} 6;${abc_rw};${abc_rs_K} 6 -N 2;${abc_rf};${abc_rs_K} 8;${abc_rw};${abc_rs_K} 10;${abc_rwz};${abc_rs_K} 10 -N 2;${abc_b} ${abc_rs_K} 12;${abc_rfz};${abc_rs_K} 12 -N 2;${abc_rwz};${abc_b}"

# set abc_choice        "fraig_store; ${abc_resyn2}; fraig_store; ${abc_resyn2}; fraig_store; fraig_restore"
# set abc_choice2      "fraig_store; balance; fraig_store; ${abc_resyn2}; fraig_store; ${abc_resyn2}; fraig_store; ${abc_resyn2}; fraig_store; fraig_restore"

# set abc_map_old_cnt			"map -p -a -B 0.2 -A 0.9 -M 0"
# set abc_map_old_dly         "map -p -B 0.2 -A 0.9 -M 0"
# set abc_retime_area         "retime -D {D} -M 5"
# set abc_retime_dly          "retime -D {D} -M 6"
# set abc_map_new_area        "amap -m -Q 0.1 -F 20 -A 20 -C 5000"

# set abc_area_recovery_1       "${abc_choice}; map;"
# set abc_area_recovery_2       "${abc_choice2}; map;"

# set map_old_cnt			    "map -p -a -B 0.2 -A 0.9 -M 0"
# set map_old_dly			    "map -p -B 0.2 -A 0.9 -M 0"
# set abc_retime_area   	"retime -D {D} -M 5"
# set abc_retime_dly    	"retime -D {D} -M 6"
# set abc_map_new_area  	"amap -m -Q 0.1 -F 20 -A 20 -C 5000"

# if {$buffering==1} {
#     set max_tr_arg ""
#     if { $max_TR != 0 } {
#         set max_tr_arg " -S ${max_TR}"
#     }
#     set abc_fine_tune		"buffer -N ${max_FO} ${max_tr_arg};upsize {D};dnsize {D}"
# } elseif {$sizing} {
#     set abc_fine_tune       "upsize {D};dnsize {D}"
# } else {
#     set abc_fine_tune       ""
# }

# set abc_script "read design.blif;fx;mfs;strash;${abc_rf};${abc_resyn2};${abc_retime_dly}; scleanup;${abc_map_old_dly};retime -D {D};&get -n;&st;&dch;&nf;&put;${abc_fine_tune};stime -p;print_stats -m;write output.blif"

# set max_fanout $::env(ABC_MAX_FANOUT)                 ;# Maximum fan-out for buffer insertion
# set map_effort $::env(ABC_MAP_EFFORT)                 ;# Mapping effort (higher = prioritize delay)
# set arec_effort $::env(ABC_AREC_EFFORT)               ;# Area recovery effort (higher = max effort)
# set clock_period $::env(ABC_CLOCK_PERIOD_IN_PS)       ;# Clock period for retiming in ps
# set retime_mode 6                                     ;# Retiming mode (6 = minimize area, 5 = minimize delay)

# Set default values for the variables if not provided by the environment
if {![info exists ::env(ABC_MAX_FANOUT)]} {
    set max_fanout 10 ;# Default maximum fan-out for buffer insertion
} else {
    set max_fanout $::env(ABC_MAX_FANOUT)
}

if {![info exists ::env(ABC_MAP_EFFORT)]} {
    set map_effort 0.5 ;# Default mapping effort (higher = prioritize delay)
} else {
    set map_effort $::env(ABC_MAP_EFFORT)
}

if {![info exists ::env(ABC_AREC_EFFORT)]} {
    set arec_effort 0.6 ;# Default area recovery effort (higher = max effort)
} else {
    set arec_effort $::env(ABC_AREC_EFFORT)
}

if {![info exists ::env(ABC_CLOCK_PERIOD_IN_PS)]} {
    set clock_period 1000 ;# Default clock period for retiming in ps
} else {
    set clock_period $::env(ABC_CLOCK_PERIOD_IN_PS)
}

set constr1 [open $::env(OBJECTS_DIR)/abc_universal.script w]
# puts $constr1 "fx\nmfs\nstrash\n${abc_rf}\n ${abc_resyn2} \n${abc_retime_dly}\nscleanup\n${abc_map_old_dly}\nretime -D {D}\n&get -n \n &st\n&dch\n&nf\n&put\n ${abc_fine_tune}\n stime -p \n print_stats -m"
# puts $constr1 "strash \ndch \nmap -B 0.6 \ntopo \nstime -c \nbuffer -N 5 \nupsize -c \ndnsize -c"
# puts $constr1 "&get -n \n&st \n&dch \n&nf \n&put \nbuffer -c \ntopo \nstime -c \nupsize -c \ndnsize -c"

puts $constr1 "strash"; # structural hashing 
puts $constr1 "dch"; # delay-aware combinational optimization
puts $constr1 "map -B $map_effort -A $arec_effort"; # technology mapping
puts $constr1 "retime -D $clock_period -M 6";

puts $constr1 "topo"; # topological cleanup
puts $constr1 "stime -c\n"; # report timing
puts $constr1 "buffer -N $max_fanout";

# puts $constr1 "if -g -K 4";  # Optimize paths with gate fan-in <= 4
# puts $constr1 "dch -G\n";      # Consider larger gates for timing improvements

puts $constr1 "upsize -c\n"; # increase cell drive strength
puts $constr1 "dnsize -c\n"; # decrease cell drive strength

close $constr1

set abc_script $::env(OBJECTS_DIR)/abc_universal.script
# set abc_script $::env(SCRIPTS_DIR)/abc_speed.script

# Technology mapping for cells
# ABC supports multiple liberty files, but the hook from Yosys to ABC doesn't
if {[info exist ::env(ABC_CLOCK_PERIOD_IN_PS)]} {
  puts "\[FLOW\] Set ABC_CLOCK_PERIOD_IN_PS to: $::env(ABC_CLOCK_PERIOD_IN_PS)"
  set log_file $::env(OBJECTS_DIR)/abc_execution.log
  abc -D [expr $::env(ABC_CLOCK_PERIOD_IN_PS)] \
      -script $abc_script \
      -liberty $::env(DONT_USE_SC_LIB) \
      -constr $::env(OBJECTS_DIR)/abc.constr 
} else {
  puts "\[WARN\]\[FLOW\] No clock period constraints detected in design"
  abc -liberty $::env(DONT_USE_SC_LIB) \
      -constr $::env(OBJECTS_DIR)/abc.constr
}

if {[catch {abc -D [expr $::env(ABC_CLOCK_PERIOD_IN_PS)] -script $abc_script -liberty $::env(DONT_USE_SC_LIB) -constr $::env(OBJECTS_DIR)/abc.constr} result]} {
    puts "\[ERROR\] ABC command failed: $result"
    exit 1
}

# Replace undef values with defined constants
setundef -zero

# Splitting nets resolves unwanted compound assign statements in netlist (assign {..} = {..})
splitnets

# Remove unused cells and wires
opt_clean -purge

# Technology mapping of constant hi- and/or lo-drivers
hilomap -singleton \
        -hicell {*}$::env(TIEHI_CELL_AND_PORT) \
        -locell {*}$::env(TIELO_CELL_AND_PORT)

# Insert buffer cells for pass through wires
insbuf -buf {*}$::env(MIN_BUF_CELL_AND_PORTS)

# Reports
tee -o $::env(REPORTS_DIR)/synth_check.txt check

#report checks
tee -o $::env(REPORTS_DIR)/help.txt help sta

# Create argument list for stat
set stat_libs ""
foreach lib $::env(DONT_USE_LIBS) {
  append stat_libs "-liberty $lib "
}
tee -o $::env(REPORTS_DIR)/synth_stat.txt stat {*}$stat_libs
tee -o $::env(REPORTS_DIR)/synth_stat.json stat -json {*}$stat_libs

# Do we see the macro cells?
select -count t:sky130_sram_0kbytes_1rw_32x128_32
select -count t:sky130_sram_2kbytes_1rw_32x512_32
select -list  t:sky130_sram_0kbytes_1rw_32x128_32
select -list  t:sky130_sram_2kbytes_1rw_32x512_32

# Write synthesized design
write_verilog -noattr -noexpr -nohex -nodec $::env(RESULTS_DIR)/1_1_yosys.v
