"""Innovus 에 넣을 아날로그 스위치 매크로 (10/28, 사용자 "그 방향에 맞으니까 진행해 봐" — 디지털은 hvl 표준 셀 + Genus/Innovus, 스위치는 생성기).
row·열 MUX (real_circuit/chip_lib.py ROWM·COLM) 의 TG (N 2 / P 4 µm) 와 TGW (N 20 / P 40 µm), L 0.5, 5 V g5v0d10v5.
그리기는 이전 판 ep_demo/layout/gen_tg.py 의 build() 를 그대로 부름 (TG W10 DRC·LVS 통과 이력, 10/04). ⚠ gen_tg.py·devlib.py 는 SERN 소자 규칙 사본 —
공개 노트북에 넣기 전 출처 확인 (README §5).
쓰임: /home/dave/work/projects/sern_hog_classab_opamp/sim/.venv/bin/python gen_macros.py
"""
import sys
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H.parents[1] / 'ep_demo' / 'layout'))
import klayout.db as db                                            # noqa: E402
from devlib import Cell, finish                                    # noqa: E402
import gen_tg                                                      # noqa: E402

MACROS = {'tg_n2': (2.0, 4.6, 2), 'tgw_n20': (20.0, 4.6, None)}   # 이름 → (nfet W, 셀 안 소자 폭 한도 WMAX, 핑거 수 상한)
# tg_n2 는 핑거 상한 2: 상한 없이 5 개로 나누면 nfet 핑거 0.4 µm 가 5 V diff 최소 폭보다 얇아 difftap.2 위반 (10/28 잡 첫 판)


def lef_of(name, ly, cell, pins):
    """"""
    bb = cell.bbox(); u = lambda v: v / 1000.0
    ox, oy = bb.left, bb.bottom
    L = [f"MACRO {name}", "  CLASS BLOCK ;", f"  ORIGIN {u(-ox):.3f} {u(-oy):.3f} ;", f"  SIZE {u(bb.width()):.3f} BY {u(bb.height()):.3f} ;", "  SYMMETRY X Y ;"]
    for pn, (lay, boxes) in pins.items():
        use = 'POWER' if pn == 'VDD' else 'GROUND' if pn == 'VSS' else 'SIGNAL'
        L += [f"  PIN {pn}", f"    DIRECTION INOUT ;", f"    USE {use} ;", "    PORT", f"      LAYER {lay} ;"]
        L += [f"        RECT {u(b.left - ox):.3f} {u(b.bottom - oy):.3f} {u(b.right - ox):.3f} {u(b.top - oy):.3f} ;" for b in boxes]
        L += ["    END", f"  END {pn}"]
    L += ["  OBS"]
    for lay, (l, d) in (('met1', (68, 20)), ('met2', (69, 20))):
        r = db.Region(cell.begin_shapes_rec(ly.layer(l, d))).merged()
        L += [f"    LAYER {lay} ;"] + [f"      RECT {u(b.left - ox):.3f} {u(b.bottom - oy):.3f} {u(b.right - ox):.3f} {u(b.top - oy):.3f} ;"
                                       for p in r.each() for b in [p.bbox()]]
    L += ["  END", f"END {name}", ""]
    return "\n".join(L)


(H / 'blocks').mkdir(exist_ok=True)
for name, (wn, wmax, nfm) in MACROS.items():
    ly = db.Layout(); ly.dbu = 0.001
    C = Cell(ly, name)
    r = gen_tg.build(C, 0.0, 0.0, wn, wmax, nf_max=nfm)
    C.label('a', 'lbl_m2', r['xa'], 1.0); C.label('b', 'lbl_m2', r['xb'], 1.0)
    C.label('ctl', 'lbl_m1', *r['gn']); C.label('ctlb', 'lbl_m1', *r['gp'])
    C.label('VSS', 'lbl_m1', 0.3, r['ytap_p']); C.label('VDD', 'lbl_m1', 0.3, r['ytap_n'])
    finish(C)
    ly.write(str(H / 'blocks' / f'{name}.gds'))
    (H / 'blocks' / f'{name}.cdl').write_text(f".subckt {name} a b ctl ctlb VDD VSS\n" + "\n".join(r['cdl']) + f"\n.ends {name}\n")
    um = lambda v: int(round(v * 1000))
    M2 = lambda x: db.Box(um(x - 0.15), um(0.25), um(x + 0.15), um(r['ytap_n']))
    pad = lambda p: db.Box(um(p[0] - 0.17), um(p[1] - 0.17), um(p[0] + 0.17), um(p[1] + 0.17))
    pins = {'a': ('met2', [M2(r['xa'])]), 'b': ('met2', [M2(r['xb'])]), 'ctl': ('met1', [pad(r['gn'])]), 'ctlb': ('met1', [pad(r['gp'])]),
            'VSS': ('met1', [db.Box(0, um(r['ytap_p'] - 0.25), um(wmax), um(r['ytap_p'] + 0.25))]),
            'VDD': ('met1', [db.Box(0, um(r['ytap_n'] - 0.25), um(wmax), um(r['ytap_n'] + 0.25))])}
    (H / 'blocks' / f'{name}.lef').write_text(lef_of(name, ly, C.c, pins))
    bb = C.c.bbox()
    print(f"{name}: nf n/p = {r['nf']}, {bb.width() / 1000:.3f} × {bb.height() / 1000:.3f} µm, shorts {C.shorts() or 'none'}")
