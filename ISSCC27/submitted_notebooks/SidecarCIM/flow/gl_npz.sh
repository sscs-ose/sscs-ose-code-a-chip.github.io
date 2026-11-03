#!/bin/bash
# usage: gl_npz.sh <flowdir> <top> <kind dense|dense8|w6a4|w8a4|top> <npz> <tag random|real>
# env: RUN=<run dir> (default newest flow/<flowdir>/runs/RUN_*), NCASES (default 100), GL_UD (cell delay, ns)
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT"; source .venv/bin/activate
fd=$1; top=$2; kind=$3; npz=$4; tag=$5
fdn=${fd//\//_}
[ $kind = top ] && export GL_IN="rst w_load_en w_load_addr w_load_row s_load_en s_load_col s_load_slots s_load_shift start x_in"
run=${RUN:-$(ls -d flow/$fd/runs/RUN_*|tail -1)}
pre=flow/vcd_compute/${fdn}_$tag
python3 flow/gl_stim_npz.py $kind $npz ${NCASES:-100} $pre
mkdir -p /tmp/gl_$fdn$tag
GL_UD=${GL_UD:-0} python3 flow/gl_sim.py $top $run $pre flow/vcd_compute/${fdn}_$tag.gl.vcd /tmp/gl_$fdn$tag | grep -v "VCD info"
python3 flow/vcd_window.py flow/vcd_compute/${fdn}_$tag.gl.vcd flow/vcd_compute/${fdn}_$tag.busy.vcd
rm -f flow/vcd_compute/${fdn}_$tag.gl.vcd
POW_TAG=$tag bash flow/power.sh $fd $run flow/vcd_compute/${fdn}_$tag.busy.vcd tb/dut
grep "^Total" $run/power_$tag.rpt
