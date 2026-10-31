#!/bin/bash
# 제출 판 오픈소스 signoff 한 단계. 쓰임 (Olympus, sbatch --wrap 또는 셸):
#   run_step.sh read|drc|ext|lvs <gds> <top> <outdir> [cdl]
#   read = Magic GDS 읽기만 · drc = Magic DRC (drc(full)) · ext = Magic 추출 + antenna (같은 Magic 실행) · lvs = Netgen (ext 결과 + CDL)
# 결과 요약 (노트북이 바로 읽음): <outdir>/<단계>.json  (+ drc → <top>.magic.sum, ext → ext/<top>.mag.spice·antenna.fb, lvs → lvs/<top>.netgen.out)
# 환경: FLATGLOB (기본 = 소자 층이 계층에 나뉜 셀 틀, 아래), MAGIC_TECH=std|rram (ext 기본 rram, drc 기본 std)
set -u
STEP=$1; GDS=$(readlink -f "$2"); TOP=$3; D=$(mkdir -p "$4" && readlink -f "$4"); CDL=${5:-}
O=/home/grads/s/seokjindaveoh/work/ep_dr/opensrc; MAGIC=$HOME/opt/oss_eda/bin/magic; NETGEN=$HOME/cac/env/bin/netgen
export PDK_ROOT=$O/pdk GDS TOP
export FLATGLOB=${FLATGLOB-"nsw_* bias_beta_p* nudge_inj_p* wbuf_p* tp_ch_* tp_kv_*"}
STD=$PDK_ROOT/sky130A/libs.tech/magic/sky130A.magicrc; RR=$(readlink -f $O/tech/sky130A_rram.magicrc)
mkdir -p "$D/ext" "$D/lvs"; cd "$D" || exit 1
T() { /usr/bin/time -f "%e %M" -o $STEP.time "$@"; }
case $STEP in
  read) export OUT=$PWD/read.sum; T $MAGIC -dnull -noconsole -rcfile $STD $O/chip/read_magic.tcl < /dev/null > read.log 2>&1 ;;
  drc)  RC=$STD; [ "${MAGIC_TECH:-std}" = rram ] && RC=$RR
        export OUT=$PWD/$TOP.magic.sum; T $MAGIC -dnull -noconsole -rcfile $RC $O/scripts/chip_drc_magic.tcl < /dev/null > drc.log 2>&1 ;;
  ext)  RC=$RR; [ "${MAGIC_TECH:-rram}" = std ] && RC=$STD
        export OUT=$PWD/ext/$TOP.mag.spice ANT=1; T $MAGIC -dnull -noconsole -rcfile $RC $O/scripts/chip_ext_magic.tcl < /dev/null > ext.log 2>&1 ;;
  lvs)  cd lvs; python3 -I $O/scripts/cdl2spice_chip.py "$CDL" $TOP.src.spice && python3 -I $O/scripts/mag_fix_chip.py ../ext/$TOP.mag.spice $TOP.mag.spice > magfix.log || exit 3
        T $NETGEN -batch lvs "$TOP.mag.spice $TOP" "$TOP.src.spice $TOP" $PDK_ROOT/sky130A/libs.tech/netgen/sky130A_setup.tcl $TOP.netgen.out -json < /dev/null > netgen.log 2>&1; rc=$?; mv $STEP.time ..; cd ..; python3 -I $O/chip/summarize.py $STEP "$D" $TOP $rc; exit $rc ;;
  *) echo "단계: read|drc|ext|lvs"; exit 2 ;;
esac
rc=$?
python3 -I $O/chip/summarize.py $STEP "$D" $TOP $rc
