"""새 die (실제 크기 배치) 의 pad frame (10/28, 조정 세션: "새 die 2020 × 1810 µm 의 pad frame … place/die_real.gds 와 pads json").
사용자 지시 (10/28): "각 블럭 길이 연결하는 것과 lvs 통과와 DRC 통과가 되면은 CaC 제출 기준에 만족", "동시실행 너무 한번에 많이 하지는 말고".

규칙은 (d3) 와 같다 — ../../floorplan_opt.py 의 fill_spares·place_pads, ../../padframe_gds.py 를 이 파일로 복사해 씀 (원본은 고치지 않음):
  - die = up10(core + 2 × 334) (IO ring 30 + 204 + 10, core 전원 ring 4 × 20, 틈 10), core 를 die 가운데에.
  - 패드 44 개 (신호 23 + 전원 21 쪽 이름 패드) 의 원하는 중심 = 이어지는 블록 자리. 블록 자리는 d3 사각형 대신 place_real.json 의 실제 자리.
  - 변마다 패드 사이 최소 15 µm, 남는 틈은 예비 아날로그 패드로 채우고 그중 변마다 둘을 VDD·VSS clamp 로 (fill_spares), 나머지 틈은 com_bus_slice, 아래 변에 이음 slice 하나.
  - GDS: 실제 sky130_ef_io 셀 + core 전원 ring (met5 자리표시) + core 자리 (240/0 상자). prBoundary (235/4) 는 IO 셀 안 것까지 지움 (DRC x.prBndry, 10/26).
IO 라이브러리 = 로컬 volare c6d73a35 `libs.ref/sky130_fd_io/gds` (Olympus layout/iolib/ 사본과 md5 같음, 10/28 확인).
낸다: die_real.json (패드·filler·모서리·ring·core 자리·블록), die_real.gds (top `ep_die_real`), die_real.png
쓰임: /home/dave/work/projects/sern_hog_classab_opamp/sim/.venv/bin/python padframe_real.py
"""
import json
from pathlib import Path

import klayout.db as db

H = Path(__file__).resolve().parent
L = H.parents[1]
IO = Path.home() / 'pdk/volare/sky130A/libs.ref/sky130_fd_io/gds'
LYP = Path.home() / 'pdk/volare/sky130A/libs.tech/klayout/tech/sky130A.lyp'
PR = json.loads((H / 'place_real.json').read_text())
D3 = json.loads((L / 'floorplan_opt_D3.json').read_text())

