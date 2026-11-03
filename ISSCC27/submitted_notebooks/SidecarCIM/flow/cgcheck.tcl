# env: LIB SPEF ODB SDC TAG  -> worst clock-gating (dlclkp GATE pin) setup/hold slack for one corner
read_liberty $::env(LIB)
read_db $::env(ODB)
read_sdc $::env(SDC)
read_spef $::env(SPEF)
set pins [get_pins -of_objects [get_cells -filter "ref_name==sky130_fd_sc_hd__dlclkp_1"] -filter "name==GATE"]
puts "CG_PINS $::env(TAG) [llength $pins]"
foreach mode {max min} {
  set paths [find_timing_paths -to $pins -path_delay $mode -group_path_count 1 -sort_by_slack]
  foreach p $paths { puts "CG $::env(TAG) $mode [format %.4f [get_property $p slack]]" }
}
