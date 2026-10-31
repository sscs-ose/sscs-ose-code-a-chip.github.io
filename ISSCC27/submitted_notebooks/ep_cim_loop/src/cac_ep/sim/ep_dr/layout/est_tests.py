"""(d2) test 영역 채우기 (10/27, 사용자 "그래 일단은 test pattern 넣어서 decap이 최대한 없게 보이도록 하자", "그려만 놓고 pad 연결은 안해놓아도 되지 뭐",
"일단 ring 오실레이터는 들어가야하고 … Sheet 저항 보기 위한 것도 넣을까?"). 패드 연결 없음, DRC·LVS 없음 — est_blocks.py 와 같은 가견적 셀.
est_blocks_d2.py (= est_blocks.py 사본) 의 셀 함수 부분을 그대로 쓰고, 아래 test 구조를 더함:
  ring oscillator (5 V: NAND enable + INV 101 + DFF 8 분주), clamp 다이오드 한 쌍 (p+ in nwell), 단일 1T1R (PDK 셀, 가견적 배열과 같은 W 1.5 셀),
  접근 nFET 단독 (W 3 / L 0.5, nf 2), 입력 스위치 축소판 (W 20), 비교기 (StrongARM + 전치 증폭기 + latch 근사), HOG op-amp 단독, 짝 소자 (n·p 각 2),
  Kelvin 4 단자 sheet 저항 (high-poly·xhigh-poly·p+ poly·n+ diff·nwell·met1·met2·met3), contact·via chain (licon·mcon·via1·via2).
영역 = floorplan_opt_D2.json 의 test 블록 (cell tp_*). 영역마다 꼭 넣을 구조 다음 Kelvin 저항·chain 을 돌려 가며 채움 (선반 채우기 = est 의 pack).
낸다: out/est_tests.gds (셀 B_tp_*), est_tests.json. 쓰임: /home/dave/work/projects/sern_hog_classab_opamp/sim/.venv/bin/python est_tests.py
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

# ── test 구조 셀
ly.read(str(DEMO / 'cells' / 'rram_1t1r_marked.gds'), opt)            # 단일 1T1R (RRAM_1T1R_larger, PDK 셀)
um = lambda v: int(round(v * 1000))


def rbox(c, ld, x0, y0, x1, y1):
    c.shapes(ly.layer(*ld)).insert(db.Box(um(min(x0, x1)), um(min(y0, y1)), um(max(x0, x1)), um(max(y0, y1))))


CONTACT = {  # 몸통 층 → 탭 접촉 쌓기 (몸통에서 met1 까지)
    'poly': [((66, 44), 0.17), ((67, 20), 0.6), ((67, 44), 0.17), ((68, 20), 0.6)],
    'diff': [((66, 44), 0.17), ((67, 20), 0.6), ((67, 44), 0.17), ((68, 20), 0.6)],
    'm1': [], 'm2': [((68, 44), 0.15), ((68, 20), 0.6)], 'm3': [((69, 44), 0.2), ((69, 20), 0.6), ((68, 44), 0.15), ((68, 20), 0.6)]}


def kelvin(name, kind, body, marks, w, L=40.0):
    """Kelvin 4 단자 sheet 저항: 몸통 (L × w, 가로) + 양 끝 force 패드 + 안쪽 sense 팔 2 개 (위로). body = 몸통 층, marks = 덮는 표시 층."""
    c = ly.create_cell(name); T = 1.6                                   # 패드 한 변
    rbox(c, body, 0, 0, L, w)
    for x in (-T, L):                                                    # force 패드
        rbox(c, body, x, -T / 2 + w / 2, x + T, T / 2 + w / 2)
    for x in (6.0, L - 6.0 - w):                                         # sense 팔 + 패드
        rbox(c, body, x, w, x + w, w + 4.0); rbox(c, body, x - (T - w) / 2, w + 4.0, x + (T + w) / 2, w + 4.0 + T)
    for (xc, yc) in ((-T / 2, w / 2), (L + T / 2, w / 2), (6.0 + w / 2, w + 4.0 + T / 2), (L - 6.0 - w / 2, w + 4.0 + T / 2)):
        for ld, s in CONTACT[kind]:
            rbox(c, ld, xc - s / 2, yc - s / 2, xc + s / 2, yc + s / 2)
    for ld in marks:                                                     # 표시 층 (몸통 가운데, 탭 사이)
        rbox(c, ld, 3.0, -0.3, L - 3.0, w + 0.3)
    PIN[name] = dict(a=(-T / 2, w / 2), z=(L + T / 2, w / 2))
    return name


def chain_cell(name, lo, hi, cut, cs, n=20, lw=0.6, p=2.0):
    """contact·via chain: 아래 층·위 층 막대를 번갈아 잇고 이음마다 cut (n 고리)."""
    c = ly.create_cell(name)
    for i in range(n):
        x = i * p
        rbox(c, lo if i % 2 == 0 else hi, x, 0, x + p + lw, lw)
        rbox(c, cut, x + p + lw / 2 - cs / 2, lw / 2 - cs / 2, x + p + lw / 2 + cs / 2, lw / 2 + cs / 2)
    PIN[name] = dict(a=(0.3, lw / 2), z=(n * p + lw, lw / 2))
    return name


def diode_pair(name):
    """clamp 다이오드 한 쌍 근사: p+ anode (diff + psd) in nwell + n-tap (tap + nsd) + diode 표시 (81/23), 두 개 나란히."""
    c = ly.create_cell(name)
    for k in range(2):
        x = k * 8.0
        rbox(c, (64, 20), x, 0, x + 7.0, 7.0)                            # nwell
        rbox(c, (65, 20), x + 2.0, 2.0, x + 5.0, 5.0); rbox(c, (94, 20), x + 1.8, 1.8, x + 5.2, 5.2); rbox(c, (81, 23), x + 2.0, 2.0, x + 5.0, 5.0)
        rbox(c, (65, 44), x + 0.6, 0.6, x + 6.4, 1.2); rbox(c, (93, 44), x + 0.4, 0.4, x + 6.6, 1.4)
        for (xc, yc) in ((x + 3.5, 3.5), (x + 3.5, 0.9)):
            for ld, s in CONTACT['diff']:
                rbox(c, ld, xc - s / 2, yc - s / 2, xc + s / 2, yc + s / 2)
        rbox(c, (75, 20), x - 0.6, -0.6, x + 7.6, 7.6)                  # hvi
    PIN[name] = dict(a=(3.5, 3.5), z=(11.5, 3.5))
    return name


def one_t_one_r(name):
    """단일 1T1R (PDK 셀) + 행 (TE)·열 (source)·WL 패드 met2."""
    c = ly.create_cell(name); r = ly.cell('RRAM_1T1R_larger')
    c.insert(db.CellInstArray(r.cell_index(), db.Trans(um(1.5), um(1.5))))
    for k in range(3):
        rbox(c, (69, 20), 6.0 + k * 3.0, 0.5, 8.0 + k * 3.0, 2.5)
    PIN[name] = dict(a=(2.0, 3.0), z=(14.0, 1.5))
    return name


# 셀 만들기
POLY, DIFF, NW, M1, M2, M3 = (66, 20), (65, 20), (64, 20), (68, 20), (69, 20), (70, 20)
RPM, URPM, PSD, NSD, NPC = (86, 20), (79, 20), (94, 20), (93, 44), (95, 20)
RES = [kelvin('kv_hpo_035', 'poly', POLY, [RPM, PSD, NPC], 0.35), kelvin('kv_hpo_1', 'poly', POLY, [RPM, PSD, NPC], 1.0),
       kelvin('kv_xpo_068', 'poly', POLY, [URPM, PSD, NPC], 0.68), kelvin('kv_xpo_2', 'poly', POLY, [URPM, PSD, NPC], 2.0),
       kelvin('kv_ppo_1', 'poly', POLY, [PSD, NPC], 1.0), kelvin('kv_ndiff_1', 'diff', DIFF, [NSD], 1.0),
       kelvin('kv_nwell_3', 'diff', NW, [], 3.0), kelvin('kv_m1_05', 'm1', M1, [], 0.5), kelvin('kv_m2_05', 'm2', M2, [], 0.5),
       kelvin('kv_m3_1', 'm3', M3, [], 1.0)]
CHN = [chain_cell('ch_licon', POLY, (67, 20), (66, 44), 0.17), chain_cell('ch_mcon', (67, 20), M1, (67, 44), 0.17),
       chain_cell('ch_via1', M1, M2, (68, 44), 0.15), chain_cell('ch_via2', M2, M3, (69, 44), 0.2)]
diode_pair('tp_diode'); one_t_one_r('tp_1t1r')
mos_cell('tp_nacc_w3', 'n', 3.0, 0.5, 2); mos_cell('tp_nsw_w20', 'n', 20.0, 0.5, 4)
mos_cell('tp_nm', 'n', 2.0, 0.5, 2); mos_cell('tp_pm', 'p', 4.0, 0.5, 2)
rows('tp_ro', [('nand5', 1), ('inv5', 101), ('dff5', 8)], width=80.0, out='side',
     contents='ring oscillator: NAND enable + INV 101 단 + DFF 8 (÷256)', source='devlib 5 V 논리 근사')
RO = 'B_tp_ro'

# 영역마다: 꼭 넣을 구조 → 남는 높이를 저항·chain 으로 (pack 과 같은 선반 채우기를 미리 셈)
F = json.load(open(H / 'floorplan_opt_D3.json'))                 # 최신 배치 (10/27 write buffer 두 개 → 띠 오른쪽 영역이 좁아짐)
AREA = {b['cell'][2:]: (b['rect'][2] - b['rect'][0], b['rect'][3] - b['rect'][1]) for b in F['blocks'] if b['kind'] == 'test'}
MUST = {'tp_tl': [(RO, 1), ('tp_diode', 1), ('tp_1t1r', 1), ('tp_nacc_w3', 1), ('tp_nsw_w20', 1)],
        'tp_br': [('sa5', 1), ('pre5', 1), ('lat5', 1), ('hog', 1), ('tp_nm', 2), ('tp_pm', 2), ('tg20', 1)],
        'tp_bandl': [('ch_licon', 1), ('ch_mcon', 1)],
        'tp_bandr': [('kv_hpo_035', 1), ('kv_xpo_068', 1), ('ch_via1', 1), ('ch_via2', 1)]}
FILL = RES + CHN
GAP, RAIL = 1.0, 8.0                                                   # pack 의 틈, 위·아래 rail·bias 선 자리 (±4)


def shelf_h(seq, width):
    x = y = rowh = 0.0
    for cname in seq:
        b = BB(cname)
        if x > 0 and x + b.width() > width:
            x, y, rowh = 0.0, y + rowh + GAP, 0.0
        x += b.width() + GAP; rowh = max(rowh, b.height())
    return y + rowh


for name, (w, h) in AREA.items():
    seq = [c for c, n in MUST[name] for _ in range(n)]
    assert all(BB(c).width() <= w - 1 for c in seq), (name, [(c, BB(c).width()) for c in seq if BB(c).width() > w - 1])
    assert shelf_h(seq, w - 1) <= h - RAIL, (name, '꼭 넣을 구조가 안 들어감', shelf_h(seq, w - 1), h)
    k = 0
    while True:
        cand = FILL[k % len(FILL)]
        if BB(cand).width() > w - 1 or shelf_h(seq + [cand], w - 1) > h - RAIL:
            if k > 3 * len(FILL):
                break
            k += 1; continue
        seq.append(cand); k += 1
    items = []
    for c in seq:                                                       # pack 은 (셀, 개수) 를 받음 — 이어진 같은 셀을 묶음
        if items and items[-1][0] == c:
            items[-1] = (c, items[-1][1] + 1)
        else:
            items.append((c, 1))
    pack(name, items, width=w - 1, gap=GAP, contents=f'test 구조 {len(seq)} 개', source='devlib·PDK 1T1R·hog.gds')
    print(name, f'영역 {w:.1f} × {h:.1f}', f'블록 {INFO[name]["w"]:.1f} × {INFO[name]["h"]:.1f}', f'구조 {len(seq)}')

so = db.SaveLayoutOptions()
for v in INFO.values():
    so.add_cell(ly.cell(v['cell']).cell_index())
ly.write(str(H / 'out' / 'est_tests.gds'), so)
json.dump(INFO, open(H / 'est_tests.json', 'w'), indent=1, ensure_ascii=False)
