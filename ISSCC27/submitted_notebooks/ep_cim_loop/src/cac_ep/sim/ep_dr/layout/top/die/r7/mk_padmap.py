"""die pad map: place/die_real.json 의 패드 자리 (slot) 에 core 넷을 다시 배정하고, core 핀 자리 (core 좌표) 를 패드 핀에 맞춘다.
사용자 (10/28): "하는 김에 패드까지 연결하면 작업을 하고", "패드끼리 자리를 바꿔 가지고 조금 더 레이아웃 편하게 해도 돼".
규칙: 같은 셀 종류끼리만 바꾼다 (pad frame GDS 그대로 씀). 전원 패드·ESD clamp 자리는 그대로.
쓰임: <klayout python> mk_padmap.py → pad_map.json · pad_map.md
"""
import json
import sys
from pathlib import Path

import klayout.db as db

H = Path(__file__).resolve().parent              # die/r7 (route/die/mk_padmap.py 사본)
sys.path.insert(0, str(H))                       # die/r7 사본: routelib 도 여기
import routelib as R  # noqa: E402

TOPD = H.parents[1]
DJ = json.load(open(TOPD / 'place' / 'die_real.json'))
OX, OY = DJ['core']['offset_in_die']; CW, CH = DJ['core']['w'], DJ['core']['h']
IOLEF = Path.home() / 'pdk/volare/sky130A/libs.ref/sky130_fd_io/lef/sky130_ef_io.lef'
M = R.parse_lef(str(IOLEF))

# 패드 GDS 변환 (die_real.gds 의 실제 인스턴스) ← rect 로 짝지음
ly = db.Layout(); ly.read(str(TOPD / 'place' / 'die_real.gds'))
top = ly.top_cells()[0]
TR = {}
for inst in top.each_inst():
    c = ly.cell(inst.cell_index).name
    if c.startswith('sky130_ef_io__') and ('_pad' in c):
        TR[(c, round(inst.dbbox().left, 2), round(inst.dbbox().bottom, 2))] = inst.dcplx_trans
SIDE = {'top': 'N', 'bottom': 'S', 'left': 'W', 'right': 'E'}

# ── 새 배정 (옛 이름 → 새 넷). 바꾼 것만 적음 (나머지는 그대로)
#   아래 변: VRAILP·VRAILM 을 input_drive (nudge, R180) rail 핀 (core x 1103–1116) 양옆 예비 자리로 — P 서쪽, M 동쪽 (엇갈림 없음)
#   오른쪽 변: VWH·VWLO 를 하나씩 더 (write buffer free 가 오른쪽, WU 줄 위·아래 띠 높이에 맞춘 예비 자리)
MOVE = {('bottom', 'VRAILP'): '', ('bottom', 'VRAILM'): '', ('bottom', 'SPARE19'): 'VRAILP', ('bottom', 'SPARE18'): 'VRAILM',
        ('right', 'SPARE12'): 'VWH', ('right', 'SPARE13'): 'VWLO',
        ('bottom', 'SPARE17'): 'IBIASP'}   # die r7: IBIASP = slot 31 (slot 32 는 VRAILM 이 씀)
PINOF = {'gpio_in': 'IN_H', 'gpio_out': 'PAD_A_ESD_0_H', 'analog': 'P_CORE'}
OUTS = {'LQ1', 'LQ2'}


def die_rect(t, r):
    b = t * db.DBox(r[0] / 1000, r[1] / 1000, r[2] / 1000, r[3] / 1000)
    return (b.left, b.bottom, b.right, b.top)


