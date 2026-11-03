"""nwell8_nets.py 결과 확인: ① Magic nwell.8 상자 (chip_core.magic.sum.boxes) 가 모두 KLayout 2.0 µm 미만 HV nwell 쌍 근처 (0.5 µm) 에 드는가 ② 이름 없는 넷 ($n) 이 어디 닿는가 (m1·m2·m3 도형 범위·label).
쓰임: nwell8_cover.py <gds> <top> <magic boxes>"""
import sys, collections
import klayout.db as db
gds, top, bx = sys.argv[1:4]
exec(open(__file__.replace('nwell8_cover.py', 'nwell8_nets.py')).read().split('l2n.extract_netlist()')[0].split('gds, top, deff, sizes, out = sys.argv[1:6]')[1])
l2n.extract_netlist()
dbu = ly.dbu
nwhv = (nw & hvi).merged()
ep = nwhv.isolated_check(int(round(2.0 / dbu)))
R = db.Region()
for e in ep.each():
    R.insert(e.bbox().enlarged(500, 500))
R.merge()
n = cov = 0
for l in open(bx):
    b, why = l.rstrip('\n').split('\t')
    if 'nwell.8' not in why:
        continue
    x1, y1, x2, y2 = map(float, b.split()); n += 1
    p = db.Point(int((x1 + x2) / 2 * 0.005 / dbu), int((y1 + y2) / 2 * 0.005 / dbu))
    cov += not R.interacting(db.Region(db.Box(p, p).enlarged(1, 1))).is_empty()
print(f'Magic nwell.8 상자 {n} 중 KLayout 쌍 근처 {cov}')
# 이름 없는 넷
seen = set()
for e in ep.each():
    for ed in (e.first, e.second):
        mx, my = (ed.p1.x + ed.p2.x) / 2, (ed.p1.y + ed.p2.y) / 2
        dx, dy = ed.p2.x - ed.p1.x, ed.p2.y - ed.p1.y; L_ = max((dx * dx + dy * dy) ** 0.5, 1)
        for s in (1, -1):
            net = l2n.probe_net(nw, db.DPoint((mx + s * dy / L_ * 20) * dbu, (my - s * dx / L_ * 20) * dbu))
            if net is not None and not net.name and net.cluster_id not in seen:
                seen.add(net.cluster_id)
                info = {nm: l2n.shapes_of_net(net, lay, True).bbox().to_dtype(dbu) for nm, lay in (('nw', nw), ('ntap', ntap), ('m1', m1), ('m2', m2), ('m3', m3), ('m4', m4))}
                print(net.expanded_name(), {k: str(v) for k, v in info.items() if not v.empty()})
