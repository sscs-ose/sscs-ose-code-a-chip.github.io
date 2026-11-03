#!/usr/bin/env python3
"""row_blk 용 TG 매크로 사본 4 개 → macros/ (원본 ../../layout/blocks/tg_n2.*, tgw_n20.* 은 읽기만).

만드는 것 (셀 이름에 rb_ 를 붙여 다른 블록의 tg_n2 와 겹치지 않게):
  rb_tg_n2     = tg_n2 그대로 (원점만 옮김)
  rb_tgw_n20   = tgw_n20 그대로 (원점만 옮김)
  rb_tg_n2_av  = tg_n2 의 a 를 매크로 VDD rail 에 묶은 판 (ROWM XW1: a = vdd)
  rb_tg_n2_as  = tg_n2 의 a 를 매크로 VSS rail 에 묶은 판 (ROWM XW3: a = vss)

원점 정규화: 원본 LEF 는 `ORIGIN 0.460 0.185` 인데 RECT 는 이미 bbox 왼쪽 아래 기준이다
(GDS 원점은 bbox 안쪽 (0.46, 0.185) 에 있음). LEF ORIGIN 해석이 도구마다 달라질 여지를 없애려고
GDS 를 (+0.46, +0.185) 옮겨 bbox 왼쪽 아래 = (0, 0) 으로 만들고 LEF 는 ORIGIN 0 0 + 같은 RECT 로 쓴다.

a 묶음 (원본 GDS 좌표, nm): a 핀 met2 = x −20..310, y 250..8320 / VSS rail met1 y 0..500 / VDD rail met1 y 8070..8570
  av: met2 a 를 y 8570 까지 늘이고 via1 150×150 (x 75..225, y 8335..8485) → VDD rail
  as: met2 a 를 y 0 까지 늘이고 via1 150×150 (x 75..225, y 85..235) → VSS rail
  두 판 모두 a 글자 (69/5) 를 지우고, LEF 에서 a 핀을 빼고 (늘인 띠는 OBS met2), CDL 은 a → VDD / VSS.

"""
from pathlib import Path
import klayout.db as db

HERE = Path(__file__).resolve().parent
SRC = HERE.parent.parent / 'layout' / 'blocks'
OUT = HERE / 'macros'
OUT.mkdir(exist_ok=True)
DX, DY = 460, 185                       # 원본 GDS 원점 → bbox 왼쪽 아래

M2, V1, M2_TXT = (69, 20), (68, 44), (69, 5)
A_STRIP = db.Box(-20, 250, 310, 8320)   # tg_n2 의 a 핀 met2 (원본 좌표)
VARIANTS = {
    # 이름: (원본, a 를 묶을 전원, 늘인 a 띠, via1)
    'rb_tg_n2':    ('tg_n2', None, None, None),
    'rb_tgw_n20':  ('tgw_n20', None, None, None),
    'rb_tg_n2_av': ('tg_n2', 'VDD', db.Box(-20, 250, 310, 8570), db.Box(75, 8335, 225, 8485)),
    'rb_tg_n2_as': ('tg_n2', 'VSS', db.Box(-20, 0, 310, 8320), db.Box(75, 85, 225, 235)),
}


def build_cell(ly_out, name, src, tie, strip, via):
    ly = db.Layout()
    ly.read(str(SRC / f'{src}.gds'))
    top = ly.cell(src)
    assert top is not None and abs(ly.dbu - 0.001) < 1e-12
    c = ly_out.create_cell(name)
    t = db.Trans(DX, DY)
    for li in ly.layer_indexes():
        info = ly.get_info(li)
        lo = ly_out.layer(info.layer, info.datatype)
        for s in top.shapes(li).each():
            if s.is_text():
                if tie and (info.layer, info.datatype) == M2_TXT and s.text.string == 'a':
                    continue                    # a 는 이제 전원 → 글자 지움
                c.shapes(lo).insert(s.text.transformed(t))
            else:
                c.shapes(lo).insert(s.polygon.transformed(t))
    if tie:
        lm2 = ly_out.layer(*M2)
        # 원래 a 띠 (도형 여러 개로 되어 있음) 위에 늘인 띠를 겹쳐 그린다 (merge 하면 띠 하나)
        r = db.Region(c.shapes(lm2)).merged()
        assert any(p.bbox() == A_STRIP.transformed(t) for p in r.each()), f'{name}: a 띠를 못 찾음'
        c.shapes(lm2).insert(strip.transformed(t))
        c.shapes(ly_out.layer(*V1)).insert(via.transformed(t))
    return c


