"""저장된 블록 (상용 P&R 판) 의 DEF 에서 오픈소스 흐름의 '제약 파일' 을 한 번 뽑는다 (10/30).
목적: 칩 배치·배선·LVS 를 그대로 두려면 블록 외곽·핀 이름·핀 자리·층이 같아야 한다 → 그 값을 글자 파일로 고정.
  blocks/<blk>/pins.cfg : 핀 한 줄 = 이름 방향 층 x1 y1 x2 y2 (µm, 블록 원점)  — row_ctrl LibreLane 판의 pin_order.cfg 에 해당
  blocks/<blk>/fp.json  : die, 표준 셀 줄 (원점·줄 수·site 수·첫 줄 방향), 트랙, 전원망 규칙 (값만; 도형은 pnr.tcl 이 규칙으로 그림)
DEF 의 셀 배치·배선은 읽지 않는다 (합성·배치·배선은 Yosys + OpenROAD 가 새로 함).
쓰임: python3 mk_spec.py <blk> <ref.def>     (로컬에서 한 번. 결과 파일만 패키지에 들어감)
"""
import json
import re
import sys
from pathlib import Path

H = Path(__file__).resolve().parent.parent          # digital_oss/
ORI = {'N': lambda x, y: (x, y), 'S': lambda x, y: (-x, -y), 'W': lambda x, y: (-y, x), 'E': lambda x, y: (y, -x),
       'FN': lambda x, y: (-x, y), 'FS': lambda x, y: (x, -y), 'FW': lambda x, y: (y, x), 'FE': lambda x, y: (-y, -x)}

blk, ref = sys.argv[1], Path(sys.argv[2])
t = ref.read_text()
die = [int(v) for v in re.search(r'DIEAREA \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)', t).groups()]
FULL = '--full' in sys.argv          # 매크로 블록 (col_blk·row_blk): 줄·매크로 자리·전원망 도형·막기를 목록으로
rows = re.findall(r'^ROW \S+ (\S+) (\d+) (\d+) (\w+) DO (\d+) BY 1 STEP (\d+) 0', t, re.M)
site, x0, y0, o0, nsite, step = rows[0][0], int(rows[0][1]), int(rows[0][2]), rows[0][3], int(rows[0][4]), int(rows[0][5])
ys = [int(r[2]) for r in rows]
rh = 4070
if not FULL:
    assert all(int(r[1]) == x0 and int(r[4]) == nsite for r in rows) and ys == [y0 + k * rh for k in range(len(rows))]
    assert all(r[3] == ('FS' if (k % 2 == 0) == (o0 == 'FS') else 'N') for k, r in enumerate(rows)), 'row orient 번갈아'
tracks = {}
for d, off, n, st, lay in re.findall(r'^TRACKS ([XY]) (-?\d+) DO (\d+) STEP (\d+) LAYER (\S+) ;', t, re.M):
    tracks.setdefault(lay, {})[d] = [int(off), int(st)]

pins = []
sec = t[t.index('\nPINS '):t.index('END PINS')]
for ent in sec.split('\n- ')[1:]:
    nm = ent.split()[0]
    d = re.search(r'DIRECTION (\w+)', ent).group(1)
    lay = re.search(r'LAYER (\S+) \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)', ent)
    pl = re.search(r'(?:FIXED|PLACED) \( (-?\d+) (-?\d+) \) (\w+)', ent)
    x1, y1, x2, y2 = map(int, lay.groups()[1:]); px, py = int(pl.group(1)), int(pl.group(2)); f = ORI[pl.group(3)]
    c = [f(x1, y1), f(x2, y2)]
    pins.append((nm, d, lay.group(1), px + min(a for a, _ in c), py + min(b for _, b in c), px + max(a for a, _ in c), py + max(b for _, b in c)))

# stripe 는 core 위·아래로 0.9 µm 내밀기, via 는 같은 넷 띠 × stripe 마다 M1M2 4 × 1 (cut 0.15, 간격 0.17, 덮개 met1·met2 x 0.175 y 0.07)
vias = re.search(r'\+ CUTSIZE (\d+) (\d+)\s+\+ LAYERS (\S+) (\S+) (\S+)\s+\+ CUTSPACING (\d+) (\d+)\s+\+ ENCLOSURE (\d+) (\d+) (\d+) (\d+)\s+\+ ROWCOL (\d+) (\d+)', t)
v = vias.groups()
fp = dict(top=blk, die=die, site=site, row_x=x0, row_y0=y0, row_h=rh, nrows=len(rows), nsites=nsite, site_w=step,
          first_orient='MX' if o0 == 'FS' else 'R0', tracks=tracks,
          pdn=dict(band_w=1250, stripe_layer='met2', stripe_w=500, stripe_sp=1500, stripe_pitch=20000, stripe_off=1500, stripe_ext=900,
                   via=dict(cut=[int(v[0]), int(v[1])], layers=[v[2], v[3], v[4]], cutsp=[int(v[5]), int(v[6])],
                            enc=[int(v[7]), int(v[8]), int(v[9]), int(v[10])], rowcol=[int(v[11]), int(v[12])])),
          source=f'{ref.name} (DIEAREA·ROW·TRACKS·PINS·VIAS 만 읽음)')
