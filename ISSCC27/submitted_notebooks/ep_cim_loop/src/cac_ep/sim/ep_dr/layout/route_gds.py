"""보고용 배치·연결 GDS + 그림 (10/27, DRC 안 함). out/<바탕>.gds (PAD frame) + <배선>.json (route_v2.py / route_est.py) →
out/<바탕>_pr.gds (top ep_<바탕>_pr = ep_<바탕> + 블록 + 배선 251/k), out/<바탕>_pr.png (KLayout, 이름표 없음 — 이름표는 route_*.py 의 TikZ).
블록: 블록 GDS 를 주면 (가견적판, est_blocks.py) 블록 자리에 실제 셀 B_* + 외곽선 250/9, core 빈 곳은 decap 타일 (B_decap_tile) 로 채움.
      안 주면 (v2) 블록마다 색 상자 250/k.
쓰임 (Olympus): QT_QPA_PLATFORM=offscreen ~/opt/kl312/bin/python route_gds.py [route_v2.json chip_v2 [블록 gds]]
  v2 = route_gds.py, 가견적판 = route_gds.py route_est.json chip_est out/est_blocks.gds
"""
import json
import os
import sys

import klayout.db as db
import klayout.lay as lay

H = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(H, 'out')
RJ, NAME, BGDS = (sys.argv[1:] + ['route_v2.json', 'chip_v2', ''][len(sys.argv) - 1:])[:3]
J = json.load(open(os.path.join(H, RJ)))
W, Hh = J['die']['w'], J['die']['h']
KIND = dict(array=(1, 0xDBE5F1), diode=(2, 0xF2F2F2), pitch_row=(3, 0xE6E9EF), pitch_col=(3, 0xE6E9EF), analog=(4, 0xE4DDF0),
            digital=(5, 0xD5DCEA), decap=(6, 0xEEF2E6))
CLS = dict(ana=(1, 0x500000), dig=(2, 0x001C54), bus=(3, 0x4B3B7A), pwr=(4, 0x7F7F7F))
um = lambda v: int(round(v * 1000))

ly = db.Layout(); ly.read(os.path.join(OUT, NAME + '.gds'))
base = ly.cell('ep_' + NAME)
if BGDS:
    opt = db.LoadLayoutOptions(); opt.cell_conflict_resolution = db.LoadLayoutOptions.SkipNewCell
    ly.read(os.path.join(H, BGDS), opt)
T = ly.create_cell(f'ep_{NAME}_pr')
T.insert(db.CellInstArray(base.cell_index(), db.Trans()))
LO = ly.layer(250, 9)
used = db.Region()
for b in J['blocks'].values():
    x0, y0, x1, y1 = b['rect']
    if BGDS and b.get('cell'):                                    # 실제 셀: bbox 왼쪽 아래를 블록 자리 왼쪽 아래에
        c = ly.cell(b['cell']); t0 = db.DTrans(db.DTrans.M90 if b.get('mirror') else db.DTrans.R0)   # mirror = 좌우 뒤집기
        bb = c.dbbox().transformed(t0)
        T.insert(db.DCellInstArray(c.cell_index(), db.DTrans(x0 - bb.left, y0 - bb.bottom) * t0))
        T.shapes(LO).insert(db.Box(um(x0), um(y0), um(x1), um(y1)))
        used.insert(db.Box(um(x0 - 4), um(y0 - 4), um(x1 + 4), um(y1 + 4)))
    else:
        T.shapes(ly.layer(250, KIND[b['kind']][0])).insert(db.Box(um(x0), um(y0), um(x1), um(y1)))
