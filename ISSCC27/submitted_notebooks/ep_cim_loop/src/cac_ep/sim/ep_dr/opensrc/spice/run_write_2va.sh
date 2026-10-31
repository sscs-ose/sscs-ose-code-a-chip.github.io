#!/bin/bash
# 칩 쓰기 덱 (chip_write3 형식) 을 ngspice + OSDI 로 — 쓰는 셀 2 개만 RRAM Verilog-A, 나머지 RRAM 은 고정 저항 (10/30). 클러스터 없이 (노트북·로컬).
# 쓰임: [STATIC=lin|sinh] [NT=스레드] [TMAX=20p] [METHOD=gear|trap] [ABSTOL=1e-12] [TSTOP=…] bash run_write_2va.sh <SPICE 덱 .sp (옆에 _ref.json)> <출력 폴더>
# ngspice 설정 (10/30 Olympus 시험): abstol 1e-15 (SPICE absi 와 같게) 이면 첫 시간점에서 verify 전류계 vvern 이 안 모임 → 1e-12.
#   tmax 를 tstep (20 ps, ngspice 기본) 보다 크게 하면 PWL 가장자리에서 같은 vvern 로 멈춤: gear 30·50 ps 는 15.2 ns (RST 내림), trap 50 ps 는 70.2 ns (SCK).
#   abstol 1e-9…1e-11 로 풀어도 같음 → gear + tmax 20 ps + abstol 1e-12 (끝까지 감, 느림).
# 환경: NGSPICE, OPENVAF (없으면 PATH), PY (없으면 python3). 결과: <출력>/chip.log (.meas), chip.raw (파형), cmp.md (SPICE 대조표).
set -e
H=$(dirname "$(readlink -f "$0")"); DECK=$(readlink -f "$1"); W=$(readlink -m "$2"); mkdir -p "$W"; cd "$W"
PY=${PY:-python3}; NG=${NGSPICE:-ngspice}; OV=${OPENVAF:-openvaf}
ST=${STATIC:-lin}; NT=${NT:-2}; TMAX=${TMAX:-20p}; METHOD=${METHOD:-gear}; ABSTOL=${ABSTOL:-1e-12}
REF=${DECK%.sp}_ref.json
# 1) RRAM VA (t0 판: 동작점에서 상태 변화율 0) → OSDI
[ -f reram_t0.osdi ] || $OV "$H/va/sky130_fd_pr_reram__reram_cell_osdi_t0.va" -o reram_t0.osdi
# 2) 쓰는 셀 2 개만 VA, 나머지 338 개 = 초기 G 의 저항 → ngspice 문법
$PY -I "$H/mk_write_2va.py" "$DECK" chip_2va.sp --ref "$REF" --static $ST --va "$H/va/orig_sky130_fd_pr_reram__reram_cell.va"
$PY -I "$H/spice2ng_osdi.py" chip_2va.sp chip.cir 1e-4
sed -i -E "1,4s/abstol=\S+/abstol=$ABSTOL/; 1,4s/method=\S+/method=$METHOD/" chip.cir; sed -n 2p chip.cir
P=$(grep -i '^\.probe' chip_2va.sp | sed -E 's/^\.probe\s+tran\s+//I' || true); [ -n "$P" ] && sed -i "0,/^\.save/s//.save $P/" chip.cir
[ -n "$TSTOP" ] && sed -i -E "s/^\.tran (\S+) (\S+)/.tran \1 $TSTOP/" chip.cir
sed -i -E "s/^\.tran (\S+) (\S+)\s*$/.tran \1 \2 0 $TMAX/" chip.cir          # tmax 를 적어 둠 (기본 20 ps = tstep)
printf 'set ngbehavior=hsa\nset num_threads=%s\nosdi %s/reram_t0.osdi\n' "$NT" "$W" > .spiceinit
t0=$(date +%s); set +e; $NG -b chip.cir -o chip.log -r chip.raw > chip.stdout 2>&1; rc=$?; set -e
echo "ngspice rc=$rc $(( $(date +%s)-t0 )) s  $(grep -m1 -i 'too small\|error' chip.log || true)"
# 3) SPICE (RRAM VA 340 개) 와 대조
$PY -I "$H/cmp_write_2va.py" "$H/ref/chip_write3_spice_meas.txt" chip.log > cmp.md && cat cmp.md
exit $rc
