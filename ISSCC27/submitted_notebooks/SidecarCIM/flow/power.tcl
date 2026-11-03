# Post-layout power (OpenROAD/OpenSTA). Env: TOP RUNFINAL PDKROOT VCD(optional) SCOPE OUT
set top    $::env(TOP)
set fin    $::env(RUNFINAL)
set lib    "$::env(PDKROOT)/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
read_liberty $lib
read_db $fin/odb/$top.odb
read_sdc $fin/sdc/$top.sdc
read_spef $fin/spef/nom/$top.nom.spef
set_propagated_clock [all_clocks]
if {[info exists ::env(VCD)] && $::env(VCD) ne ""} {
  read_vcd -scope $::env(SCOPE) $::env(VCD)
  report_activity_annotation -report_unannotated
} else {
  set_power_activity -input -activity 0.1
}
report_power -digits 6
exit
