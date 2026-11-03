"""hvl liberty 에서 쓸 셀만 남긴 사본 (Yosys dfflibmap·abc 가 고를 셀 = 상용 판 DR_OK_CELLS 와 같은 27 개).
쓰임: python3 mk_lib.py <in.lib> <out.lib> <cells.txt>"""
import re
import sys
src, dst, keepf = sys.argv[1:4]
keep = {l.split()[0] for l in open(keepf) if l.strip() and not l.startswith('#')}
t = open(src).read()
out, i, n = [], 0, 0
for m in re.finditer(r'\n\s*cell\s*\(\s*"?([A-Za-z0-9_]+)"?\s*\)\s*\{', t):
    if m.start() < i:
        continue
    j, depth = m.end(), 1                       # 중괄호 짝 찾기
    while depth:
        c = t[j]; depth += (c == '{') - (c == '}'); j += 1
    out.append(t[i:m.start()])
    if m.group(1) in keep:
        out.append(t[m.start():j]); n += 1
    i = j
out.append(t[i:])
open(dst, 'w').write(''.join(out))
print('kept cells', n, 'of', len(keep))
