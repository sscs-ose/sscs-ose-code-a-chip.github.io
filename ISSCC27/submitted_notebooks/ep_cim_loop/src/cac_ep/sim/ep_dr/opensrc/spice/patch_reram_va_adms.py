"""SkyWater ReRAM Verilog-A (sky130_fd_pr_reram__reram_cell.va) 를 ADMS (Xyce buildxyceplugin) 가 읽게 문법만 고친 사본.
ADMS 2.3.7 은 선언과 동시에 값을 주는 `real a0 = 0.25e-9;` 를 못 읽는다 (lexical error, line 54) → 선언과 대입을 나눈다.
식·상수는 그대로. 주의: 이 모형은 $abstime 차이로 filament 두께를 직접 적분하는 (내부 상태를 변수에 들고 가는) 방식이라,
문법이 통과해도 Xyce 에서 시간 단계 사이에 그 값이 유지되는지는 따로 확인해야 한다.
쓰임: python patch_reram_va_adms.py <in.va> <out.va>"""
import re
import sys

s = open(sys.argv[1]).read()
inits = []


def strip_init(m):
    inits.append((m.group(1), m.group(2)))
    return f"real {m.group(1)};"


body, n1 = re.subn(r"^\s*real\s+(a0)\s*=\s*([^;]+);", lambda m: '    ' + strip_init(m), s, flags=re.M)
body, n2 = re.subn(r"real\s+p\s*=\s*10\s*;", "real p;", body)          # soft_minmax 안의 쓰지 않는 변수
assert n1 == 1 and n2 == 1, (n1, n2)
a = "    analog begin\n"
assert body.count(a) == 1
body = body.replace(a, a + ''.join(f"        {k} = {v};\n" for k, v in inits))
open(sys.argv[2], 'w').write(body)
print('patched', inits)
