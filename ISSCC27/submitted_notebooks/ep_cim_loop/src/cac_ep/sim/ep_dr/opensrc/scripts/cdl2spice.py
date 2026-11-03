"""Pegasus 용 CDL → Netgen 용 SPICE (같은 회로, 표기만 바꿈).
바꾸는 것:
  ② w·l 의 단위 (1.5u, 0.42u) → µm 숫자 (Magic ext2spice 는 µm 숫자로 씀). 나머지 속성 (sa·sb·area·perim·mult …) 은 버림 (netgen 도 무시)
  ③ CDL 저항 `R0 TE D $[reram]` → `XR0 TE D sky130_rram` (RRAM 은 black box 2 단자 소자로 비교) — Magic 쪽 tech 사본도 같은 이름으로 뽑는다
  ④ `+` 이어 쓰기 합치기, `*` 주석·`*.PININFO` 버림, X 줄의 `/` 지움, `.INCLUDE` 는 풀어 넣음
쓰임: python cdl2spice.py <in.cdl> <out.spice>
"""
import re
import sys

SI = {'f': 1e-15, 'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'm': 1e-3, '': 1.0}
RRAM = 'sky130_rram'


def um(v):
    """'1.5u' → '1.5' (µm). 단위 없는 값은 이미 µm 로 본다 (hvl CDL 원본은 단위 없음 = µm 뜻)."""
    m = re.fullmatch(r'([-+0-9.eE]+)([a-zA-Z]*)', v)
    num, suf = float(m.group(1)), m.group(2).lower()
    if suf in ('', 'um'):
        return f'{num:g}'
    return f'{num * SI[suf[0]] / 1e-6:g}'


def lines(path):
    out = []
    for raw in open(path):
        s = raw.rstrip('\n')
        if not s.strip() or s.lstrip().startswith('*'):
            continue
        if s.lstrip().upper().startswith('.INCLUDE'):
            inc = s.split(None, 1)[1].strip().strip('"\'')
            out += lines(inc)
            continue
        if s.lstrip().startswith('+') and out:
            out[-1] += ' ' + s.lstrip()[1:]
        else:
            out.append(s.strip())
    return out


def conv(s):
    t = s.split()
    k = t[0][0].upper()
    if k == 'M':                                            # Mname d g s b model params
        name, nets, model, par = t[0], t[1:5], t[5], t[6:]
        if not model.startswith('sky130_'):
            model = 'sky130_fd_pr__' + model
        kv = dict(p.split('=', 1) for p in par if '=' in p)
        keep = [f"{p}={um(kv[p])}" for p in ('w', 'l') if p in kv]
        if kv.get('m', '1') not in ('1', '1.0'):
            keep.append(f"m={kv['m']}")
        return ' '.join(['X' + name, *nets, model, *keep])
    if k == 'R' and any(x.startswith('$[') for x in t):     # CDL 모형 저항
        model = [x for x in t if x.startswith('$[')][0][2:-1]
        if model == 'reram':
            return f"X{t[0]} {t[1]} {t[2]} {RRAM}"
        return s
    if k == 'X':
        return ' '.join(x for x in t if x != '/')
    return s


def main(src, dst):
    out = []
    for s in lines(src):
        c = conv(s)
        out.append(c)
    # sky130_rram 은 정의하지 않는다: nfet 처럼 양쪽 다 정의 없는 소자 (netgen 이 placeholder 를 만들고 핀 순서로 비교 — TE, BE 순서 고정)
    open(dst, 'w').write('\n'.join(out) + '\n')


if __name__ == '__main__':
    main(*sys.argv[1:3])
