# Default LibreLane SDC + one multicycle exception for latch-stored weights.
source $::env(SCRIPTS_DIR)/base.sdc

# Weight latches (dcim_core USE_LATCH=1) open in the clock-low phase after a load edge and are
# stable before the first compute edge: load edge n, latch open n+0.5, start edge n+1, first
# accumulate edge n+2. Real latch-to-flop budget is 1.5 cycles; STA default is 0.5 cycle
# (launch at falling edge). So: setup multicycle 2, hold unchanged. No-op without latches.
set wlat {}
foreach c [all_registers -level_sensitive -cells] {
  # integrated clock gates (dlclkp) are not weight storage
  if {![string match "*dlclkp*" [get_property $c ref_name]]} { lappend wlat $c }
}
if {[llength $wlat] > 0} {
  set_multicycle_path 2 -setup -from $wlat
  set_multicycle_path 1 -hold  -from $wlat
}
