"""IO ring rail 연결 검사 (10/26, tape-out 준비, 사용자 "나중에 tape-out 내는 것도 고려하고 있어. 그러니 최적화 해봐봐").
IO 셀마다 met4·met5 에 rail 이름표 (71/5, 72/5) 가 있다. met3–met5 + via3·via4 를 flat 으로 이어 net 을 뽑고,
이름표 자리마다 net 을 찍어 rail 이름별 net 개수를 센다. 1 개 = 한 바퀴 이어짐, 2 개 이상 = 끊김, 한 net 에 두 이름 = 단락.
쓰임 (Olympus): QT_QPA_PLATFORM=offscreen ~/opt/kl312/bin/python rail_check.py out/chip_v2.gds ep_chip_v2
"""
import collections
import sys

import klayout.db as db

gds, top = sys.argv[1:3]
RAILS = {'AMUXBUS_A', 'AMUXBUS_B', 'VCCD', 'VCCHIB', 'VDDA', 'VDDIO', 'VDDIO_Q', 'VSSA', 'VSSD', 'VSSIO', 'VSSIO_Q', 'VSWITCH'}
ly = db.Layout(); ly.read(gds); T = ly.cell(top)
l2n = db.LayoutToNetlist(db.RecursiveShapeIterator(ly, T, []))   # flat
L = {k: l2n.make_layer(ly.layer(*v), k) for k, v in dict(m3=(70, 20), v3=(70, 44), m4=(71, 20), v4=(71, 44), m5=(72, 20)).items()}
for a, v, b in (('m3', 'v3', 'm4'), ('m4', 'v4', 'm5')):
    l2n.connect(L[a]); l2n.connect(L[v]); l2n.connect(L[a], L[v]); l2n.connect(L[v], L[b])
l2n.connect(L['m5'])
l2n.extract_netlist()

hits, n_lab = collections.defaultdict(set), collections.Counter()
for lay, met in (((71, 5), 'm4'), ((72, 5), 'm5')):
    it = db.RecursiveShapeIterator(ly, T, ly.layer(*lay)); it.shape_flags = db.Shapes.STexts
    while not it.at_end():
        t = it.shape().text.transformed(it.trans())
        if t.string in RAILS and it.cell().cell_index() != T.cell_index():   # top 의 이름표 (core 전원 ring) 는 IO rail 이 아님
            n_lab[t.string] += 1
            net = l2n.probe_net(L[met], db.DPoint(t.x * ly.dbu, t.y * ly.dbu))
            hits[t.string].add(net.cluster_id if net else None)
        it.next()
by_net = collections.defaultdict(set)
for r, ids in hits.items():
    for i in ids:
        by_net[i].add(r)
ok = True
for r in sorted(RAILS):
    ids = hits.get(r, set()); good = len(ids) == 1 and None not in ids
    ok &= good
    print(f'{r:10s} net {len(ids):3d}  이름표 {n_lab[r]:4d}  {"이어짐" if good else "끊김 / 금속 없음"}')
INTENDED = [{'VCCD', 'VCCHIB'}, {'VDDIO', 'VDDIO_Q', 'VSWITCH'}, {'VSSIO', 'VSSIO_Q'}]   # 이음 slice (VCCHIB = VCCD, VSWITCH = VDDIO), _Q 는 IO 패드 안에서 묶임
shorts = {i: rs for i, rs in by_net.items() if len(rs) > 1}
for i, rs in shorts.items():
    print('묶임:', sorted(rs), '(의도)' if rs in INTENDED else '(의도 밖 단락)')
bad = [rs for rs in shorts.values() if rs not in INTENDED]
print('결과:', '모든 rail 한 바퀴 이어짐, 의도 밖 단락 없음' if ok and not bad else '문제 있음')
