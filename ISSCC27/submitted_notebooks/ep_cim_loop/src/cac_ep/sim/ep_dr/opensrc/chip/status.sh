#!/bin/bash
# 제출 판 오픈소스 signoff 상태 (Olympus). 쓰임: bash status.sh  → 잡 목록 + 단계별 json 한 줄씩
S=/mnt/shared-scratch/Yi_S/seokjindaveoh/ep_dr_opensrc_runs
squeue -u $USER -h -o "%.10i %.14j %.8T %.10M" | grep "ep_dr_step\|ep_dr_chip"
for d in core_s die_s; do for s in read drc ext lvs; do
  f=$S/$d/$s.json; [ -s $f ] && python3 -c "import json;d=json.load(open('$f'));print('$d', '$s', {k:d.get(k) for k in ('exit','wall_s','maxrss_mb','total','hvntm_1','antenna_violations','final')})"
done; done
