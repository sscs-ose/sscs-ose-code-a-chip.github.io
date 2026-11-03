"""가견적 블록 (10/27, 사용자 "내가 옛날에 가견적으로 만들어두려고 한 게 있긴 해. 그것을 활용해봐", "블록 내부 배선도 대충은 해놓아볼래?",
"보고를 할 것인데, 그럴듯하게 만들어서 보고하는 게 목적이야"). DRC·LVS 없음 — 실제 셀로 면적·모양, 블록 안 배선은 대충 (보고 그림용).
있는 셀 (ep_demo/layout 3차 배치도 blocks/ep_top_v3.gds, 10/19): 1T1R 배열 arr_ep_64x32_p5115, 열 띠 colrow (열마다 TG 4 + clamp 다이오드 2),
  행 구동 rowcell (행마다 TG 6), 사용자 HOG op-amp (sern_hog_classab_opamp/sim/layout/out/hog.gds) — 셀 안 배선은 원래 그대로.
새로 그리는 것: ep_demo/layout/devlib.py·gen_tg.py (5 V g5v0d10v5, 고치지 않고 import) 로 입력 NMOS 스위치, 5 V 논리 (줄마다 레지스터·decoder —
  v3 덱에서 ±2.5 V), StrongARM·전치 증폭기, write buffer, bias·β 미러, nudge 주입기, 판독 TG, 레벨 변환기, decap.
블록 안 배선 (대충): 5 V 논리 셀 = 출력 (n·p drain) 과 입력 (게이트) 묶음 met2. 논리 줄 = 이웃 셀 사슬 met3 + 줄마다 클록선 met3 + 출력선 met4
  (행 쪽 블록 = 줄마다 가로, 열 decoder = 열 pitch 세로). 입력 구동 = 열마다 VRAILP·VRAILM rail met2, 소자마다 행 출력선 met3, 게이트선 met4.
  묶음 블록 = 부품 차례로 L 자 met3·met2, HOG bias (vbn·vbp) 선, 위·아래 전원 rail met4.
개수는 v3 칩 덱 (real_circuit/gen_chip_deck2.py, chip_lib.py, wu_lib.py) 기준. 5 V 논리 셀은 트랜지스터 수만 맞춘 근사 (nfet 줄 + nwell 안 pfet 줄).
낸다: out/est_blocks.gds (블록마다 셀 B_<이름>), est_blocks.json (블록 → 폭·높이 µm, 내용, 출처).
쓰임: /home/dave/work/projects/sern_hog_classab_opamp/sim/.venv/bin/python est_blocks.py
"""
import json
import math
import sys
from pathlib import Path

import klayout.db as db

H = Path(__file__).resolve().parent
DEMO = H.parents[1] / 'ep_demo' / 'layout'
sys.path.insert(0, str(DEMO))
from devlib import Cell, mos, tap, finish, gate_pad                # noqa: E402
import gen_tg                                                        # noqa: E402

ly = db.Layout(); ly.dbu = 0.001
ly.read(str(DEMO / 'blocks' / 'ep_top_v3.gds'))
opt = db.LoadLayoutOptions(); opt.cell_conflict_resolution = db.LoadLayoutOptions.SkipNewCell
for f in (Path('/home/dave/work/projects/sern_hog_classab_opamp/sim/layout/out/hog.gds'), H / 'stdlib' / 'sky130_scl_9T.gds'):
    ly.read(str(f), opt)
BB = lambda c: ly.cell(c).dbbox()
INFO, PIN = {}, {}                                                  # PIN: 셀 → {핀: (x, y)} 셀 좌표 (a = 입력, z = 출력)
ML = {1: (68, 20), 2: (69, 20), 3: (70, 20), 4: (71, 20)}
VL = {1: (68, 44), 2: (69, 44), 3: (70, 44)}
WM = {1: 0.30, 2: 0.40, 3: 0.60, 4: 0.90}


