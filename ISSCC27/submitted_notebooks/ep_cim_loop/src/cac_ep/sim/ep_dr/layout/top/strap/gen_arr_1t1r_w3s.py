"""1T1R 배열 + 덧대기 (strap) 생성기 — 원본 ../../gen_arr_1t1r_w3.py 의 사본. 셀 c1t1r_w3·행 띠·WL·열선·핀 이름·핀 위치는 원본과 같고, 아래 세 가지만 더한다.
10/28, 사용자 "배열 선 저항 확인과 met3·met4 덧대는 줄 … 까지 해야 다 완성되는 거 아니야?", 조정 세션 "행은 가능하면 ≤ 10 Ω, 열은 ≤ 15 Ω".
  ① 행 met3 줄: 행 띠 (met2 y −0.67..−0.25) 위 met3 y −1.25..0.55 (폭 1.80 µm, 블록 met3 밀도 ≤ 62% 를 지키는 폭), via2 를 띠 위에 0.4 µm 간격으로 (128 × 64 에서 행마다 818 개).
     동쪽 EXT 구간 (x ≥ 마지막 셀 오른쪽 −0.31) 은 met3 를 y −0.64..0.55 로 좁혀, 이웃 행 WL landing 위의 met3 자리 (y +2.05..+2.47 주변) 를 비운다.
  ② 열 met4 줄: x −1.2..1.7 (폭 2.9 µm, 열선 왼쪽으로 치우침). 셀마다 via stack 하나
     (열선 왼쪽 met1 pad → via1 15 → met2 pad → via2 6 → met3 pad → via3 6 → met4). met3 pad 는 위·아래 행 met3 줄과 0.3 µm 띄운다.
     열 아래 끝 (EXT_B) 에 큰 stack 하나 더 (via1 24, via2 7, via3 7) — 열 MUX 쪽에서 met2 로 닿는 landing 도 겸한다.
  ③ WL 동쪽 landing: EXT_R 에서 WL met2 를 y 2.05..2.47 (0.42 µm) 로 넓힘 → 최상위 배선이 via2 로 닿을 수 있다 (row 띠·이웃 행 띠와 0.27 µm 이상).
  met3·met4 는 배열 bbox 안쪽으로 0.3 µm 들여 그린다 (이웃 블록 met3·met4 와 간격).
쓰임: ARR_NR=4 ARR_NC=4 python gen_arr_1t1r_w3s.py → strap/arr_w3s_4x4.{gds,cdl}  (기본 이름 arr_w3s_<NR>x<NC>)
저항 계산은 r_strap.py 가 이 파일의 상수를 읽어서 한다.
"""
import os
from pathlib import Path

import klayout.db as db

H = Path(__file__).resolve().parent
PX, PY = 5115, 3410                                            # 열·행 pitch (nm)
EXT_L, EXT_R, EXT_B = 1500, 1500, 2500                         # 원본과 같음
L = dict(diff=(65, 20), tap=(65, 44), poly=(66, 20), licon=(66, 44), li=(67, 20), mcon=(67, 44), m1=(68, 20), via=(68, 44), m2=(69, 20),
         nsdm=(93, 44), psdm=(94, 20), npc=(95, 20), hvi=(75, 20), rram=(230, 20), t1=(68, 5), t2=(69, 5),
         via2=(69, 44), m3=(70, 20), via3=(70, 44), m4=(71, 20))

# ── 덧대기 도형 (nm, 셀 원점 기준. r_strap.py 가 읽는다)
INSET = 300                                                    # met3·met4 를 bbox 안쪽으로
ROW_BAND = (-670, -250)                                        # 원본 행 띠 (met2)
WL_BAND = (2250, 2470)                                         # 원본 WL (met2)
COL_X = (-310, -70)                                            # 원본 열선 (met1)
R3_Y = (-1250, 550)                                            # 행 met3 줄 (폭 1800; 2010 이면 블록 met3 밀도 64% > 62%)
R3_YE = (-640, 550)                                            # 동쪽 EXT 쪽 좁힌 met3 (폭 1190)
R3_XE_BACK = 310                                               # 넓은 met3 는 마지막 셀 오른쪽 끝 −0.31 µm 에서 멈춤
V2R_Y = (-560, -360)                                           # 행 띠 위 via2 (met2 둘러쌈 110, met3 둘러쌈 ≥ 80)
V2R_P = 400                                                    # via2 간격 (0.2 + 0.2)
C4_X = (-1200, 1700)                                           # 열 met4 줄 (폭 2900 < 3 µm: 넓은 금속 간격 규칙 피함)
M1P = (-1200, 0, -70, 1650)                                    # 셀 안 stack: met1 pad (열선과 붙음)
M2P = (-1200, 0, 0, 1650)                                      # met2 pad (행 띠와 250, WL 과 600, 게이트 met2 와 505)
M3P = (-1200, 850, 0, 1650)                                    # met3 pad (행 met3 줄 위 550 과 300, 다음 행 줄 아래 2160 과 510)
V1C, V1R = (-1030, -710, -390), (110, 430, 750, 1070, 1390)   # via1 15 개 (0.15, 둘러쌈 ≥ 110)
V23C, V23R = (-1100, -700, -300), (950, 1350)                  # via2·via3 6 개씩 (0.2, 둘러쌈 100)
M1S = (-1200, -2200, 1700, -1100)                              # 열 아래 끝 stack (행 0 GND met1 y −0.94 과 160)
M2S = (-1200, -2200, 1700, -830)                               # (행 0 띠 −0.67 과 160)
M3S = (-1200, -2200, 1700, -1760)                              # (행 0 met3 줄 −1.25 와 510)
V1SC, V1SR = tuple(-945 + 320 * k for k in range(8)), (-2045, -1725, -1405)    # via1 24 개
V23SC, V23SR = tuple(-1100 + 400 * k for k in range(7)), (-2080,)              # via2·via3 7 개씩
WLP_Y = (2050, 2470)                                           # WL landing (동쪽 EXT, 마지막 셀 riser 와 x 140 띄움)
WLP_DX = 140


