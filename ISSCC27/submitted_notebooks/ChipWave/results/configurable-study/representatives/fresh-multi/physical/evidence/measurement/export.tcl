if {[catch {
read_liberty {/home/asic03/project/user37/CodeAChip_Submission/ISSCC27/submitted_notebooks/ChipNebula_CPU/toolchain/orfs/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib}
read_db {/home/asic03/project/user37/CodeAChip_Experiments/Configurable_PPA_20261016/representatives/fresh-multi/physical/evidence/measurement/6_final.odb}
read_sdc {/home/asic03/project/user37/CodeAChip_Experiments/Configurable_PPA_20261016/representatives/fresh-multi/physical/evidence/orfs-work/results/sky130hd/nebula_cpu_npu_top/nebula/6_final.sdc}
set_propagated_clock [all_clocks]
read_spef {/home/asic03/project/user37/CodeAChip_Experiments/Configurable_PPA_20261016/representatives/fresh-multi/physical/evidence/orfs-work/results/sky130hd/nebula_cpu_npu_top/nebula/6_final.spef}
set remove {}
set inventory [open {/home/asic03/project/user37/CodeAChip_Experiments/Configurable_PPA_20261016/representatives/fresh-multi/physical/evidence/measurement/cell-inventory.tsv} w]
puts $inventory "instance	master	signal_pins	liberty_model	preserved"
foreach inst [[ord::get_db_block] getInsts] {
  set master [$inst getMaster]
  set name [$master getName]
  set signals 0
  foreach mt [$master getMTerms] {if {[$mt getSigType] ni {POWER GROUND}} {incr signals}}
  set modeled [expr {[llength [get_lib_cells -quiet $name]] > 0}]
  if {$signals > 0 && !$modeled} {error "Missing actual signal-cell Liberty model: $name"}
  set keep [expr {$signals > 0 || $modeled}]
  if {!$keep} {lappend remove $name}
  puts $inventory "[$inst getName]	$name	$signals	$modeled	$keep"
}
close $inventory
write_verilog -sort -remove_cells [lsort -unique $remove] {/home/asic03/project/user37/CodeAChip_Experiments/Configurable_PPA_20261016/representatives/fresh-multi/physical/evidence/measurement/6_final.sta.v}
report_parasitic_annotation -report_unannotated > {/home/asic03/project/user37/CodeAChip_Experiments/Configurable_PPA_20261016/representatives/fresh-multi/physical/evidence/measurement/database-parasitics.rpt}
} message options]} {puts stderr $message; puts stderr [dict get $options -errorinfo];exit 1}
exit
