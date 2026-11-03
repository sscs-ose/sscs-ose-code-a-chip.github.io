# Chip v2 PRE_GLOBAL_ROUTE_TCL with a selectable layer adjustment (the old chip's hook,
# asic/orfs/pre_global_route_a3_013.tcl, fixes 0.13; the sky130hd platform default is 0.2). A larger
# adjustment keeps more of every gcell free in the global route, which the detailed route then uses.
# env: CHIPV2_GRT_ADJ (default 0.13), optional CHIPV2_GRT_ADJ_M1M2 for met1-met2 (pin-access layers).
set adj [expr {[info exists ::env(CHIPV2_GRT_ADJ)] ? $::env(CHIPV2_GRT_ADJ) : 0.13}]
set_global_routing_layer_adjustment $::env(MIN_ROUTING_LAYER)-$::env(MAX_ROUTING_LAYER) $adj
if {[info exists ::env(CHIPV2_GRT_ADJ_M1M2)]} {
  set_global_routing_layer_adjustment met1-met2 $::env(CHIPV2_GRT_ADJ_M1M2)
}
set_routing_layers -clock $::env(MIN_CLK_ROUTING_LAYER)-$::env(MAX_ROUTING_LAYER)
set_routing_layers -signal $::env(MIN_ROUTING_LAYER)-$::env(MAX_ROUTING_LAYER)
puts "CHIPV2_PRE_GRT adjustment=$adj m1m2=[expr {[info exists ::env(CHIPV2_GRT_ADJ_M1M2)] ? $::env(CHIPV2_GRT_ADJ_M1M2) : $adj}]"
