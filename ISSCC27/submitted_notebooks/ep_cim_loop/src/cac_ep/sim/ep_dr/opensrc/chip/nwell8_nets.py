"""Magic nwell.8 (HV nwell 간격 < 2.0 µm) 판정용: KLayout 연결 추출로 간격이 2.0 µm 보다 가까운 HV nwell 쌍마다 두 nwell 의 넷을 찾는다.
HV nwell = nwell & hvi (Magic mvnwell 과 같은 뜻). 연결: nwell–ntap(tap&nsdm)–licon–li–mcon–met1–via1(RRAM 표지 230/20 자리 뺌)–met2–…–met5, 이름 = x/5 label.
쓰임 (Olympus, klayout python): nwell8_nets.py <gds> <top> <def> <lef_sizes.txt> <out.json>"""
import collections, json, re, sys
import klayout.db as db
gds, top, deff, sizes, out = sys.argv[1:6]
ly = db.Layout(); ly.read(gds)
l2n = db.LayoutToNetlist(db.RecursiveShapeIterator(ly, ly.cell(top), []))
L = lambda a, b, n: l2n.make_layer(ly.layer(a, b), n)
T = lambda a, b, n: l2n.make_text_layer(ly.layer(a, b), n)
nw, hvi, tap, nsdm = L(64, 20, 'nw'), L(75, 20, 'hvi'), L(65, 44, 'tap'), L(93, 44, 'nsdm')
licon, li, mcon, m1, v1, m2, v2, m3, v3, m4, v4, m5 = (L(66, 44, 'licon'), L(67, 20, 'li'), L(67, 44, 'mcon'), L(68, 20, 'm1'), L(68, 44, 'v1'), L(69, 20, 'm2'),
                                                     L(69, 44, 'v2'), L(70, 20, 'm3'), L(70, 44, 'v3'), L(71, 20, 'm4'), L(71, 44, 'v4'), L(72, 20, 'm5'))
rr = L(230, 20, 'rram')
ntap = tap & nsdm; v1c = v1 - rr
l2n.register(ntap, 'ntap'); l2n.register(v1c, 'v1c')
txt = {k: T(k, 5, f't{k}') for k in (67, 68, 69, 70, 71, 72)}
chain = [nw, ntap, licon, li, mcon, m1, v1c, m2, v2, m3, v3, m4, v4, m5]
for a, b in zip(chain, chain[1:]):
    l2n.connect(a, b)
for x in chain:
    l2n.connect(x)
for k, m in zip((67, 68, 69, 70, 71, 72), (li, m1, m2, m3, m4, m5)):
    l2n.connect(m, txt[k])
l2n.extract_netlist()
nwhv = (nw & hvi).merged()
dbu = ly.dbu
ep = nwhv.isolated_check(int(round(2.0 / dbu)))           # 서로 다른 HV nwell 사이 2.0 µm 미만
notch = nwhv.notch_check(int(round(2.0 / dbu)))            # 같은 nwell 도형 안의 홈 (같은 넷)
# 블록 자리
t = open(deff).read(); c = t[t.find('COMPONENTS'):t.find('END COMPONENTS')]
sz = {l.split()[0]: (float(l.split()[1]), float(l.split()[2])) for l in open(sizes)}
comps = [(m.group(1), m.group(2), int(m.group(3)) / 1000, int(m.group(4)) / 1000) for m in re.finditer(r'-\s+(\S+)\s+(\S+).*?(?:PLACED|FIXED)\s+\(\s*(-?\d+)\s+(-?\d+)', c, re.S)]
def blk(x, y):
    for n, mm, cx, cy in comps:
        w, h = sz.get(mm, (1.5, 4))
        if cx <= x <= cx + w and cy <= y <= cy + h:
            return mm
    return 'top'
def netname(e):
    mx, my = (e.p1.x + e.p2.x) / 2, (e.p1.y + e.p2.y) / 2
    dx, dy = e.p2.x - e.p1.x, e.p2.y - e.p1.y; L_ = max((dx * dx + dy * dy) ** 0.5, 1)
    for s in (1, -1):
        p = db.DPoint((mx + s * dy / L_ * 20) * dbu, (my - s * dx / L_ * 20) * dbu)   # 20 dbu = 0.02 µm 안쪽
        n = l2n.probe_net(nw, p)
        if n is not None:
            return n.expanded_name() or f'(이름 없음 #{n.cluster_id})'
    return '(못 찾음)'
C = collections.Counter(); D = collections.defaultdict(list); diff = []
for e in ep.each():
    a, b = netname(e.first), netname(e.second)
    x, y = e.bbox().center().x * dbu, e.bbox().center().y * dbu
    k = (blk(x, y), 'same' if a == b else 'diff', a if a == b else ' / '.join(sorted((a, b))))
    C[k] += 1; d = e.distance() * dbu if hasattr(e, 'distance') else None; D[k].append(d)
    if a != b:
        diff.append(dict(x=round(x, 2), y=round(y, 2), blk=k[0], nets=[a, b], dist_um=d))
NC = collections.Counter(blk(e.bbox().center().x * dbu, e.bbox().center().y * dbu) for e in notch.each())
J = dict(n_isolated_pairs=ep.count(), n_notch=notch.count(), notch_by_blk=dict(NC),
         pairs=[dict(blk=k[0], kind=k[1], nets=k[2], n=v, dist_min_um=min(x for x in D[k] if x is not None) if any(x is not None for x in D[k]) else None) for k, v in sorted(C.items())],
         diff_pairs=diff[:200])
json.dump(J, open(out, 'w'), indent=1, ensure_ascii=False)
print('isolated', ep.count(), 'notch', notch.count())
for p in J['pairs']: print(p)
