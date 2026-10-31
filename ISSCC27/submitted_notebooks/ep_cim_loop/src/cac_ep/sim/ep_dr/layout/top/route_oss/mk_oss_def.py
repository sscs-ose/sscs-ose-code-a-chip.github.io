"""OpenROAD 입력 DEF 만들기: mk_route.py 의 chip/chip_pre.def (배치·핀·미리 그린 선·전원) + NETS 절 (OpenROAD 가 이을 넷).

- SKIP_NETS (미리 그린 선으로 모든 핀이 이어진 넷) = SPECIALNETS 에만 → OpenROAD 에서 special = 배선 안 함 (NanoRoute skip_routing 과 같은 뜻)
  은 or_route.tcl 이 special 표시를 지워 배선 대상이 되게 한다 (route_nets.txt).
- VDD·VSS 는 SPECIALNETS 그대로 (블록 PG 핀은 or_route.tcl 의 global_connect).
쓰임: <python> mk_oss_def.py   → chip/chip_oss.def, chip/route_nets.txt
"""
import re
from pathlib import Path

import routelib as R

H = Path(__file__).resolve().parent
TOPD = H.parent
CH = H / 'chip'

M = {}
for f in sorted((TOPD / 'place' / 'lef').glob('*.lef')):
    R.parse_lef(str(f), M)
for f in sorted((H / 'lef_fix').glob('*.lef')):
    R.parse_lef(str(f), M)
R.parse_lef(str(TOPD.parents[1] / 'digital' / 'pdk' / 'sky130_fd_sc_hvl.lef'), M)

cfg = (CH / 'cfg_chip.tcl').read_text()
skip = set(re.search(r'set SKIP_NETS \{([^}]*)\}', cfg).group(1).split())
TOP, PORTS, CONN = R.parse_verilog(str(CH / 'chip_core_route.v'), M, top='chip_core')
NETS = R.nets_of(CONN)
port_names = {p for p, _ in PORTS}
PG = {'VDD', 'VSS', "1'b0"}

route = {}
for n, pins in NETS.items():
    if n in skip or n in PG:
        continue
    conns = []
    for inst, p in pins:
        cell = CONN[inst][0]
        if M[cell].use.get(p) in ('POWER', 'GROUND'):
            continue
        conns.append((inst, p))
    route[n] = conns
for p in port_names:                       # 포트만 있고 블록 핀이 없는 넷은 없지만 확인
    if p not in skip and p not in route and p not in PG:
        route[p] = []

pre = (CH / 'chip_pre.def').read_text()
assert pre.rstrip().endswith('END DESIGN')
body = pre.rstrip()[:-len('END DESIGN')]
# OpenROAD DEF 읽기는 SPECIALNETS 의 DEF 5.8 `+ VIA <via> ( x y )` 를 못 읽는다 ("VIA in special net is unsupported", 잡 721769)
# → 같은 뜻의 `+ ROUTED <아래 층> 0 ( x y ) <via>` 로 바꿈 (도형 같음)
VBOT = {'via': 'met1', 'via2': 'met2', 'via3': 'met3', 'via4': 'met4'}
body, nv = re.subn(r'\+ VIA ((via\d?)_\S+) \( (-?\d+) (-?\d+) \)',
                   lambda m: f'+ ROUTED {VBOT[m.group(2)]} 0 ( {m.group(3)} {m.group(4)} ) {m.group(1)}', body)
print('special VIA -> ROUTED', nv)
sn = pre[pre.index('SPECIALNETS'):]
special_names = set(re.findall(r'^- (\S+)', sn, re.M))

# OpenROAD global_route·detailed_route 는 special 도형 (SWire) 이 붙은 넷을 "이미 배선됨" 으로 보고 건너뛴다 (시험: 56 / 80 넷만 배선).
# → 이을 넷의 SPECIALNETS 항목을 뺀다. 뺀 도형: core 핀 drawing (핀과 같은 사각형 → def2gds.py 가 핀 층을 drawing 으로도 씀),
#   nudge row 100–105 의 미리 그린 선 (배열 row ↔ row_blk, met2 + via2 + met3) → TritonRoute 가 직접 잇는다.
both = sorted(set(route) & special_names)
cnt = [0]


def drop(m):
    if m.group(1) in route:
        cnt[0] += 1
        return ''
    return m.group(0)


i0 = body.index('SPECIALNETS'); i1 = body.index('END SPECIALNETS')
sec = re.sub(r'^- (\S+)\b.*?\+ USE \w+ ;\n', drop, body[i0:i1], flags=re.M | re.S)
nleft = len(re.findall(r'^- ', sec, re.M))
sec = re.sub(r'^SPECIALNETS \d+ ;', f'SPECIALNETS {nleft} ;', sec)
body = body[:i0] + sec + body[i1:]
print(f'SPECIALNETS 에서 뺀 넷 {cnt[0]}, 남은 {nleft}')

add = []
for cb in (CH / 'capm_blk.txt', CH / 'halo_blk.txt'):
    if cb.exists():
        add += [ln for ln in cb.read_text().splitlines() if ln.strip()]
if add:
    m0 = re.search(r'^BLOCKAGES (\d+) ;\n', body, re.M)
    body = body[:m0.start()] + f'BLOCKAGES {int(m0.group(1)) + len(add)} ;\n' + '\n'.join(add) + '\n' + body[m0.end():]
    print('met blockages (capm + 넓은 금속 둘레)', len(add))

out = [f'NETS {len(route)} ;']
for n in sorted(route):
    c = ''.join(f' ( {i} {p} )' for i, p in route[n])
    if n in port_names:
        c = f' ( PIN {n} )' + c
    out.append(f'- {n}{c}\n  + USE SIGNAL ;')
out.append('END NETS')
(CH / 'chip_oss.def').write_text(body + '\n'.join(out) + '\nEND DESIGN\n')
(CH / 'route_nets.txt').write_text('\n'.join(sorted(route)) + '\n')
both = sorted(set(route) & special_names)
print(f'route nets {len(route)} (special 도형도 있는 넷 {len(both)}), skip {len(skip)}, '
      f'pins in route nets {sum(len(v) for v in route.values())}')
print('both:', ' '.join(both))
