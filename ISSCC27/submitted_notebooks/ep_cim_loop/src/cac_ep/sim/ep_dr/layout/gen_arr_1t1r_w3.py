"""1T1R 배열 생성기 — 접근 nFET W 3 µm (핑거 2 × 1.5 µm, drain 공유), L 0.5 µm, 5 V g5v0d10v5 + SKY130 RRAM (via1 + 230/20 표시).
10/28, 사용자 "현재 flowplan을 확정 … 그 다음에 DRC, LVS가 만족 되도록, 작업해볼래?". 회로 기준 = real_circuit/gen_chip_deck2.py 의 셀
(RRAM TE = 행, BE → nFET drain, source = 열, 게이트 = WL, body = VSS, nFET w=3 l=0.5).
셀 도형은 PDK 셀 RRAM_1T1R_larger (W 1.5, ep_demo/layout/cells/rram_1t1r_marked.gds) 의 층·간격을 따라 새로 그린 것 (코드는 가져오지 않음):
  S1 | G1 | D (공유) | G2 | S2 — 두 source 는 아래 met1 막대로 묶어 왼쪽 VS 패드 → 열선 (met1 세로),
  drain 은 위 met1 막대로 S2 를 넘어 오른쪽 RRAM 의 BE (met1) → via1 + 230/20 → TE (met2) → met2 riser → 행 띠 (met2 가로, 셀 아래쪽),
  게이트 = 두 핑거를 위 poly 막대로 잇고 poly 패드 → li → met1 → via1 → met2 → WL 띠 (met2 가로, 셀 위쪽), body = 아래 p-tap → met1 GND.
행 pitch 3.41 µm (PDK 셀 높이 그대로), 열 pitch 5.115 µm (열 주변 회로 폭). LVS = ep_demo/pdk/Sky130_LVS/sky130_1r.lvs.pvl (RRAM = R(reram) met2→met1).
쓰임: ARR_NR=4 ARR_NC=4 NAME=arr_w3_4x4 python gen_arr_1t1r_w3.py → blocks/NAME.gds, blocks/NAME.cdl (+ 셀 c1t1r_w3)
"""
import os
from pathlib import Path

import klayout.db as db

H = Path(__file__).resolve().parent
NR = int(os.environ.get('ARR_NR', '4')); NC = int(os.environ.get('ARR_NC', '4'))
PX = int(os.environ.get('ARR_PX', '5115')); PY = int(os.environ.get('ARR_PY', '3410'))
NAME = os.environ.get('NAME', f'arr_w3_{NR}x{NC}')
EXT_L, EXT_R, EXT_B = 1500, 1500, 2500                       # 행 띠 왼쪽 (입력 구동)·오른쪽 (row MUX), 열선 아래 (열 MUX) 로 내민 길이 (nm)
L = dict(diff=(65, 20), tap=(65, 44), poly=(66, 20), licon=(66, 44), li=(67, 20), mcon=(67, 44), m1=(68, 20), via=(68, 44), m2=(69, 20),
         nsdm=(93, 44), psdm=(94, 20), npc=(95, 20), hvi=(75, 20), rram=(230, 20), t1=(68, 5), t2=(69, 5))
ly = db.Layout(); ly.dbu = 0.001
I = {k: ly.layer(*v) for k, v in L.items()}


def bx(c, k, x0, y0, x1, y1):
    c.shapes(I[k]).insert(db.Box(x0, y0, x1, y1))


# ── 셀 (nm, PDK 셀과 같은 원점: VS 패드 왼쪽 −460, GND 아래 −940, WL 패드 위 2470)
C = ly.create_cell('c1t1r_w3')
G1, G2 = (445, 945), (1235, 1735)                              # 핑거 피치 = L 500 + S/D 290 (devlib 와 같은 값)
bx(C, 'diff', 180, 180, 2000, 1680); bx(C, 'nsdm', 55, 55, 2125, 1805); bx(C, 'hvi', 0, -780, 2180, 1860)
for g0, g1 in (G1, G2):
    bx(C, 'poly', g0, 50, g1, 1810)
