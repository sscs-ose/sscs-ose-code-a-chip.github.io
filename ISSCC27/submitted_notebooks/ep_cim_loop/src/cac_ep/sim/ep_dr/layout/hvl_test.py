"""SKY130 5 V 표준 셀 (sky130_fd_sc_hvl, volare c6d73a35, ~/pdk/volare/sky130A/libs.ref/sky130_fd_sc_hvl) 이 Cadence Pegasus DRC·LVS 에서
깨끗한지 시험 (10/28). 쓸 셀 몇 개를 한 줄로 맞붙여 놓고 전원 rail 에 vdd·vss 이름표 → blocks/hvl_test.gds + .cdl (hvl CDL 전체 + top).
쓰임: /home/dave/work/projects/sern_hog_classab_opamp/sim/.venv/bin/python hvl_test.py
"""
import re
from pathlib import Path

import klayout.db as db

H = Path(__file__).resolve().parent
LIB = Path('/home/dave/pdk/volare/sky130A/libs.ref/sky130_fd_sc_hvl')
CELLS = ['inv_1', 'inv_4', 'nand2_1', 'nor2_1', 'and2_1', 'mux2_1', 'buf_4', 'buf_16', 'dfrtp_1', 'dlxtp_1']
lef = (LIB / 'lef' / 'sky130_fd_sc_hvl.lef').read_text()
SIZE = {m: float(w) for m, w in re.findall(r'MACRO sky130_fd_sc_hvl__(\w+)\s.*?SIZE ([\d.]+) BY', lef, re.S)}
cdl = (LIB / 'cdl' / 'sky130_fd_sc_hvl.cdl').read_text()
PINS = {m: p.split() for m, p in re.findall(r'^\.SUBCKT sky130_fd_sc_hvl__(\w+) ([^\n]+)', cdl, re.M)}

ly = db.Layout(); ly.dbu = 0.001
ly.read(str(LIB / 'gds' / 'sky130_fd_sc_hvl.gds'))
T = ly.create_cell('hvl_test')
x, S = 0.0, ['.SUBCKT hvl_test vdd vss']
for k, n in enumerate(CELLS):
    c = ly.cell(f'sky130_fd_sc_hvl__{n}')
    T.insert(db.DCellInstArray(c.cell_index(), db.DTrans(x, 0)))
    pw = {'VGND': 'vss', 'VNB': 'vss', 'VPB': 'vdd', 'VPWR': 'vdd'}
    S.append(f"X{k} " + ' '.join(pw.get(p, f'i{k}_{p}') for p in PINS[n]) + f" sky130_fd_sc_hvl__{n}")
    x += SIZE[n]
S.append('.ENDS hvl_test')
m1 = ly.layer(68, 20)                                              # hvl 셀은 tap rail (VNB 아래 −0.115…0.115, VPB 위 3.955…4.185) 이
for y0, y1 in ((-115, 625), (3445, 4185)):                         # 전원 rail (VGND 0.255…0.625, VPWR 3.445…3.815) 과 따로 → 줄 양 끝에서 met1 로 이음
    T.shapes(m1).insert(db.Box(-500, y0, 0, y1)); T.shapes(m1).insert(db.Box(int(x * 1000), y0, int(x * 1000) + 500, y1))
lt = ly.layer(68, 5)
T.shapes(lt).insert(db.Text('vdd', db.Trans(int(0.6 * 1000), 3630)))
T.shapes(lt).insert(db.Text('vss', db.Trans(int(0.6 * 1000), 440)))
so = db.SaveLayoutOptions(); so.add_cell(T.cell_index())
(H / 'blocks').mkdir(exist_ok=True)
ly.write(str(H / 'blocks' / 'hvl_test.gds'), so)
cdl_u = re.sub(r'\b([wl])=([0-9.]+)(?=\s)', r'\1=\2u', cdl)            # CDL 단위 없음 = m 로 읽힘 → µm
(H / 'blocks' / 'hvl_test.cdl').write_text(cdl_u + '\n' + '\n'.join(S) + '\n')
print('hvl_test:', len(CELLS), 'cells, width', round(x, 3), 'um')
