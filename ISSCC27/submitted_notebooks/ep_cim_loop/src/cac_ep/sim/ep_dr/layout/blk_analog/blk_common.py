"""blk_analog 공통부 (10/28) — 정수 nm 좌표 도형, 비아 쌓기 셀, 금속 폭·간격 미리 검사, 연결 검사 (KLayout LayoutToNetlist), 핀 JSON.
소자 규칙 값은 ep_demo/layout/devlib.py (SERN gen_neuron.py 사본, DRC 통과 이력) 와 같은 값을 쓰고, 고치지 않는다 (devlib 는 import 만).
diff–diff (hvi) 0.30, nsdm/psdm 간격 0.38 (작으면 합침), 반대 implant–diff/tap 0.13, met1·met2 0.14/0.14, met3 0.30/0.30, via2 0.20 (met2 0.04/0.085,
met3 0.065), via1 0.15 (met1 0.055/0.085, met2 0.055/0.085), mcon 0.17 (met1 0.03/0.06).
"""
import json
import sys
from pathlib import Path

import klayout.db as db

H = Path(__file__).resolve().parent
DEMO = H.parents[2] / 'ep_demo' / 'layout'
sys.path.insert(0, str(DEMO))
from devlib import LAY as DEVLIB_LAY                                  # noqa: E402  (층 번호는 devlib 와 같게)

LAYERS = dict(DEVLIB_LAY)
LAYERS.update(lbl_m3=(70, 5), pin_m3=(70, 16))
CUTS = ('licon', 'mcon', 'via', 'via2')
MIN_WS = {'li1': (170, 170), 'm1': (140, 140), 'm2': (140, 140), 'm3': (300, 300), 'poly': (150, 210)}


def g5(v):
    """nm → 5 nm 격자."""
    return int(round(v / 5.0)) * 5


class Blk:
    """셀 하나 + 층 색인. 좌표는 모두 정수 nm."""

    def __init__(self, ly, name):
        self.ly, self.c = ly, ly.create_cell(name)
        self.L = {k: ly.layer(*v) for k, v in LAYERS.items()}

    def box(self, lay, x1, y1, x2, y2, cell=None):
        b = db.Box(g5(min(x1, x2)), g5(min(y1, y2)), g5(max(x1, x2)), g5(max(y1, y2)))
        (cell or self.c).shapes(self.L[lay]).insert(b)
        return b

    def sq(self, lay, x, y, s, cell=None):
        return self.box(lay, x - s / 2, y - s / 2, x + s / 2, y + s / 2, cell)

    def text(self, lay, s, x, y):
        self.c.shapes(self.L[lay]).insert(db.Text(s, db.Trans(g5(x), g5(y))))

    def inst(self, sub, x, y, nx=1, ny=1, dx=0, dy=0):
        if nx == 1 and ny == 1:
            self.c.insert(db.CellInstArray(sub.cell_index(), db.Trans(g5(x), g5(y))))
        else:
            self.c.insert(db.CellInstArray(sub.cell_index(), db.Trans(g5(x), g5(y)), db.Vector(g5(dx), 0), db.Vector(0, g5(dy)), nx, ny))


def via_cells(B):
    """비아 쌓기 셀: v12 (met1 패드 0.33 + via1 + met2 패드 0.33), v23 (met2 0.37 + via2 + met3 0.50, met3 최소 면적 0.24), v123 (met1 0.33 + via1 + met2 0.37 + via2)."""
    ly = B.ly
    v12 = ly.create_cell('v12'); v23 = ly.create_cell('v23'); v123 = ly.create_cell('v123'); vm2m3 = ly.create_cell('v2only')
    for c, parts in ((v12, (('m1', 330), ('via', 150), ('m2', 330))),
                     (v23, (('m2', 370), ('via2', 200), ('m3', 500))),
                     (v123, (('m1', 330), ('via', 150), ('m2', 370), ('via2', 200))),
                     (vm2m3, (('m2', 370), ('via2', 200)))):
        for lay, s in parts:
            B.sq(lay, 0, 0, s, cell=c)
    return dict(v12=v12, v23=v23, v123=v123, v2=vm2m3)


