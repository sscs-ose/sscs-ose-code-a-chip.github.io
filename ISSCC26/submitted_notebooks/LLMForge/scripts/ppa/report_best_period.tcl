proc report_best_period {step} {
  # slack margin for updated clock as a percent of clock period
  set margin 5
  set numPaths 10

  set timing_report_file [file join $::env(REPORTS_DIR) "${step}_timing_report.txt"]

  set clks [all_clocks]
  if { [llength $clks] == 0 } {
    utl::warn "FLW" 6 "No clocks found."
  } else {
    set clk [lindex $clks 0]
    set clk_name [get_name $clk]
    set period [get_property $clk "period"]
    # Period is in sdc/liberty units.
    utl::info "FLW" 7 "clock $clk_name period $period" 

    # utl::info "FLW" 7 "clock $clk_name period $period" > $timing_report_file

    if { [llength $clks] == 1 } {
      set slack [sta::time_sta_ui [sta::worst_slack_cmd "max"]]
      if { $slack < 1e30 } {
        set ref_period [expr ($period - $slack) * (1.0 - $margin/100.0)]
        utl::info "FLW" 8 "Clock $clk_name min period [format %.3f $ref_period]"
        utl::info "FLW" 9 "Clock $clk_name worst slack [format %.3f $slack]"
      } else {
        utl::warn "FLW" 13 "No constrained path found. Skipping sdc update."
      }
    } else {
      utl::warn "FLW" 10 "more than one clock found. Skipping sdc update."
    }
  }

  # utl::info "FLW" 11 "Path endpoint count [sta::endpoint_count]"

  # Report the N worst delay paths.
  # utl::info "FLW" 12 "Reporting the $numPaths worst delay paths:"
  # The following command assumes that your STA reporting command accepts the "-max_paths" option.
  # You might need to adjust the options depending on your STA tool.
  # set report [sta::report_timing -verbose -max_paths $numPaths]
  # utl::info "FLW" 12 "info: [sta::info]"

}