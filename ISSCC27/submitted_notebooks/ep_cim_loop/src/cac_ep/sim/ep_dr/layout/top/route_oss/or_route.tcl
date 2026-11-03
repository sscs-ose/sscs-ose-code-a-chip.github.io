# 입력: env CFG (mk_route.py 가 쓴 cfg_chip.tcl: LEFS·SKIP_NETS·DIE_W·DIE_H), env DEF (mk_oss_def.py 의 chip_oss.def), env RNETS (route_nets.txt), env OUTD
# 흐름: LEF → DEF (배치 FIXED·핀·미리 그린 선·전원 = SPECIALNETS, 이을 넷 = NETS) → global_connect (블록 PG 핀)
#       → global_route (FastRoute) → detailed_route (TritonRoute) → DEF
source $env(CFG)
set OUTD $env(OUTD)
if {![info exists TOP_LAYER]} { set TOP_LAYER met4 }
if {![info exists BOT_LAYER]} { set BOT_LAYER met1 }
set thr [expr {[info exists env(NTHR)] ? $env(NTHR) : 8}]
file mkdir $OUTD
proc stage {s} { set r ?; catch { set r [string trim [exec ps -o rss= -p [pid]]] }; puts "STAGE $s [clock milliseconds] rss_kb $r" }
proc say {args} { puts "ORR: [join $args { }]" }
stage start
set_thread_count $thr

foreach l $LEFS { read_lef $l }
stage lef
read_def $env(DEF)
stage def
set block [ord::get_db_block]
say "insts [llength [$block getInsts]] nets [llength [$block getNets]] bterms [llength [$block getBTerms]]"

# NETS 넷 중 SPECIALNETS 에도 도형이 있는 것 (core 핀 drawing, nudge row 100–105) 은 DEF 를 읽으면 special 로 표시된다 → 지워서 배선 대상으로
set fp [open $env(RNETS) r]; set rnets [split [string trim [read $fp]] "\n"]; close $fp
set ncl 0; set nsw 0
foreach n $rnets {
    set net [$block findNet $n]
    if {$net eq "NULL"} { say "MISSING $n"; continue }
    if {[$net isSpecial]} { $net clearSpecial; incr ncl }
    foreach it [$net getITerms] { $it clearSpecial }
    incr nsw [llength [$net getSWires]]
}
say "route nets [llength $rnets], special cleared $ncl, swires on route nets $nsw"
set nsp 0; foreach net [$block getNets] { if {[$net isSpecial]} { incr nsp } }
say "special nets (not routed) $nsp"

add_global_connection -net VDD -pin_pattern {^(VDD|vdd|VPWR|VPB)$} -power
add_global_connection -net VSS -pin_pattern {^(VSS|vss|VGND|VNB)$} -ground
global_connect
set fp [open $PRE_TCL r]; set ptxt [read $fp]; close $fp
set tech [ord::get_db_tech]
foreach {- pn nn ln x1 y1 x2 y2} [regexp -all -inline {create_pg_pin -name (\S+) -net (\S+) -geom (\S+) ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)} $ptxt] {
    set net [$block findNet $nn]
    set bt [odb::dbBTerm_create $net $pn]
    $bt setIoType INOUT
    $bt setSigType [expr {$nn eq "VSS" ? "GROUND" : "POWER"}]
    set bp [odb::dbBPin_create $bt]
    odb::dbBox_create $bp [$tech findLayer $ln] [expr {round($x1*1000)}] [expr {round($y1*1000)}] [expr {round($x2*1000)}] [expr {round($y2*1000)}]
    $bp setPlacementStatus FIRM
    say "PGPIN $pn $ln $x1 $y1 $x2 $y2"
}
stage gconnect

make_tracks
set_routing_layers -signal ${BOT_LAYER}-${TOP_LAYER}
if {[info exists env(GRT_ADJ)]} { set_global_routing_layer_adjustment ${BOT_LAYER}-${TOP_LAYER} $env(GRT_ADJ) }
global_route -guide_file $OUTD/route.guide -congestion_report_file $OUTD/grt_congestion.rpt -verbose -allow_congestion
stage grt
write_def $OUTD/chip_core_grt.def

set dargs [list -output_drc $OUTD/drt_drc.rpt -output_maze $OUTD/drt_maze.log -verbose 1]
if {[info exists env(DRT_ITER)]} { lappend dargs -droute_end_iter $env(DRT_ITER) }
detailed_route {*}$dargs
stage drt

# 결과
set nopen 0
foreach n $rnets {
    set net [$block findNet $n]
    if {$net eq "NULL"} continue
    if {[$net getWire] eq "NULL"} { incr nopen; say "NO WIRE $n" }
}
say "route nets without wire $nopen"
catch { check_antennas -report_file $OUTD/antenna.rpt }
write_def $OUTD/chip_core_routed.def
catch { write_db $OUTD/chip_core_routed.odb }
stage done
say "DONE"
exit
