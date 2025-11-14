proc write_power_report {step} {
	set clks [all_clocks]

	if { [llength $clks] == 0 } {
		utl::warn "FLW" 6 "No clocks found."
	} else {
		set_propagated_clock [all_clocks]

		if {$::env(USE_STA_VCD) && [info exists ::env(STA_VCD_FILE)]} {
			puts "Reading VCD file for setting power activity."
			sta::read_power_activities -scope $::env(VERILOG_TESTBENCH_MODULE)/$::env(STA_TB_DUT_INSTANCE) -vcd $::env(STA_VCD_FILE)

			
			# list all cells from all loaded libs
			# Adjust to your exact cell names from the .lib filenames
			set want {sky130_sram_0kbytes_1rw_32x128_32 sky130_sram_2kbytes_1rw_32x512_32}

			set found {}
			foreach lc [get_lib_cells *] {
			# lib cell names look like "<lib>/<cell>"
			set full [get_name $lc]
			set cell [lindex [split $full "/"] end]
			if {[lsearch -exact $want $cell] >= 0} {
				puts "Loaded: $full"
				lappend found $cell
			}
			}
			puts "Found [llength $found]/[llength $want] target SRAM lib cells."

		} else {
			puts "No VCD file found. Using default power activity values."
			sta::set_power_activity -input -activity .1
			sta::set_power_activity -input_port rst -activity 0
		}

		current_design $::env(DESIGN_NAME)

		set power_report_file [file join $::env(REPORTS_DIR) "${step}_power_report.txt"]
		sta::report_power > $power_report_file

		unset_propagated_clock [all_clocks]
	}
}