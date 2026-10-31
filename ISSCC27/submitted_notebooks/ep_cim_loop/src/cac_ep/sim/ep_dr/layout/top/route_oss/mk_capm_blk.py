"""MiM cap (capm 89/44) 둘레 met3 배선 막기 — Pegasus CDR.capm.3b ("capm bottom plate (capm + 0.14) ↔ 다른 넷 met3 ≥ 1.2 µm") 를 TritonRoute 가 모름 (LEF 간격 0.3 µm 만 봄, 잡 721778 에서 C1_f met3 가 wu1 안을 지나 2 곳).
블록 자리는 모든 판에서 같으므로 merge 된 GDS 에서 capm 을 읽어 (core 좌표) 0.14 + 1.2 + 0.06 µm 키운 상자를 met3 BLOCKAGES 로 낸다.
쓰임: <klayout python> mk_capm_blk.py <chip_core.gds> → chip/capm_blk.txt (DEF BLOCKAGES 줄), 블록 met3 핀과 겹치는 것을 알림
"""
import sys
from pathlib import Path
import klayout.db as db

H = Path(__file__).resolve().parent
ly = db.Layout(); ly.read(sys.argv[1]); top = ly.cell('chip_core')
cap = db.Region(top.begin_shapes_rec(ly.layer(89, 44))); cap.merge()
blk = cap.sized(int(1.40 / ly.dbu)).merged()
rects = []
for p in blk.each():
    for b in db.Region(p).decompose_trapezoids_to_region().each() if not p.is_box() else [p]:
        bb = b.bbox(); rects.append((bb.left, bb.bottom, bb.right, bb.top))
lines = [f'- LAYER met3 RECT ( {a} {b} ) ( {c} {d} ) ;' for a, b, c, d in rects]
(H / 'chip' / 'capm_blk.txt').write_text('\n'.join(lines) + '\n')
pins = db.Region(top.begin_shapes_rec(ly.layer(70, 16)))
print(f'capm polygons {cap.count()}, blockage rects {len(rects)}, bbox {blk.bbox()}; met3 pin shapes inside {(pins & blk).count()}')
