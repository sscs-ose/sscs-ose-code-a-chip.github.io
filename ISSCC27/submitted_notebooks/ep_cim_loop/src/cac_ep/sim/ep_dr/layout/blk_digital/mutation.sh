#!/bin/bash
# testbench 가 틀린 RTL 을 잡는지 (돌연변이 시험): RTL 사본을 한 군데씩 고쳐 FAIL 이 나와야 한다
cd /home/grads/s/seokjindaveoh/work/ep_dr/layout/blk_digital
IV=~/cac/env/bin; HP=pdk
md() {  # $1 이름, $2 sed 식
  sed "$2" rtl/data_blk.v > mut/d.v; cmp -s mut/d.v rtl/data_blk.v && { echo "$1: sed no-op"; return; }
  $IV/iverilog -g2005 -o mut/d.vvp mut/d.v tb/ref_data_blk.v tb/tb_data_blk.v && echo "$1: $($IV/vvp -n mut/d.vvp | grep -a "TB_DATA: [PF]")"
}
mg() {
  sed "$2" rtl/glob_dig.v > mut/g.v; cmp -s mut/g.v rtl/glob_dig.v && { echo "$1: sed no-op"; return; }
  $IV/iverilog -g2005 -DFUNCTIONAL -o mut/g.vvp $HP/primitives.v $HP/sky130_fd_sc_hvl.v rtl/glob_cells.v mut/g.v tb/ref_glob_dig.v tb/tb_glob_dig.v 2>/dev/null && echo "$1: $($IV/vvp -n mut/g.vvp | grep -a "TB_GLOB: [PF]")"
}
md "d1 shift dir " "s/q <= {q\[N-2:0\], sdi}/q <= {sdi, q[N-1:1]}/"
md "d2 gb=READ.dl" "s/assign gb  = {NI{READ}} \& ~dl/assign gb  = {NI{READ}} \& dl/"
md "d3 latch ~dld" "s/if (dload) dl = q/if (!dload) dl = q/"
md "d4 sp<->sm   " "s/assign sp  = {NO{READ}} \& dl/assign sp  = {NO{READ}} \& ~dl/"
md "d5 neg edge  " "s/posedge data_clk/negedge data_clk/"
mg "g1 cfg order " "s/wire m1 = cfg\[0\], m0 = cfg\[1\]/wire m1 = cfg[1], m0 = cfg[0]/"
mg "g2 PROG noFRM" "s/wire PROG  = FORM | (WRm \& ~pv)/wire PROG  = (WRm \& ~pv)/"
mg "g3 sck_r sld " "s/wire sck_r = sck \& sldb/wire sck_r = sck \& sld/"
mg "g4 latch sld " "s/if (sldb) cfg = cq/if (sld) cfg = cq/"
mg "g5 SENSE     " "s/wire SENSE = READ \& wu_en/wire SENSE = READ/"
mg "g6 ts swap   " "s/ts_row1 = cfg\[8\], ts_row2 = cfg\[9\]/ts_row1 = cfg[9], ts_row2 = cfg[8]/"
mg "g7 neg edge  " "s/posedge cfg_clk/negedge cfg_clk/"
