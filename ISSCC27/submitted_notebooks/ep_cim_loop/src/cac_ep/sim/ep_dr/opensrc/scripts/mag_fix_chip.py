"""Magic 추출 netlist 에서 diff 저항 (res_generic_nd/pd) 의 3 번째 단자 (기판·n-well) 를 지운다 — CDL 쪽이 2 단자라서 (cdl2spice_chip.py ⑤).
쓰임: python mag_fix_chip.py <in.spice> <out.spice>"""
import re
import sys
src, dst = sys.argv[1:3]
import os
drop = os.environ.get('DROP_INST')
n = nd = 0
out = []
skip = False
for l in open(src):
    t = l.split()
    if skip and l.startswith('+'):
        continue
    skip = False
    if drop and t and re.fullmatch(drop, t[0]):
        nd += 1; skip = True; continue
    if t and t[0][0] in 'Xx' and len(t) >= 5 and re.fullmatch(r'sky130_fd_pr__res_generic_[np]d', t[4]):
        l = ' '.join(t[:3] + t[4:]) + '\n'; n += 1
    out.append(l)
open(dst, 'w').writelines(out)
print('res_generic_nd/pd 3 번째 단자 지움:', n, '/ 지운 인스턴스:', nd)
