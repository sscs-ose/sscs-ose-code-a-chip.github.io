"""SPICE 덱 → ngspice 덱 (회로는 그대로, 문법만). real_circuit/gen_sys_deck.py 의 to_ngspice() 와 같은 규칙을 덱 파일에 건다
(그 함수는 생성기 안에 있어 따로 부를 수 없음 → 같은 내용을 옮김):  .option 줄 버림, .lib/.include 따옴표 지움, ngspice 옵션 머리줄.
SPICE 기본 TNOM 25 ↔ ngspice 27 → tnom=25. 허용 오차는 RELTOL 인자 (기본 1e-6 = 이전 이식과 같음, SPICE 덱은 relv=reli=1e-7).
쓰임: python spice2ng.py <in.sp> <out.cir> [RELTOL] ["추가 .options 문자열"]
  예: … 1e-4 "abstol=1e-12 vntol=1e-6 rshunt=1e12"  (뒤에 준 값이 앞 값을 덮는다)"""
import sys
src, dst = sys.argv[1], sys.argv[2]
rt = sys.argv[3] if len(sys.argv) > 3 else '1e-6'
extra = sys.argv[4] if len(sys.argv) > 4 else ''
L = open(src).read().splitlines()
out = []
for l in L:
    if l.lower().startswith('.option'):
        continue
    if l.startswith('.lib ') or l.startswith('.include '):
        l = l.replace("'", '')
    out.append(l)
solver = 'klu' if 'sparse' not in extra else ''                     # "sparse" 를 주면 KLU 대신 ngspice 기본 Sparse 1.3
extra = extra.replace('sparse', '').strip()
hdr = [f".options reltol={rt} abstol=1e-15 vntol=1e-10 method=gear {solver}".rstrip(), ".options tnom=25 noacct"] + ([f".options {extra}"] if extra else [])
open(dst, 'w').write('\n'.join(out[:1] + hdr + out[1:]) + '\n')
print(dst, len(out), 'lines, reltol', rt, 'extra', extra or '-')
