"""nudge 주입기 + β 미러 + HOG bias 셀 생성기 (10/28) — 셀 둘: nudge_inj, bias_beta.
netlist 기준:
  nudge_inj  = real_circuit/gen_chip_deck3.py 주입기 줄 (j = 0…2): XMP{j} ip pref vdd vdd P 42/2 nf8, XMN{j} in nref vss vss N 15/2 nf3,
               XSW1 TG(ip, yp, sp, spb) · XSW2 TG(ip, ym, sm, smb) · XSW3 TG(in, ym, sp, spb) · XSW4 TG(in, yp, sm, smb), TG = N 2 / P 4 (L 0.5).
               yp{j}·ym{j} = nudge 배열 출력 행 nr{100+2j}·nr{101+2j}.
  bias_beta  = chip_lib.beta_mirror(m=8, kn=0.796, kp=0.882): XMPref pref pref vdd (P 42/2 nf8), XMbn pref vbn vss (N 0.7164/1 m8),
               XMNref nref nref vss (N 15/2 nf3), XMbp bx vbp vdd (P 1.764/0.8 m8), XMbpc nref vbpc bx (P 1.323/0.5 m8)  (Vbm_p·Vbm_n 0 V = 단락)
               + HOG_BIAS (sern_hog_classab_opamp/sim/char/decks/hog_tr.spice): XBN vbn vbn vss (N 0.9/1), XBP x vbp vdd (P 2/0.8), XBPC vbp vbpc x (P 1.5/0.5).
               HOG_BIAS 의 이상 전류원 Ibn (vdd→vbn 5 µA)·Ibp (vbp→vss 5 µA) 는 셀 밖 (IBIAS 패드 쪽) — vbn·vbp 를 핀으로.
netlist 와 다른 것: XMP·XMPref nf 8 (5.25 µm) → nf 4 (10.5 µm), W·L 같음.  m=8 단위 소자 폭을 5 nm 격자에 맞춤:
  XMbn 0.7164 → 0.715 (−0.20 %), XMbp 1.764 → 1.765 (+0.06 %), XMbpc 1.323 → 1.325 (+0.15 %) — LVS 기준 CDL 도 이 값 (차이를 README 에 적음).
쓰임: /home/dave/work/projects/sern_hog_classab_opamp/sim/.venv/bin/python gen_nudge_bias.py → out/nudge_inj.*, out/bias_beta.*
"""
from pathlib import Path

import klayout.db as db

import blk_common as bc
from rowch import RowCh, band, dev, GAP
from devlib import finish

H = Path(__file__).resolve().parent
L5 = 0.5


def tg_devs(k, a, b, en, enb):
    return dev(f'XSW{k}n', 'n', 2, L5, 1, d=a, g=en, s=b), dev(f'XSW{k}p', 'p', 4, L5, 1, d=a, g=enb, s=b)


