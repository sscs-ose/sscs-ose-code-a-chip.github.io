# Critical-path classification at ss (SPEF + SPICE views, SDC as written for the core clock): every core_clk setup
# endpoint with slack < 8 ns, written one per line (endpoint slack) for grouping by block in crit_classify.py.
# env: RUN, MACRO_LIB_DIR, OUT
set L [lindex [glob /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib] 0]
read_liberty $L
foreach f [glob $::env(MACRO_LIB_DIR)/*.physical.lib] { read_liberty $f }
read_db $::env(RUN)/6_final.odb
read_sdc $::env(RUN)/6_final.sdc
set_propagated_clock [all_clocks]
read_spef $::env(RUN)/6_final.spef
set fh [open $::env(OUT) w]
foreach path [find_timing_paths -path_delay max -group_path_count 200000 -endpoint_path_count 1 -slack_max 8.0 -path_group core_clk] {
  set sp [get_full_name [get_property $path startpoint]]
  puts $fh "[get_full_name [get_property $path endpoint]] [get_property $path slack] $sp"
}
close $fh
exit
