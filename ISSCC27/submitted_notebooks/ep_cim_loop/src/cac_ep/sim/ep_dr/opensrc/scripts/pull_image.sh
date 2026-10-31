#!/bin/bash
# 컨테이너 이미지 받기 (Olympus singularity, 사용자 권한). 풀기 (rootfs) 는 login 노드 tmpfs /tmp 에서 — 공유 scratch 에서 풀면
# nix store 의 작은 파일이 많아 15 MB/분 (10/28 첫 시도, 40 분에 92 MB) 로 끝나지 않는다.
# 쓰임: nohup scripts/pull_image.sh <out.sif> <docker://…> > <log> 2>&1 &
OUT=$1; SRC=$2; T=/tmp/sing_$USER/$(basename "$OUT" .sif); mkdir -p "$T"
t0=$(date +%s)
SINGULARITY_DISABLE_CACHE=true SINGULARITY_TMPDIR=$T singularity pull --force "$OUT" "$SRC"
echo "EXIT $? pull_s=$(( $(date +%s)-t0 ))"; ls -la "$OUT"
