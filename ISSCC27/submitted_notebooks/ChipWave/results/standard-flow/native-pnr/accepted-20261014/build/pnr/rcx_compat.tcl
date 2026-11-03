# ORFS uses the newer split rules API; 26Q3 accepts the identical rules in extract_parasitics.
if {[llength [info commands set_extraction_rules_file]] == 0} {
  proc set_extraction_rules_file {rules} {
    if {![file exists $rules] || [file size $rules] == 0} {error "Missing frozen extraction rules: $rules"}
    set ::nebula_rcx_rules $rules
    puts "RCX_API_COMPAT rules=$rules"
  }
  rename extract_parasitics nebula_native_extract_parasitics
  proc extract_parasitics {args} {
    if {![info exists ::nebula_rcx_rules]} {error "Frozen extraction rules were not set"}
    puts "RCX_API_COMPAT extract_parasitics -ext_model_file $::nebula_rcx_rules $args"
    nebula_native_extract_parasitics -ext_model_file $::nebula_rcx_rules {*}$args
  }
}
