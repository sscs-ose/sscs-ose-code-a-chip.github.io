# mk_route.py 가 씀: route_design 뒤에 source
# CDR.m3.2 notch: NanoRoute via2 pad ↔ col_blk 안 met3 (같은 넷), 잡 721323
if {[catch {create_shape -net col1_clk_n -layer met3 -rect {664.600 626.000 664.980 626.300} -status fixed -shape stripe} m]} { puts "TOPR: PATCH FAIL col1_clk_n $m" } else { puts "TOPR: PATCH col1_clk_n met3" }