# ── floorplan_opt.py 에서 그대로 (상수)
M = 30.0
RING_OUT = M + 204 + 10 + 4 * 20
up10 = lambda v: float(-(-v // 10) * 10)
CELL = {
    'gpio': ('sky130_ef_io__gpiov2_pad', 80.0, 197.965), 'analog': ('sky130_ef_io__analog_esd_pad', 75.0, 200.0),
    'vdda': ('sky130_ef_io__vdda_hvc_clamped_pad', 75.0, 197.965), 'vssa': ('sky130_ef_io__vssa_hvc_clamped_pad', 75.0, 197.965),
    'vddio': ('sky130_ef_io__vddio_hvc_clamped_pad', 75.0, 197.965), 'vssio': ('sky130_ef_io__vssio_hvc_clamped_pad', 75.0, 197.965),
    'vccd': ('sky130_ef_io__vccd_lvc_clamped_pad', 75.0, 197.965), 'vssd': ('sky130_ef_io__vssd_lvc_clamped_pad', 75.0, 197.965),
    'connect': ('sky130_ef_io__connect_vcchib_vccd_and_vswitch_vddio_slice_20um', 20.0, 197.965)}
SLICE = {w: f'sky130_ef_io__com_bus_slice_{w}um' for w in (20, 10, 5, 1)}
CORNER = 'sky130_ef_io__corner_pad'
PAD_GAP = 15
G_, A_ = 'gpio', 'analog'
ptype = lambda n, c: 'spare' if n.startswith('SPARE') else 'power' if c not in (G_, A_) or n == 'VCM' else 'digital' if c == G_ else 'analog'
ROT = {'top': 0, 'left': 1, 'bottom': 2, 'right': 3}


# ── floorplan_opt.py fill_spares 사본 (바꾼 것 없음)
def fill_spares(P_SIDES, SPAN):
    sw, k_sp, out = CELL[A_][1], 6, {}
    for side, items in P_SIDES.items():
        a, b = SPAN[side]; L_ = abs(b - a); d = 1 if b > a else -1
        widths = [CELL[c][1] for _, c, _ in items]
        u = [max(0, int(round((cc - a) * d - w / 2))) for (_, _, cc), w in zip(items, widths)]
        for i in range(1, len(u)):
            u[i] = max(u[i], u[i - 1] + widths[i - 1] + PAD_GAP)
        u[-1] = min(u[-1], int(L_) - widths[-1])
        for i in range(len(u) - 2, -1, -1):
            u[i] = min(u[i], u[i + 1] - widths[i] - PAD_GAP)
        starts = [0.0] + [ui + w for ui, w in zip(u, widths)]
        ends = list(u) + [float(L_)]
        gaps = [e - s for s, e in zip(starts, ends)]
        if side == 'bottom':
            j = max(range(len(gaps)), key=lambda i: gaps[i]); gaps[j] -= CELL['connect'][1] + PAD_GAP
        new = []
        for i in range(len(gaps)):
            k = max(0, int((gaps[i] - PAD_GAP) // (sw + PAD_GAP)))
            for q in range(k):
                pitch = (gaps[i] - PAD_GAP) / k
                dist = starts[i] + PAD_GAP + q * pitch + sw / 2
                new.append((f'SPARE{k_sp}', A_, a + d * dist)); k_sp += 1
            if i < len(items):
                new.append(items[i])
        vdd, vss = ('vddio', 'vssio') if side in ('top', 'bottom') else ('vdda', 'vssa')
        sig = [cc for nm, c, cc in new if c in (G_, A_) and not nm.startswith('SPARE') and nm != 'VCM']
        clp = [cc for nm, c, cc in new if c not in (G_, A_)]
        sp = [k for k, (nm, _, _) in enumerate(new) if nm.startswith('SPARE') and int(nm[5:]) >= 6]
        worst = lambda extra: max((min(abs(x - y) for y in clp + extra) for x in sig), default=0.0)
        pairs = [(k, k2) for k in sp for k2 in sp if k2 == k + 1]
        if pairs:
            k1, k2 = min(pairs, key=lambda kk: worst([new[kk[0]][2], new[kk[1]][2]]))
            new[k1] = ('VDD', vdd, new[k1][2]); new[k2] = ('VSS', vss, new[k2][2])
        elif sp:
            k1 = min(sp, key=lambda k: worst([new[k][2]]))
            new[k1] = ('VDD', vdd, new[k1][2])
        out[side] = new
    return out


# ── floorplan_opt.py place_pads 사본 (바꾼 것: 이름표 tag 대신 고정 문자열)
def place_pads(P_SIDES, DIE_W, DIE_H, fill=True):
    SPAN = {'top': (M + 204, DIE_W - M - 200), 'bottom': (DIE_W - M - 204, M + 200), 'right': (DIE_H - M - 204, M + 200), 'left': (M + 204, DIE_H - M - 200)}
    if fill:
        P_SIDES = fill_spares(P_SIDES, SPAN)

    def place(side, s, w, h):
        if side == 'top':
            return (s, DIE_H - M - h), [s, DIE_H - M - h, s + w, DIE_H - M]
        if side == 'bottom':
            return (s, M + h), [s - w, M, s, M + h]
        if side == 'left':
            return (M + h, s), [M, s, M + h, s + w]
        return (DIE_W - M - h, s), [DIE_W - M - h, s - w, DIE_W - M, s]

    PADS, FILL = [], []
    for side, items in P_SIDES.items():
        a, b = SPAN[side]; L_ = abs(b - a); d = 1 if b > a else -1
        widths = [CELL[c][1] for _, c, _ in items]
        conn = side == 'bottom'
        u = [max(0, int(round((cc - a) * d - w / 2))) for (_, _, cc), w in zip(items, widths)]
        for i in range(1, len(u)):
            u[i] = max(u[i], u[i - 1] + widths[i - 1] + PAD_GAP)
        u[-1] = min(u[-1], int(L_) - widths[-1])
        for i in range(len(u) - 2, -1, -1):
            u[i] = min(u[i], u[i + 1] - widths[i] - PAD_GAP)
        assert u[0] >= 0, ('real', side, '패드가 변에 안 들어감', u)
        ends = [0] + [ui + w for ui, w in zip(u, widths)]
        gaps = [ui - e for ui, e in zip(u + [int(L_)], ends)]
        n = len(items) + 1
        i_conn = max(range(n), key=lambda i: gaps[i]) if conn else -1
        assert not conn or gaps[i_conn] >= CELL['connect'][1]
        if conn:
            gaps[i_conn] -= CELL['connect'][1]
        s = a
        for i in range(n):
            gg = gaps[i]
            if i == i_conn:
                o, r = place(side, s, CELL['connect'][1], CELL['connect'][2]); FILL.append(dict(cell=CELL['connect'][0], side=side, origin=o, rot=ROT[side], rect=r))
                s += d * CELL['connect'][1]
            for w in (20, 10, 5, 1):
                while gg >= w:
                    o, r = place(side, s, w, 197.965); FILL.append(dict(cell=SLICE[w], side=side, origin=o, rot=ROT[side], rect=r))
                    s += d * w; gg -= w
            if i < len(items):
                nm, c, _ = items[i]; cn, w, h = CELL[c]
                o, r = place(side, s, w, h)
                PADS.append(dict(name=nm, type=ptype(nm, c), io=c, cell=cn, side=side, origin=[round(v, 3) for v in o], rot=ROT[side], rect=[round(v, 3) for v in r]))
                s += d * w
        assert abs(s - b) < 1e-6, (side, s, b)
    CORNERS = [dict(cell=CORNER, at='TR', rot=0, origin=[DIE_W - M - 200, DIE_H - M - 204]), dict(cell=CORNER, at='TL', rot=1, origin=[M + 204, DIE_H - M - 200]),
               dict(cell=CORNER, at='BL', rot=2, origin=[M + 200, M + 204]), dict(cell=CORNER, at='BR', rot=3, origin=[DIE_W - M - 204, M + 200])]
    n_by = {t: sum(p['type'] == t for p in PADS) for t in ('digital', 'analog', 'power', 'spare')}
    assert n_by['digital'] == 11 and n_by['analog'] == 12 and n_by['power'] >= 14, n_by
    RING_IN = M + 204 + 10
    RINGS = [dict(net=nn, offset=round(RING_IN + k * 20, 2), width=15.0) for k, nn in enumerate(('VSS', 'VDD', 'VCM', 'VCCD'))]
    fill_ratio = {sd: round(sum(CELL[c][1] for _, c, _ in it) / abs(SPAN[sd][1] - SPAN[sd][0]), 3) for sd, it in P_SIDES.items()}
    return PADS, FILL, CORNERS, n_by, RINGS, fill_ratio


# ── die 와 패드 원하는 중심 (floorplan_opt.py build_stacked 의 P_SIDES 와 같은 식, 블록 = 실제 배치)
CORE_W, CORE_H = PR['core']['w'], PR['core']['h']
DIE_W, DIE_H = up10(CORE_W + 2 * (RING_OUT + 10)), up10(CORE_H + 2 * (RING_OUT + 10))
assert max(DIE_W, DIE_H) <= 2500, ('die 한도 2.5 mm', DIE_W, DIE_H)
OX, OY = round((DIE_W - CORE_W) / 2, 3), round((DIE_H - CORE_H) / 2, 3)
I = PR['instances']
BD = {k: [OX + v['x'], OY + v['y'], OX + v['x'] + v['w'], OY + v['y'] + v['h']] for k, v in I.items()}
cx = lambda n: (BD[n][0] + BD[n][2]) / 2
cy = lambda n: (BD[n][1] + BD[n][3]) / 2
# d3 이름 → 실제 인스턴스: input drive (free/nudge) = idrv_f/n, global digital (5 V) = glob, WU1 = wu1,
#   row decoder (free/nudge) = rowb_f/n (row 쪽 세 블록이 row_blk 하나), readout TG (free) = rotg_f, nudge injector = ninj, bias = bias
xf, xnn = cx('idrv_f'), cx('idrv_n')
yd, ybd, xd = cy('glob'), cy('wu1'), cx('glob')
P_SIDES = {
    'top': [('VSSL', 'vssd', xd - 120), ('VDDL', 'vccd', xd - 40), ('SCK', G_, xd + 40), ('SDI', G_, xd + 120), ('SLD', G_, xd + 200),
            ('RST', G_, xd + 280), ('SEL_EN', G_, xd + 360), ('WP', G_, xd + 440), ('VRAILP', A_, xf + 120), ('VRAILM', A_, xf + 200),
            ('VDD', 'vdda', OX + CORE_W / 2 + 200), ('VSS', 'vssa', OX + CORE_W / 2 + 280), ('VCM', A_, OX + CORE_W / 2 + 360)],
    'right': [('VDD', 'vddio', cy('rowb_f') + 60), ('VSS', 'vssio', cy('rowb_f') - 30), ('SPARE4', A_, cy('rowb_f') - 120),
              ('VBUS_F', A_, cy('rotg_f')), ('IBIAS', A_, cy('ninj') + 40), ('VBNC', A_, cy('bias')), ('VBPC', A_, cy('bias') - 80)],
    'bottom': [('VRAILM', A_, xnn + 40), ('VRAILP', A_, xnn - 40), ('VCM', A_, OX + CORE_W / 2 - 200), ('VSS', 'vssa', OX + CORE_W / 2 - 280),
               ('VDD', 'vdda', OX + CORE_W / 2 - 360), ('SPARE1', A_, OX + 300), ('SPARE2', A_, OX + 220), ('SPARE3', A_, OX + 140), ('SPARE5', A_, OX + 60)],
    'left': [('VSS', 'vssio', cy('rowb_n') - 40), ('VDD', 'vddio', cy('rowb_n') + 40), ('VBUS_N', A_, ybd - 120),
             ('VWL', A_, ybd - 40), ('VWLO', A_, ybd + 40), ('VWH', A_, ybd + 120), ('VSSL', 'vssd', yd - 200), ('VDDL', 'vccd', yd - 120),
             ('LQ1', G_, yd - 40), ('LQ2', G_, yd + 40), ('CK', G_, yd + 120), ('CK3', G_, yd + 200), ('LAT', G_, yd + 280)]}
PADS, FILL, CORNERS, n_by, RINGS, fill_ratio = place_pads(P_SIDES, DIE_W, DIE_H, fill=True)
# d3 와 비교 (같은 이름·변의 패드가 core 기준으로 얼마나 옮겨졌나)
d3_core = D3['core']['offset_in_die']
named = lambda P, o: {(p['side'], p['name'], k): ((p['rect'][0] + p['rect'][2]) / 2 - o[0], (p['rect'][1] + p['rect'][3]) / 2 - o[1])
                      for k, p in enumerate(P)}
order = lambda P: {sd: [p['name'] for p in P if p['side'] == sd] for sd in ('top', 'right', 'bottom', 'left')}
same_list = order(PADS) == order(D3['pads'])

blocks = [dict(name=k, cell=v['cell'], rect=[round(v['x'], 3), round(v['y'], 3), round(v['x'] + v['w'], 3), round(v['y'] + v['h'], 3)]) for k, v in I.items()]
blocks += [dict(name=k, cell='test area', rect=v['rect']) for k, v in PR['test_areas'].items() if k not in I]   # 블록이 생긴 test 자리는 위 instances 에 있음
J = dict(version='실제 크기 배치 die (10/28) — (d3) 패드 규칙, core = place_real.json',
         note='좌표 µm. 패드·filler·모서리·ring = die 좌표 (원점 = die 왼쪽 아래). blocks = core 좌표. chip_core 를 die 에 놓는 자리 = core.offset_in_die (R0).',
         iolib='sky130_ef_io / sky130_fd_io (volare sky130 c6d73a35f524070e85faff4a6a9eef49553ebc2b), 크기 = LEF',
         rails=D3['rails'], core=dict(w=CORE_W, h=CORE_H, offset_in_die=[OX, OY]), die=dict(w=DIE_W, h=DIE_H, margin=M),
         corners=CORNERS, pads=PADS, fillers=FILL, core_rings=RINGS, blocks=blocks, pad_count=n_by, side_fill=fill_ratio,
         d3=dict(die=[D3['die']['w'], D3['die']['h']], pad_count=D3['pad_count'], same_pad_order=same_list))
(H / 'die_real.json').write_text(json.dumps(J, indent=1, ensure_ascii=False))
print(f'die {DIE_W} × {DIE_H}, core offset ({OX}, {OY}), pads {len(PADS)} {n_by} (d3 {D3["pad_count"]}), fillers {len(FILL)}, side fill {fill_ratio}, '
      f'패드 순서 d3 와 같음: {same_list}')

# ── GDS (padframe_gds.py 사본: 경로·이름만)
ly = db.Layout(); ly.dbu = 0.001
ly.read(str(IO / 'sky130_fd_io.gds'))                            # fd_io 먼저 (ef_io 의 빈 참조 셀을 채움)
opt = db.LoadLayoutOptions(); opt.cell_conflict_resolution = db.LoadLayoutOptions.SkipNewCell
for f in ('sky130_ef_io.gds', 'sky130_ef_io__analog.gds', 'sky130_ef_io__connect_vcchib_vccd_and_vswitch_vddio_slice_20um.gds'):
    ly.read(str(IO / f), opt)
T = ly.create_cell('ep_die_real')
um = lambda v: int(round(v * 1000))
missing = set()


def inst(name, ox, oy, rot):
    c = ly.cell(name)
    if c is None or c.bbox().empty():
        missing.add(name); return
    T.insert(db.CellInstArray(c.cell_index(), db.Trans(rot, False, um(ox), um(oy))))


for c in CORNERS:
    inst(c['cell'], *c['origin'], c['rot'])
for p in PADS:
    inst(p['cell'], *p['origin'], p['rot'])
for f in FILL:
    inst(f['cell'], *f['origin'], f['rot'])
LY = {k: ly.layer(*v) for k, v in dict(bnd=(235, 4), m5=(72, 20), m5t=(72, 5), core=(240, 0)).items()}
for p in PADS:                                                     # 패드 이름 (bond pad 가운데, met5 이름표)
    x0, y0, x1, y1 = p['rect']; pcx, pcy = (x0 + x1) / 2, (y0 + y1) / 2
    dpt = 64.0
    bx, by = {'top': (pcx, DIE_H - M - dpt), 'bottom': (pcx, M + dpt), 'left': (M + dpt, pcy), 'right': (DIE_W - M - dpt, pcy)}[p['side']]
    T.shapes(LY['m5t']).insert(db.Text(p['name'], db.Trans(um(bx), um(by))))
for rg in RINGS:                                                   # core 전원 ring (met5 자리표시)
    o, w = rg['offset'], rg['width']
    outer = db.Region(db.Box(um(o), um(o), um(DIE_W - o), um(DIE_H - o)))
    inner = db.Region(db.Box(um(o + w), um(o + w), um(DIE_W - o - w), um(DIE_H - o - w)))
    T.shapes(LY['m5']).insert(outer - inner)
    T.shapes(LY['m5t']).insert(db.Text(rg['net'], db.Trans(um(DIE_W / 2), um(o + w / 2))))
T.shapes(LY['core']).insert(db.Box(um(OX), um(OY), um(OX + CORE_W), um(OY + CORE_H)))   # core 자리 (240/0, DRC 덱이 안 보는 층)
ly.clear_layer(LY['bnd'])
so = db.SaveLayoutOptions(); so.add_cell(T.cell_index())
ly.write(str(H / 'die_real.gds'), so)
inner_ring = RINGS[-1]['offset'] + RINGS[-1]['width']
print('die_real.gds', 'missing', sorted(missing), f'core ↔ 안쪽 ring 틈 {min(OX, OY) - inner_ring:.2f} µm')

# ── 그림 (padframe_gds.py 와 같은 그리기)
import klayout.lay as lay                                          # noqa: E402
lv = lay.LayoutView()
lv.set_config('background-color', '#ffffff'); lv.set_config('grid-visible', 'false')
lv.set_config('text-visible', 'false'); lv.set_config('cell-box-visible', 'false')
lv.load_layout(str(H / 'die_real.gds'), True)
if LYP.exists():
    lv.load_layer_props(str(LYP))
lv.add_missing_layers()
for lp in lv.each_layer():
    if (lp.source_layer, lp.source_datatype) == (240, 0):
        lp.dither_pattern = 1; lp.fill_color = lp.frame_color = 0x500000; lp.width = 2
cv = lv.active_cellview(); cv.cell_name = 'ep_die_real'
lv.max_hier()
lv.zoom_box(db.DBox(-30, -30, DIE_W + 30, DIE_H + 30))
px = 2400
lv.save_image(str(H / 'die_real.png'), px, int(px * (DIE_H + 60) / (DIE_W + 60)))
