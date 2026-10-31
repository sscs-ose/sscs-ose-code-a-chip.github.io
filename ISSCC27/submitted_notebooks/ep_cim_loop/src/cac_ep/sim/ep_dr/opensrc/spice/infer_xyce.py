"""판독 덱 (real_circuit/infer_deck.py, SPICE `.dc … sweep data=d` + `.measure`) → Xyce 덱 (10/30, 사용자 "test 1,000 장을 Xyce 로, best 1 개").
Xyce 의 DC `.meas` 는 sweep 전체에 값 하나라, 대신 `.DC DATA=d` + `.PRINT DC` 로 표본마다 출력 행 전압을 쓴다.
  1) spice2xyce.py 로 바꾼 덱을 받아, 2) `.measure` 줄을 빼고, 3) SPICE 꼴 `.data d / + 이름… / + 값…` 을 Xyce 꼴 `.DATA d 이름… / 값… / .ENDDATA` 로,
  4) `.dc Vdum 0 0 1 sweep data=d` → `.DC DATA=d`, 5) 쓸기 변수 s0… 를 `.param` 으로 선언, 6) `.PRINT DC FORMAT=CSV` 로 출력 행 (y) 전압.
쓰임: python infer_xyce.py deck <spice2xyce 결과 .cir> <out.cir> <출력 행 node 이름…>
      python infer_xyce.py compare <Xyce .cir.csv> <ref: infer_deck 의 weights npz> <key> <n>   (Python solver 와 대조, ep_dr 를 sys.path 에)"""
import re
import sys

if sys.argv[1] == 'deck':
    src, dst, ynodes = sys.argv[2], sys.argv[3], sys.argv[4:]
    L = open(src).read().splitlines()
    out, names, rows, i = [], [], [], 0
    while i < len(L):
        l = L[i]
        if re.match(r'\s*\.meas', l, re.I):
            i += 1; continue
        if re.match(r'\s*\.data\s+d\s*$', l, re.I):
            i += 1; names = L[i][1:].split(); i += 1
            while not re.match(r'\s*\.enddata', L[i], re.I):
                rows.append(L[i][1:].split()); i += 1
            i += 1; continue
        if re.match(r'\s*\.dc\s', l, re.I):
            i += 1; continue
        if re.match(r'\s*\.end\s*$', l, re.I):
            i += 1; continue
        out.append(l); i += 1
    out += ['.param ' + ' '.join(f'{n}=-1' for n in names)]
    out += ['.DATA d ' + ' '.join(names)] + ['+ ' + ' '.join(r) for r in rows] + ['.ENDDATA', '.DC DATA=d']
    out += ['.PRINT DC FORMAT=CSV ' + ' '.join(f'v({n})' for n in ynodes), '.END']
    open(dst, 'w').write('\n'.join(out) + '\n')
    print(dst, 'samples', len(rows), 'params', len(names))
