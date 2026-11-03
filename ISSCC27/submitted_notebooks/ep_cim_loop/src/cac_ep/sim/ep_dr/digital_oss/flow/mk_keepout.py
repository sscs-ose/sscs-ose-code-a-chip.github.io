"""칩 전원 drop 자리 막기 (한 번만, 로컬): 칩 배선 (route_oss/mk_route.py) 은 블록 전원 핀 위에 via1·via2·via3 stack 을 세워 met5 로 올린다.
상용 판 블록은 그 자리에 met2·met3 신호선이 없었지만, 오픈소스 판은 자유롭게 배선해 stack pad 와 겹친다 → 칩에서 VDD·VSS·신호 단락 (10/30 시험).
→ 저장된 칩 배선 입력 (route_oss/chip/chip_pre.def) 의 VDD·VSS stack 자리 (블록 안) 를 블록 좌표로 옮겨 met2·met3 배선 막기로 (pad + 0.3 µm).
같은 블록을 R0·R180 두 번 놓으므로 두 인스턴스 자리를 합친다. 쓰임: python3 mk_keepout.py <ep_dr> <blk>   → blocks/<blk>/keepout.json"""
import json
import re
import sys
from pathlib import Path

E, blk = Path(sys.argv[1]), sys.argv[2]
H = Path(__file__).resolve().parent.parent
t = (E / 'layout/top/route_oss/chip/chip_pre.def').read_text()
P = json.loads((E / 'layout/top/place/place_real.json').read_text())['instances']
fp = json.loads((H / 'blocks' / blk / 'fp.json').read_text())
W, Hh = fp['die'][2], fp['die'][3]
PAD = {'met2': (185, 140), 'met3': (165, 165)}           # via_1x1/via2_1x1/via3_1x1 의 met2·met3 pad 반폭 (chip_pre.def VIAS)
HALO = 300
LAY = {'via_1x1_xx': ['met2'], 'via2_1x1_xx': ['met2', 'met3'], 'via3_1x1_xx': ['met3']}
ss = t[t.index('\nSPECIALNETS'):t.index('END SPECIALNETS')]
pts = []
for ent in re.split(r'\n\s*- ', ss)[1:]:
    if ent.split()[0] not in ('VDD', 'VSS'):
        continue
    for m in re.finditer(r'VIA (\S+) \( (-?\d+) (-?\d+) \)', ent):
        for l in LAY.get(m.group(1), []):
            pts.append((l, int(m.group(2)), int(m.group(3))))
    for m in re.finditer(r'RECT (met2|met3) \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)', ent):
        x1, y1, x2, y2 = map(int, m.groups()[1:])
        pts.append((m.group(1), (x1 + x2) // 2, (y1 + y2) // 2))
rects = set()
for n, v in P.items():
    if v['cell'] != blk:
        continue
    x0, y0 = round(v['x'] * 1000), round(v['y'] * 1000)
    o = v['def_orient']
    for l, x, y in pts:
        if o == 'N':
            bx, by = x - x0, y - y0
        elif o == 'S':                                   # R180: 블록 원점 = 인스턴스 bbox 왼쪽 아래
            bx, by = W - (x - x0), Hh - (y - y0)
        else:
            raise SystemExit(f'orient {o}')
        if 0 <= bx <= W and 0 <= by <= Hh:
            hx, hy = PAD[l]
            rects.add((l, bx - hx - HALO, by - hy - HALO, bx + hx + HALO, by + hy + HALO))
json.dump(dict(note='칩 전원 drop stack (route_oss/chip/chip_pre.def VDD·VSS via) 자리의 met2·met3 배선 막기, 블록 좌표 nm (mk_keepout.py)',
               rects=sorted(rects)), open(H / 'blocks' / blk / 'keepout.json', 'w'), indent=0)
print(blk, 'keepout rects', len(rects), {l: sum(1 for r in rects if r[0] == l) for l in ('met2', 'met3')})
