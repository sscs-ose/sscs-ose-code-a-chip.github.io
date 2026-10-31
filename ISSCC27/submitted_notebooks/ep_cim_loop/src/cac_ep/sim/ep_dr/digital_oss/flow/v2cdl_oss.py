"""OpenROAD 배선 뒤 Verilog netlist → LVS source CDL (상용 판 digital/v2cdl_hvl.py 와 같은 규칙, 새로 씀).
- hvl 셀 전원 핀 VPWR·VPB → VDD, VGND·VNB → VSS. filler (fill_*) 는 뺌 (소자 없는 subckt).
- subckt 핀 순서 = pins.cfg 순서 + VDD VSS (= 저장된 블록 CDL 머리줄과 같음 → 칩 netlist 의 X 줄을 그대로 씀).
- `assign a = b;` 는 같은 넷으로 합침 (포트 이름을 남김).
쓰임: python3 v2cdl_oss.py <netlist.v> <hvl_u.cdl[,macro.cdl…]> <pins.cfg> <out.cdl>
"""
import re
import sys

vf, hcdl, pcfg, out = sys.argv[1:5]
ports = {}
for cf in hcdl.split(','):                     # hvl 셀 CDL (+ 매크로 CDL, 쉼표로)
    for l in open(cf):
        if l.upper().startswith('.SUBCKT'):
            t = l.split(); ports[t[1]] = t[2:]
order = [l.split()[0] for l in open(pcfg) if l.strip() and not l.startswith('#')]
src = re.sub(r'//.*', '', open(vf).read())
src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
body = src[src.index(';', src.index('module')) + 1:src.rindex('endmodule')]
stm = [s.strip() for s in body.split(';') if s.strip()]


def nm(s):
    s = s.strip()
    return s[1:].strip() if s.startswith('\\') else s


par = {}


def find(a):
    while par.get(a, a) != a:
        a = par[a]
    return a


keep = set(order) | {'VDD', 'VSS'}
insts = []
for s in stm:
    w = s.split(None, 1)
    if w[0] in ('input', 'output', 'inout', 'wire'):
        continue
    if w[0] == 'assign':
        a, b = [nm(x) for x in w[1].split('=')]
        ra, rb = find(a), find(b)
        if ra != rb:
            if rb in keep:
                par[ra] = rb
            else:
                par[rb] = ra
        continue
    m = re.match(r'(\S+)\s+(\\\S+|\S+)\s*\((.*)\)\s*$', s, re.S)
    assert m, ('형식', s[:80])
    cell, inst, conns = m.group(1), nm(m.group(2)), m.group(3)
    if re.search(r'__fill_\d+$', cell):
        continue
    cd = {p: nm(n) for p, n in re.findall(r'\.(\w+)\s*\(\s*(\\\S+\s|[^()\s]*)\s*\)', conns)}
    insts.append((cell, inst, cd))
# .INCLUDE (저장된 블록 CDL 과 같이 hvl 셀 + 매크로 CDL): 칩 netlist (net/mk_top.py) 가 이 줄을 따라 lib/ 에 사본을 모은다
lines = [f'* block CDL — v2cdl_oss.py ({vf.split("/")[-1]})'] + [f'.INCLUDE {c}' for c in hcdl.split(',')] + ['',
         f'.SUBCKT TOPNAME ' + ' '.join(order) + ' VDD VSS']
nfl = 0
for cell, inst, cd in insts:
    nets = []
    for p in ports[cell]:
        if p in ('VPWR', 'VPB', 'VDD') and p not in cd:
            nets.append('VDD')
        elif p in ('VGND', 'VNB', 'VSS') and p not in cd:
            nets.append('VSS')
        elif cd.get(p):
            nets.append(find(cd[p]))
        else:
            nfl += 1; nets.append(f'nc_{inst}_{p}')
    iname = 'X' + re.sub(r'[^A-Za-z0-9_]', '_', inst)
    lines.append(f'{iname} ' + ' '.join(nets) + f' {cell}')
top = re.search(r'module\s+(\S+)', src).group(1)
lines = [l.replace('.SUBCKT TOPNAME', f'.SUBCKT {top}') for l in lines]
lines.append(f'.ENDS {top}')
open(out, 'w').write('\n'.join(lines) + '\n')
print('cdl', out, 'instances', len(insts), 'floating pins', nfl)