def finish_hvi(B, margin=185):
    """hvi (75/20) 를 셀 전체 bbox + margin 으로 (hvdifftap.21: hvi 가 diff/tap 을 0.18 이상)."""
    bb = B.c.bbox()
    B.c.shapes(B.L['hvi']).insert(bb.enlarged(margin, margin))
    return B.c.bbox()


def precheck(ly, top, lays=('m1', 'm2', 'm3', 'li1')):
    """금속 폭·간격 미리 검사 (병합 뒤 Region.width_check / space_check). 반환 {층: (폭 위반 수, 간격 위반 수)}."""
    out = {}
    for k in lays:
        r = db.Region(top.begin_shapes_rec(ly.layer(*LAYERS[k]))).merged()
        w, s = MIN_WS[k]
        out[k] = (r.width_check(w).count(), r.space_check(s).count())
    return out


def netcheck(ly, top):
    """KLayout 연결 추출 (소자 없이 금속·컨택만): 라벨이 둘 이상 붙은 넷 = 단락, 같은 라벨이 둘 이상 넷 = 끊김.
    diff 는 poly 를 뺀 S/D 조각만 잇는다 (게이트 아래로 S·D 가 붙지 않게)."""
    l2n = db.LayoutToNetlist(db.RecursiveShapeIterator(ly, top, []))
    mk = lambda k: l2n.make_layer(ly.layer(*LAYERS[k]), k)
    diff, poly, tap = mk('diff'), mk('poly'), mk('tap')
    sd = diff - poly
    l2n.register(sd, 'sd')
    li, m1, m2, m3 = mk('li1'), mk('m1'), mk('m2'), mk('m3')
    licon, mcon, via, via2 = mk('licon'), mk('mcon'), mk('via'), mk('via2')
    t1 = l2n.make_text_layer(ly.layer(*LAYERS['lbl_m1']), 't1')
    t2 = l2n.make_text_layer(ly.layer(*LAYERS['lbl_m2']), 't2')
    t3 = l2n.make_text_layer(ly.layer(*LAYERS['lbl_m3']), 't3')
    for a in (sd, poly, tap, li, m1, m2, m3, licon, mcon, via, via2):
        l2n.connect(a)
    for a, b in ((licon, sd), (licon, poly), (licon, tap), (licon, li), (mcon, li), (mcon, m1), (via, m1), (via, m2), (via2, m2), (via2, m3),
                 (t1, m1), (t2, m2), (t3, m3)):
        l2n.connect(a, b)
    l2n.extract_netlist()
    nl = l2n.netlist()
    circ = nl.circuit_by_name(top.name)
    names = {}
    shorts = []
    for n in circ.each_net():
        nm = n.name or ''
        if not nm:
            continue
        parts = [p for p in nm.split(',') if p]
        if len(set(parts)) > 1:
            shorts.append(nm)
        for p in set(parts):
            names[p] = names.get(p, 0) + 1
    opens = sorted(k for k, v in names.items() if v > 1)
    return dict(nets=sum(1 for _ in circ.each_net()), labelled=len(names), shorts=shorts, opens=opens)


def write_pins_json(path, name, bbox_nm, pins, extra=None):
    """핀 JSON: 셀 좌표 (µm, 셀 원점 기준). pins = {핀: [(층, x1, y1, x2, y2), …]}."""
    u = lambda v: round(v / 1000.0, 3)
    d = dict(cell=name, units='um (cell coordinates)', bbox=[u(v) for v in bbox_nm],
             size=[u(bbox_nm[2] - bbox_nm[0]), u(bbox_nm[3] - bbox_nm[1])],
             pins={k: [dict(layer=l, rect=[u(a), u(b), u(c), u(e)]) for (l, a, b, c, e) in v] for k, v in pins.items()})
    if extra:
        d.update(extra)
    Path(path).write_text(json.dumps(d, indent=1, ensure_ascii=False))
    return d
