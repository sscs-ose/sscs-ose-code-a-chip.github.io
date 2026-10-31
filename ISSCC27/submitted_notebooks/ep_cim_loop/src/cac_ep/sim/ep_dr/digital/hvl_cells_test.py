"""hvl 셀 두 줄 시험 (10/28): layout/hvl_test.py (한 줄, 10 셀) 의 사본을 고침.
→ blocks/hvl_cells2.gds + .cdl (hvl CDL (u 붙인 것) 전체 + top). DRC·LVS 는 signoff_cells.sbatch.
쓰임: /home/dave/work/projects/sern_hog_classab_opamp/sim/.venv/bin/python hvl_cells_test.py
"""
import re
from pathlib import Path

import klayout.db as db

H = Path(__file__).resolve().parent
LIB = Path('/home/dave/pdk/volare/sky130A/libs.ref/sky130_fd_sc_hvl')
ROW0 = ['inv_1', 'inv_2', 'inv_4', 'inv_8', 'buf_1', 'buf_2', 'buf_4', 'buf_8', 'nand2_1', 'nand3_1', 'nor2_1', 'nor3_1',
        'and2_1', 'and3_1', 'or2_1', 'or3_1', 'fill_1', 'fill_2', 'fill_4', 'fill_8']
ROW1 = ['a21oi_1', 'o21ai_1', 'a21o_1', 'o21a_1', 'a22oi_1', 'o22ai_1', 'mux2_1', 'xor2_1', 'xnor2_1', 'dfrtp_1', 'dlxtp_1',
        'fill_8', 'fill_4', 'fill_2', 'fill_1']
RH = 4.07
lef = (LIB / 'lef' / 'sky130_fd_sc_hvl.lef').read_text()
SIZE = {m: float(w) for m, w in re.findall(r'MACRO sky130_fd_sc_hvl__(\w+)\s.*?SIZE ([\d.]+) BY', lef, re.S)}
cdl = (H / 'pdk' / 'sky130_fd_sc_hvl_u.cdl').read_text()
PINS = {m: p.split() for m, p in re.findall(r'^\.SUBCKT sky130_fd_sc_hvl__(\w+) ([^\n]+)', cdl, re.M)}

ly = db.Layout(); ly.dbu = 0.001
ly.read(str(LIB / 'gds' / 'sky130_fd_sc_hvl.gds'))
T = ly.create_cell('hvl_cells2')
S = ['.SUBCKT hvl_cells2 vdd vss']
pw = {'VGND': 'vss', 'VNB': 'vss', 'VPB': 'vdd', 'VPWR': 'vdd'}
w0, w1 = sum(SIZE[n] for n in ROW0), sum(SIZE[n] for n in ROW1)
pad = ['fill_1'] * int(round(abs(w0 - w1) / SIZE['fill_1']))                  # 짧은 줄을 fill_1 로 채워 두 줄 길이를 맞춤 (0.48 µm 배수)
ROW0, ROW1 = (ROW0 + pad, ROW1) if w0 < w1 else (ROW0, ROW1 + pad)
w0 = sum(SIZE[n] for n in ROW0)
assert abs(sum(SIZE[n] for n in ROW1) - w0) < 1e-6, (w0, w1)
k = 0
for r, cells in enumerate((ROW0, ROW1)):
    x = 0.0
    for n in cells:
        c = ly.cell(f'sky130_fd_sc_hvl__{n}')
        tr = db.DTrans(x, 0) if r == 0 else db.DTrans(db.DTrans.M0, x, 2 * RH)   # MX: y → 2·RH − y
        T.insert(db.DCellInstArray(c.cell_index(), tr))
        if not n.startswith('fill_'):                                     # filler = 소자 없음 → source 에 넣으면 '빠진 인스턴스' 로 셈 (721103)
            S.append(f"X{k} " + ' '.join(pw.get(p, f'i{k}_{p}') for p in PINS[n]) + f" sky130_fd_sc_hvl__{n}")
        x += SIZE[n]; k += 1
S.append('.ENDS hvl_cells2')
m1 = ly.layer(68, 20)
W = int(round(w0 * 1000))
for yb in (0, 4070, 8140):                                               # 경계 0 = VSS, 4.07 = VDD, 8.14 = VSS
    T.shapes(m1).insert(db.Box(0, yb - 625, W, yb + 625))
T.shapes(m1).insert(db.Box(-1500, -625, -1000, 8765))                    # 두 VSS 띠를 줄 왼쪽 밖에서 met1 로 이음 (블록에서는 met2 stripe 가 함)
T.shapes(m1).insert(db.Box(-1500, -625, 0, 625)); T.shapes(m1).insert(db.Box(-1500, 7515, 0, 8765))
lt = ly.layer(68, 5)
T.shapes(lt).insert(db.Text('vdd', db.Trans(600, 4070)))
T.shapes(lt).insert(db.Text('vss', db.Trans(600, 0)))
so = db.SaveLayoutOptions(); so.add_cell(T.cell_index())
(H / 'blocks').mkdir(exist_ok=True)
ly.write(str(H / 'blocks' / 'hvl_cells2.gds'), so)
(H / 'blocks' / 'hvl_cells2.cdl').write_text(cdl + '\n' + '\n'.join(S) + '\n')
print('hvl_cells2:', k, 'cells, 2 rows, width', round(w0, 3), 'um')