def wire(T, m, pts, w=None):
    w = w or WM[m]
    T.shapes(ly.layer(*ML[m])).insert(db.DPath([db.DPoint(x, y) for x, y in pts], w, w / 2, w / 2))


def via(T, x, y, lo, hi):
    """lo 금속 → hi 금속 via 쌓기 (via 0.2 + 양쪽 패드 0.4)."""
    for m in range(lo, hi):
        T.shapes(ly.layer(*VL[m])).insert(db.DBox(x - 0.1, y - 0.1, x + 0.1, y + 0.1))
        for mm in (m, m + 1):
            T.shapes(ly.layer(*ML[mm])).insert(db.DBox(x - 0.2, y - 0.2, x + 0.2, y + 0.2))


def place(T, cname, x, y, flip=False):
    """셀 cname 의 bbox 왼쪽 아래를 (x, y) 에. flip = 위아래 뒤집기. 반환: 셀 → 블록 좌표 변환."""
    c = ly.cell(cname); t0 = db.DCplxTrans(1, 0, flip, 0, 0)
    bt = c.dbbox().transformed(t0)
    t = db.DCplxTrans(1, 0, flip, x - bt.left, y - bt.bottom)
    T.insert(db.DCellInstArray(c.cell_index(), t))
    return t


def pins(cname, t):
    b = BB(cname)
    p = PIN.get(cname) or {'a': (b.left + 0.3 * b.width(), b.center().y), 'z': (b.left + 0.75 * b.width(), b.center().y)}
    return {k: t * db.DPoint(*v) for k, v in p.items()}


def block(name, T, contents, source):
    b = T.dbbox()
    INFO[name] = dict(cell=T.name, w=round(b.width(), 3), h=round(b.height(), 3), contents=contents, source=source)
    return T


def tile(name, cname, nx, ny, px=None, py=None, contents='', source=''):
    T = ly.create_cell('B_' + name); b = BB(cname)
    px, py = px or b.width(), py or b.height()
    for i in range(nx):
        for j in range(ny):
            place(T, cname, i * px, j * py)
    return block(name, T, contents, source)


def chain(T, a, b):
    """핀 a (met2) → 핀 b (met2): met3 가로 + met2 세로 L 자."""
    via(T, a.x, a.y, 2, 3); wire(T, 3, [(a.x, a.y), (b.x, a.y)]); via(T, b.x, a.y, 2, 3)
    if abs(b.y - a.y) > 0.3:
        wire(T, 2, [(b.x, a.y), (b.x, b.y)])


def pack(name, items, width, gap=1.0, contents='', source=''):
    """선반 채우기 + 부품 차례로 잇기 + 위·아래 전원 rail (met4) + HOG bias 선."""
    T = ly.create_cell('B_' + name); x = y = rowh = 0.0; P = []
    for cname, n in items:
        b = BB(cname)
        for _ in range(n):
            if x > 0 and x + b.width() > width:
                x, y, rowh = 0.0, y + rowh + gap, 0.0
            P.append((cname, place(T, cname, x, y))); x += b.width() + gap; rowh = max(rowh, b.height())
    pp = [pins(c, t) for c, t in P]
    for k in range(len(pp) - 1):
        chain(T, pp[k]['z'], pp[k + 1]['a'])
    bb = T.dbbox()
    yb, yt = bb.bottom - 1.5, bb.top + 1.5
    for yy in (yb, yt, yb - 2.0, yt + 2.0):                          # VSS·VDD (met4), vbn·vbp 줄 (met3)
        wire(T, 4 if yy in (yb, yt) else 3, [(bb.left, yy), (bb.right, yy)])
    for q in pp:
        for k, yy in (('vbn', yb - 2.0), ('vbp', yt + 2.0)):
            if k in q:
                wire(T, 2, [(q[k].x, q[k].y), (q[k].x, yy)]); via(T, q[k].x, yy, 2, 3)
    return block(name, T, contents, source)