slots = []
core_pins = {}
for k, p in enumerate(DJ['pads']):
    cell = p['cell']; side = SIDE[p['side']]
    rr = p['rect']
    t = None
    for (c, x, y), tt in TR.items():
        b = tt * db.DBox(0, 0, M[cell].size[0] / 1000, M[cell].size[1] / 1000)
        if c == cell and abs(b.left - rr[0]) < 0.5 and abs(b.bottom - rr[1]) < 0.5 and abs(b.right - rr[2]) < 0.5 and abs(b.top - rr[3]) < 0.5:
            t = tt
    if t is None:
        raise SystemExit(f'no GDS instance for pad {k} {p["name"]} {cell} {rr}')
    new = MOVE.get((p['side'], p['name']), p['name'])
    kind = 'power' if 'clamped_pad' in cell else ('gpio_out' if new in OUTS else 'gpio_in') if 'gpiov2' in cell else 'analog'
    if new.startswith('SPARE') or new == '':
        kind = 'spare'
    s = dict(idx=k, old=p['name'], new=new if not new.startswith('SPARE') else '', cell=cell, side=side, rect_die=rr,
             trans=[t.disp.x, t.disp.y, t.angle], kind=kind)
    if kind in PINOF:
        pin = PINOF[kind]
        r = [x for l, x in M[cell].pins[pin] if l in ('met2', 'met3')]
        r = min(r, key=lambda q: q[1])                                    # core 쪽 끝 조각
        dr = die_rect(t, r)
        s['pin'] = pin; s['pin_die'] = dr
        if side in 'NS':
            c = (dr[0] + dr[2]) / 2 - OX; w = dr[2] - dr[0]
        else:
            c = (dr[1] + dr[3]) / 2 - OY; w = dr[3] - dr[1]
        s['proj_core'] = c; s['pin_w'] = w
    if kind == 'power':
        # 전원 패드 손가락 (met3, core 쪽 끝) 두 개
        net = 'VDD' if new == 'VDD' else 'VSS' if new == 'VSS' else new
        pin = {'sky130_ef_io__vdda_hvc_clamped_pad': 'VDDA', 'sky130_ef_io__vddio_hvc_clamped_pad': 'VDDIO',
               'sky130_ef_io__vssa_hvc_clamped_pad': 'VSSA', 'sky130_ef_io__vssio_hvc_clamped_pad': 'VSSIO',
               'sky130_ef_io__vccd_lvc_clamped_pad': 'VCCD', 'sky130_ef_io__vssd_lvc_clamped_pad': 'VSSD'}[cell]
        fr = [die_rect(t, x) for l, x in M[cell].pins[pin] if l == 'met3']
        s['fingers_die'] = fr; s['rail'] = pin
        cx = sum((f[0] + f[2]) / 2 for f in fr) / len(fr) - OX; cy = sum((f[1] + f[3]) / 2 for f in fr) / len(fr) - OY
        s['proj_core'] = cx if side in 'NS' else cy
    slots.append(s)
    if s['new'] and kind != 'spare':
        core_pins.setdefault(s['new'], []).append(dict(side=side, pos=s['proj_core'], width=s.get('pin_w', 8.0), kind=kind, slot=k))

json.dump(dict(note='core 좌표 µm (core 왼쪽 아래 원점). pos = 패드 핀 가운데를 core 변에 내린 자리 (변을 따라). die 좌표 = core + offset',
               offset=[OX, OY], core=[CW, CH], slots=slots, core_pins=core_pins, moved={f'{a}:{b}': v for (a, b), v in MOVE.items()}),
          open(H / 'pad_map.json', 'w'), indent=1, ensure_ascii=False)
L = ['# die pad map (route/die/pad_map.json) — 이전 → 새 배정', '',
     '같은 셀 종류끼리만 바꿈 (pad frame `place/die_real.gds` 그대로). 전원·ESD clamp 패드 자리 그대로. core 좌표 = core 왼쪽 아래 원점 (die = core + (336.70, 338.43)).', '',
     '| # | 변 | 셀 | die 자리 (µm) | 이전 | **새** | 핀 | core 위 자리 |', '|---|---|---|---|---|---|---|---|']
for s in slots:
    ch = '' if (s['old'] == s['new'] or (s['old'].startswith('SPARE') and s['new'] == '')) else ' ←'
    L.append(f"| {s['idx']} | {s['side']} | {s['cell'].replace('sky130_ef_io__', '')} | {s['rect_die'][0]:.1f},{s['rect_die'][1]:.1f} | {s['old']} | "
             f"**{s['new'] or '(예비)'}**{ch} | {s.get('pin', s.get('rail', ''))} | {s.get('proj_core', 0):.2f} |")
(H / 'pad_map.md').write_text('\n'.join(L) + '\n')
print('slots', len(slots), 'core nets', len(core_pins))
for n, v in sorted(core_pins.items()):
    print(n, [(x['side'], round(x['pos'], 2)) for x in v])
