read_db build/pnr/results/6_final.odb
set block [ord::get_db_block]
if {[$block getName] ne "nebula_cpu_npu_top"} {error "Wrong final ODB top"}
set f [open build/gds/odb_instances.tsv w]
puts $f "instance\tmaster"
foreach inst [$block getInsts] {puts $f "[$inst getName]\t[[$inst getMaster] getName]"}
close $f
write_def build/gds/final.def
