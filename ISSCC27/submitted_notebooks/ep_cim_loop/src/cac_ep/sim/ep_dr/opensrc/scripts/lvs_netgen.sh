#!/bin/bash
# 오픈소스 LVS — Magic 추출 + Netgen 비교 (sky130A_setup.tcl). 블록 하나.
# 쓰임: lvs_netgen.sh <gds> <cdl> <top> <outdir>   (환경 MAGIC_TECH=rram 이면 RRAM 을 뽑는 Magic tech 사본 tech/sky130A_rram.magicrc 사용)
#   → <outdir>/<top>.mag.spice (추출), <top>.src.spice (CDL 변환), <top>.netgen.out (비교 보고), <top>.lvs.sum (결과 한 줄)
set -u
HERE=$(dirname "$(readlink -f "$0")"); GDS=$(readlink -f "$1"); CDL=$(readlink -f "$2"); TOP=$3; OUT=$4
OSS=${OSS:-$HOME/opt/oss_eda}; MAGIC=${MAGIC:-$OSS/bin/magic}; NETGEN=${NETGEN:-$HOME/cac/env/bin/netgen}
export PDK_ROOT=${PDK_ROOT:-$HOME/work/ep_dr/opensrc/pdk}
RC=$PDK_ROOT/sky130A/libs.tech/magic/sky130A.magicrc
[ "${MAGIC_TECH:-}" = rram ] && RC=$(readlink -f "$HERE/../tech/sky130A_rram.magicrc")
SETUP=$PDK_ROOT/sky130A/libs.tech/netgen/sky130A_setup.tcl
mkdir -p "$OUT/ext"; cd "$OUT" || exit 1
t0=$(date +%s.%N)
GDS=$GDS TOP=$TOP OUT=$PWD/ext/$TOP.mag.spice "$MAGIC" -dnull -noconsole -rcfile "$RC" "$HERE/ext_magic.tcl" < /dev/null > ext_magic.log 2>&1
cp ext/$TOP.mag.spice $TOP.mag.spice
t1=$(date +%s.%N)
"$OSS/bin/python" -I "$HERE/cdl2spice.py" "$CDL" "$TOP.src.spice"
"$NETGEN" -batch lvs "$TOP.mag.spice $TOP" "$TOP.src.spice $TOP" "$SETUP" "$TOP.netgen.out" -json < /dev/null > netgen.log 2>&1
t2=$(date +%s.%N)
res=$(grep -E "^Final result" "$TOP.netgen.out" | tail -1)
printf 'lvs top=%s magic_tech=%s result="%s" extract_s=%.1f netgen_s=%.1f\n' "$TOP" "${MAGIC_TECH:-std}" "$res" \
  "$(echo "$t1 - $t0" | bc)" "$(echo "$t2 - $t1" | bc)" | tee "$TOP.lvs.sum"
