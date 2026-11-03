#!/bin/bash
# 디지털 블록 하나를 오픈소스로 RTL → GDS → 검사 (10/30). Yosys 합성 → OpenROAD 배치·배선 → KLayout GDS → Magic DRC → Magic 추출 + Netgen LVS
#   → Icarus 게이트 시뮬 (상용 판과 같은 testbench) → 저장된 블록과 외곽·핀 비교. 결과 요약 = <out>/<blk>/summary.json
# 쓰임: bash run_block.sh <glob_dig|data_blk> [out 폴더 (기본 digital_oss/out)]
# 도구: PATH 의 yosys openroad iverilog vvp python3 (klayout 모듈), 환경 MAGIC NETGEN PDK_ROOT (노트북이 정함, 없으면 PATH·~/pdk/volare)
set -u
H=$(cd "$(dirname "$0")" && pwd); EP=$(dirname "$H")
BLK=${1:?block}; OUTR=${2:-$H/out}; O=$OUTR/$BLK
[ -f "$H/blocks/$BLK/block.env" ] || { echo "블록 없음: $BLK"; exit 2; }
source "$H/blocks/$BLK/block.env"
PY=${PY:-python3}; YOSYS=${YOSYS:-yosys}; OPENROAD=${OPENROAD:-openroad}; IVERILOG=${IVERILOG:-iverilog}; VVP=${VVP:-vvp}
export MAGIC=${MAGIC:-magic} NETGEN=${NETGEN:-netgen} PDK_ROOT=${PDK_ROOT:-$HOME/pdk/volare} OPENSRC=${OPENSRC:-$EP/opensrc}
NTHR=${NJ:-4}
P=$EP/digital/pdk                      # hvl 셀 파일 (tech LEF, 셀 LEF, ff 5.5 V lib, GDS, CDL (u 붙임), Verilog 모형)
SS="bash $EP/layout/top/oss_nb/tools/signoff_step.sh"
REF_LEF=$EP/layout/top/route_oss/chip/lef/$TOP.lef; REF_CDL=$EP/layout/top/net/lib/$TOP.cdl
mkdir -p "$O"; cd "$O" || exit 1
[ "${SKIP_PNR:-0}" = 1 ] || : > steps.txt
T() { local n=$1; shift; local t0=$(date +%s%N); "$@"; local rc=$?; local ms=$(( ($(date +%s%N) - t0) / 1000000 )); echo "$n $((ms / 1000)).$(( (ms % 1000) / 100 )) $rc" >> steps.txt; return $rc; }
rtl=""; for f in $RTL; do rtl="$rtl $EP/$f"; done
tb=""; for f in $TB; do tb="$tb $EP/$f"; done
# 매크로 블록 (block.env 의 MACRO_VH·XLEF·XGDS·XCDL): top RTL = 디지털 RTL + 매크로 인스턴스 목록, 매크로 LEF·GDS·CDL
XLEF=${XLEF:-}; XGDS=${XGDS:-}; XCDL=${XCDL:-}
xlef=""; for f in $XLEF; do xlef="$xlef $EP/$f"; done
xgds=""; for f in $XGDS; do xgds="$xgds,$EP/$f"; done
xcdl=""; for f in $XCDL; do xcdl="$xcdl,$EP/$f"; done
if [ -n "${MACRO_VH:-}" ]; then $PY "$H/flow/mk_${TOP}_v.py" "$EP/$MACRO_VH" $O/${TOP}_top.v > /dev/null || exit 3; rtl="$rtl $O/${TOP}_top.v"; fi
FILLJ=""; [ -f "$H/blocks/$BLK/fill.json" ] && FILLJ="$H/blocks/$BLK/fill.json"

# 1. 쓸 셀만 남긴 liberty, Yosys 합성 (개발용: SKIP_PNR=1 이면 1–2 단계를 건너뛰고 있는 DEF·netlist 를 씀)
if [ "${SKIP_PNR:-0}" != 1 ]; then
T lib $PY "$H/flow/mk_lib.py" $P/sky130_fd_sc_hvl__ff_085C_5v50.lib hvl_ok.lib "$H/flow/cells.txt" > lib.log 2>&1 || { cat lib.log; exit 3; }
T synth env TOP=$TOP RTL="$rtl" LIBF=$O/hvl_ok.lib OUT=$O/${TOP}_syn.v STAT=$O/synth_stat.rpt $YOSYS -q -l yosys.log -c "$H/flow/synth.tcl" > /dev/null 2>&1 \
  || { tail -20 yosys.log; exit 4; }
grep -q conb_1 ${TOP}_syn.v && { echo "conb_1 (상수) 가 생김 — 쓰지 않는 셀"; exit 4; }
# 2. OpenROAD 배치·배선
CLEAR_PINS="${CLEAR_PINS:-}" $PY "$H/flow/fp_tcl.py" "$H/blocks/$BLK" fp.tcl > fp.log
T pnr env FPTCL=$O/fp.tcl XLEF="$xlef" TLEF=$P/sky130_fd_sc_hvl__nom.tlef SCLEF=$P/sky130_fd_sc_hvl.lef LIBF=$O/hvl_ok.lib NL=$O/${TOP}_syn.v \
  SDC=$EP/$SDC OUTD=$O NTHR=$NTHR DENS=$DENS REPAIR=$REPAIR $OPENROAD -exit -no_init -threads $NTHR "$H/flow/pnr.tcl" > openroad.log 2>&1 \
  || { grep -aE "ERROR|Error" openroad.log | head; tail -5 openroad.log; exit 5; }