def bx(c, i, x0, y0, x1, y1):
    c.shapes(i).insert(db.Box(x0, y0, x1, y1))


def build(NR, NC, NAME, out=H):
    ly = db.Layout(); ly.dbu = 0.001
    I = {k: ly.layer(*v) for k, v in L.items()}

    # ── 셀 (원본과 한 줄도 다르지 않게 — LVS 의 c1t1r_w3 와 같아야 함)
    C = ly.create_cell('c1t1r_w3')
    b = lambda k, *a: bx(C, I[k], *a)
    G1, G2 = (445, 945), (1235, 1735)
    b('diff', 180, 180, 2000, 1680); b('nsdm', 55, 55, 2125, 1805); b('hvi', 0, -780, 2180, 1860)
    for g0, g1 in (G1, G2):
        b('poly', g0, 50, g1, 1810)
    b('poly', G1[0], 1810, G2[1], 1960)
    b('poly', 525, 1855, 855, 2185); b('npc', 505, 1835, 875, 2205)
    b('licon', 605, 1935, 775, 2105); b('li', 525, 1855, 855, 2185); b('mcon', 605, 1935, 775, 2105)
    b('m1', 530, 1860, 850, 2180); b('via', 615, 1945, 765, 2095); b('m2', 505, 1820, 875, 2470)
    YS = ((240, 410), (580, 750), (920, 1090), (1260, 1430))
    for x0, x1, ym in ((220, 390, (405, 575)), (1005, 1175, (1205, 1375)), (1790, 1960, (405, 575))):
        for y0, y1 in YS:
            b('licon', x0, y0, x1, y1)
        b('li', x0, 160, x1, 1510); b('mcon', x0, ym[0], x1, ym[1])
    b('m1', -460, 345, 2020, 635)
    b('m1', 945, 1145, 2665, 1435)
    b('m1', 2345, 1160, 2665, 1420)
    b('via', 2430, 1215, 2580, 1365); b('rram', 2380, 1165, 2630, 1415)
    b('m2', 2375, 1130, 2635, 1450)
    b('m2', 2345, -620, 2665, 1300)
    b('tap', 180, -600, 2000, -190); b('psdm', 55, -725, 2125, 35)
    for x0 in (415, 890, 1365, 1790):
        b('licon', x0, -480, x0 + 170, -310)
    b('li', 270, -480, 2105, -310)
    for x0 in (350, 830, 1310, 1790):
        b('mcon', x0, -480, x0 + 170, -310)
    b('m1', 180, -940, 2000, -190)

    # ── 덧대기 셀 1: 셀마다 열 via stack (소자 없음, 셀 배열과 같은 pitch 로 겹쳐 놓음)
    S = ly.create_cell('s1t1r_w3s')
    s = lambda k, *a: bx(S, I[k], *a)
    s('m1', *M1P); s('m2', *M2P); s('m3', *M3P)
    for x0 in V1C:
        for y0 in V1R:
            s('via', x0, y0, x0 + 150, y0 + 150)
    for x0 in V23C:
        for y0 in V23R:
            s('via2', x0, y0, x0 + 200, y0 + 200); s('via3', x0, y0, x0 + 200, y0 + 200)

    # ── 덧대기 셀 2: 열 하나 (met4 줄 + 아래 끝 stack)
    yt = (NR - 1) * PY + M3P[3]                                # met4 위 끝 = 맨 위 행 met3 pad 위 끝
    K = ly.create_cell('s_col_w3s')
    k_ = lambda k, *a: bx(K, I[k], *a)
    k_('m4', C4_X[0], -EXT_B + INSET, C4_X[1], yt)
    k_('m1', *M1S); k_('m2', *M2S); k_('m3', *M3S)
    for x0 in V1SC:
        for y0 in V1SR:
            k_('via', x0, y0, x0 + 150, y0 + 150)
    for x0 in V23SC:
        for y0 in V23SR:
            k_('via2', x0, y0, x0 + 200, y0 + 200); k_('via3', x0, y0, x0 + 200, y0 + 200)

    # ── 덧대기 셀 3: via2 하나 (행 띠 위에 배열로)
    V = ly.create_cell('v2_w3s')
    bx(V, I['via2'], 0, 0, 200, 200)

    # ── 배열 (원본과 같은 순서·좌표)
    T = ly.create_cell(NAME)
    T.insert(db.CellInstArray(C.cell_index(), db.Trans(0, 0), db.Vector(PX, 0), db.Vector(0, PY), NC, NR))
    T.insert(db.CellInstArray(S.cell_index(), db.Trans(0, 0), db.Vector(PX, 0), db.Vector(0, PY), NC, NR))
    T.insert(db.CellInstArray(K.cell_index(), db.Trans(0, 0), db.Vector(PX, 0), db.Vector(0, PY), NC, 1))
    xr = (NC - 1) * PX + 2665
    x3a, x3b, x3e = -EXT_L + INSET, xr - R3_XE_BACK, xr + EXT_R - INSET
    v2x0 = x3a + 100
    nv2 = (x3e - 100 - 200 - v2x0) // V2R_P + 1                # 마지막 via2 도 met3 끝에서 100 이상
    T.insert(db.CellInstArray(V.cell_index(), db.Trans(v2x0, V2R_Y[0]), db.Vector(V2R_P, 0), db.Vector(0, PY), nv2, NR))
    for r in range(NR):
        y = r * PY
        bx(T, I['m2'], -EXT_L, y - 670, xr + EXT_R, y - 250)   # 행 (TE) — 원본
        bx(T, I['m2'], -EXT_L, y + 2250, xr + EXT_R, y + 2470) # WL — 원본
        bx(T, I['m2'], xr + WLP_DX, y + WLP_Y[0], xr + EXT_R, y + WLP_Y[1])   # WL 동쪽 landing (새로)
        bx(T, I['m3'], x3a, y + R3_Y[0], x3b, y + R3_Y[1])     # 행 met3 줄 (넓은 부분)
        bx(T, I['m3'], x3b, y + R3_YE[0], x3e, y + R3_YE[1])   # 동쪽 EXT 쪽 좁힌 부분 (맞붙음)
        T.shapes(I['t2']).insert(db.Text(f'row_{r}', db.Trans(-EXT_L + 200, y - 460)))
        T.shapes(I['t2']).insert(db.Text(f'wl_{r}', db.Trans(xr + EXT_R - 200, y + 2360)))
    for c in range(NC):
        bx(T, I['m1'], c * PX - 310, -EXT_B, c * PX - 70, (NR - 1) * PY + 635)   # 열 (source) — 원본
        T.shapes(I['t1']).insert(db.Text(f'col_{c}', db.Trans(c * PX - 190, -EXT_B + 200)))
    T.shapes(I['t1']).insert(db.Text('vss', db.Trans(1090, -565)))
    out.mkdir(exist_ok=True)
    so = db.SaveLayoutOptions(); so.add_cell(T.cell_index())
    ly.write(str(out / f'{NAME}.gds'), so)
    Sx = [f".subckt {NAME} " + ' '.join(f'row_{r}' for r in range(NR)) + ' ' + ' '.join(f'wl_{r}' for r in range(NR)) + ' '
          + ' '.join(f'col_{c}' for c in range(NC)) + ' vss']
    Sx += [f"X_c{c}_r{r} row_{r} wl_{r} col_{c} vss c1t1r_w3" for r in range(NR) for c in range(NC)]
    Sx += [f".ends {NAME}", "", ".subckt c1t1r_w3 TE WL S B", "R0 TE D $[reram]",
           "M1 D WL S B nfet_g5v0d10v5 w=1.5u l=0.5u", "M2 D WL S B nfet_g5v0d10v5 w=1.5u l=0.5u", ".ends c1t1r_w3"]
    (out / f'{NAME}.cdl').write_text('\n'.join(Sx) + '\n')
    bb = T.bbox()
    print(f'{NAME}: {NC} × {NR} 1T1R + strap, pitch {PX / 1000} × {PY / 1000} µm, bbox ({bb.left / 1000:.3f}, {bb.bottom / 1000:.3f})'
          f'–({bb.right / 1000:.3f}, {bb.top / 1000:.3f}) = {bb.width() / 1000:.2f} × {bb.height() / 1000:.2f} µm, 행마다 via2 {nv2}')
    return dict(xr=xr, x3a=x3a, x3b=x3b, x3e=x3e, v2x0=v2x0, nv2=nv2, yt=yt, bbox=(bb.left, bb.bottom, bb.right, bb.top))


if __name__ == '__main__':
    nr = int(os.environ.get('ARR_NR', '4')); nc = int(os.environ.get('ARR_NC', '4'))
    build(nr, nc, os.environ.get('NAME', f'arr_w3s_{nr}x{nc}'))
