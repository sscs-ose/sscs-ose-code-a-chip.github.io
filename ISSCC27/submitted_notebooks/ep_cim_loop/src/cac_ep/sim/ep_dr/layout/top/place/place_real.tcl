# core 1346.6 x 1133.14 um, 원점 = core 왼쪽 아래. location = 방향 적용 뒤 bbox 왼쪽 아래 (DEF COMPONENTS 와 같은 뜻).
# LEF: place/lef/<cell>.lef (ORIGIN 0 0). GDS merge: place_real.json 의 instances.<inst>.gds (원점을 LEF 원점에 맞춘 파일).
# floorplan 예: create_floorplan -box_size {0 0 1346.6 1133.14 0 0 1346.6 1133.14 0 0 1346.6 1133.14}
# 옛 명령 (legacy UI): placeInstance <inst> <x> <y> <R0|R180|MY> -fixed

set PLACE_REAL {
  {arr_f arr_w3s_128x64 686.090 665.100 r0}
  {arr_n arr_w3s_128x64 332.600 30.000 r180}
  {idrv_f input_drive 227.420 665.440 r0}
  {idrv_n input_drive 665.510 32.580 r180}
  {rowb_f row_blk 1019.000 660.580 r0}
  {rowb_n row_blk 30.000 88.130 r180}
  {colb_f col_blk 680.800 498.040 r0}
  {colb_n col_blk 330.280 473.040 r180}
  {data_f data_blk 181.620 661.730 r0}
  {data_n data_blk 1124.180 30.000 r180}
  {wu1 wu 218.480 511.625 my}
  {wbuf_n wbuf 136.270 511.625 r0}
  {rotg_n tg_n2 115.750 511.625 r0}
  {wu2 wu 1036.320 511.625 r0}
  {wbuf_f wbuf 1143.120 511.625 my}
  {rotg_f tg_n2 1225.330 511.625 r0}
  {glob glob_dig 30.000 1036.170 r0}
  {bias bias_beta 1179.980 30.000 r0}
  {ninj nudge_inj 1179.980 68.705 r0}
  {ilatb1 sky130_fd_sc_hvl__inv_2 307.680 496.540 r0}
  {ilatb2 sky130_fd_sc_hvl__inv_2 1036.320 496.540 r0}
  {tp_tl tp_tl 30.000 665.100 r0}
  {tp_bandl tp_bandl 30.000 477.560 r0}
  {tp_bandr tp_bandr 1268.170 483.040 r0}
  {tp_br tp_br 1179.980 116.370 r0}
}
foreach m $PLACE_REAL {
    lassign $m inst cell x y o
    place_inst $inst [list $x $y] $o -fixed
}
set nbad 0
foreach m $PLACE_REAL {
    lassign $m inst cell x y o
    set ib [get_db inst:$inst]
    lassign [lindex [get_db $ib .bbox] 0] bx1 by1 bx2 by2
    if {abs($bx1 - $x) > 0.001 || abs($by1 - $y) > 0.001 || [string tolower [get_db $ib .orient]] ne $o || [get_db $ib .place_status] ne "fixed"} {
        incr nbad; puts "PLACE_REAL MISPLACED $inst plan {$x $y $o} got {$bx1 $by1 [get_db $ib .orient] [get_db $ib .place_status]}"
    }
}
puts "PLACE_REAL placed [llength $PLACE_REAL], mismatched $nbad"
if {$nbad > 0} { error "placement != place_real" }

# test 자리 (블록 아직 없음, 배치만 비워 둠): tp_tl {30.000 665.100 118.180 969.220}, tp_bandl {30.000 477.560 78.420 631.240}, tp_bandr {1268.170 483.040 1316.600 636.720}, tp_br {1179.980 116.370 1268.160 446.440}
# 배선 자리 (route_areas): routing ring (bottom) {0.000 0.000 1346.600 30.000}, routing ring (top) {0.000 1103.140 1346.600 1133.140}, routing ring (left) {0.000 30.000 30.000 1103.140}, routing ring (right) {1316.600 30.000 1346.600 1103.140}, bus channel (nudge side) {330.280 635.100 665.800 665.100}, bus channel (middle) {665.800 468.040 680.800 665.100}, bus channel (free side) {680.800 468.040 1016.320 498.040}
