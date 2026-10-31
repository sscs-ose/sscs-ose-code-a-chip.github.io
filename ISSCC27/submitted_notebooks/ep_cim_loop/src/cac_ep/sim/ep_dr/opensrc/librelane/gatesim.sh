#!/bin/bash
# digital/run_row.sbatch 의 2b-gate-sim-pnr 와 같은 명령, netlist 만 LibreLane 것. 쓰임: bash gatesim.sh <run 태그>
D=/home/grads/s/seokjindaveoh/work/ep_dr/digital; HP=$D/pdk; IV=~/cac/env/bin
R=/home/grads/s/seokjindaveoh/work/ep_dr/opensrc/librelane/row_ctrl/runs/$1; cd $R || exit 1
t0=$(date +%s)
$IV/iverilog -g2005 -DFUNCTIONAL -DUNIT_DELAY=#1 -o tb_gate.vvp $HP/primitives.v $HP/sky130_fd_sc_hvl.v final/nl/row_ctrl.nl.v \
  $D/tb/ref_rowl.v $D/tb/tb_row_ctrl.v > gate_sim.log 2>&1 && $IV/vvp -n tb_gate.vvp >> gate_sim.log 2>&1
echo "gate sim elapsed=$(( $(date +%s)-t0 ))s"; grep -a "TB_ROW:" gate_sim.log || tail -20 gate_sim.log
