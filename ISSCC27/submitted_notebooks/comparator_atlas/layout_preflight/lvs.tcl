if {[catch {
    lvs [list $::env(PREFLIGHT_LAYOUT) $::env(PREFLIGHT_CELL)] \
        [list $::env(PREFLIGHT_REFERENCE) $::env(PREFLIGHT_CELL)] \
        $::env(PREFLIGHT_SETUP) $::env(PREFLIGHT_LVS_REPORT) -json
    puts "PREFLIGHT_LVS_RESULT [verify equivalent] [verify unique]"
} message options]} {
    puts stderr "PREFLIGHT_LVS_ERROR: $message"
    puts stderr [dict get $options -errorinfo]
    exit 1
}
quit
