# CDL netlists of a chip v2 final database for LVS, run through `make run` (RUN_SCRIPT): write_cdl of
# 6_final.odb as in the ORFS cdl.tcl, then the concatenation that the Makefile rule
# $(OBJECTS_DIR)/6_final_concat.cdl performs. The masters file must describe the OpenRAM macros too: the
# platform CDL_FILE (fixed with '=' in the platform config) has only the standard cells, so
# CHIPV2_CDL_MASTERS names the old chip's sky130hd_with_openram_masters_v3.cdl (the caller checks its hash).
# Asking make for those files instead walks the dependency chain back to synthesis in a work home that
# starts at CTS.
source $::env(SCRIPTS_DIR)/load.tcl
erase_non_stage_variables final
load_design 6_final.odb 6_final.sdc
set masters [expr {[info exists ::env(CHIPV2_CDL_MASTERS)] ? $::env(CHIPV2_CDL_MASTERS) : $::env(CDL_FILE)}]
write_cdl -masters $masters $::env(RESULTS_DIR)/6_final.cdl
set out "$::env(OBJECTS_DIR)/6_final_concat.cdl"
set fo [open $out w]
foreach f [list "$::env(RESULTS_DIR)/6_final.cdl" $masters] {
  set fi [open $f]
  fcopy $fi $fo
  close $fi
}
close $fo
puts "CHIPV2_CDL_DONE cdl=$::env(RESULTS_DIR)/6_final.cdl concat=$out masters=$masters"