bx(C, 'poly', G1[0], 1810, G2[1], 1960)                        # 두 핑거를 잇는 poly 막대 (diff 위 130 nm 밖)
bx(C, 'poly', 525, 1855, 855, 2185); bx(C, 'npc', 505, 1835, 875, 2205)
bx(C, 'licon', 605, 1935, 775, 2105); bx(C, 'li', 525, 1855, 855, 2185); bx(C, 'mcon', 605, 1935, 775, 2105)
bx(C, 'm1', 530, 1860, 850, 2180); bx(C, 'via', 615, 1945, 765, 2095); bx(C, 'm2', 505, 1820, 875, 2470)    # 게이트 → WL
YS = ((240, 410), (580, 750), (920, 1090), (1260, 1430))        # S/D licon 줄 (PDK 셀과 같음)
for x0, x1, ym in ((220, 390, (405, 575)), (1005, 1175, (1205, 1375)), (1790, 1960, (405, 575))):   # S1, D, S2
    for y0, y1 in YS:
        bx(C, 'licon', x0, y0, x1, y1)
    bx(C, 'li', x0, 160, x1, 1510); bx(C, 'mcon', x0, ym[0], x1, ym[1])
bx(C, 'm1', -460, 345, 2020, 635)                              # 두 source → VS 패드 (열선과 겹침)
bx(C, 'm1', 945, 1145, 2665, 1435)                             # drain → RRAM BE
bx(C, 'm1', 2345, 1160, 2665, 1420)                            # BE 패드
bx(C, 'via', 2430, 1215, 2580, 1365); bx(C, 'rram', 2380, 1165, 2630, 1415)       # RRAM (via1 + 230/20)
bx(C, 'm2', 2375, 1130, 2635, 1450)                            # TE
bx(C, 'm2', 2345, -620, 2665, 1300)                            # riser → 행 띠
bx(C, 'tap', 180, -600, 2000, -190); bx(C, 'psdm', 55, -725, 2125, 35)              # body p-tap
for x0 in (415, 890, 1365, 1790):
    bx(C, 'licon', x0, -480, x0 + 170, -310)
bx(C, 'li', 270, -480, 2105, -310)
for x0 in (350, 830, 1310, 1790):
    bx(C, 'mcon', x0, -480, x0 + 170, -310)
bx(C, 'm1', 180, -940, 2000, -190)                             # GND (body)

# ── 배열
T = ly.create_cell(NAME)
T.insert(db.CellInstArray(C.cell_index(), db.Trans(0, 0), db.Vector(PX, 0), db.Vector(0, PY), NC, NR))
xr = (NC - 1) * PX + 2665
for r in range(NR):
    y = r * PY
    bx(T, 'm2', -EXT_L, y - 670, xr + EXT_R, y - 250)          # 행 (TE)
    bx(T, 'm2', -EXT_L, y + 2250, xr + EXT_R, y + 2470)        # WL
    T.shapes(I['t2']).insert(db.Text(f'row_{r}', db.Trans(-EXT_L + 200, y - 460)))
    T.shapes(I['t2']).insert(db.Text(f'wl_{r}', db.Trans(xr + EXT_R - 200, y + 2360)))
for c in range(NC):
    bx(T, 'm1', c * PX - 310, -EXT_B, c * PX - 70, (NR - 1) * PY + 635)   # 열 (source)
    T.shapes(I['t1']).insert(db.Text(f'col_{c}', db.Trans(c * PX - 190, -EXT_B + 200)))
T.shapes(I['t1']).insert(db.Text('vss', db.Trans(1090, -565)))   # body (한 셀 GND, 나머지는 기판으로 이어짐)
(H / 'blocks').mkdir(exist_ok=True)
so = db.SaveLayoutOptions(); so.add_cell(T.cell_index())
ly.write(str(H / 'blocks' / f'{NAME}.gds'), so)
S = [f".subckt {NAME} " + ' '.join(f'row_{r}' for r in range(NR)) + ' ' + ' '.join(f'wl_{r}' for r in range(NR)) + ' '
     + ' '.join(f'col_{c}' for c in range(NC)) + ' vss']
S += [f"X_c{c}_r{r} row_{r} wl_{r} col_{c} vss c1t1r_w3" for r in range(NR) for c in range(NC)]
S += [f".ends {NAME}", "", ".subckt c1t1r_w3 TE WL S B", "R0 TE D $[reram]",
      "M1 D WL S B nfet_g5v0d10v5 w=1.5u l=0.5u", "M2 D WL S B nfet_g5v0d10v5 w=1.5u l=0.5u", ".ends c1t1r_w3"]
(H / 'blocks' / f'{NAME}.cdl').write_text('\n'.join(S) + '\n')
bb = T.bbox()
print(f'{NAME}: {NC} × {NR} 1T1R (W 3 µm), pitch {PX / 1000} × {PY / 1000} µm, bbox {bb.width() / 1000:.2f} × {bb.height() / 1000:.2f} µm')