def rows(name, items, width=None, height=None, util=0.85, out=None, contents='', source=''):
    """같은 높이 셀을 줄로 (홀수 줄 위아래 뒤집어 전원 공유) + 이웃 셀 사슬 met3 + 줄마다 클록선 met3 + 출력선 met4.
    out = 'side' (줄마다 가로 met4, 양쪽 끝까지) / 'top' (열 pitch 5.115 세로 met4) / None."""
    rowh = max(BB(c).height() for c, _ in items)
    seq = [c for c, n in items for _ in range(n)]

    def n_rows(wd):
        x, r = 0.0, 1
        for c in seq:
            w = BB(c).width()
            if x > 0 and x + w > wd:
                x, r = 0.0, r + 1
            x += w
        return r
    if width is None:                                             # 높이 안에 들어갈 때까지 폭을 넓힘
        width = sum(BB(c).width() for c in seq) / max(1, int(height // rowh)) / util
        while n_rows(width) * rowh > height:
            width += 0.46
    T = ly.create_cell('B_' + name); x, r = 0.0, 0; RW = [[]]
    for c in seq:
        w = BB(c).width()
        if x > 0 and x + w > width:
            x, r = 0.0, r + 1; RW.append([])
        RW[-1].append(pins(c, place(T, c, x, r * rowh, flip=(r % 2 == 1)))); x += w
    for r, row in enumerate(RW):
        for k in range(len(row) - 1):
            chain(T, row[k]['z'], row[k + 1]['a'])
        yc = r * rowh + (0.18 if r % 2 == 0 else 0.82) * rowh       # 클록·제어선 (nfet 쪽)
        wire(T, 3, [(0, yc), (width, yc)])
        if out == 'side':
            ym = row[-1]['z'].y
            via(T, row[0]['z'].x, ym, 2, 4); via(T, row[-1]['z'].x, ym, 2, 4)
            wire(T, 4, [(-0.5, ym), (width + 0.5, ym)])
    if out == 'top':
        for k in range(int(width // 5.115)):
            xx = 2.5 + k * 5.115
            wire(T, 4, [(xx, 0), (xx, len(RW) * rowh + 0.5)])
            via(T, xx, (k % len(RW) + 0.5) * rowh, 3, 4)
    return block(name, T, contents, source)


# ── 5 V 소자 셀 (devlib) + 핀
def mos_cell(name, typ, W, L, nf):
    C = Cell(ly, name)
    tap(C, 'p' if typ == 'n' else 'n', 0, nf * (L + 0.29) + 0.29, 0.25, 'VSS' if typ == 'n' else 'VDD')
    d = mos(C, typ, 0, 0.55, W, L, nf, 's', 'd', 'g')
    if typ == 'p':
        C.box(None, 'nw', -0.40, -0.40, d['x1'] + 0.40, d['y1'] + 0.40)
    gx = d['gxs'][len(d['gxs']) // 2]; gate_pad(C, d, gx); C.via1('g', gx, d['gy'])
    xd = d['drns'][len(d['drns']) // 2] if d['drns'] else d['srcs'][-1]; C.via1('d', xd, d['yd'])
    xs = d['srcs'][len(d['srcs']) // 2]
    PIN[name] = dict(a=(gx, d['gy']), z=(xd, d['yd']), s=(xs, d['ys']), d=(xd, d['yd']), g=(gx, d['gy']))
    finish(C)
    return name


def logic5(name, nn, npf, wn=1.0, wp=2.0, L=0.5):
    """5 V 논리 근사: nfet nf=nn 한 줄 (아래) + nwell 안 pfet nf=npf 한 줄 (위) + 탭 두 줄.
    셀 안 배선: 출력 = n·p drain 스트랩을 met2 로 묶음, 입력 = n·p 게이트를 met2 로 묶음."""
    C = Cell(ly, name)
    wmax = max(nn, npf) * (L + 0.29) + 0.29 + 0.4
    tap(C, 'p', 0, wmax, 0.25, 'VSS')
    dn = mos(C, 'n', 0.2, 0.55, wn * nn, L, nn, 's', 'z', 'a')
    nw0 = dn['y1'] + 0.30
    dp = mos(C, 'p', 0.2, nw0 + 0.10, wp * npf, L, npf, 's', 'z', 'a')
    yt = dp['y1'] + 0.25
    tap(C, 'n', 0, wmax, yt, 'VDD')
    C.box(None, 'nw', -0.40, nw0, wmax + 0.40, yt + 0.60)
    xz = max(dn['drns'][-1], dp['drns'][-1])
    for dv in (dn, dp):
        C.box('z', 'm1', dv['drns'][-1], dv['yd'] - 0.17, xz, dv['yd'] + 0.17); C.via1('z', xz, dv['yd'])
    C.box('z', 'm2', xz - 0.15, dn['yd'], xz + 0.15, dp['yd'])
    xa = dn['gxs'][0]
    for dv in (dn, dp):
        gate_pad(C, dv, xa); C.via1('a', xa, dv['gy'])
    C.box('a', 'm2', xa - 0.15, dn['gy'], xa + 0.15, dp['gy'])
    ym = (dn['gy'] + dp['yd']) / 2
    PIN[name] = dict(a=(xa, ym), z=(xz, ym))
    finish(C)
    return name


def res_cell(name, seg=10.0, nseg=20, w=0.35, s=0.45):
    """고저항 poly 굽은 선 (1 MΩ 근사: 0.35 µm × 200 µm ≈ 570 □ × 2 kΩ/□). poly + rpm 표시 + 양 끝 met2 패드."""
    C = Cell(ly, name); p = w + s
    for k in range(nseg):
        C.box(None, 'poly', k * p, 0, k * p + w, seg)
        if k < nseg - 1:
            y = seg - w if k % 2 == 0 else 0
            C.box(None, 'poly', k * p, y, (k + 1) * p + w, y + w)
    C.c.shapes(ly.layer(86, 20)).insert(db.DBox(-0.2, -0.2, nseg * p + 0.2, seg + 0.2))
    xe, ye = (nseg - 1) * p + w / 2, (seg if nseg % 2 == 1 else 0.0)
    for net, (x, y) in (('a', (w / 2, 0.0)), ('z', (xe, ye))):
        C.box(net, 'li1', x - 0.2, y - 0.2, x + 0.2, y + 0.2); C.via1(net, x, y)
    PIN[name] = dict(a=(w / 2, 0.0), z=(xe, ye))
    return name


def tg_cell(name, wn, wmax=6.0):
    C = Cell(ly, name); r = gen_tg.build(C, 0.0, 0.0, wn, wmax); finish(C)
    ym = r['y1'] / 2
    PIN[name] = dict(a=(r['xa'], ym), z=(r['xb'], ym))
    return name


def hog_pins():
    c = ly.cell('hog'); P = {}
    it = c.begin_shapes_rec(ly.layer(69, 5)); it.shape_flags = db.Shapes.STexts
    while not it.at_end():
        t = it.shape().text.transformed(it.trans()); P[t.string] = (t.x * ly.dbu, t.y * ly.dbu); it.next()
    PIN['hog'] = dict(a=P['inp'], z=P['out'], vbn=P['vbn'], vbp=P['vbp'])


def input_drive(name, n_dev=198):
    """입력 2:1 스위치 NMOS 격자 + 대충 배선: 열마다 rail (짝 = VRAILP, 홀 = VRAILM, met2) ← 소스, 소자마다 행 출력선 (met3) → 오른쪽 끝 (배열 쪽),
    열마다 게이트선 (met4, DATA 쪽에서 옴)."""
    T = ly.create_cell('B_' + name); b = BB('nsw_w1000')
    px, py = b.width() + 1.2, b.height() + 1.0
    npc = int(AH // py); nx = math.ceil(n_dev / npc); WB = nx * px + 1.0; HB = npc * py
    for i in range(nx):
        xr = i * px - 0.6
        for j in range(npc):
            if i * npc + j >= n_dev:
                break
            q = pins('nsw_w1000', place(T, 'nsw_w1000', i * px, j * py))
            wire(T, 1, [(xr, q['s'].y), (q['s'].x, q['s'].y)]); via(T, xr, q['s'].y, 1, 2)
            yo = j * py + 2.0 + (i % nx) * (b.height() - 4.0) / nx
            wire(T, 2, [(q['d'].x, q['d'].y), (q['d'].x, yo)]); via(T, q['d'].x, yo, 2, 3)
            wire(T, 3, [(q['d'].x, yo), (WB, yo)])
            via(T, q['g'].x, q['g'].y, 2, 4)
        wire(T, 2, [(xr, 0), (xr, HB)])
        wire(T, 4, [(i * px + PIN['nsw_w1000']['g'][0] - b.left, 0), (i * px + PIN['nsw_w1000']['g'][0] - b.left, HB)])
    return block(name, T, f'NMOS W 1000 L 0.5 nf 50 × {n_dev} (행 98 × 2 + bias 행 2) + rail·행 출력선·게이트선', 'devlib')


L5 = dict(dff5=(12, 12), lat5=(6, 6), nand5=(2, 2), inv5=(1, 1), and5=(3, 3), ls5=(4, 2))
for k, (a, b) in L5.items():
    logic5(k, a, b)
logic5('sa5', 7, 4, wn=4.0, wp=2.0); logic5('pre5', 5, 2, wn=4.0, wp=4.0)
mos_cell('nsw_w1000', 'n', 1000, 0.5, 50)                           # 입력 2:1 스위치 하나 (W 1000, L 0.5)
mos_cell('wb_po', 'p', 400, 0.5, 80); mos_cell('wb_no', 'n', 200, 0.5, 40)
mos_cell('wb_p2', 'p', 32, 0.5, 8); mos_cell('wb_n2', 'n', 16, 0.5, 4); mos_cell('wb_p1', 'p', 8, 0.5, 2); mos_cell('wb_n1', 'n', 4, 0.5, 1)
mos_cell('inj_p', 'p', 42, 2.0, 8); mos_cell('inj_n', 'n', 15, 2.0, 3)
mos_cell('bm_n', 'n', 8 * 0.9 * 0.796, 1.0, 8); mos_cell('bm_p', 'p', 8 * 2 * 0.882, 0.8, 8); mos_cell('bm_pc', 'p', 8 * 1.5 * 0.882, 0.5, 8)
mos_cell('hb_n', 'n', 0.9, 1.0, 1); mos_cell('hb_p', 'p', 2.0, 0.8, 1); mos_cell('hb_pc', 'p', 1.5, 0.5, 1)
mos_cell('ck_n64', 'n', 64, 0.5, 16); mos_cell('ck_p128', 'p', 128, 0.5, 32); mos_cell('ck_n16', 'n', 16, 0.5, 4); mos_cell('ck_p32', 'p', 32, 0.5, 8)
mos_cell('decap_t', 'n', 10, 10.0, 1)
res_cell('r1m')
tg_cell('tg10', 10); tg_cell('tg20', 20, 8.0)
hog_pins()

# ── 블록 (이름은 floorplan_est.py 와 같게)
SRC_D = 'ep_demo/layout/blocks/ep_top_v3.gds (10/19)'
tile('crossbar', 'arr_ep_64x32_p5115', 2, 2, contents='1T1R 64×32 × 4 = 128×64', source=SRC_D)
tile('col_strip', 'colrow', 2, 1, contents='열 64: TG 4 (sense·0·RESET·SET 선택) + clamp 다이오드 2', source=SRC_D)
tile('row_mux', 'rowcell', 4, 32, contents='행 128: TG 6 (row 3 + WL 3), 4 줄 접기', source=SRC_D)
AH = INFO['crossbar']['h']; AW = INFO['crossbar']['w']
rows('col_dec', [('dff5', 120), ('nand5', 192), ('inv5', 128)], width=AW, out='top',
     contents='COL1·COL2 shift reg. 60 + 60 DFF, 열 decoder 64 (NAND 3 + INV 2)', source='devlib 5 V 논리 근사')
rows('row_tok', [('dff5', 106)], height=AH, out='side', contents='ROW1 100 + ROW2 6 DFF', source='devlib 5 V 논리 근사')
rows('row_dec', [('nand5', 6 * 128), ('inv5', 6 * 128)], height=AH, out='side', contents='행 decoder 128 (NAND 6 + INV 6)', source='devlib 5 V 논리 근사')
rows('data', [('dff5', 52), ('lat5', 52), ('and5', 104), ('inv5', 52)], height=AH, out='side',
     contents='DATA 52 DFF + latch 52 + 입력 gate AND 104', source='devlib 5 V 논리 근사')
input_drive('input_drive')
for k in ('wu1', 'wu2'):
    pack(k, [('hog', 4), ('r1m', 16), ('sa5', 3), ('pre5', 1), ('lat5', 1), ('tg10', 8)], width=90,
         contents='HOG 4 (A1–A4) + 1 MΩ 16 + StrongARM 3 + 전치 증폭기 + latch + TG 8', source='hog.gds (사용자) + devlib')
pack('write_buffer', [('wb_po', 1), ('wb_no', 1), ('wb_p2', 1), ('wb_n2', 1), ('wb_p1', 1), ('wb_n1', 1), ('nand5', 4), ('inv5', 1)], width=75,
     contents='XNOR (NAND 4 + INV) + 구동 2 단 + 출력 PMOS W 400 / NMOS W 200', source='devlib')
pack('bias', [('bm_p', 1), ('bm_pc', 1), ('bm_n', 1), ('hb_p', 1), ('hb_pc', 1), ('hb_n', 1), ('decap_t', 4)], width=46,
     contents='HOG bias (5 µA 기준) + β 미러 (단위 소자 m = 8) + bias 선 decap 4', source='devlib')
pack('nudge_injector', [('inj_p', 3), ('inj_n', 3), ('tg10', 12)], width=70, contents='주입기 3: PMOS W 42 / NMOS W 15 미러 + TG 4', source='devlib')
for k in ('readout_tg_f', 'readout_tg_n'):
    pack(k, [('tg20', 1)], width=20, contents='판독 TG (R2 → VBUS)', source='devlib·gen_tg')
pack('global_digital_5v', [('ck_n64', 5), ('ck_p128', 5), ('ck_n16', 5), ('ck_p32', 5), ('ls5', 20)], width=120,
     contents='레지스터 클록 buffer 5 (INV 4 단 끝 64/128) + 레벨 변환기 20', source='devlib')
rows('global_digital_1v8', [('DFFRX1', 12), ('TLATX1', 12), ('NAND2X1', 16), ('INVX1', 12), ('NOR2X1', 6), ('AND2X1', 6), ('CLKBUFX8', 2)], width=60,
     contents='설정 레지스터 12 + latch 12 + 동작 decoder (1.8 V 합성 자리)', source='sky130_scl_9T (Cadence, 내부용)')
tile('decap_tile', 'decap_t', 1, 1, contents='nfet MOS cap W 10 L 10 (빈 곳 채움 단위)', source='devlib')

so = db.SaveLayoutOptions()
for v in INFO.values():
    so.add_cell(ly.cell(v['cell']).cell_index())
(H / 'out').mkdir(exist_ok=True)
ly.write(str(H / 'out' / 'est_blocks.gds'), so)
json.dump(INFO, open(H / 'est_blocks.json', 'w'), indent=1, ensure_ascii=False)
for k, v in INFO.items():
    print(f"{k:20s} {v['w']:8.1f} × {v['h']:7.1f} µm  {v['contents']}")
