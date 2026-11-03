"""δ clamp 매크로 (열 블록, hidden 열마다 하나) — real_circuit/gen_chip_deck3.py 278–281 줄의 회로를 실제 SKY130 소자로 그린다 (10/28).
회로 (열 노드 col = nd):
    R1: col → da (r_ser 100 Ω),  D_a: anode da, cathode vrailm   (위 다이오드, 노드가 −v_b 아래로 못 가게... 덱 주석 "위 다이오드 → VRAILM")
    D_b: anode vrailp, cathode db,  R2: db → col (r_ser 100 Ω)    (아래 다이오드 "아래 다이오드 ← VRAILP")
    (r_ser = 100 Ω, v_b = 0.3 V: out/weights/nostab_5bit.npz 5b_s0 config. 덱의 다이오드는 level-1 카드 is 5e-10 n 1.2 = 실제 소자 아님)
소자 고름:
  - 다이오드 = diode_pd2nw (p+ diff 가 anode, 섬 nwell 이 cathode). pw2nd 는 anode 가 기판 (= VSS −2.5 V) 에 묶여 못 씀.
    칩 전체가 VSS −2.5 / VDD +2.5 V (5 V 폭) 이고 쓰기 때 역바이어스가 5 V 까지 → hvi 를 덮음 → LVS 덱 이름으로는 diode_pd2nw_11v0
    (sky130.lvs.v0.0_1.1.pvl: nwell·areaid.de·hvi 가 있으면 11v0, hvi 없으면 05v5). hvl 셀·TG 매크로 (hvi) 옆에 놓여 nwell 종류도 같게.
  - 100 Ω = RES_GENERIC_ND (n+ diff 저항, diff:res 65/13 표지, hvi 밖 = LV n+ diff). 덱이 뽑는 저항 중 크기가 맞는 것:
    poly 정밀 저항 (res_high_po) 은 폭 0.35–5.73 고정 + rpm 이라 100 Ω 이 L < W (너무 짧음), li1 표지 (67/13) 는 덱에 device 문이 없음,
    금속 저항은 0.125 Ω/□ 라 800 □. n+ diff ≈ 120 Ω/□ (ngspice 모형 rdn 108–132, tt ≈ 120) → W 1.0 µm × L 0.82 µm ≈ 100 Ω.
    PDK 로는 단자가 5 V 까지 가면 res_generic_nd__hv (hvi 안) 가 맞지만, 이 LVS 덱은 hvi 안 diff 저항을 단락으로 뽑음 (아래 hvi 주석) → LV 판.
배치 (아래 → 위, 폭 = 열 pitch 5.115 µm, 옆 매크로와 맞붙여도 되게):
  VSS p+ tap 띠 (met1 rail, 끝까지) → nwell B 섬 (p+ = vrailp anode, met1 rail 끝까지 / n+ tap = db) → R2 (db ↔ col) → R1 (col ↔ da)
  → nwell A 섬 (p+ = da / n+ tap = vrailm, met1 rail 끝까지). col = met2 세로 띠 (높이 전체). db·da·col 사이는 li1 로만 이음.
  hvi = 다이오드 섬 둘레 두 조각, 폭은 매크로 끝까지 (옆 매크로와 이어짐). nwell 은 좌우 끝에서 0.635 µm (= hvnwell.8 1.27 의 반) 안쪽.
낸다: macros/clamp_d2r.{gds,cdl,lef}, macros/clamp_d2r_x4.{gds,cdl} (4 열 맞붙임 시험)
쓰임: /home/dave/work/projects/sern_hog_classab_opamp/sim/.venv/bin/python gen_clamp.py
검증 (Olympus ~/work/ep_dr/digital/macros, signoff_macro.sbatch):
  - DRC (sky130_rev_0.0_2.12) = 밀도 12 건만 (하나·4 열 모두, 잡 721116·721117)
  - LVS: 기본 덱 sky130.lvs.v0.0_1.1.pvl 은 연결은 다 맞고 R 의 W·L 만 'missing' (덱의 RES_GENERIC_ND device 문에 속성 추출이 없는데
    lvs_check_property R W/L 은 모든 R 에 걸림 → 어떤 diff 저항도 MATCH 못 함, 잡 721116).
    → 사본 덱 macros/sky130_d2r.lvs.pvl (RES_GENERIC_ND/PD 에 원본 덱의 RES_PROPERTIES 를 붙인 두 줄만 다름) 로 MATCH (잡 721121·721122).
    L 을 2 µm 로 틀리게 준 source 는 59 % 차이로 MISMATCH (잡 721123) → W·L 비교가 실제로 걸림을 확인.
  쓰임: NAME=clamp_d2r LVS_DECK=$HOME/work/ep_dr/digital/macros/sky130_d2r.lvs.pvl sbatch -t 00:20:00 signoff_macro.sbatch
"""
from pathlib import Path

