"""write buffer 셀 생성기 (10/28) — 칩에 두 개 (XWBf → vwf, XWBn → vwn), 셀은 하나.
netlist 기준 = real_circuit/chip_lib.py WBUF + wu_lib.primitives() (NAND2: P 2/0.5 ×2 병렬, N 2/0.5 ×2 직렬 · INV: N 1 / P 2):
  XN1 (wp, pol → n1), XN2 (wp, n1 → n2), XN3 (pol, n1 → n3), XN4 (n2, n3 → xr), XI0 (xr → f0) = XNOR,
  XP1/XM1 f0 → f1 (P 8 nf2 / N 4), XP2/XM2 f1 → f2 (P 32 nf8 / N 16 nf4),
  XPo out f2 vwh (bulk vdd) P 400, XMo out f2 vwl (bulk vss) N 200 — 모두 L 0.5, g5v0d10v5.
배치 (rowch.py): 아래 NMOS 줄 = 논리 N 11 개 + XMo, 위 PMOS 줄 = 논리 P 11 개 + XPo, 가운데 통로 met3 트랙 9 개.
  NAND 직렬 마디 (s1–s4) = 이웃한 두 N 소자 드레인 스트랩을 met1 로 바로 (트랙 없음).
  출력단 (XMo·XPo, 같은 x): S/D 줄 위에 바로 via1·via2 → met3 판: vwl 띠 (XMo 아래쪽) · out 판 (XMo 위쪽 + 통로 + XPo 아래쪽) · vwh 띠 (XPo 위쪽).
  netlist 와 핑거만 다름: XPo nf 80 (5 µm) → nf 40 (10 µm), W 400 같음.
핀 (met3): wp·pol 왼쪽 끝, out·vwh·vwl 오른쪽 끝, vdd (위 띠)·vss (아래 띠).
쓰임: /home/dave/work/projects/sern_hog_classab_opamp/sim/.venv/bin/python gen_wbuf.py → out/wbuf.gds·.cdl·.json
"""
import os
from pathlib import Path

import klayout.db as db

import blk_common as bc
from rowch import RowCh, band, dev, v123, GAP
from devlib import finish

H = Path(__file__).resolve().parent
NAME = os.environ.get('NAME', 'wbuf')
L5 = 0.5
NROW = [
    dev('XN1a', 'n', 2, L5, 1, d='s1', g='wp', s='n1'), dev('XN1b', 'n', 2, L5, 1, d='s1', g='pol', s='vss'),
    dev('XN2a', 'n', 2, L5, 1, d='s2', g='wp', s='n2'), dev('XN2b', 'n', 2, L5, 1, d='s2', g='n1', s='vss'),
    dev('XN3a', 'n', 2, L5, 1, d='s3', g='pol', s='n3'), dev('XN3b', 'n', 2, L5, 1, d='s3', g='n1', s='vss'),
    dev('XN4a', 'n', 2, L5, 1, d='s4', g='n2', s='xr'), dev('XN4b', 'n', 2, L5, 1, d='s4', g='n3', s='vss'),
    dev('XI0n', 'n', 1, L5, 1, d='f0', g='xr', s='vss'), dev('XM1', 'n', 4, L5, 1, d='f1', g='f0', s='vss'),
    dev('XM2', 'n', 16, L5, 4, d='f2', g='f1', s='vss')]
PROW = [
    dev('XP1a', 'p', 2, L5, 1, d='n1', g='wp', s='vdd'), dev('XP1b', 'p', 2, L5, 1, d='n1', g='pol', s='vdd'),
    dev('XP2a', 'p', 2, L5, 1, d='n2', g='wp', s='vdd'), dev('XP2b', 'p', 2, L5, 1, d='n2', g='n1', s='vdd'),
    dev('XP3a', 'p', 2, L5, 1, d='n3', g='pol', s='vdd'), dev('XP3b', 'p', 2, L5, 1, d='n3', g='n1', s='vdd'),
    dev('XP4a', 'p', 2, L5, 1, d='xr', g='n2', s='vdd'), dev('XP4b', 'p', 2, L5, 1, d='xr', g='n3', s='vdd'),
    dev('XI0p', 'p', 2, L5, 1, d='f0', g='xr', s='vdd'), dev('XP1', 'p', 8, L5, 2, d='f1', g='f0', s='vdd'),
    dev('XP2', 'p', 32, L5, 8, d='f2', g='f1', s='vdd')]
XMO = dev('XMo', 'n', 200, L5, 40, d='out', g='f2', s='vwl')
XPO = dev('XPo', 'p', 400, L5, 40, d='out', g='f2', s='vwh')
Y_NT = 25.5                                                          # n-tap 띠 가운데


