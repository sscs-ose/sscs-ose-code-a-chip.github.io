#!/usr/bin/env python3
"""row_ctrl_syn.v (Genus 평탄 netlist) + ROWM 매크로 636 개 → row_blk_syn.v (평탄 module row_blk).

- 논리 기준: ../../real_circuit/chip_lib.py 의 ROWM 줄 (읽기만, ast 로 목록을 읽어 매크로 연결을 그대로 옮김 → 손으로 적은 표 없음).
  Olympus 에는 real_circuit/chip_lib.py 가 없어 로컬에서 읽을 때 rowm.json 사본을 쓰고, 없으면 그것을 읽는다
    ROWM row wl bus vw vwl wsel wselb wz wzb sns snsb wlv wlvb wlw wlwb wl0 wl0b vdd vss
    TG / TGW 포트 = a b en enb vdd vss  (en = nfet 게이트 = 매크로 ctl, enb = pfet 게이트 = 매크로 ctlb)
- 행 r 의 bus = R1 (r < N1 = 100) / R2 (r >= 100)  (gen_chip_deck3.py: bus = R1 if r < NRX else R2)
- a 가 vdd 인 TG → rb_tg_n2_av (a 핀 없음), a 가 vss 인 TG → rb_tg_n2_as. 덱의 노드 0 → 핀 vzero.
  블록 핀 = 입력 10 + inout vw vwl vzero R1 R2 row[105:0] wl[105:0].
사용: python3 mk_netlist.py row_ctrl_syn.v row_blk_syn.v   (매크로 배치 표 row_blk_macros.txt 도 씀)
"""
import ast
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHIP_LIB = HERE.parent.parent / 'real_circuit' / 'chip_lib.py'
NR, N1 = 106, 100
MACRO = {'TGW': 'rb_tgw_n20', 'TG': 'rb_tg_n2'}


ROWM_JSON = HERE / 'rowm.json'      # chip_lib.py 가 없는 곳 (Olympus) 용 사본: 로컬에서 읽을 때마다 다시 씀


def read_rowm():
    if not CHIP_LIB.exists():
        return json.loads(ROWM_JSON.read_text())['ROWM']
    tree = ast.parse(CHIP_LIB.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', '') == 'ROWM' for t in node.targets):
            rowm = ast.literal_eval(node.value)
            ROWM_JSON.write_text(json.dumps({'source': str(CHIP_LIB), 'ROWM': rowm}, indent=1, ensure_ascii=False) + '\n')
            return rowm
    sys.exit('FATAL: chip_lib.py 에 ROWM 이 없음')


def rowm_instances():
    """[(inst, cell, {pin: formal})]  — formal 은 ROWM subckt 의 노드 이름"""
    L = read_rowm()
    hdr = L[0].split()
    assert hdr[:2] == ['.subckt', 'ROWM'], hdr
    formals = hdr[2:]
    out = []
    for ln in L[1:-1]:
        t = ln.split()
        name, nodes, typ = t[0], t[1:-1], t[-1]
        assert typ in MACRO and len(nodes) == 6, ln
        a, b, en, enb, vdd, vss = nodes
        assert (vdd, vss) == ('vdd', 'vss'), ln
        assert b not in ('vdd', 'vss', '0'), ln
        for n in (a, b, en, enb):
            assert n in formals or n == '0', (ln, n)
        if a == 'vdd':
            cell, pins = 'rb_tg_n2_av', {'b': b, 'ctl': en, 'ctlb': enb}
        elif a == 'vss':
            cell, pins = 'rb_tg_n2_as', {'b': b, 'ctl': en, 'ctlb': enb}
        else:
            cell, pins = MACRO[typ], {'a': a, 'b': b, 'ctl': en, 'ctlb': enb}
        assert typ == 'TG' or cell == 'rb_tgw_n20'
        out.append((name, cell, pins))
    return formals, out


def actual(formal, r):
    if formal == '0':
        return 'vzero'
    if formal in ('row', 'wl') or formal in DEC:
        return f'{formal}[{r}]'
    if formal == 'bus':
        return 'R1' if r < N1 else 'R2'
    if formal in ('vw', 'vwl'):
        return formal
    sys.exit(f'FATAL: ROWM 노드 {formal} 를 모름')


DEC = ['wsel', 'wselb', 'wz', 'wzb', 'sns', 'snsb', 'wlv', 'wlvb', 'wlw', 'wlwb', 'wl0', 'wl0b']
INPUTS = ['sdi', 'row1_clk', 'row2_clk', 'rstb', 'sel_en', 'PROG', 'VER', 'SENSE', 'READb', 'WRANY']
ANALOG = ['vw', 'vwl', 'vzero', 'R1', 'R2']


def main(src, dst):
    formals, insts = rowm_instances()
    assert set(DEC) <= set(formals), formals
    v = Path(src).read_text()
    m = re.search(r'module\s+row_ctrl\s*\((.*?)\)\s*;', v, re.S)
    assert m, 'row_ctrl module 머리를 못 찾음'
    ports = [p.strip() for p in m.group(1).split(',')]
    assert ports == INPUTS + DEC, ports
    new_hdr = 'module row_blk(%s);' % ', '.join(INPUTS + ANALOG + ['row', 'wl'])
    body = v[m.end():]
    body, nout = re.subn(r'\n\s*output\s+\[105:0\][^;]*;', '', body)
    assert nout == 1, nout
    for d in DEC:
        assert re.search(r'wire \[105:0\][^;]*\b%s\b' % d, body), f'wire 선언에 {d} 없음'
    assert 'assign' not in body
    decl = ('\n  inout %s;\n  inout [105:0] row, wl;\n  wire %s;\n  wire [105:0] row, wl;'
            % (', '.join(ANALOG), ', '.join(ANALOG)))
    lines, tab = [], []
    for r in range(NR):
        for name, cell, pins in insts:
            conn = ', '.join(f'.{p}({actual(f, r)})' for p, f in pins.items())
            iname = f'rm{r}_{name}'
            lines.append(f'  {cell} {iname} ({conn});')
            tab.append(f'{iname} {cell} {r} {name}')
    end = body.rstrip()
    assert end.endswith('endmodule')
    body = end[:-len('endmodule')] + '  // ROWM 매크로 (행마다 TGW 1 + TG 5, chip_lib.py ROWM)\n' + '\n'.join(lines) + '\nendmodule\n'
    Path(dst).write_text(v[:m.start()] + new_hdr + decl + body)
    Path(dst).with_name('row_blk_macros.txt').write_text('\n'.join(tab) + '\n')
    n = {}
    for _, c, _p in insts:
        n[c] = n.get(c, 0) + NR
    print(f'{dst}: macros {len(lines)} {n}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