def build_cell(name, ngroups, prow_groups, left_pins, right_pins, ports, ext_rows_hint=()):
    """ngroups / prow_groups: 소자 묶음 목록 (같은 묶음은 x 를 맞춤). 두 번 그린다: 1) 트랙 수 2) 실제."""
    def draw(y_nt):
        ly = db.Layout(); ly.dbu = 0.001
        R = RowCh(ly, name); C = R.C
        # 묶음 안 k 번째 N·P 소자를 같은 x 에 (TG 의 N·P 가 같은 줄기 x → 순서 제약 없음)
        x = 0.4 + GAP
        nlist, plist = [], []
        W = lambda d: d['nf'] * (d['L'] + 0.29) + 0.29
        for gn, gp in zip(ngroups, prow_groups):
            for k in range(max(len(gn), len(gp))):
                w = 0.0
                for lst, grp in ((nlist, gn), (plist, gp)):
                    if k < len(grp):
                        lst.append(dict(grp[k], x=x)); w = max(w, W(grp[k]))
                x += w + GAP
        nr = R.place_n(nlist)
        pr = R.place_p(plist, y_nt)
        XR = round((max(nr[-1]['x1'], pr[-1]['x1']) + 1.5) / 0.005) * 0.005
        band(C, 'p', 0.0, XR, 0.25, 'vss')
        band(C, 'n', 0.0, XR, y_nt, 'vdd')
        for r in nr:
            R.auto_terms(r, tap_y=0.25)
        for r in pr:
            R.auto_terms(r, tap_y=y_nt)
        xext = {n: (0.0, 0.0) for n in left_pins}
        xext.update({n: (XR, XR) for n in right_pins})
        y_lo = max(r['gy'] for r in nr) + 0.50
        R.solve_tracks(y_lo, extra_nets=list(left_pins) + list(right_pins), share=True, xext=xext, order_hint=ext_rows_hint)
        return ly, R, nr, pr, XR, xext, y_lo

    # 1) 트랙 수 → PMOS 줄 위치
    ly, R, nr, pr, XR, xext, y_lo = draw(100.0)
    ytop = max(R.track_y.values()) + 0.17 + 0.14 + 0.185 + 0.165
    gy_rel = min(r['gy'] for r in pr) - 100.0                          # y_nt 기준 가장 낮은 PMOS 게이트 패드
    y_nt = round((ytop - gy_rel + 0.05) / 0.005) * 0.005
    ly, R, nr, pr, XR, xext, y_lo = draw(y_nt)
    C = R.C
    R.draw_stubs_tracks(xext=xext)
    pd0 = min(r['yb'] for r in pr)
    C.box(None, 'nw', -0.40, pd0 - 0.40, XR + 0.40, y_nt + 0.65)
    pins = {}
    for n in list(left_pins) + list(right_pins):
        y = R.track_y[n]
        x = 0.2 if n in left_pins else XR - 0.2
        C.label(n, 'lbl_m3', x, y)
        x1, x2 = (0.0, 0.4) if n in left_pins else (XR - 0.4, XR)
        pins[n] = [('met3', int(x1 * 1000), int((y - 0.17) * 1000), int(x2 * 1000), int((y + 0.17) * 1000))]
    C.label('vss', 'lbl_m3', 0.5, 0.25); C.label('vdd', 'lbl_m3', 0.5, y_nt)
    pins['vss'] = [('met3', 0, 0, int(XR * 1000), 500)]
    pins['vdd'] = [('met3', 0, int((y_nt - 0.25) * 1000), int(XR * 1000), int((y_nt + 0.25) * 1000))]
    bb = finish(C)
    devs = [r['dev'] for r in nr + pr]
    cdl = [f".subckt {name} " + ' '.join(ports)]
    for d in devs:
        m = 'nfet_g5v0d10v5' if d['typ'] == 'n' else 'pfet_g5v0d10v5'
        cdl.append(f"M{d['name']} {d['d']} {d['g']} {d['s']} {d['b']} {m} w={d['W']:g}u l={d['L']:g}u")
    cdl.append(f".ends {name}")
    out = H / 'out'; out.mkdir(exist_ok=True)
    so = db.SaveLayoutOptions(); so.add_cell(C.c.cell_index())
    ly.write(str(out / f'{name}.gds'), so)
    (out / f'{name}.cdl').write_text('\n'.join(cdl) + '\n')
    pc = bc.precheck(ly, C.c); nc = bc.netcheck(ly, C.c)
    bbn = [int(round(v * 1000)) for v in bb]
    bc.write_pins_json(out / f'{name}.json', name, bbn, pins,
                       dict(info=dict(devices=len(devs), track_rows=R.nrows, tracks=R.track_y, precheck=pc, netcheck=nc)))
    print(f"{name}: {len(devs)} 소자, {bb[2] - bb[0]:.2f} × {bb[3] - bb[1]:.2f} µm, 트랙 줄 {R.nrows}")
    print('precheck', pc); print('netcheck', nc)


def nudge_inj():
    ng, pg = [], []
    for j in range(3):
        ip, inn, yp, ym = f'ip{j}', f'in{j}', f'yp{j}', f'ym{j}'
        sp, spb, sm, smb = f'sp{j}', f'spb{j}', f'sm{j}', f'smb{j}'
        t = [tg_devs(f'1_{j}', ip, yp, sp, spb), tg_devs(f'2_{j}', ip, ym, sm, smb), tg_devs(f'3_{j}', inn, ym, sp, spb), tg_devs(f'4_{j}', inn, yp, sm, smb)]
        ng.append([dev(f'XMN{j}', 'n', 15, 2.0, 3, d=inn, g='nref', s='vss')] + [a for a, _ in t])
        pg.append([dev(f'XMP{j}', 'p', 42, 2.0, 4, d=ip, g='pref', s='vdd')] + [b for _, b in t])
    left = ['pref', 'nref'] + [f'{s}{j}' for j in range(3) for s in ('sp', 'spb', 'sm', 'smb')]
    right = [f'{s}{j}' for j in range(3) for s in ('yp', 'ym')]
    ports = right + left + ['vdd', 'vss']
    build_cell('nudge_inj', ng, pg, left, right, ports)


def bias_beta():
    ng = [[dev('XBN', 'n', 0.9, 1.0, 1, d='vbn', g='vbn', s='vss'), dev('XMbn', 'n', 8 * 0.715, 1.0, 8, d='pref', g='vbn', s='vss')],
          [dev('XMNref', 'n', 15, 2.0, 3, d='nref', g='nref', s='vss')]]
    pg = [[dev('XBP', 'p', 2.0, 0.8, 1, d='x', g='vbp', s='vdd'), dev('XBPC', 'p', 1.5, 0.5, 1, d='vbp', g='vbpc', s='x'),
           dev('XMbp', 'p', 8 * 1.765, 0.8, 8, d='bx', g='vbp', s='vdd'), dev('XMbpc', 'p', 8 * 1.325, 0.5, 8, d='nref', g='vbpc', s='bx')],
          [dev('XMPref', 'p', 42, 2.0, 4, d='pref', g='pref', s='vdd')]]
    left = ['vbn', 'vbp', 'vbpc']
    right = ['pref', 'nref']
    build_cell('bias_beta', ng, pg, left, right, left + right + ['vdd', 'vss'])


if __name__ == '__main__':
    nudge_inj()
    bias_beta()
