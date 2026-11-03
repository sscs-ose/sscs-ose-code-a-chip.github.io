#!/bin/bash
# ReRAM VA → OSDI (OpenVAF) → 1R 쓰기 격자를 ngspice 47 과 VACASK 로. 쓰임: bash run_osdi_cell.sh <VA 파일> <태그> [SPICE p1r 덱]
# (sbatch --wrap 으로 부름. 결과 runs/spice/osdi_<태그>/)
VA=$(readlink -f "$1"); TAG=$2; DECK=${3:-/home/grads/s/seokjindaveoh/work/ep_demo/char/decks/p1r_pw10n.sp}
O=/home/grads/s/seokjindaveoh/work/ep_dr/opensrc; S=/mnt/shared-scratch/Yi_S/seokjindaveoh/oss_img/iic-osic-tools.sif
W=$O/runs/spice/osdi_$TAG; mkdir -p $W; cd $W || exit 1
cp $VA reram.va
singularity exec $S /foss/tools/bin/openvaf reram.va -o reram_ov.osdi > openvaf.log 2>&1; echo "openvaf rc=$?"
singularity exec $S /foss/tools/bin/openvaf-r reram.va -o reram_ovr.osdi > openvaf_r.log 2>&1; echo "openvaf-r rc=$?"
~/opt/oss_eda/bin/python -I $O/spice/p1r_cells.py $DECK $W reram_ovr.osdi
printf 'set ngbehavior=hsa\nosdi %s/reram_ov.osdi\n' "$W" > .spiceinit
t0=$(date +%s); ~/opt/ngspice-47/bin/ngspice -b p1r_ng.cir -o p1r_ng.log > p1r_ng.stdout 2>&1; echo "ngspice rc=$? $(( $(date +%s)-t0 ))s"
grep -m3 -i "error\|too small\|abort" p1r_ng.log
t0=$(date +%s); singularity exec $S /foss/tools/bin/vacask p1r_vc.sim > p1r_vc.log 2>&1; echo "vacask rc=$? $(( $(date +%s)-t0 ))s"; tail -3 p1r_vc.log
ls -la
