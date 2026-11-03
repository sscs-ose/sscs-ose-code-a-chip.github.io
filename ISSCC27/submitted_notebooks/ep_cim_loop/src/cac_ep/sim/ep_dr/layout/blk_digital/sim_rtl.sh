#!/bin/bash
# RTL 시뮬만 (두 블록). glob_dig 는 출력 구동 셀이 hvl 셀이라 hvl 기능 모형을 같이 읽는다
cd /home/grads/s/seokjindaveoh/work/ep_dr/layout/blk_digital
IV=~/cac/env/bin; HP=pdk
$IV/iverilog -g2005 -o tb_data_rtl.vvp rtl/data_blk.v tb/ref_data_blk.v tb/tb_data_blk.v && $IV/vvp -n tb_data_rtl.vvp > rtl_data_sim.log 2>&1
tail -25 rtl_data_sim.log
$IV/iverilog -g2005 -DFUNCTIONAL -o tb_glob_rtl.vvp $HP/primitives.v $HP/sky130_fd_sc_hvl.v rtl/glob_cells.v rtl/glob_dig.v tb/ref_glob_dig.v tb/tb_glob_dig.v && $IV/vvp -n tb_glob_rtl.vvp > rtl_glob_sim.log 2>&1
tail -25 rtl_glob_sim.log
