# DRV violators (max slew / max cap) of a final database at tt with its SPEF, one line per pin, plus the driver cell
# and the limit source, for the C5 explanation. env: RUN, MACRO_LIB_DIR, OUT
set L [lindex [glob /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib] 0]
read_liberty $L
foreach f [glob $::env(MACRO_LIB_DIR)/*.physical.lib] { read_liberty $f }
read_db $::env(RUN)/6_final.odb
read_sdc $::env(RUN)/6_final.sdc
set_propagated_clock [all_clocks]
read_spef $::env(RUN)/6_final.spef
sta::with_output_to_variable r { report_check_types -max_slew -max_capacitance -violators -digits 3 }
set fh [open $::env(OUT) w]; puts $fh $r; close $fh
exit
