"""nwell8_nets.py 보충: 이름 없는 넷 (셀 안 넷) 은 인스턴스 경로까지 붙여 같은 넷인지 다시 본다. 쌍마다 (넷, 경로) 와 간격.
쓰임: nwell8_path.py <gds> <top> <out.json>"""
import sys, json, collections
import klayout.db as db
gds, top, out = sys.argv[1:4]
exec(open(__file__.replace('nwell8_path.py', 'nwell8_nets.py')).read().split('l2n.extract_netlist()')[0].split('gds, top, deff, sizes, out = sys.argv[1:6]')[1])
l2n.extract_netlist()
dbu = ly.dbu
ep = (nw & hvi).merged().isolated_check(int(round(2.0 / dbu)))
def key(ed):
    mx, my = (ed.p1.x + ed.p2.x) / 2, (ed.p1.y + ed.p2.y) / 2
    dx, dy = ed.p2.x - ed.p1.x, ed.p2.y - ed.p1.y; L_ = max((dx * dx + dy * dy) ** 0.5, 1)
    for s in (1, -1):
        path = []
        net = l2n.probe_net(nw, db.DPoint((mx + s * dy / L_ * 20) * dbu, (my - s * dx / L_ * 20) * dbu), path)
        if net is not None:
            nm = net.expanded_name()
            if net.name:
                return nm, nm
            return nm + ' @' + '/'.join(sc.expanded_name() for sc in path), net.circuit().name
    return '(못 찾음)', ''
C = collections.Counter(); dist = collections.defaultdict(list); ex = {}
for e in ep.each():
    (a, ca), (b, cb) = key(e.first), key(e.second)
    k = ('같은 넷' if a == b else '다른 넷', ' | '.join(sorted({ca, cb})) if a != b else (a if '@' not in a else f'{ca} 안 넷'))
    C[k] += 1; dist[k].append(round(e.first.distance(e.second.p1) * dbu if False else e.bbox().width() * dbu, 3))
    ex.setdefault(k, (a, b))
J = [dict(kind=k[0], nets=k[1], n=v, example=ex[k]) for k, v in sorted(C.items())]
json.dump(J, open(out, 'w'), indent=1, ensure_ascii=False)
for j in J: print(j)
