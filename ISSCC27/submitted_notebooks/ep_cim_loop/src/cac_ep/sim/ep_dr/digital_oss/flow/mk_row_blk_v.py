"""row_blk top RTL (오픈소스 합성 입력): row_ctrl (RTL) + 행 MUX 매크로 636 개 (행마다 ROWM = TGW 1 + TG 5).
매크로 연결 규칙은 상용 판 digital/row_blk/mk_netlist.py 와 같다 (chip_lib.py ROWM 줄 → rowm.json 사본을 읽음, 인스턴스 이름 rm<r>_<XT1…>):
a 가 vdd 인 TG → rb_tg_n2_av, vss 인 TG → rb_tg_n2_as (a 핀 없음), 노드 0 → vzero, bus = R1 (행 < 100) / R2.
쓰임: python3 mk_row_blk_v.py <digital/row_blk/rowm.json> <out.v>"""
import json
import sys
src, out = sys.argv[1:3]
NR, N1 = 106, 100
L = json.load(open(src))['ROWM']
hdr = L[0].split()
assert hdr[:2] == ['.subckt', 'ROWM']
DEC = ['wsel', 'wselb', 'wz', 'wzb', 'sns', 'snsb', 'wlv', 'wlvb', 'wlw', 'wlwb', 'wl0', 'wl0b']
INPUTS = ['sdi', 'row1_clk', 'row2_clk', 'rstb', 'sel_en', 'PROG', 'VER', 'SENSE', 'READb', 'WRANY']
ANALOG = ['vw', 'vwl', 'vzero', 'R1', 'R2']


def actual(f, r):
    if f == '0':
        return 'vzero'
    if f in ('row', 'wl') or f in DEC:
        return f'{f}[{r}]'
    if f == 'bus':
        return 'R1' if r < N1 else 'R2'
    assert f in ('vw', 'vwl'), f
    return f


insts = []
for ln in L[1:-1]:
    t = ln.split()
    name, (a, b, en, enb, vdd, vss), typ = t[0], t[1:-1], t[-1]
    if a == 'vdd':
        insts.append((name, 'rb_tg_n2_av', {'b': b, 'ctl': en, 'ctlb': enb}))
    elif a == 'vss':
        insts.append((name, 'rb_tg_n2_as', {'b': b, 'ctl': en, 'ctlb': enb}))
    else:
        insts.append((name, 'rb_tgw_n20' if typ == 'TGW' else 'rb_tg_n2', {'a': a, 'b': b, 'ctl': en, 'ctlb': enb}))
V = ['// row_blk top — mk_row_blk_v.py (row_ctrl + ROWM 매크로)',
     '(* blackbox *) module rb_tg_n2 (inout a, inout b, input ctl, input ctlb); endmodule',
     '(* blackbox *) module rb_tgw_n20 (inout a, inout b, input ctl, input ctlb); endmodule',
     '(* blackbox *) module rb_tg_n2_av (inout b, input ctl, input ctlb); endmodule',
     '(* blackbox *) module rb_tg_n2_as (inout b, input ctl, input ctlb); endmodule',
     f'module row_blk ({", ".join(INPUTS + ANALOG)}, row, wl);',
     f'  input {", ".join(INPUTS)};', f'  inout {", ".join(ANALOG)};', '  inout [105:0] row, wl;',
     f'  wire [105:0] {", ".join(DEC)};',
     '  row_ctrl u_ctrl (' + ', '.join(f'.{p}({p})' for p in INPUTS + DEC) + ');']
for r in range(NR):
    for name, cell, pins in insts:
        V.append(f'  {cell} rm{r}_{name} (' + ', '.join(f'.{p}({actual(f, r)})' for p, f in pins.items()) + ');')
V += ['endmodule', '']
open(out, 'w').write('\n'.join(V))
print('row_blk top', out, 'macros', NR * len(insts))
