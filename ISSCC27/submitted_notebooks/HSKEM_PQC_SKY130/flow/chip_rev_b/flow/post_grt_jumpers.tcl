# Chip v2, POST_GLOBAL_ROUTE_TCL hook of the old chip's global-route recipe (which repairs no antennas
# before the detailed route). The first routed checkpoint had 2,219 antenna nets (old chip: 480), two
# thirds of them met3 side-area violations: wires of a few hundred um that reach a minimum-size gate on
# met3. Jumpers move the wire next to such a gate to an upper layer: no cell is added, so the slew cost of
# the global-route diodes (the reason the recipe skips the repair) does not arise. The detailed route then
# repairs only what is left, with diodes.
set before [check_antennas -report_file $::env(REPORTS_DIR)/grt_antennas_before_jumpers.log]
puts "CHIPV2_POST_GRT antenna_nets_before_jumpers=$before"
repair_antennas -jumper_only -iterations 3
set after [check_antennas -report_file $::env(REPORTS_DIR)/grt_antennas_after_jumpers.log]
puts "CHIPV2_POST_GRT antenna_nets_after_jumpers=$after"
estimate_parasitics -global_routing
