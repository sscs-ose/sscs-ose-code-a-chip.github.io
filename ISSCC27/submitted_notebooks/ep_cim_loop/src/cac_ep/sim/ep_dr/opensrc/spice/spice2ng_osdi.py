"""SPICE 덱 (RRAM = `.hdl` Verilog-A) → ngspice 덱 (RRAM = OpenVAF OSDI). 회로·값은 그대로, 문법만:
  .option 줄 버림, .lib/.include 따옴표 지움, `.hdl` 줄 버림 (OSDI 는 .spiceinit 의 `osdi <파일>` 로 읽음),
  `X… a b sky130_fd_pr__reram_cell p=v …` → `N… a b rrmK` + `.model rrmK sky130_fd_pr_reram__reram_cell p=v …`
  (Tfilament_0·t_step 은 모형 parameter 라 값 묶음마다 .model 하나, `t_step=tstep` 처럼 .param 이름이면 숫자로 풂),
  `G… CUR='식'` → `B… I={식}` (gen_sys_deck.py to_ngspice 와 같음), `.meas` 의 v(a,b) → v(a)-v(b), 큰 덱은 .meas 가 읽는 것만 `.save`, 머리에 ngspice 옵션 (tnom=25 = SPICE 기본).
쓰임: python spice2ng_osdi.py <in.sp> <out.cir> [RELTOL] ["추가 .options"]"""
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
rt = sys.argv[3] if len(sys.argv) > 3 else '1e-4'
extra = sys.argv[4] if len(sys.argv) > 4 else ''
L = open(src).read().splitlines()
SI = {'f': 1e-15, 'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'm': 1e-3, 'k': 1e3}
params = {}
for l in L:
    for k, v in re.findall(r'(\w+)\s*=\s*([0-9.eE+-]+[fpnumk]?)\b', l) if l.lower().startswith('.param') else []:
        params[k.lower()] = v


def num(v):
    v = params.get(v.lower(), v)
    m = re.fullmatch(r'([0-9.eE+-]+)([fpnumk]?)', v)
    return float(m.group(1)) * SI.get(m.group(2), 1.0)


models, out, n_rr = {}, [], 0
for l in L:
    s = l.strip()
    low = s.lower()
    if low.startswith('.option') or low.startswith('.hdl'):
        continue
    if low.startswith('.lib ') or low.startswith('.include '):
        l = l.replace("'", '').replace('"', '')
    m = re.match(r'^X(\S+)\s+(\S+)\s+(\S+)\s+sky130_fd_pr_reram__reram_cell\b(.*)$', s, re.I)
    if m:
        kv = tuple(sorted((k.lower(), f'{num(v):.6e}') for k, v in re.findall(r'(\w+)\s*=\s*(\S+)', m.group(4))))
        if kv not in models:
            models[kv] = f'rrm{len(models)}'
        l = f"N{m.group(1)} {m.group(2)} {m.group(3)} {models[kv]}"
        n_rr += 1
    if low.startswith('.meas'):                                       # ngspice .meas 는 v(a,b) 를 못 읽음 → v(a)-v(b)
        l = re.sub(r"\b(find|max|min|avg)\s+v\((\w+),(\w+)\)", r"\1 par('v(\2)-v(\3)')", l, flags=re.I)
        l = re.sub(r"v\((\w+),(\w+)\)", r"(v(\1)-v(\2))", l)
    m = re.match(r"^G(\S+) (\S+) (\S+) CUR='(.*)'$", s)
    if m:
        l = f"B{m.group(1)} {m.group(2)} {m.group(3)} I={{{m.group(4)}}}"
    out.append(l)
# ngspice 는 .save 가 없으면 모든 node 를 메모리에 둔다 (chip_write3: 69,429 node × 8 만 단계 = 42 GB, 잡 721341) → .meas 가 읽는 것만 저장
sv = set()
for l in out:
    if l.lower().startswith('.meas'):
        sv |= {f'v({n})' for n in re.findall(r'\bv\((\w+)\)', l, re.I)} | {f'i({n})' for n in re.findall(r'\bi\((\w+)\)', l, re.I)}
hdr = [f".options reltol={rt} abstol=1e-15 vntol=1e-10 method=gear klu", ".options tnom=25 noacct"] + ([f".options {extra}"] if extra else [])
if sv and len(out) > 1000:
    hdr.append('.save ' + ' '.join(sorted(sv)))
hdr += [f".model {nm} sky130_fd_pr_reram__reram_cell " + ' '.join(f'{k}={v}' for k, v in kv) for kv, nm in models.items()]
open(dst, 'w').write('\n'.join(out[:1] + hdr + out[1:]) + '\n')
print(dst, len(out), 'lines, RRAM', n_rr, 'instances,', len(models), 'models')
