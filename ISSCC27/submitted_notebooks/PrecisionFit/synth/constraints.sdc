# Shared timing constraint for all three candidate designs (Week 4, optional).
#
# The rule the guide sets: pick ONE period that the WIDEST candidate
# (conservative uniform) closes with small positive slack, and apply it to all
# three. Choosing a period only the narrow designs meet would silently reward
# narrower designs on timing for a reason unrelated to the accuracy-vs-area
# claim.
#
# The 14.6 ns (68.5 MHz) below was derived exactly this way: the widest config
# was run through OpenSTA at a deliberately loose period, the worst slack was
# read back, and the period tightened until slack was small-but-positive
# (~+2.0 ns for conservative_uniform at the TT corner). It is recorded in the
# notebook (section 9) and applied identically to all three LibreLane configs.
#
# Licensed under the Apache License, Version 2.0. See the repo LICENSE file.

create_clock -name clk -period 14.6 [get_ports clk]   ;# 68.5 MHz -- TT signoff corner
                                                       ;# Full LibreLane 3.x setup: synth/ol_<design>.yaml.
                                                       ;# Signoff corner: nom_tt_025C_1v80 (standard academic PVT).
                                                       ;# SS-max-OCV corner cannot close at practical freq; effective
                                                       ;# SS critical path ~24 ns for this fully-parallel topology.
                                                       ;# Conservative_uniform TT critical path: ~12.6 ns → +2.0 ns slack.

set_input_delay  -clock clk 1.0 [all_inputs]
set_output_delay -clock clk 1.0 [all_outputs]
set_clock_uncertainty 0.2 [get_clocks clk]