def build():
    ly = db.Layout(); ly.dbu = 0.001
    R = RowCh(ly, NAME); C = R.C
    nr = R.place_n(NROW)
    pr = R.place_p(PROW, Y_NT)
    xo = max(nr[-1]['x1'], pr[-1]['x1']) + GAP + 0.6
    XMO['x'] = xo; XPO['x'] = xo
    rmo = R.place_n([XMO])[0]; R.nrow = nr + [rmo]
    rpo = R.place_p([XPO], Y_NT)[0]; R.prow = pr + [rpo]
    XR = round((rmo['x1'] + 2.0) / 0.005) * 0.005                     # 셀 오른쪽 끝 (5 nm 격자)
    # ── 탭 띠 (met1·met2·met3) + 전원 소스 연결
    band(C, 'p', 0.0, XR, 0.25, 'vss')
    band(C, 'n', 0.0, XR, Y_NT, 'vdd')
    # ── 논리 단자
    for r in nr:
        d = r['dev']
        skip = ('d',) if d['d'].startswith('s') else ()
        R.auto_terms(r, skip=skip, tap_y=0.25)
    for a, b in zip(nr[0:8:2], nr[1:8:2]):                           # NAND 직렬 마디: 두 드레인 스트랩을 met1 로
        C.box(a['dev']['d'], 'm1', a['drns'][-1] - 0.115, a['yd'] - 0.17, b['drns'][-1] + 0.115, a['yd'] + 0.17)
    for r in pr:
        R.auto_terms(r, tap_y=Y_NT)
    # ── 출력단 게이트 (f2) 는 보통 줄기, S/D 는 바로 위 met3
    for r in (rmo, rpo):
        xg, gy = R.gate_left(r)
        R.stub('f2', xg, gy, r['side'], pad=False)
    VWL = (0.80, 2.90); OUT = (3.35, 21.50); VWH = (Y_NT - 3.55, Y_NT - 0.7)       # out 판 (> 3 µm) 과 띠 사이 0.45 (huge met3 0.40)
    for x in rmo['srcs']:
        for y in (1.60, 2.40):
            v123(C, 'vwl', x, y)
    for x in rmo['drns']:
        for y in (4.00, 4.80, 5.60):
            v123(C, 'out', x, y)
    for x in rpo['srcs']:
        for y in (22.40, 23.20, 24.00):
            v123(C, 'vwh', x, y)
    for x in rpo['drns']:
        for y in (15.0, 15.8, 16.6, 17.4, 18.2, 19.0, 19.8, 20.6):
            v123(C, 'out', x, y)
    xa = rmo['x0'] + 0.60
    C.box('vwl', 'm3', rmo['x0'] - 0.20, VWL[0], XR, VWL[1])
    C.box('out', 'm3', xa, OUT[0], XR, OUT[1])
    C.box('vwh', 'm3', rpo['x0'] - 0.20, VWH[0], XR, VWH[1])
    # ── 통로 트랙
    y_lo = max(r['gy'] for r in R.nrow) + 0.50
    R.solve_tracks(y_lo, order_hint=['wp', 'pol', 'n1', 'n2', 'n3', 'xr', 'f0', 'f1', 'f2'])
    ytop = max(R.track_y.values()) + 0.17
    assert ytop + 0.14 + 0.185 <= min(r['gy'] for r in R.prow) - 0.165, (ytop, min(r['gy'] for r in R.prow))
    R.draw_stubs_tracks(xext={'wp': (0.0, 0.0), 'pol': (0.0, 0.0)})
    # ── n-well (PMOS 줄 + n-tap 띠)
    pd0 = min(r['yb'] for r in R.prow)
    C.box(None, 'nw', -0.40, pd0 - 0.40, XR + 0.40, Y_NT + 0.65)
    # ── 라벨·핀
    pins = {}
    for n in ('wp', 'pol'):
        y = R.track_y[n]
        C.label(n, 'lbl_m3', 0.2, y)
        pins[n] = [('met3', 0, int((y - 0.17) * 1000), 400, int((y + 0.17) * 1000))]
    for n, (y1, y2) in (('vwl', VWL), ('out', OUT), ('vwh', VWH)):
        C.label(n, 'lbl_m3', XR - 0.5, (y1 + y2) / 2)
        pins[n] = [('met3', int((XR - 2) * 1000), int(y1 * 1000), int(XR * 1000), int(y2 * 1000))]
    C.label('vss', 'lbl_m3', 0.5, 0.25); C.label('vdd', 'lbl_m3', 0.5, Y_NT)
    pins['vss'] = [('met3', 0, 0, int(XR * 1000), 500)]
    pins['vdd'] = [('met3', 0, int((Y_NT - 0.25) * 1000), int(XR * 1000), int((Y_NT + 0.25) * 1000))]
    pins = {k: [(l, int(a), int(b), int(c), int(e)) for (l, a, b, c, e) in v] for k, v in pins.items()}
    bb = finish(C)
    # ── CDL (기준 = SPICE WBUF, 소자 W·L 그대로, 핑거는 LVS 가 합침)
    devs = NROW + PROW + [XMO, XPO]
    cdl = [f".subckt {NAME} wp pol out vwh vwl vdd vss"]
    for d in devs:
        m = 'nfet_g5v0d10v5' if d['typ'] == 'n' else 'pfet_g5v0d10v5'
        cdl.append(f"M{d['name']} {d['d']} {d['g']} {d['s']} {d['b']} {m} w={d['W']}u l={d['L']}u")
    cdl.append(f".ends {NAME}")
    out = H / 'out'; out.mkdir(exist_ok=True)
    so = db.SaveLayoutOptions(); so.add_cell(C.c.cell_index())
    ly.write(str(out / f'{NAME}.gds'), so)
    (out / f'{NAME}.cdl').write_text('\n'.join(cdl) + '\n')
    pc = bc.precheck(ly, C.c); nc = bc.netcheck(ly, C.c)
    bbn = [int(round(v * 1000)) for v in bb]
    bc.write_pins_json(out / f'{NAME}.json', NAME, bbn, pins, dict(info=dict(devices=len(devs), tracks=R.track_y, precheck=pc, netcheck=nc)))
    print(f"{NAME}: {len(devs)} 소자, {bb[2] - bb[0]:.2f} × {bb[3] - bb[1]:.2f} µm, 트랙 {len(R.track_y)}")
    print('precheck', pc); print('netcheck', nc)


if __name__ == '__main__':
    build()
