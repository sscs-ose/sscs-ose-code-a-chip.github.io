# 환경: FPTCL (fp_tcl.py 가 fp.json·pins.cfg 로 쓴 값), TLEF, SCLEF, LIBF, NL (Yosys netlist), SDC, OUTD, NTHR, DENS, REPAIR (1 = repair_design)
# 순서: floorplan (die·core·줄·트랙) → 핀 (pins.cfg 그대로) → 전원망 (줄 경계 met1 띠 + met2 stripe + via, 상용 판과 같은 규칙) →
#       전역 배치 → (repair_design) → 상세 배치 → filler → 전역 배선 → 상세 배선 (met1–met3) → DEF·Verilog
source $::env(FPTCL)
set OUTD $::env(OUTD)
proc stage {n} { puts "STAGE $n [clock milliseconds]" }
stage start
read_lef $::env(TLEF)
read_lef $::env(SCLEF)
if {[info exists ::env(XLEF)]} { foreach f $::env(XLEF) { read_lef $f } }      ;# 매크로 LEF (col_blk·row_blk)
read_liberty $::env(LIBF)
read_verilog $::env(NL)
link_design $TOP
read_sdc $::env(SDC)
set db [ord::get_db]; set block [ord::get_db_block]; set tech [$db getTech]
set dbu [$tech getDbUnitsPerMicron]
proc um {v} { return [expr {$v / double($::dbu)}] }

# ── floorplan: die = 저장된 블록과 같음, core = 줄 영역 (첫 줄 방향도 같게: 상용 판은 맨 아래 줄이 FS = MX)
set cx2 [expr {$ROW_X + $NSITES * $SITE_W}]; set cy2 [expr {$ROW_Y0 + $NROWS * $ROW_H}]
if {[info exists CORE]} { lassign $CORE ROW_X ROW_Y0 cx2 cy2 }
initialize_floorplan -die_area [list 0 0 [um $DIE_W] [um $DIE_H]] -core_area [list [um $ROW_X] [um $ROW_Y0] [um $cx2] [um $cy2]] -site $SITE
foreach r [$block getRows] { odb::dbRow_destroy $r }
# initialize_floorplan 은 core 왼쪽 아래를 site 격자 (die 원점 기준) 로 맞춘다 (IFP-0028) → 저장된 블록과 같은 core 로 되돌림
$block setCoreArea [odb::new_Rect $ROW_X $ROW_Y0 $cx2 $cy2]
puts "CORE AREA [[$block getCoreArea] xMin] [[$block getCoreArea] yMin] [[$block getCoreArea] xMax] [[$block getCoreArea] yMax]"
set site [[lindex [$db getLibs] 0] findSite $SITE]
if {$site eq "NULL" || $site eq ""} { foreach l [$db getLibs] { set s [$l findSite $SITE]; if {$s ne "NULL" && $s ne ""} { set site $s } } }
if {[info exists ROW_LIST]} {
    # 전역 배치용 임시 줄 = core 전체 (줄이 없는 매크로 영역을 gpl 이 'dummy' 로 채워 매크로 면적과 두 번 세므로 (GPL-0301)).
    # 전역 배치 뒤 지우고 저장된 블록과 같은 std 셀 줄 (ROW_LIST, channel 만) 을 만든 다음 상세 배치 → std 셀은 그 줄에만 놓인다
    set nt 0
    for {set y $ROW_Y0} {$y + $ROW_H <= $cy2} {incr y $ROW_H} {
        odb::dbRow_create $block TMP_$nt $site $ROW_X $y [expr {$nt % 2 ? "MX" : "R0"}] HORIZONTAL [expr {($cx2 - $ROW_X) / $SITE_W}] $SITE_W; incr nt
    }
    puts "TMP ROWS $nt"
} else {
for {set k 0} {$k < $NROWS} {incr k} {
    set or [expr {($k % 2 == 0) ? $FIRST_OR : ($FIRST_OR eq "MX" ? "R0" : "MX")}]
    odb::dbRow_create $block ROW_$k $site $ROW_X [expr {$ROW_Y0 + $k * $ROW_H}] $or HORIZONTAL $NSITES $SITE_W
}
}
# 매크로 (아날로그 스위치·clamp): 저장된 블록과 같은 자리·방향에 고정
set nm 0
if {[info exists MACROS]} {
    foreach m $MACROS {
        lassign $m in ms x y or
        set inst [$block findInst $in]
        if {$inst eq "NULL" || $inst eq ""} { error "macro $in 가 netlist 에 없음" }
        if {[[$inst getMaster] getName] ne $ms} { error "macro $in master [[$inst getMaster] getName] != $ms" }
        $inst setOrient $or; $inst setLocation $x $y; $inst setPlacementStatus FIRM; incr nm
    }
}
puts "MACROS placed $nm"
# 배선 막기 (저장된 블록 DEF BLOCKAGES 의 LAYER 사각형: row_blk 서쪽 끝 met2 = 위 단계에서 배열 met2 띠를 겹쳐 놓을 자리)
foreach b [expr {[info exists ROUTE_BLK] ? $ROUTE_BLK : {}}] { lassign $b l x1 y1 x2 y2; odb::dbObstruction_create $block [$tech findLayer $l] $x1 $y1 $x2 $y2 }
puts "ROWS [llength [$block getRows]] core [um $ROW_X] [um $ROW_Y0] [um $cx2] [um $cy2]"
foreach t $TRACKS {
    lassign $t lay xo xp yo yp
    make_tracks $lay -x_offset [um $xo] -x_pitch [um $xp] -y_offset [um $yo] -y_pitch [um $yp]
}

