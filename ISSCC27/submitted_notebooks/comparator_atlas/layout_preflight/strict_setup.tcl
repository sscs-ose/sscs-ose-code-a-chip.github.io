model blackbox off
foreach circuit {1 2} {
    set available [cells list -all -circuit$circuit]
    foreach {device kind} {
        sky130_fd_pr__nfet_01v8 nmos
        sky130_fd_pr__nfet_01v8_lvt nmos
        sky130_fd_pr__pfet_01v8 pmos
    } {
        if {[lsearch -exact $available $device] >= 0} {
            set target [list -circuit$circuit $device]
            model $target $kind
            puts "PREFLIGHT_DEVICE_CLASS $circuit $device [model $target]"
        }
    }
}
# Keep the technology's real terminal permutations and W/L comparisons.
# Classifying four-terminal primitives does not equate different model names.
source [file join $::env(PDK_ROOT) sky130A libs.tech netgen sky130A_setup.tcl]
