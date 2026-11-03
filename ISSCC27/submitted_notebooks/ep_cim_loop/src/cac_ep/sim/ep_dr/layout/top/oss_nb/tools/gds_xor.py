"""두 GDS 의 도형이 같은지 (층마다 평탄화 XOR). 쓰임: python3 gds_xor.py <a.gds> <b.gds> [top] [--json out.json]
출력: 'XOR <top> same' 또는 다른 층과 XOR 넓이 (µm²). 이름표 (text) 는 따로 개수만 비교한다."""
import json
import sys

import klayout.db as db

args = [a for a in sys.argv[1:] if not a.startswith('--')]
jout = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
if jout in args:
    args.remove(jout)
fa, fb = args[0], args[1]


def load(f, top=None):
    ly = db.Layout()
    ly.read(f)
    c = ly.cell(top) if top else ly.top_cell()
    return ly, c


la, ca = load(fa, args[2] if len(args) > 2 else None)
lb, cb = load(fb, ca.name)
keys = sorted({(i.layer, i.datatype) for i in la.layer_infos()} | {(i.layer, i.datatype) for i in lb.layer_infos()})
diff = {}
texts = {}
for (l, d) in keys:
    ia, ib = la.find_layer(l, d), lb.find_layer(l, d)
    ra = db.Region(ca.begin_shapes_rec(ia)) if ia is not None else db.Region()
    rb = db.Region(cb.begin_shapes_rec(ib)) if ib is not None else db.Region()
    x = ra ^ rb
    if not x.is_empty():
        diff[f'{l}/{d}'] = round(x.area() * la.dbu ** 2, 4)
    ta = db.Texts(ca.begin_shapes_rec(ia)).count() if ia is not None else 0
    tb = db.Texts(cb.begin_shapes_rec(ib)).count() if ib is not None else 0
    if ta != tb:
        texts[f'{l}/{d}'] = [ta, tb]
res = dict(top=ca.name, same=not diff and not texts, xor_area_um2=diff, text_count_diff=texts,
           bbox_a=str(ca.dbbox()), bbox_b=str(cb.dbbox()))
print(f"XOR {ca.name}: {'same' if res['same'] else 'DIFF'}" + ('' if res['same'] else f" layers {diff} labels {texts}"))
if jout:
    json.dump(res, open(jout, 'w'), indent=1)