# ── 핀: pins.cfg 의 사각형 그대로 (FIXED)
set np 0
foreach p $PINS {
    lassign $p nm dir lay x1 y1 x2 y2
    set bt [$block findBTerm $nm]
    if {$bt eq "NULL" || $bt eq ""} { error "pin $nm 가 netlist 에 없음" }
    set bp [odb::dbBPin_create $bt]
    odb::dbBox_create $bp [$tech findLayer $lay] $x1 $y1 $x2 $y2
    $bp setPlacementStatus FIRM
    incr np
}
set nbt [llength [$block getBTerms]]
puts "PINS placed $np of bterms $nbt"
if {$np != $nbt} { error "핀 수가 다름: pins.cfg $np, netlist $nbt" }

# ── 전원: VDD ← VPWR·VPB, VSS ← VGND·VNB (hvl 은 넷마다 rail 이 둘)
foreach {n t} {VDD POWER VSS GROUND} {
    set net [$block findNet $n]
    if {$net eq "NULL" || $net eq ""} { set net [odb::dbNet_create $block $n] }
    $net setSpecial; $net setSigType $t
}
add_global_connection -net VDD -inst_pattern .* -pin_pattern {^VPWR$} -power
add_global_connection -net VDD -inst_pattern .* -pin_pattern {^VPB$} -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern {^VGND$} -ground
add_global_connection -net VSS -inst_pattern .* -pin_pattern {^VNB$} -ground
add_global_connection -net VDD -inst_pattern .* -pin_pattern {^VDD$} -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern {^VSS$} -ground
global_connect
if {[info exists SPECIAL]} {
    # 전원망·special 신호 도형 = 저장된 블록 DEF 의 SPECIALNETS 목록 그대로 (fp.json special) — 핀처럼 고정 제약
    set vias [dict create]
    foreach vd $VIADEFS {
        lassign $vd vn kind data
        set v [odb::dbVia_create $block $vn]
        if {$kind eq "gen"} {
            lassign $data cw ch l1 lc l2 csx csy ebx eby etx ety nr nc
            set vp [odb::dbViaParams]
            $vp setXCutSize $cw; $vp setYCutSize $ch; $vp setXCutSpacing $csx; $vp setYCutSpacing $csy
            $vp setXBottomEnclosure $ebx; $vp setYBottomEnclosure $eby; $vp setXTopEnclosure $etx; $vp setYTopEnclosure $ety
            $vp setNumCutRows $nr; $vp setNumCutCols $nc
            $vp setBottomLayer [$tech findLayer $l1]; $vp setCutLayer [$tech findLayer $lc]; $vp setTopLayer [$tech findLayer $l2]
            $v setViaParams $vp
        } else {
            foreach r $data { lassign $r l x1 y1 x2 y2; odb::dbBox_create $v [$tech findLayer $l] $x1 $y1 $x2 $y2 }
        }
        dict set vias $vn $v
    }
    set nsh 0
    foreach sp $SPECIAL {
        set n [lindex $sp 0]
        set net [$block findNet $n]
        if {$net eq "NULL" || $net eq ""} { error "special net $n 없음" }
        $net setSpecial
        if {![info exists sw($n)]} { set sw($n) [odb::dbSWire_create $net ROUTED] }
        if {[lindex $sp 1] eq "VIA"} {
            lassign $sp n - vn x y shp
            odb::dbSBox_create $sw($n) [dict get $vias $vn] $x $y $shp
        } else {
            lassign $sp n l x1 y1 x2 y2 shp
            odb::dbSBox_create $sw($n) [$tech findLayer $l] $x1 $y1 $x2 $y2 $shp
        }
        incr nsh
    }
    puts "SPECIAL shapes $nsh"
} else {
# via M1M2 (cut 4 × 1) — 상용 판 DEF 의 M1M2_PR_1 과 같은 값
lassign $VIA_CUT cw ch; lassign $VIA_CUTSP csx csy; lassign $VIA_ENC ebx eby etx ety; lassign $VIA_ROWCOL nr nc
set via [odb::dbVia_create $block M1M2_PR_1]
set vp [odb::dbViaParams]
$vp setXCutSize $cw; $vp setYCutSize $ch; $vp setXCutSpacing $csx; $vp setYCutSpacing $csy
$vp setXBottomEnclosure $ebx; $vp setYBottomEnclosure $eby; $vp setXTopEnclosure $etx; $vp setYTopEnclosure $ety
$vp setNumCutRows $nr; $vp setNumCutCols $nc
$vp setBottomLayer [$tech findLayer met1]; $vp setCutLayer [$tech findLayer via]; $vp setTopLayer [$tech findLayer met2]
$via setViaParams $vp
set sw(VDD) [odb::dbSWire_create [$block findNet VDD] ROUTED]
set sw(VSS) [odb::dbSWire_create [$block findNet VSS] ROUTED]
set m1 [$tech findLayer met1]; set m2 [$tech findLayer $PDN_STRIPE_LAYER]
# 줄 경계 띠: 줄 방향 R0 = 아래 VSS / 위 VDD, MX = 반대
set bands {}
for {set k 0} {$k <= $NROWS} {incr k} {
    set y [expr {$ROW_Y0 + $k * $ROW_H}]
    set or [expr {($k % 2 == 0) ? $FIRST_OR : ($FIRST_OR eq "MX" ? "R0" : "MX")}]
    if {$k < $NROWS} { set n [expr {$or eq "R0" ? "VSS" : "VDD"}] } else {
        set orp [expr {(($k - 1) % 2 == 0) ? $FIRST_OR : ($FIRST_OR eq "MX" ? "R0" : "MX")}]
        set n [expr {$orp eq "R0" ? "VDD" : "VSS"}] }
    set h [expr {$PDN_BAND_W / 2}]
    odb::dbSBox_create $sw($n) $m1 $ROW_X [expr {$y - $h}] $cx2 [expr {$y + $h}] FOLLOWPIN
    lappend bands [list $n $y]
}
# met2 stripe 짝 (VDD, VSS): core 왼쪽 + offset 부터 pitch 마다, 짝이 core 안에 들어갈 때까지. 위·아래로 ext 만큼 내밀기
set ns 0; set nv 0
for {set x [expr {$ROW_X + $PDN_STRIPE_OFF}]} {$x + 2 * $PDN_STRIPE_W + $PDN_STRIPE_SP <= $cx2} {set x [expr {$x + $PDN_STRIPE_PITCH}]} {
    foreach {n xl} [list VDD $x VSS [expr {$x + $PDN_STRIPE_W + $PDN_STRIPE_SP}]] {
        odb::dbSBox_create $sw($n) $m2 $xl [expr {$ROW_Y0 - $PDN_STRIPE_EXT}] [expr {$xl + $PDN_STRIPE_W}] [expr {$cy2 + $PDN_STRIPE_EXT}] STRIPE
        incr ns
        set xc [expr {$xl + $PDN_STRIPE_W / 2}]
        foreach b $bands { lassign $b bn by; if {$bn eq $n} { odb::dbSBox_create $sw($n) $via $xc $by STRIPE; incr nv } }
    }
}
puts "PDN bands [llength $bands] stripes $ns vias $nv"
}
# NDR (넓은 아날로그 넷, 상용 판과 같은 폭·간격)
if {[info exists NDRS]} {
    foreach r $NDRS {
        lassign $r nm wl sl nets
        create_ndr -name $nm -width $wl -spacing $sl
        set k 0
        foreach pat $nets { foreach net [get_nets -quiet $pat] { assign_ndr -ndr $nm -net [get_full_name $net]; incr k } }
        puts "NDR $nm nets $k"
    }
}
stage floorplan

