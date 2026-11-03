proc box_um {x1 y1 x2 y2} {
    box values ${x1}um ${y1}um ${x2}um ${y2}um
}

proc check_and_save {cell} {
    select top cell
    expand
    box values {*}[select bbox]
    drc on
    drc check
    drc catchup
    set reasons [drc listall why]
    set count 0
    foreach {reason rectangles} $reasons {
        incr count [llength $rectangles]
    }
    set style [drc list style]
    if {$style ne "drc(full)"} {error "Unexpected DRC style: $style"}
    drc style
    puts "NOMINAL27_DRC_STYLE $cell $style"
    set report [open ${cell}.drc.txt w]
    puts $report "cell: $cell\ntechnology: [tech name]\ndrc_style: $style"
    puts $report "grid_um: [cif scale out]\ncount: $count"
    puts $report $reasons
    close $report
    save $cell
    gds write ${cell}.gds
    puts "NOMINAL27_DRC $cell $count"
}

proc pcells {} {
    source $::env(NOMINAL27_REQUEST)
    set report [open pcells.tsv w]
    puts $report "cell\tmodel\tw_um\tl_um\tnf\tm\tgrid_um"
    foreach request $device_specs {
        lassign $request cell model width length
        load $cell -silent
        box_um 0 0 0 0
        set parameters [dict merge [sky130::${model}_defaults] \
            [dict create w $width l $length nf 1 m 1 guard 1 doports 1 topc 1 botc 0]]
        set checked [sky130::${model}_check $parameters]
        foreach key {w l nf m} {
            if {[dict get $parameters $key] != [dict get $checked $key]} {
                error "PCell changed $cell $key"
            }
        }
        sky130::${model}_draw $checked
        property FIXED_BBOX {}
        findlabel G
        lassign [sky130::getbox] x y x2 y2
        set x [expr {($x+$x2)/2.0}]
        set y [expr {($y+$y2)/2.0}]
        box_um [expr {$x-0.15}] [expr {$y-0.11}] [expr {$x+0.15}] [expr {$y+0.29}]
        paint metal1
        save $cell
        puts $report "$cell\t$model\t$width\t$length\t1\t1\t[cif scale out]"
    }
    close $report
}

proc export_netlists {} {
    extract style ngspice()
    extract no resistance
    extract do capacitance
    extract do coupling
    extract all
    ext2spice lvs
    ext2spice blackbox off
    ext2spice hierarchy off
    ext2spice subcircuit on
    ext2spice subcircuit top on
    ext2spice merge none
    ext2spice scale off
    ext2spice -o atlas.lvs.spice
    ext2spice extresist off
    ext2spice cthresh 0
    ext2spice -o atlas.c.spice

    extresist threshold 0
    extresist minresist 0
    extresist mindelay 0
    extresist simplify off
    extresist blackbox off
    extract do resistance
    extract all
    ext2spice extresist on
    ext2spice cthresh 0
    ext2spice rthresh 0
    ext2spice -o atlas.rc.spice
}

proc main {} {
    if {[tech name] ne "sky130A"} {error "Real sky130A technology not loaded"}
    units internal
    snap internal
    random seed 1
    drc euclidean on
    drc style drc(full)
    switch -- $::env(NOMINAL27_MODE) {
        pcells {pcells}
        route {
            load atlas -silent
            source $::env(NOMINAL27_REQUEST)
            check_and_save atlas
            export_netlists
            load nominal27_spacing_bad -silent
            box_um 0 0 1 1
            paint metal1
            box_um 1.07 0 2.07 1
            paint metal1
            check_and_save nominal27_spacing_bad
        }
        default {error "Unknown nominal27 Magic mode"}
    }
    puts "NOMINAL27_MAGIC_COMPLETE $::env(NOMINAL27_MODE)"
}

if {[catch {main} message options]} {
    puts stderr "NOMINAL27_MAGIC_ERROR: $message"
    puts stderr [dict get $options -errorinfo]
    exit 1
}
exit 0
