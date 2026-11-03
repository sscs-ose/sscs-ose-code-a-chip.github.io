# SPDX-License-Identifier: Apache-2.0
#
# Timing constraints for sar_sequencer.
#
# ---------------------------------------------------------------------------
# The clock period is the CONVERSION PHASE, not the sample rate
# ---------------------------------------------------------------------------
# The converter runs at 1 MS/s with N+2 = 10 phases per conversion, so one
# phase -- one clk period -- is 100 ns. At that period this block closes timing
# with enormous slack: 27 flops of sky130 standard cells against a 100 ns
# budget is not a timing problem. That is the honest constraint for THIS
# converter, and it is the default below.
#
# It also means a PPA sweep at 100 ns measures area and power only. To find
# where the block actually stops closing, override SAR_CLK_PERIOD_NS.
# ---------------------------------------------------------------------------

current_design sar_sequencer

set clk_name      core_clock
set clk_port_name clk

if { [info exists ::env(SAR_CLK_PERIOD_NS)] } {
  set clk_period $::env(SAR_CLK_PERIOD_NS)
} else {
  set clk_period 100.0
}

create_clock -name $clk_name -period $clk_period [get_ports $clk_port_name]

# ---------------------------------------------------------------------------
# The half-cycle path, stated deliberately
# ---------------------------------------------------------------------------
# The phase register advances on the RISING edge of clk. The decision register
# q captures cmp on the FALLING edge. So the loop
#
#     phase flops -> d[] -> (capacitor DAC settles) -> (comparator decides)
#                        -> cmp -> q flops
#
# has HALF a clock period, not a full one.
#
# STA derives the half cycle by itself for the part of that path INSIDE this
# block, because q is genuinely negedge-triggered. What it cannot see is that
# most of the path is OUTSIDE: d drives a 1.24 pF binary-weighted array, the
# array settles, and a StrongARM comparator resolves. Left unbudgeted, the tool
# assumes the whole half period is available to the logic. It is not.
#
# The split below is a DESIGN CHOICE, not a measurement. It reserves 80 % of
# the half period for the analog path and leaves 20 % for this block. Change it
# when the analog settling time is measured, and re-run.
set ext_pct  0.80

set half_period [expr {$clk_period / 2.0}]
set ext_budget  [expr {$half_period * $ext_pct}]

# cmp arrives this long after the rising edge that launched d. It is captured on
# the falling edge, so the logic inside this block gets
# (half_period - ext_budget) = 20 % of the half period.
set_input_delay -clock $clk_name $ext_budget [get_ports cmp]

# d must be valid early enough for the array to settle within the same window.
set_output_delay -clock $clk_name $ext_budget [get_ports {d[*]}]

# The remaining I/O is not in the decision loop: start and rst_n are control,
# code/code_bin/eoc/phase are read by whatever consumes conversions. Budget them
# at a conventional 20 % of the period.
# Listed explicitly rather than subtracted from all_inputs/all_outputs:
# remove_from_collection is a Synopsys command and OpenSTA does not have it.
set io_pct 0.2
set_input_delay  -clock $clk_name [expr {$clk_period * $io_pct}] \
                 [get_ports {rst_n start}]
set_output_delay -clock $clk_name [expr {$clk_period * $io_pct}] \
                 [get_ports {phase[*] code[*] code_bin[*] eoc}]

# ---------------------------------------------------------------------------
# NOT captured here, and it matters
# ---------------------------------------------------------------------------
# The d -> cmp loop closes through analog that has no timing model. This SDC
# asserts a budget for it; it does not verify one. The number that settles the
# question is the DAC settling time plus comparator decision time measured in
# ngspice, compared against (clk_period / 2). Until that comparison is made,
# every slack figure this flow reports is conditional on ext_pct being right.
