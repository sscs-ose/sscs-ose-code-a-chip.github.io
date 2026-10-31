#!/bin/bash
# opensrc/chip/run_step.sh 사본 — 도구 경로를 환경 변수로 받게만 바꿈 (Olympus 고정 경로 → MAGIC·NETGEN·PDK_ROOT), /usr/bin/time → nb_timeit.py.
# 쓰임: MAGIC=… NETGEN=… PDK_ROOT=… OPENSRC=<repo>/cac_ep/sim/ep_dr/opensrc signoff_step.sh read|drc|ext|lvs <gds> <top> <outdir> [cdl]
#   read = Magic GDS 읽기만 · drc = Magic DRC (drc(full)) · ext = Magic 추출 + antenna · lvs = Netgen (ext 결과 + CDL)
# 결과 요약: <outdir>/<단계>.json (opensrc/chip/summarize.py)
set -u
STEP=$1; GDS=$(readlink -f "$2"); TOP=$3; D=$(mkdir -p "$4" && readlink -f "$4"); CDL=${5:-}
O=${OPENSRC:?}; : "${MAGIC:?}" "${NETGEN:?}" "${PDK_ROOT:?}"
H=$(cd "$(dirname "$0")" && pwd)
export PDK_ROOT GDS TOP
export FLATGLOB=${FLATGLOB-"nsw_* bias_beta_p* nudge_inj_p* wbuf_p* tp_ch_* tp_kv_*"}
STD=$PDK_ROOT/sky130A/libs.tech/magic/sky130A.magicrc; RR=$(readlink -f "${RRAM_MAGICRC:-$O/tech/sky130A_rram.magicrc}")
mkdir -p "$D/ext" "$D/lvs"; cd "$D" || exit 1
T() { python3 "$H/nb_timeit.py" $STEP.time "$@"; }
case $STEP in
  read) export OUT=$PWD/read.sum; T $MAGIC -dnull -noconsole -rcfile $STD $O/chip/read_magic.tcl < /dev/null > read.log 2>&1 ;;
  drc)  RC=$STD; [ "${MAGIC_TECH:-std}" = rram ] && RC=$RR
        export OUT=$PWD/$TOP.magic.sum; T $MAGIC -dnull -noconsole -rcfile $RC $O/scripts/chip_drc_magic.tcl < /dev/null > drc.log 2>&1 ;;
  ext)  RC=$RR; [ "${MAGIC_TECH:-rram}" = std ] && RC=$STD
        export OUT=$PWD/ext/$TOP.mag.spice ANT=${ANT:-1}; T $MAGIC -dnull -noconsole -rcfile $RC $O/scripts/chip_ext_magic.tcl < /dev/null > ext.log 2>&1 ;;
  lvs)  cd lvs; python3 -I $O/scripts/cdl2spice_chip.py "$CDL" $TOP.src.spice && python3 -I $O/scripts/mag_fix_chip.py ../ext/$TOP.mag.spice $TOP.mag.spice > magfix.log || exit 3
        T $NETGEN -batch lvs "$TOP.mag.spice $TOP" "$TOP.src.spice $TOP" $PDK_ROOT/sky130A/libs.tech/netgen/sky130A_setup.tcl $TOP.netgen.out -json < /dev/null > netgen.log 2>&1; rc=$?; mv $STEP.time ..; cd ..; python3 -I $O/chip/summarize.py $STEP "$D" $TOP $rc; exit $rc ;;
  *) echo "단계: read|drc|ext|lvs"; exit 2 ;;
esac
rc=$?
python3 -I $O/chip/summarize.py $STEP "$D" $TOP $rc
exit $rc
