"""LVS 가 틀린 것을 실제로 잡는지 보는 음성 대조 3 개를 만든다 (원본은 그대로, 사본만 <outdir> 에).
  ② arr_w3_4x4_swap.cdl : 셀 하나 (X_c2_r1) 의 행 (TE) 과 WL 을 바꾼 회로도
  ③ arr_w3_4x4_rflip.cdl : RRAM 방향을 뒤집은 회로도 (R0 D TE) — Netgen 이 RRAM 핀을 바꿔 맞추지 않는지
쓰임: python neg_controls.py <blocks 폴더> <outdir>"""
import sys
from pathlib import Path
import klayout.db as db

B, O = Path(sys.argv[1]), Path(sys.argv[2]); O.mkdir(parents=True, exist_ok=True)
ly = db.Layout(); ly.read(str(B / 'hvl_test.gds')); t = ly.cell('hvl_test')
sh = t.shapes(ly.layer(68, 20)); n = sh.size(); sh.clear()
ly.write(str(O / 'hvl_test_norail.gds')); print('hvl_test_norail: removed', n, 'top-level met1 boxes')
s = (B / 'arr_w3_4x4.cdl').read_text()
a = 'X_c2_r1 row_1 wl_1 col_2 vss c1t1r_w3'; assert a in s
(O / 'arr_w3_4x4_swap.cdl').write_text(s.replace(a, 'X_c2_r1 wl_1 row_1 col_2 vss c1t1r_w3')); print('arr_w3_4x4_swap.cdl written')
a = 'R0 TE D $[reram]'; assert a in s
(O / 'arr_w3_4x4_rflip.cdl').write_text(s.replace(a, 'R0 D TE $[reram]')); print('arr_w3_4x4_rflip.cdl written')