def lef_text(name, cell):
    """LEF 를 매크로 GDS 에서 바로 만든다 (ORIGIN 0 0, bbox 왼쪽 아래 = 원점).
    원본 LEF 는 OBS 에 핀 도형 (rail·ctl 패드·a/b 띠) 까지 다시 넣었고 met2 OBS 띠 (0.33 µm) 가 핀 (0.30 µm) 보다 넓다
    → 배선기가 핀을 OBS 에 덮인 것으로 보거나, 전원 stripe 의 via1 이 rail (= OBS) 위에서 빠질 수 있음.
    여기서는 met1·met2 를 합친 도형 하나하나를 보고 글자 (68/5·69/5) 가 들어 있으면 그 이름의 핀 (실제 금속 그대로),
    없으면 OBS (bbox) 로 쓴다. a 를 전원에 묶은 판은 a 글자가 없어 늘인 띠가 OBS 가 된다."""
    ly = cell.layout()
    bb = cell.bbox()
    assert bb.left == 0 and bb.bottom == 0
    use = {'VDD': 'POWER', 'VSS': 'GROUND'}
    pins, obs = {}, {}
    for (ml, tl), lname in (((68, 20), (68, 5)), ((69, 20), (69, 5))):
        lyr = 'met1' if ml == 68 else 'met2'
        reg = db.Region(cell.begin_shapes_rec(ly.layer(ml, 20))).merged()
        texts = [(s.text.string, s.text.trans.disp) for s in cell.shapes(ly.layer(*lname)).each() if s.is_text()]
        for poly in reg.each():
            nm = [t for t, d in texts if poly.inside(db.Point(d.x, d.y))]
            assert len(set(nm)) <= 1, (name, nm)
            b = poly.bbox()
            if nm:
                # 핀은 실제 금속 그대로: a/b 띠는 0.30 µm 띠 + via 자리 0.33 µm 패드 → 가로로 잘라 사각형 여러 개
                for tp in poly.decompose_trapezoids(0):
                    tb = tp.bbox()
                    assert tp.area() == tb.area(), f'{name}: 핀 {nm[0]} 조각이 사각형이 아님'
                    pins.setdefault(nm[0], []).append((lyr, tb))
            else:
                obs.setdefault(lyr, []).append(b)
    f = lambda b: '%.3f %.3f %.3f %.3f' % (b.left / 1000, b.bottom / 1000, b.right / 1000, b.top / 1000)
    L = [f'MACRO {name}', '  CLASS BLOCK ;', '  ORIGIN 0 0 ;', f'  FOREIGN {name} 0 0 ;',
         '  SIZE %.3f BY %.3f ;' % (bb.width() / 1000, bb.height() / 1000), '  SYMMETRY X Y ;']
    order = [p for p in ('a', 'b', 'ctl', 'ctlb', 'VSS', 'VDD') if p in pins]
    assert set(order) == set(pins), pins.keys()
    for p in order:
        # ctl·ctlb = 게이트 → INPUT (INOUT 이면 timing 엔진이 넷마다 구동점이 둘이라고 IMPESI 오류 2,000 여 개, 잡 721153)
        dirn = 'INPUT' if p in ('ctl', 'ctlb') else 'INOUT'
        L += [f'  PIN {p}', f'    DIRECTION {dirn} ;', f'    USE {use.get(p, "SIGNAL")} ;', '    PORT']
        for lyr, b in pins[p]:
            L += [f'      LAYER {lyr} ;', f'        RECT {f(b)} ;']
        L += ['    END', f'  END {p}']
    L += ['  OBS']
    for lyr in ('met1', 'met2'):
        if obs.get(lyr):
            L += [f'    LAYER {lyr} ;'] + [f'      RECT {f(b)} ;' for b in obs[lyr]]
    L += ['  END', f'END {name}', '']
    return '\n'.join(L)


def cdl_text(name, src, tie):
    lines = (SRC / f'{src}.cdl').read_text().strip().splitlines()
    out = []
    for ln in lines:
        t = ln.split()
        if t[0].lower() == '.subckt':
            ports = t[2:]
            if tie:
                ports = [p for p in ports if p != 'a']
            out.append('.subckt %s %s' % (name, ' '.join(ports)))
        elif t[0].lower() == '.ends':
            out.append(f'.ends {name}')
        else:
            if tie:
                t = [tie if (k in (1, 3) and x == 'a') else x for k, x in enumerate(t)]
            out.append(' '.join(t))
    return '\n'.join(out) + '\n'


ly_all = db.Layout(); ly_all.dbu = 0.001
lefs, cdls = [], []
for name, (src, tie, strip, via) in VARIANTS.items():
    ly1 = db.Layout(); ly1.dbu = 0.001
    c1 = build_cell(ly1, name, src, tie, strip, via)
    ly1.write(str(OUT / f'{name}.gds'))
    build_cell(ly_all, name, src, tie, strip, via)
    lt, ct = lef_text(name, c1), cdl_text(name, src, tie)
    (OUT / f'{name}.lef').write_text('VERSION 5.7 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n\n' + lt + '\nEND LIBRARY\n')
    (OUT / f'{name}.cdl').write_text(ct)
    lefs.append(lt); cdls.append(ct)
    bb = c1.bbox()
    print(f'{name}: bbox {bb} (원점 = bbox 왼쪽 아래: {bb.left == 0 and bb.bottom == 0})')
ly_all.write(str(OUT / 'rb_macros.gds'))
(OUT / 'rb_macros.lef').write_text('VERSION 5.7 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n\n' + '\n'.join(lefs) + '\nEND LIBRARY\n')
(OUT / 'rb_macros.cdl').write_text('* rb_macros.cdl -- mk_macros.py 출력 (원본 layout/blocks/tg_n2·tgw_n20 .cdl)\n' + '\n'.join(cdls))
print('wrote', OUT)