# ── 배치
global_placement -density $::env(DENS)
if {[info exists ROW_LIST]} {
    foreach r [$block getRows] { odb::dbRow_destroy $r }
    set k 0
    foreach r $ROW_LIST { lassign $r x y or n; odb::dbRow_create $block ROW_$k $site $x $y $or HORIZONTAL $n $SITE_W; incr k }
    puts "ROWS (std cell rows of the saved block) $k"
}
# 배치 막기 (매크로 영역, 저장된 블록과 같은 사각형): gpl 이 dummy 로 세어 이용률을 넘기므로 (GPL-0301) 전역 배치 뒤에 둔다
foreach b [expr {[info exists PLACE_BLK] ? $PLACE_BLK : {}}] { lassign $b x1 y1 x2 y2; odb::dbBlockage_create $block $x1 $y1 $x2 $y2 }
stage gpl
if {$::env(REPAIR) == 1} {
    set_wire_rc -signal -layer met2
    estimate_parasitics -placement
    repair_design
    stage repair
}
if {[catch {detailed_placement -use_diamond_legalizer -max_displacement {1000 100}}]} { detailed_placement -max_displacement {1000 100} }
check_placement -verbose
filler_placement {sky130_fd_sc_hvl__fill_8 sky130_fd_sc_hvl__fill_4 sky130_fd_sc_hvl__fill_2 sky130_fd_sc_hvl__fill_1}
check_placement
stage dpl

