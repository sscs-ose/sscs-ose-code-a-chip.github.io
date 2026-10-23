# Worst setup path to one pin (ss, SPEF + SPICE views). env: RUN, MACRO_LIB_DIR, PIN
set L [lindex [glob /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib] 0]
read_liberty $L
foreach f [glob $::env(MACRO_LIB_DIR)/*.physical.lib] { read_liberty $f }
read_db $::env(RUN)/6_final.odb
read_sdc $::env(RUN)/6_final.sdc
set_propagated_clock [all_clocks]
read_spef $::env(RUN)/6_final.spef
report_checks -path_delay max -to [get_pins $::env(PIN)] -fields {fanout} -digits 2
exit