import klayout.db as db

H = Path(__file__).resolve().parent
NAME = 'clamp_d2r'
W, HT = 5.115, 9.80                       # 매크로 폭 = 열 pitch, 높이
L = {'diff': (65, 20), 'tap': (65, 44), 'nwell': (64, 20), 'hvi': (75, 20), 'psdm': (94, 20), 'nsdm': (93, 44),
     'licon': (66, 44), 'li1': (67, 20), 'mcon': (67, 44), 'met1': (68, 20), 'via': (68, 44), 'met2': (69, 20),
     'areaid_de': (81, 23), 'diff_res': (65, 13), 'li1_lbl': (67, 5), 'met1_lbl': (68, 5), 'met2_lbl': (69, 5)}
NW_IN = 0.635                             # nwell 섬 좌우 여백
RES_W, RES_L, RES_T = 1.00, 0.82, 0.50    # n+ diff 저항: 폭, 몸통 길이 (diff:res), 끝 단자 길이
CUT, CUT_P = 0.17, 0.36                   # licon·mcon 크기, 줄 간격 (mcon 간격 0.19 기준 → licon 도 같은 자리에 쌓음)


def build(ly):
    c = ly.create_cell(NAME)
    def um(v):                            # µm → nm, 제조 격자 5 nm 위인지 확인 (첫 판 x.1b ×296, mcon 간격 0.189 = 반올림, 잡 721113)
        n = int(round(v * 1000))
        assert n % 5 == 0, f'off-grid {v}'
        return n
    def box(lyr, x0, y0, x1, y1):
        c.shapes(ly.layer(*L[lyr])).insert(db.Box(um(x0), um(y0), um(x1), um(y1)))
    def cuts(lyr, x0, x1, yc, xs=None):  # x0..x1 안에 CUT 정사각을 CUT_P 간격으로 (가운데 맞춤, 시작점은 5 nm 격자로), 중심 y = yc
        if xs is None:
            n = int((x1 - x0 - CUT) / CUT_P + 1e-9) + 1
            s = x0 + (x1 - x0 - (CUT + (n - 1) * CUT_P)) / 2
            s = int(s * 1000 // 5) * 5 / 1000
            xs = [round(s + k * CUT_P, 3) for k in range(n)]
        for x in xs:
            box(lyr, x, yc - CUT / 2, x + CUT, yc + CUT / 2)
        return xs

    # hvi 는 두 조각 (아래: VSS tap + nwell B 섬, 위: nwell A 섬). 가운데 diff 저항은 hvi 밖 (LV n+ diff):
    #   LVS 덱 (sky130.lvs.v0.0_1.1.pvl 1057–1065 줄) 이 HV_source_drain = (diff AND hvi) NOT poly 로 diff:res 몸통까지 넣어
    #   hvi 안의 diff 저항은 두 끝이 단락으로 뽑힌다 (첫 판 잡 721113: R 두 개가 col 하나에 붙고 da·db 넷이 사라짐)
    box('hvi', 0, 0, W, 3.41 + 0.20); box('hvi', 0, 6.85 - 0.20, W, HT)
    # ── VSS p+ tap 띠 (기판). psdm 는 매크로 끝까지 (옆 매크로와 합쳐짐), tap 은 0.2 µm 안쪽
    box('tap', 0.20, 0.20, W - 0.20, 0.65); box('psdm', 0, 0.075, W, 0.775)
    box('li1', 0.25, 0.26, W - 0.25, 0.59)
    xs = cuts('licon', 0.30, W - 0.30, 0.425); cuts('mcon', 0, 0, 0.425, xs)
    box('met1', 0, 0.15, W, 0.70)
    x_d0, x_d1 = NW_IN + 0.33, W - NW_IN - 0.33          # 섬 안 p+ diff·n+ tap x (hvdifftap.17·19: HV nwell 감쌈 0.33)
    # ── nwell B 섬: 아래 p+ diff (anode = vrailp), 위 n+ tap (cathode = db)
    box('nwell', NW_IN, 1.10, W - NW_IN, 3.41)
    box('diff', x_d0, 1.43, x_d1, 2.23); box('areaid_de', x_d0, 1.43, x_d1, 2.23)
    box('psdm', x_d0 - 0.125, 1.305, x_d1 + 0.125, 2.43)
    box('tap', x_d0, 2.63, x_d1, 3.08); box('nsdm', x_d0 - 0.125, 2.43, x_d1 + 0.125, 3.205)
    box('li1', x_d0 + 0.035, 1.62, x_d1 - 0.035, 2.04)
    xs = cuts('licon', x_d0 + 0.10, x_d1 - 0.10, 1.83); cuts('mcon', 0, 0, 1.83, xs)
    box('met1', 0, 1.55, W, 2.10)                                         # vrailp rail
    box('li1', x_d0 + 0.035, 2.70, x_d1 - 0.035, 3.01)
    cuts('licon', x_d0 + 0.10, x_d1 - 0.10, 2.855)
    # ── 저항 둘 (가로, 왼쪽 끝 = col, 오른쪽 끝 = db / da). n+ diff, nsdm 하나로 둘을 덮음
    rx0 = round((W - (2 * RES_T + RES_L)) / 2, 2)
    rb0, rb1 = rx0 + RES_T, rx0 + RES_T + RES_L                           # 몸통 (diff:res)
    rx1 = rb1 + RES_T
    for y0 in (3.90, 5.40):                                               # R2 (아래, db), R1 (위, da)
        box('diff', rx0, y0, rx1, y0 + RES_W); box('diff_res', rb0, y0, rb1, y0 + RES_W)
        for xa in (rx0 + (RES_T - CUT) / 2, rb1 + (RES_T - CUT) / 2):
            for yc in (y0 + 0.26, y0 + RES_W - 0.26):
                box('licon', xa, yc - CUT / 2, xa + CUT, yc + CUT / 2)
    box('nsdm', rx0 - 0.125, 3.775, rx1 + 0.125, 6.525)
    xl = rx0 + (RES_T - CUT) / 2                                          # 왼쪽 단자 licon x
    xr = rb1 + (RES_T - CUT) / 2                                          # 오른쪽 단자 licon x
    box('li1', xl - 0.08, 3.995, xl + CUT + 0.08, 6.305)                  # col: R2 왼쪽 ↔ R1 왼쪽
    box('li1', xr - 0.085, 2.70, xr + CUT + 0.085, 4.805)                 # db: tap B ↔ R2 오른쪽
    box('li1', xr - 0.085, 5.495, xr + CUT + 0.085, 7.745)                # da: R1 오른쪽 ↔ p+ A
    # col: li1 → mcon → met1 패드 → via → met2 세로 띠 (높이 전체, 핀)
    yc = 5.15
    box('mcon', xl, yc - CUT / 2, xl + CUT, yc + CUT / 2)
    box('met1', xl - 0.095, yc - 0.18, xl + CUT + 0.095, yc + 0.18)
    box('via', xl + 0.01, yc - 0.075, xl + 0.16, yc + 0.075)
    xm0, xm1 = xl - 0.075, xl + CUT + 0.075
    box('met2', xm0, 0, xm1, HT)
    # ── nwell A 섬: 아래 p+ diff (anode = da), 위 n+ tap (cathode = vrailm)
    box('nwell', NW_IN, 6.85, W - NW_IN, HT - NW_IN)
    box('diff', x_d0, 7.18, x_d1, 7.98); box('areaid_de', x_d0, 7.18, x_d1, 7.98)
    box('psdm', x_d0 - 0.125, 7.055, x_d1 + 0.125, 8.18)
    box('tap', x_d0, 8.38, x_d1, 8.83); box('nsdm', x_d0 - 0.125, 8.18, x_d1 + 0.125, 8.955)
    box('li1', x_d0 + 0.035, 7.415, x_d1 - 0.035, 7.745)
    cuts('licon', x_d0 + 0.10, x_d1 - 0.10, 7.58)
    box('li1', x_d0 + 0.035, 8.44, x_d1 - 0.035, 8.77)
    xs = cuts('licon', x_d0 + 0.10, x_d1 - 0.10, 8.605); cuts('mcon', 0, 0, 8.605, xs)
    box('met1', 0, 8.33, W, 8.88)                                         # vrailm rail
    pins = {'col': ('met2', [(xm0, 0, xm1, HT)]), 'vrailp': ('met1', [(0, 1.55, W, 2.10)]),
            'vrailm': ('met1', [(0, 8.33, W, 8.88)]), 'VSS': ('met1', [(0, 0.15, W, 0.70)])}
    dio = dict(a=round((x_d1 - x_d0) * 0.80, 4), p=round(2 * ((x_d1 - x_d0) + 0.80), 4))
    return c, pins, dio


def label(ly, cell, pins, suffix=''):
    for pn, (lyr, rects) in pins.items():
        x0, y0, x1, y1 = rects[0]
        t = db.Text(pn + suffix, db.Trans(int(round((x0 + x1) / 2 * 1000)), int(round((y0 + y1) / 2 * 1000))))
        cell.shapes(ly.layer(*L[lyr + '_lbl'])).insert(t)


def lef_of(ly, cell, pins):
    f = lambda v: f'{v:.3f}'
    out = [f'MACRO {NAME}', '  CLASS BLOCK ;', '  ORIGIN 0.000 0.000 ;', f'  SIZE {f(W)} BY {f(HT)} ;', '  SYMMETRY X Y ;']
    for pn, (lyr, rects) in pins.items():
        use = 'GROUND' if pn == 'VSS' else 'SIGNAL'
        out += [f'  PIN {pn}', '    DIRECTION INOUT ;', f'    USE {use} ;', '    PORT', f'      LAYER {lyr} ;']
        out += [f'        RECT {f(a)} {f(b)} {f(cc)} {f(d)} ;' for a, b, cc, d in rects] + ['    END', f'  END {pn}']
    out += ['  OBS']
    for lyr in ('li1', 'met1', 'met2'):
        r = db.Region(cell.begin_shapes_rec(ly.layer(*L[lyr]))).merged()
        out += [f'    LAYER {lyr} ;'] + [f'      RECT {f(b.left / 1000)} {f(b.bottom / 1000)} {f(b.right / 1000)} {f(b.top / 1000)} ;'
                                         for p in r.each() for b in [p.bbox()]]
    out += ['  END', f'END {NAME}', '']
    return '\n'.join(out)


def cdl_sub(dio):
    # 다이오드 줄 형식은 LVS 덱 README: "DD0 n+ n- diode_pd2nw_05v5 <면적 µm²> <둘레 µm> m=1"
    # 저항: RES_GENERIC_ND (덱 device R, 속성 비교 없음). 값 100 은 설계값 (W 1.0 × L 0.82 µm, rdn_hv ≈ 122 Ω/□)
    return [f'.SUBCKT {NAME} col vrailp vrailm VSS',
            f'* δ clamp: col -R1- da -D_a-> vrailm ; vrailp -D_b-> db -R2- col  (VSS = 기판 tap, 소자 연결 없음)',
            'R1 col da 100 $[RES_GENERIC_ND] $W=1u $L=0.82u',
            f"DDa da vrailm diode_pd2nw_11v0 {dio['a']} {dio['p']} m=1",
            f"DDb vrailp db diode_pd2nw_11v0 {dio['a']} {dio['p']} m=1",
            'R2 db col 100 $[RES_GENERIC_ND] $W=1u $L=0.82u',
            f'.ENDS {NAME}']


def main():
    ly = db.Layout(); ly.dbu = 0.001
    c, pins, dio = build(ly)
    (H / f'{NAME}.lef').write_text(lef_of(ly, c, pins))
    sub = cdl_sub(dio)
    # 시험 1: 매크로 하나 (이름표 = 핀)
    ly1 = db.Layout(); ly1.dbu = 0.001
    t1 = ly1.create_cell(NAME); t1.copy_tree(c)
    label(ly1, t1, pins)
    ly1.write(str(H / f'{NAME}.gds'))
    (H / f'{NAME}.cdl').write_text('\n'.join(sub) + '\n')
    # 시험 2: 4 열 맞붙임 (pitch = 폭 5.115 µm), rail 셋은 이어지고 col 만 열마다
    ly4 = db.Layout(); ly4.dbu = 0.001
    m = ly4.create_cell(NAME); m.copy_tree(c)
    top = ly4.create_cell(NAME + '_x4')
    for k in range(4):
        top.insert(db.CellInstArray(m.cell_index(), db.Trans(int(round(k * W * 1000)), 0)))
        x0, y0, x1, y1 = pins['col'][1][0]
        top.shapes(ly4.layer(*L['met2_lbl'])).insert(db.Text(f'col{k}', db.Trans(int(round((x0 + x1) / 2 * 1000 + k * W * 1000)), int(round(HT / 2 * 1000)))))
    for pn in ('vrailp', 'vrailm', 'VSS'):
        x0, y0, x1, y1 = pins[pn][1][0]
        top.shapes(ly4.layer(*L['met1_lbl'])).insert(db.Text(pn, db.Trans(int(round(W * 1000 / 2)), int(round((y0 + y1) / 2 * 1000)))))
    so = db.SaveLayoutOptions(); so.add_cell(top.cell_index())
    ly4.write(str(H / f'{NAME}_x4.gds'), so)
    x4 = sub + ['', f'.SUBCKT {NAME}_x4 col0 col1 col2 col3 vrailp vrailm VSS'] + \
        [f'X{k} col{k} vrailp vrailm VSS {NAME}' for k in range(4)] + [f'.ENDS {NAME}_x4']
    (H / f'{NAME}_x4.cdl').write_text('\n'.join(x4) + '\n')
    print(f'{NAME}: {W} x {HT} um, diode a={dio["a"]} um2 p={dio["p"]} um, pins {list(pins)}')


if __name__ == '__main__':
    main()