if FULL:
    OR = {'N': 'R0', 'FS': 'MX', 'S': 'R180', 'FN': 'MY'}
    fp['row_list'] = [[int(r[1]), int(r[2]), OR[r[3]], int(r[4])] for r in rows]
    cs = t[t.index('\nCOMPONENTS'):t.index('END COMPONENTS')]
    fp['macros'] = [[m.group(1), m.group(2), int(m.group(3)), int(m.group(4)), OR[m.group(5)]]
                    for m in re.finditer(r'- (\S+) (\S+)\s+\+ FIXED \( (-?\d+) (-?\d+) \) (\w+)', cs) if not m.group(2).startswith('sky130_fd_sc_hvl__')]
    bs = t[t.index('\nBLOCKAGES'):t.index('END BLOCKAGES')] if '\nBLOCKAGES' in t else ''
    fp['route_blockages'] = [[m.group(1), *map(int, m.groups()[1:])] for m in re.finditer(r'- LAYER (\S+) RECT \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)', bs)]
    fp['place_blockages'] = [list(map(int, m.groups())) for m in re.finditer(r'PLACEMENT RECT \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)', bs)]
    # via 정의 (VIARULE 생성 via 또는 RECT 로 그린 via)
    vs = t[t.index('\nVIAS'):t.index('END VIAS')]
    vdef = {}
    for ent in re.split(r'\n- ', vs)[1:]:
        nm = ent.split()[0]
        g = re.search(r'CUTSIZE (\d+) (\d+)\s+\+ LAYERS (\S+) (\S+) (\S+)\s+\+ CUTSPACING (\d+) (\d+)\s+\+ ENCLOSURE (\d+) (\d+) (\d+) (\d+)\s+\+ ROWCOL (\d+) (\d+)', ent)
        if g:
            v = g.groups(); vdef[nm] = dict(cut=[int(v[0]), int(v[1])], layers=[v[2], v[3], v[4]], cutsp=[int(v[5]), int(v[6])],
                                             enc=[int(v[7]), int(v[8]), int(v[9]), int(v[10])], rowcol=[int(v[11]), int(v[12])])
        else:
            vdef[nm] = dict(rects=[[m.group(1), *map(int, m.groups()[1:])] for m in re.finditer(r'RECT (\S+) \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)', ent)])
    fp['vias'] = vdef
    # 전원망·special 신호 도형 (SPECIALNETS 그대로): [넷, 층, x1, y1, x2, y2, 모양] / [넷, 'VIA', via, x, y]
    ss = t[t.index('\nSPECIALNETS'):t.index('END SPECIALNETS')]
    pg = []
    for ent in re.split(r'\n- ', ss)[1:]:
        nm = ent.split()[0]
        for m in re.finditer(r'SHAPE (\w+) \+ RECT (\S+) \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)', ent):
            pg.append([nm, m.group(2), *map(int, m.groups()[2:]), m.group(1)])
        for m in re.finditer(r'(?:ROUTED|NEW) (\S+) (\d+) \+ SHAPE (\w+) \( (-?\d+) (-?\d+) \) (?:\( (\*|-?\d+) (\*|-?\d+) \)|(\S+))', ent):
            lay, w, shp, x1, y1 = m.group(1), int(m.group(2)), m.group(3), int(m.group(4)), int(m.group(5))
            if m.group(8):
                pg.append([nm, 'VIA', m.group(8), x1, y1, shp]); continue
            x2 = x1 if m.group(6) == '*' else int(m.group(6)); y2 = y1 if m.group(7) == '*' else int(m.group(7))
            h = w // 2
            pg.append([nm, lay, min(x1, x2) - (h if x1 == x2 else 0), min(y1, y2) - (h if y1 == y2 else 0),
                       max(x1, x2) + (h if x1 == x2 else 0), max(y1, y2) + (h if y1 == y2 else 0), shp])
    fp['special'] = pg
    print('full: rows', len(rows), 'macros', len(fp['macros']), 'blockages', len(fp['place_blockages']), 'route blk', fp['route_blockages'], 'vias', list(vdef), 'special', len(pg),
          {n: sum(1 for p in pg if p[0] == n) for n in sorted({p[0] for p in pg})})
od = H / 'blocks' / blk
od.mkdir(parents=True, exist_ok=True)
(od / 'fp.json').write_text(json.dumps(fp, indent=1))
with open(od / 'pins.cfg', 'w') as f:
    f.write(f'# {blk} 핀 {len(pins)} 개: 이름 방향 층 x1 y1 x2 y2 (µm, 블록 원점). 저장된 블록 DEF 와 같은 자리 (mk_spec.py)\n')
    for p in pins:
        f.write(f'{p[0]} {p[1]} {p[2]} ' + ' '.join(f'{v / 1000:.3f}' for v in p[3:]) + '\n')
print(blk, 'die', die, 'rows', len(rows), 'sites', nsite, 'first', o0, 'pins', len(pins), 'via', v)
