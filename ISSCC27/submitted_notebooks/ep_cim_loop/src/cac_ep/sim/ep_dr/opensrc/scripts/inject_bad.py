"""DRC 덱이 실제로 잡는지 확인용: 블록 GDS 에 일부러 위반 3 개 (met1 폭 0.1 µm, met2 간격 0.05 µm, poly 폭 0.1 µm) 를 더한 사본.
쓰임: python inject_bad.py <in.gds> <top> <out.gds>"""
import sys
import klayout.db as db
ly = db.Layout(); ly.read(sys.argv[1]); t = ly.cell(sys.argv[2]); bb = t.bbox()
x, y = bb.right + 2000, bb.bottom
t.shapes(ly.layer(68, 20)).insert(db.Box(x, y, x + 100, y + 2000))                 # met1.1 (min 0.14)
t.shapes(ly.layer(69, 20)).insert(db.Box(x + 1000, y, x + 1500, y + 2000))
t.shapes(ly.layer(69, 20)).insert(db.Box(x + 1550, y, x + 2050, y + 2000))         # met2.2 (min 0.14)
t.shapes(ly.layer(66, 20)).insert(db.Box(x + 3000, y, x + 3100, y + 2000))         # poly.1a (min 0.15)
ly.write(sys.argv[3])
