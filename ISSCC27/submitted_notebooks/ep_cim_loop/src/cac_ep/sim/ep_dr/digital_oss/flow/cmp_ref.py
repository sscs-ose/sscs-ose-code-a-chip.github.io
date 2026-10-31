"""새 블록 (OpenROAD DEF + CDL) 이 저장된 블록과 외곽·핀 이름·핀 도형 (층·사각형)·CDL 머리줄이 같은지 본다.
기준 = 칩 배선이 쓰는 LEF (layout/top/route_oss/chip/lef/<blk>.lef, place/mk_lef.py 가 저장된 GDS·DEF 에서 만든 것) 의 SIZE·PIN 과
       칩 netlist 가 쓰는 블록 CDL (layout/top/net/lib/<blk>.cdl) 의 .SUBCKT 줄. OBS 는 비교하지 않음 (블록 안 금속이라 다른 것이 정상).
쓰임: python3 cmp_ref.py <new.def> <ref.lef> <new.cdl> <ref.cdl> <out.json>"""
import json
import re
import sys

ndef, rlef, ncdl, rcdl, out = sys.argv[1:6]
ORI = {'N': lambda x, y: (x, y), 'S': lambda x, y: (-x, -y), 'W': lambda x, y: (-y, x), 'E': lambda x, y: (y, -x),
       'FN': lambda x, y: (-x, y), 'FS': lambda x, y: (x, -y), 'FW': lambda x, y: (y, x), 'FE': lambda x, y: (-y, -x)}


def read_def(p):
    t = open(p).read()
    die = [int(v) for v in re.search(r'DIEAREA \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)', t).groups()]
    pins = {}
    sec = t[t.index('\nPINS '):t.index('END PINS')]
    for ent in re.split(r'\n\s*- ', sec)[1:]:
        nm = ent.split()[0]
        lay = re.search(r'LAYER (\S+) \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)', ent)
        pl = re.search(r'(?:FIXED|PLACED) \( (-?\d+) (-?\d+) \) (\w+)', ent)
        x1, y1, x2, y2 = map(int, lay.groups()[1:]); px, py = int(pl.group(1)), int(pl.group(2)); f = ORI[pl.group(3)]
        c = [f(x1, y1), f(x2, y2)]
        pins.setdefault(nm, set()).add((lay.group(1), px + min(a for a, _ in c), py + min(b for _, b in c), px + max(a for a, _ in c), py + max(b for _, b in c)))
    ss = t[t.index('\nSPECIALNETS'):t.index('END SPECIALNETS')]
    for ent in re.split(r'\n\s*- ', ss)[1:]:
        nm = ent.split()[0]
        S = pins[nm] = set()          # place/mk_lef.py 와 같이: special net 의 핀 도형 = SPECIALNETS 도형 (DEF PINS 의 사각형 대신)
        for m in re.finditer(r'RECT (\S+) \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)', ent):
            S.add((m.group(1), *map(int, m.groups()[1:])))
        for m in re.finditer(r'(?:ROUTED|NEW) (\S+) (\d+) \+ SHAPE \w+ \( (-?\d+) (-?\d+) \) \( (\*|-?\d+) (\*|-?\d+) \)', ent):
            lay, w, x1, y1 = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
            x2 = x1 if m.group(5) == '*' else int(m.group(5)); y2 = y1 if m.group(6) == '*' else int(m.group(6))
            if w == 0:
                continue
            h = w // 2
            S.add((lay, min(x1, x2) - (h if x1 == x2 else 0), min(y1, y2) - (h if y1 == y2 else 0),
                   max(x1, x2) + (h if x1 == x2 else 0), max(y1, y2) + (h if y1 == y2 else 0)))
    return die, pins


def read_lef(p):
    t = open(p).read()
    size = [round(float(v) * 1000) for v in re.search(r'SIZE ([\d.]+) BY ([\d.]+)', t).groups()]
    pins = {}
    for m in re.finditer(r'\n  PIN (\S+)\n(.*?)\n  END \1', t, re.S):
        S = pins.setdefault(m.group(1), set()); lay = None
        for l in m.group(2).splitlines():
            l = l.strip()
            if l.startswith('LAYER'):
                lay = l.split()[1]
            elif l.startswith('RECT'):
                S.add((lay, *[round(float(v) * 1000) for v in l.split()[1:5]]))
    return size, pins


die, npins = read_def(ndef)
size, rpins = read_lef(rlef)
res = dict(size_new=[die[2] - die[0], die[3] - die[1]], size_ref=size)
res['size_same'] = res['size_new'] == size and die[:2] == [0, 0]
res['pin_names_same'] = set(npins) == set(rpins)
res['only_new'] = sorted(set(npins) - set(rpins)); res['only_ref'] = sorted(set(rpins) - set(npins))
diff = {p: dict(new=sorted(npins[p] - rpins[p])[:4], ref=sorted(rpins[p] - npins[p])[:4], n_new=len(npins[p]), n_ref=len(rpins[p]))
        for p in set(npins) & set(rpins) if npins[p] != rpins[p]}
res['pins_compared'] = len(set(npins) & set(rpins)); res['pins_shape_diff'] = len(diff); res['diff'] = dict(sorted(diff.items())[:10])
res['signal_pins_same'] = not [p for p in diff if p not in ('VDD', 'VSS')]
res['power_pins_same'] = not [p for p in diff if p in ('VDD', 'VSS')]
hd = lambda f: next(l.split()[1:] for l in open(f) if l.upper().startswith('.SUBCKT'))
res['cdl_header_same'] = hd(ncdl) == hd(rcdl)
res['identical'] = all(res[k] for k in ('size_same', 'pin_names_same', 'signal_pins_same', 'power_pins_same', 'cdl_header_same'))
json.dump(res, open(out, 'w'), indent=1)
print('CMP_REF', 'identical' if res['identical'] else 'DIFFERENT', {k: res[k] for k in ('size_same', 'pin_names_same', 'pins_compared', 'pins_shape_diff', 'signal_pins_same', 'power_pins_same', 'cdl_header_same')})