# ── 배선 (met1–met3 만: met4·met5 는 칩 전역 배선·전원 자리)
set_routing_layers -signal met1-met3
global_route -verbose -allow_congestion -congestion_iterations 100
stage grt
detailed_route -output_drc $OUTD/drt_drc.rpt -verbose 1
stage drt
set nopen 0
foreach net [$block getNets] {
    if {[$net getSigType] in {POWER GROUND} || [$net isSpecial]} { continue }
    if {[llength [$net getITerms]] + [llength [$net getBTerms]] > 1 && [$net getWire] eq "NULL"} { incr nopen; puts "NO WIRE [$net getName]" }
}
puts "NETS_WITHOUT_WIRE $nopen"
write_def $OUTD/$TOP.def
write_verilog $OUTD/${TOP}_pnr.v
write_verilog -include_pwr_gnd $OUTD/${TOP}_pnr_pg.v
set nc 0; set area 0.0; set nf 0
foreach i [$block getInsts] {
    set m [$i getMaster]
    if {[string match *fill_* [$m getName]]} { incr nf; continue }
    incr nc; set area [expr {$area + [um [$m getWidth]] * [um [$m getHeight]]}]
}
set carea [expr {[um [expr {$cx2 - $ROW_X}]] * [um [expr {$cy2 - $ROW_Y0}]]}]
puts [format "CELLS %d AREA %.1f FILLERS %d DENSITY %.3f" $nc $area $nf [expr {$area / $carea}]]
stage end