n_dc = 0
if BGDS:                                                          # core 빈 곳을 decap 타일로 (격자, 타일이 통째로 들어가는 자리만)
    c = ly.cell('B_decap_tile'); bb = c.dbbox(); px, py = bb.width() + 1.0, bb.height() + 1.0
    cx0, cy0, cx1, cy1 = J['core']
    free = db.Region(db.Box(um(cx0), um(cy0), um(cx1), um(cy1))) - used
    nx, ny = int((cx1 - cx0) // px), int((cy1 - cy0) // py)
    for i in range(nx):
        for j in range(ny):
            x, y = cx0 + i * px, cy0 + j * py
            box = db.Region(db.Box(um(x), um(y), um(x + bb.width()), um(y + bb.height())))
            if (box - free).is_empty():
                T.insert(db.DCellInstArray(c.cell_index(), db.DTrans(x - bb.left, y - bb.bottom))); n_dc += 1
M3, M4, M5, V3 = (ly.layer(70, 20), ly.layer(71, 20), ly.layer(72, 20), ly.layer(70, 44))
PITCH, WL = 1.8, 0.9                                              # 금속 그림: 가닥 간격, 가닥 폭 (µm)


def offset(pts, off):
    """Manhattan 꺾은선을 진행 방향 왼쪽으로 off 만큼 옮김 (꺾이는 점 = 두 법선 합)."""
    nv = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L_ = max(abs(x1 - x0), abs(y1 - y0)) or 1.0
        nv.append((-(y1 - y0) / L_, (x1 - x0) / L_))
    out = [(pts[0][0] + off * nv[0][0], pts[0][1] + off * nv[0][1])]
    for k in range(1, len(pts) - 1):
        a, b = nv[k - 1], nv[k]
        s = (a[0] + b[0], a[1] + b[1]) if abs(a[0] * b[0] + a[1] * b[1]) < 0.5 else a
        out.append((pts[k][0] + off * s[0], pts[k][1] + off * s[1]))
    out.append((pts[-1][0] + off * nv[-1][0], pts[-1][1] + off * nv[-1][1]))
    return out


for r in J['routes']:
    if not BGDS:                                                  # v2: 종류별 색 층
        pts = [db.Point(um(x), um(y)) for x, y in r['pts']]
        T.shapes(ly.layer(251, CLS[r['cls']][0])).insert(db.Path(pts, um(r['w']), um(r['w'] / 2), um(r['w'] / 2)))
        continue
    if r['cls'] == 'pwr':                                         # 전원 = met5 띠
        T.shapes(M5).insert(db.DPath([db.DPoint(x, y) for x, y in r['pts']], r['w']))
        continue
    n = r.get('n', 1)
    for k in range(n):                                            # 가로 = met3, 세로 = met4, 꺾이는 곳 via3
        q = offset(r['pts'], (k - (n - 1) / 2) * PITCH)
        for (x0, y0), (x1, y1) in zip(q, q[1:]):
            lay_ = M3 if abs(y1 - y0) < abs(x1 - x0) else M4
            T.shapes(lay_).insert(db.DPath([db.DPoint(x0, y0), db.DPoint(x1, y1)], WL, WL / 2, WL / 2))
        for x, y in q[1:-1]:
            T.shapes(V3).insert(db.DBox(x - 0.2, y - 0.2, x + 0.2, y + 0.2))
            for L_ in (M3, M4):
                T.shapes(L_).insert(db.DBox(x - 0.45, y - 0.45, x + 0.45, y + 0.45))
so = db.SaveLayoutOptions(); so.add_cell(T.cell_index())
gds = os.path.join(OUT, f'{NAME}_pr.gds')
ly.write(gds, so)

lv = lay.LayoutView()
for k, v in (('background-color', '#ffffff'), ('grid-visible', 'false'), ('text-visible', 'false'), ('cell-box-visible', 'false')):
    lv.set_config(k, v)
lv.load_layout(gds, True)
lv.load_layer_props(os.path.join(H, 'iolib', 'sky130A.lyp'))


def add_top(src, fill, frame, width, name, dither=0):
    lp = lay.LayerPropertiesNode()
    lp.source, lp.fill_color, lp.frame_color, lp.dither_pattern, lp.width, lp.name = src, fill, frame, dither, width, name
    lv.insert_layer(lv.end_layers(), lp)                          # 목록 끝 = 나중에 그려져 위에 보임 (10/27 첫 그림에서 확인)


for dt, col in sorted(set(KIND.values())):
    add_top(f'250/{dt}@1', col, 0x404040, 1, f'block {dt}')
add_top('250/9@1', 0x404040, 0x404040, 2, 'block outline', dither=1)   # 1 = 속 빈 무늬 (외곽선만)
for name, (dt, col) in CLS.items():                               # 배선을 블록 뒤에 넣어 맨 위에
    add_top(f'251/{dt}@1', col, col, 0, f'route {name}')
lv.add_missing_layers()                                           # 250·251 은 이미 있어 다시 안 들어감
for lp in lv.each_layer():
    if (lp.source_layer, lp.source_datatype) in ((240, 0), (241, 0), (235, 0)):
        lp.visible = False
lv.active_cellview().cell_name = f'ep_{NAME}_pr'
lv.max_hier()
lv.zoom_box(db.DBox(-30, -30, W + 30, Hh + 30))
px = 4800
lv.save_image(os.path.join(OUT, f'{NAME}_pr.png'), px, int(round(px * (Hh + 60) / (W + 60))))
print(gds, 'blocks', len(J['blocks']), 'routes', len(J['routes']), 'decap tiles', n_dc)