fi
# 3. GDS (KLayout) · LVS source CDL
T gds env FILL="$FILLJ" $PY "$H/flow/def2gds_blk.py" $TOP.def $TOP.gds "$EP/layout/top/route_oss/kl/sky130_kl.map" $P/sky130_fd_sc_hvl.gds$xgds \
  $P/sky130_fd_sc_hvl__nom.tlef $P/sky130_fd_sc_hvl.lef $xlef > gds.log 2>&1 || { cat gds.log; exit 6; }
T cdl $PY "$H/flow/v2cdl_oss.py" ${TOP}_pnr.v $P/sky130_fd_sc_hvl_u.cdl$xcdl "$H/blocks/$BLK/pins.cfg" $TOP.cdl > cdl.log 2>&1 || { cat cdl.log; exit 6; }
cp $TOP.cdl ${TOP}_lvs.cdl       # 블록 CDL 이 hvl 셀·매크로 CDL 을 .INCLUDE 함
# 4. 저장된 블록과 비교 (외곽·핀·CDL 머리줄)
T cmp $PY "$H/flow/cmp_ref.py" $TOP.def "$REF_LEF" $TOP.cdl "$REF_CDL" cmp_ref.json > cmp.log 2>&1; cat cmp.log
# 5. 게이트 시뮬 (배선 뒤 netlist, 상용 판과 같은 testbench·모형: hvl Verilog 기능 모형, DFF 단위 지연)
T gatesim bash -c "$IVERILOG -g2005 -DFUNCTIONAL -DUNIT_DELAY=#1 -o tb_gate.vvp $P/primitives.v $P/sky130_fd_sc_hvl.v ${TOP}_pnr.v $tb > gate_sim.log 2>&1 && $VVP -n tb_gate.vvp >> gate_sim.log 2>&1"
grep -a "TB_" gate_sim.log | tail -1
# 6. Magic DRC · 추출 + Netgen LVS (노트북 signoff_step.sh, 표준 Magic tech)
T drc env MAGIC_TECH=std FLATGLOB="" $SS drc $O/$TOP.gds $TOP $O/signoff > /dev/null 2>&1
T ext env MAGIC_TECH=std FLATGLOB="" ANT=1 $SS ext $O/$TOP.gds $TOP $O/signoff > /dev/null 2>&1
T lvs env FLATGLOB="" $SS lvs $O/$TOP.gds $TOP $O/signoff $O/${TOP}_lvs.cdl > /dev/null 2>&1
# Magic hvntm.1 표시가 거짓 양성인지 (그려진 hvntm 폭·간격, opensrc 「정한 것」 과 같은 판정)
T hvntm $PY "$H/flow/hvntm_check.py" $TOP.gds $TOP signoff/$TOP.magic.sum.boxes hvntm.json > hvntm.log 2>&1
# 7. 요약
REFDRC="$H/blocks/$BLK/ref_magic_drc.json" TOP=$TOP TBPASS="$TBPASS" $PY - <<'EOF'
import json, os, re
top = os.environ['TOP']
st = {l.split()[0]: dict(s=float(l.split()[1]), rc=int(l.split()[2])) for l in open('steps.txt')}
log = open('openroad.log', errors='replace').read()
cells = re.search(r'CELLS (\d+) AREA ([\d.]+) FILLERS (\d+) DENSITY ([\d.]+)', log)
drt = re.findall(r'Number of violations = (\d+)', log)
nw = re.search(r'NETS_WITHOUT_WIRE (\d+)', log)
syn = open('synth_stat.rpt').read()
sc = re.search(r'(\d+)\s+(?:[\d.]+\s+)?cells\b', syn)
j = lambda p: json.load(open(p)) if os.path.exists(p) else {}
drc, lvs, ext, cmp, hv = j('signoff/drc.json'), j('signoff/lvs.json'), j('signoff/ext.json'), j('cmp_ref.json'), j('hvntm.json')
# DRC 판정: hvntm.1 은 그려진 층으로 재서 거짓 양성이면 통과, 나머지 규칙은 저장된 블록 GDS 의 같은 Magic DRC 에도 있고 수가 그 이하일 때만
refd = j(os.environ['REFDRC']).get('rules', {})
rules = drc.get('rules') or {}
drc_extra = {k: v for k, v in rules.items() if k != 'hvntm.1' and v > refd.get(k, 0)}
g = open('gate_sim.log', errors='replace').read()
S = dict(block=top, steps=st, synth_cells=int(sc.group(1)) if sc else None,
         cells=int(cells.group(1)) if cells else None, cell_area_um2=float(cells.group(2)) if cells else None,
         fillers=int(cells.group(3)) if cells else None, density=float(cells.group(4)) if cells else None,
         drt_violations=int(drt[-1]) if drt else None, nets_without_wire=int(nw.group(1)) if nw else None,
         same_as_saved=cmp.get('identical'), cmp=cmp, gate_sim=os.environ['TBPASS'] in g,
         drc_total=drc.get('total'), drc_rules=drc.get('rules'), hvntm=hv,
         drc_ref=refd, drc_beyond_saved=drc_extra,
         drc_ok=drc.get('total') is not None and not drc_extra and ('hvntm.1' not in rules or hv.get('false_positive', False)), antenna=ext.get('antenna_violations'),
         lvs=lvs.get('final'), lvs_ok='match uniquely' in str(lvs.get('final')).lower(),
         total_s=round(sum(v['s'] for v in st.values()), 1))
json.dump(S, open('summary.json', 'w'), indent=1)
print('SUMMARY', json.dumps({k: S[k] for k in ('block', 'cells', 'cell_area_um2', 'density', 'drt_violations', 'same_as_saved', 'gate_sim', 'drc_total', 'drc_rules', 'drc_ok', 'lvs', 'total_s')}, ensure_ascii=False))
EOF
