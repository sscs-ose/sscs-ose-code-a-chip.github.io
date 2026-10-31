"""route/ 공용 도구: LEF 읽기, 배치 변환, 구조 Verilog 읽기, DEF 쓰기, 간단한 간격 검사.
좌표는 모두 nm 정수 (DEF UNITS 1000, 제조 격자 5 nm). 표준 라이브러리만 쓴다 (Olympus python3·로컬 둘 다).
"""
import re
from collections import defaultdict

GRID = 5          # nm
LAYERS = ['li1', 'met1', 'met2', 'met3', 'met4', 'met5']
CUTS = {('met1', 'met2'): 'via', ('met2', 'met3'): 'via2', ('met3', 'met4'): 'via3', ('met4', 'met5'): 'via4'}
# SKY130 규칙 (nm): 최소 폭·간격 (넓은 선 간격은 따로), via cut·간격·아래/위 enclosure (작은 값, 한 쌍 변의 큰 값)
MINW = {'met1': 140, 'met2': 140, 'met3': 300, 'met4': 300, 'met5': 1600}
MINS = {'met1': 140, 'met2': 140, 'met3': 300, 'met4': 300, 'met5': 1600}
WIDE_S = {'met1': (3000, 280), 'met2': (3000, 280), 'met3': (3000, 400), 'met4': (3000, 400), 'met5': (10 ** 9, 1600)}
VIA = {  # cut, cut 간격, 아래 금속 enclosure (모든 변, 한 쌍 변), 위 금속 enclosure (모든 변, 한 쌍 변)
    'via': dict(lo='met1', hi='met2', cut=150, sp=170, elo=(55, 85), ehi=(55, 85)),
    'via2': dict(lo='met2', hi='met3', cut=200, sp=200, elo=(40, 85), ehi=(65, 65)),
    'via3': dict(lo='met3', hi='met4', cut=200, sp=200, elo=(60, 90), ehi=(65, 65)),
    'via4': dict(lo='met4', hi='met5', cut=800, sp=800, elo=(190, 190), ehi=(310, 310)),
}


def g(v):
    """µm → nm, 5 nm 격자로 반올림."""
    return int(round(v * 1000.0 / GRID)) * GRID


def snap(n):
    return int(round(n / GRID)) * GRID


# ───────────────────────── LEF ─────────────────────────
class Macro:
    def __init__(self, name):
        self.name = name
        self.cls = ''
        self.size = (0, 0)       # nm
        self.origin = (0, 0)     # nm (LEF ORIGIN)
        self.pins = {}           # 이름 → [(layer, (x1,y1,x2,y2))]  (LEF 좌표 + ORIGIN = bbox 왼쪽 아래 기준)
        self.use = {}            # 이름 → SIGNAL/POWER/GROUND
        self.dir = {}
        self.obs = []            # [(layer, rect)]


def parse_lef(path, macros=None):
    macros = {} if macros is None else macros
    tok = re.sub(r'#[^\n]*', '', open(path).read()).replace(';', ' ; ').split()
    i, n = 0, len(tok)
    cur = None
    while i < n:
        t = tok[i]
        if t == 'MACRO':
            cur = Macro(tok[i + 1]); macros[cur.name] = cur; i += 2
            continue
        if cur is None:
            i += 1; continue
        if t == 'END' and i + 1 < n and tok[i + 1] == cur.name:
            ox, oy = cur.origin
            for p in cur.pins:
                cur.pins[p] = [(l, (r[0] + ox, r[1] + oy, r[2] + ox, r[3] + oy)) for l, r in cur.pins[p]]
            cur.obs = [(l, (r[0] + ox, r[1] + oy, r[2] + ox, r[3] + oy)) for l, r in cur.obs]
            cur = None; i += 2; continue
        if t == 'CLASS':
            cur.cls = tok[i + 1]; i += 2; continue
        if t == 'ORIGIN':
            cur.origin = (g(float(tok[i + 1])), g(float(tok[i + 2]))); i += 3; continue
        if t == 'SIZE':
            cur.size = (g(float(tok[i + 1])), g(float(tok[i + 3]))); i += 4; continue
        if t == 'PIN':
            pn = tok[i + 1]; i += 2
            cur.pins.setdefault(pn, []); cur.use[pn] = 'SIGNAL'
            layer = None
            while not (tok[i] == 'END' and tok[i + 1] == pn):
                if tok[i] == 'USE':
                    cur.use[pn] = tok[i + 1]; i += 2; continue
                if tok[i] == 'DIRECTION':
                    cur.dir[pn] = tok[i + 1]; i += 2; continue
                if tok[i] == 'LAYER':
                    layer = tok[i + 1]; i += 2; continue
                if tok[i] == 'RECT':
                    j = i + 1
                    if tok[j] == 'MASK':
                        j += 2
                    x1, y1, x2, y2 = (g(float(tok[j + k])) for k in range(4))
                    cur.pins[pn].append((layer, (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))); i = j + 4; continue
                if tok[i] == 'POLYGON':
                    j = i + 1; xs = []; ys = []
                    while tok[j] != ';':
                        xs.append(g(float(tok[j]))); ys.append(g(float(tok[j + 1]))); j += 2
                    cur.pins[pn].append((layer, (min(xs), min(ys), max(xs), max(ys)))); i = j; continue
                i += 1
            i += 2; continue
        if t == 'OBS':
            i += 1; layer = None
            while tok[i] != 'END':
                if tok[i] == 'LAYER':
                    layer = tok[i + 1]; i += 2; continue
                if tok[i] == 'RECT':
                    j = i + 1
                    if tok[j] == 'MASK':
                        j += 2
                    x1, y1, x2, y2 = (g(float(tok[j + k])) for k in range(4))
                    cur.obs.append((layer, (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))); i = j + 4; continue
                if tok[i] == 'POLYGON':
                    j = i + 1; xs = []; ys = []
                    while tok[j] != ';':
                        xs.append(g(float(tok[j]))); ys.append(g(float(tok[j + 1]))); j += 2
                    cur.obs.append((layer, (min(xs), min(ys), max(xs), max(ys)))); i = j; continue
                i += 1
            i += 1; continue
        i += 1
    return macros


# ───────────────────────── 배치 변환 ─────────────────────────
def xform_pt(x, y, w, h, orient):
    """bbox 왼쪽 아래 기준 좌표 (x, y) → 방향 적용 뒤 bbox 왼쪽 아래 기준 (DEF 규칙)."""
    o = orient.upper()
    if o == 'N':
        return x, y
    if o == 'S':
        return w - x, h - y
    if o == 'FN':
        return w - x, y
    if o == 'FS':
        return x, h - y
    if o == 'W':
        return h - y, x
    if o == 'E':
        return y, w - x
    if o == 'FW':
        return y, x
    if o == 'FE':
        return h - y, w - x
    raise ValueError(orient)


def placed_size(m, orient):
    w, h = m.size
    return (h, w) if orient.upper() in ('W', 'E', 'FW', 'FE') else (w, h)


def xform_rect(r, m, orient, loc):
    w, h = m.size
    ax, ay = xform_pt(r[0], r[1], w, h, orient)
    bx, by = xform_pt(r[2], r[3], w, h, orient)
    return (loc[0] + min(ax, bx), loc[1] + min(ay, by), loc[0] + max(ax, bx), loc[1] + max(ay, by))


class Inst:
    def __init__(self, name, macro, loc, orient):
        self.name, self.m, self.loc, self.orient = name, macro, loc, orient.upper()
        pw, ph = placed_size(macro, orient)
        self.bbox = (loc[0], loc[1], loc[0] + pw, loc[1] + ph)

    def pin_shapes(self, pin):
        return [(l, xform_rect(r, self.m, self.orient, self.loc)) for l, r in self.m.pins.get(pin, [])]

    def obs_shapes(self):
        return [(l, xform_rect(r, self.m, self.orient, self.loc)) for l, r in self.m.obs]


# ───────────────────────── 구조 Verilog ─────────────────────────
def _strip_comments(s):
    s = re.sub(r'/\*.*?\*/', ' ', s, flags=re.S)
    return re.sub(r'//[^\n]*', ' ', s)


def _ident(s):
    s = s.strip()
    if s.startswith('\\'):
        return s[1:].split()[0]
    return s


def _expand(expr, buses):
    """연결 식 → 비트 넷 이름 목록 (MSB 먼저). buses: 넷 이름 → (msb, lsb)."""
    e = expr.strip()
    if not e:
        return []
    if e.startswith('{') and e.endswith('}'):
        out = []
        depth = 0; cur = ''
        for ch in e[1:-1]:
            if ch == '{':
                depth += 1
            if ch == '}':
                depth -= 1
            if ch == ',' and depth == 0:
                out += _expand(cur, buses); cur = ''
            else:
                cur += ch
        out += _expand(cur, buses)
        return out
    m = re.match(r"^(\d+)'([bhdBHD])([0-9a-fA-FxXzZ_]+)$", e)
    if m:
        w = int(m.group(1)); v = int(m.group(3).replace('_', ''), {'b': 2, 'h': 16, 'd': 10}[m.group(2).lower()])
        return [f"1'b{(v >> k) & 1}" for k in range(w - 1, -1, -1)]
    if e.startswith('\\'):
        nm = e[1:].split()[0]; rest = e[1:][len(nm):].strip()
    else:
        mm = re.match(r'^([A-Za-z_][\w$]*)(.*)$', e)
        nm, rest = mm.group(1), mm.group(2).strip()
    m = re.match(r'^\[\s*(\d+)\s*:\s*(\d+)\s*\]$', rest)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        rng = range(a, b - 1, -1) if a >= b else range(a, b + 1)
        return [f'{nm}[{k}]' for k in rng]
    m = re.match(r'^\[\s*(\d+)\s*\]$', rest)
    if m:
        return [f'{nm}[{m.group(1)}]']
    if nm in buses:
        a, b = buses[nm]
        rng = range(a, b - 1, -1) if a >= b else range(a, b + 1)
        return [f'{nm}[{k}]' for k in rng]
    return [nm]


def parse_verilog(path, macros, top=None):
    """구조 Verilog → (top 이름, 포트 [(이름, 방향)], 인스턴스 {inst: (cell, {lefpin: net})}).
    블록 포트 폭은 LEF 핀 이름 (row[0] …) 에서 얻는다 (내림차순 [N-1:0] 가정)."""
    s = _strip_comments(open(path).read())
    mods = re.findall(r'\bmodule\s+(\\?\S+?)\s*(?:#\s*\(.*?\))?\s*\((.*?)\)\s*;(.*?)\bendmodule', s, flags=re.S)
    if not mods:
        raise ValueError('no module')
    if top is None:
        name, hdr, body = mods[-1]
    else:
        name, hdr, body = [m for m in mods if _ident(m[0]) == top][0]
    buses = {}; ports = []
    for kind, rng, names in re.findall(r'\b(input|output|inout|wire|supply0|supply1|tri)\b\s*(?:wire\s*)?(\[\s*\d+\s*:\s*\d+\s*\])?\s*([^;]*);', body):
        for nm in names.split(','):
            nm = _ident(nm)
            if not nm:
                continue
            if rng:
                a, b = map(int, re.findall(r'\d+', rng))
                buses[nm] = (a, b)
            if kind in ('input', 'output', 'inout'):
                ports.append((nm, kind))
    # 포트 비트 펼침
    pbits = []
    for nm, kind in ports:
        for b in _expand(nm, buses):
            pbits.append((b, kind))
    # 인스턴스
    insts = {}
    body2 = re.sub(r'\b(input|output|inout|wire|supply0|supply1|tri|assign)\b[^;]*;', ' ', body)
    for cell, iname, conns in re.findall(r'(\\?[A-Za-z_][\w$]*)\s+(\\\S+|[A-Za-z_][\w$\[\]]*)\s*\((.*?)\)\s*;', body2, flags=re.S):
        cell = _ident(cell); iname = _ident(iname)
        if cell not in macros:
            raise ValueError(f'cell {cell} (inst {iname}) not in LEF')
        m = macros[cell]
        pmap = {}
        for pn, expr in re.findall(r'\.\s*(\\\S+|[A-Za-z_][\w$]*)\s*\(([^()]*)\)', conns):
            pn = _ident(pn)
            bits = _expand(expr, buses)
            if not bits:
                continue
            if pn in m.pins:
                lefpins = [pn]
            else:
                idx = sorted((int(re.match(r'^' + re.escape(pn) + r'\[(\d+)\]$', p).group(1)) for p in m.pins
                              if re.match(r'^' + re.escape(pn) + r'\[(\d+)\]$', p)), reverse=True)
                if not idx:
                    raise ValueError(f'{iname}.{pn}: pin not in LEF {cell}')
                lefpins = [f'{pn}[{k}]' for k in idx]
            if len(lefpins) != len(bits):
                raise ValueError(f'{iname}.{pn}: width {len(lefpins)} vs {len(bits)} bits')
            for lp, b in zip(lefpins, bits):
                pmap[lp] = b
        insts[iname] = (cell, pmap)
    return _ident(name), pbits, insts


def nets_of(insts):
    nets = defaultdict(list)
    for iname, (cell, pmap) in insts.items():
        for p, n in pmap.items():
            nets[n].append((iname, p))
    return nets


# ───────────────────────── 도형 모음 + 간격 검사 ─────────────────────────
def rect_dist(a, b):
    dx = max(0, max(a[0], b[0]) - min(a[2], b[2]))
    dy = max(0, max(a[1], b[1]) - min(a[3], b[3]))
    return (dx * dx + dy * dy) ** 0.5, dx, dy


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


class ShapeDB:
    """층마다 (net, rect). net=None 은 블록 OBS (모든 넷과 간격). 격자 bucket 으로 찾음."""
    B = 20000

    def __init__(self):
        self.d = defaultdict(lambda: defaultdict(list))

    def add(self, layer, rect, net):
        for bx in range(rect[0] // self.B, rect[2] // self.B + 1):
            for by in range(rect[1] // self.B, rect[3] // self.B + 1):
                self.d[layer][(bx, by)].append((net, rect))

    def near(self, layer, rect, margin):
        seen = set()
        for bx in range((rect[0] - margin) // self.B, (rect[2] + margin) // self.B + 1):
            for by in range((rect[1] - margin) // self.B, (rect[3] + margin) // self.B + 1):
                for it in self.d[layer].get((bx, by), ()):
                    if id(it) not in seen:
                        seen.add(id(it)); yield it

    def conflicts(self, layer, rect, net, extra=0, same_gap=True):
        """같은 넷이 아닌 도형과 겹치거나 최소 간격보다 가까운 것. same_gap 이면 같은 넷이라도 닿지 않고 간격보다 가까우면 (notch) 넣음."""
        sp = MINS.get(layer, 140) + extra
        w = min(rect[2] - rect[0], rect[3] - rect[1])
        if w > WIDE_S.get(layer, (10 ** 9, 0))[0]:
            sp = max(sp, WIDE_S[layer][1])
        out = []
        for n2, r2 in self.near(layer, rect, sp + 3000):
            if n2 is not None and n2 == net:
                if same_gap:
                    d, dx, dy = rect_dist(rect, r2)
                    if 0 < d < MINS.get(layer, 140) - 0.5:
                        out.append((n2, r2))
                continue
            s = sp
            w2 = min(r2[2] - r2[0], r2[3] - r2[1])
            if w2 > WIDE_S.get(layer, (10 ** 9, 0))[0]:
                s = max(s, WIDE_S[layer][1])
            d, dx, dy = rect_dist(rect, r2)
            if overlaps(rect, r2) or d < s - 0.5:
                out.append((n2, r2))
        return out


# ───────────────────────── via 도형 ─────────────────────────
def via_rects(vname, cx, cy, nx=1, ny=1, big_lo='x', big_hi='x'):
    """cut 배열 nx×ny 를 (cx, cy) 가운데에. big_lo/big_hi = 큰 enclosure 를 줄 방향 ('x' 면 좌우, 'y' 면 위아래).
    → {layer: rect} (아래 금속, cut 들, 위 금속)."""
    v = VIA[vname]
    c, s = v['cut'], v['sp']
    wx = nx * c + (nx - 1) * s; wy = ny * c + (ny - 1) * s
    x1, y1 = snap(cx - wx / 2), snap(cy - wy / 2)
    cuts = [(x1 + i * (c + s), y1 + j * (c + s), x1 + i * (c + s) + c, y1 + j * (c + s) + c) for i in range(nx) for j in range(ny)]
    X1, Y1, X2, Y2 = x1, y1, x1 + wx, y1 + wy

    def enc(e, big):
        a, b = e
        ex, ey = (b, a) if big == 'x' else (a, b)
        return (X1 - ex, Y1 - ey, X2 + ex, Y2 + ey)
    return {v['lo']: enc(v['elo'], big_lo), 'cuts': (vname, cuts), v['hi']: enc(v['ehi'], big_hi)}


MINAREA = {'met1': 83000, 'met2': 67600, 'met3': 240000, 'met4': 240000, 'met5': 4000000}   # nm²


def stack(dw, net, x, y, lo, hi, pad=None):
    """(x, y) 에 lo 층 → hi 층 via 를 쌓고, 중간층에 최소 면적 pad 를 넣는다. 돌려줌 = {layer: [rect]} (간격 검사용)."""
    order = ['met1', 'met2', 'met3', 'met4', 'met5']
    a, b = order.index(lo), order.index(hi)
    used = defaultdict(list)
    for k in range(a, b):
        vname = CUTS[(order[k], order[k + 1])]
        rr = dw.add_via(net, vname, x, y)
        used[order[k]].append(rr[order[k]]); used[order[k + 1]].append(rr[order[k + 1]])
        used[vname].extend(rr['cuts'][1])
    for k in range(a + 1, b):
        l = order[k]
        rs = used[l]
        bx = (min(r[0] for r in rs), min(r[1] for r in rs), max(r[2] for r in rs), max(r[3] for r in rs))
        if (bx[2] - bx[0]) * (bx[3] - bx[1]) < MINAREA[l]:
            half = snap((MINAREA[l] ** 0.5) / 2 + 3)
            p = (snap(x) - half, snap(y) - half, snap(x) + half, snap(y) + half)
            p = (min(p[0], bx[0]), min(p[1], bx[1]), max(p[2], bx[2]), max(p[3], bx[3]))
            dw.add_rect(net, l, p); used[l].append(p)
    return used


# ───────────────────────── DEF 쓰기 ─────────────────────────
class DefWriter:
    def __init__(self, design, die, style='rect'):
        self.design, self.die, self.style = design, die, style
        self.vias = {}             # 이름 → [(layer, rect)] (가운데 기준)
        self.comps = []            # (inst, cell, x, y, orient)
        self.pins = []             # dict
        self.snets = defaultdict(list)   # net → [('rect', layer, r) | ('via', vname, x, y)]
        self.snet_use = {}
        self.nets = {}             # net → [(inst, pin)] (연결만)
        self.blockages = []        # (layer, rect)

    def via_def(self, vname, nx, ny, big_lo='x', big_hi='x'):
        key = f'{vname}_{nx}x{ny}_{big_lo}{big_hi}'
        if key not in self.vias:
            rr = via_rects(vname, 0, 0, nx, ny, big_lo, big_hi)
            lo, hi = VIA[vname]['lo'], VIA[vname]['hi']
            L = [(lo, rr[lo])] + [(vname, c) for c in rr['cuts'][1]] + [(hi, rr[hi])]
            self.vias[key] = L
        return key

    def add_via(self, net, vname, cx, cy, nx=1, ny=1, big_lo='x', big_hi='x'):
        key = self.via_def(vname, nx, ny, big_lo, big_hi)
        # via 정의는 (0,0) 가운데 기준이므로 cx, cy 를 격자에 맞추고, 정의의 cut 배열이 가운데에 오도록
        self.snets[net].append(('via', key, snap(cx), snap(cy)))
        rr = via_rects(vname, snap(cx), snap(cy), nx, ny, big_lo, big_hi)
        return rr

    def add_rect(self, net, layer, r):
        r = tuple(snap(v) for v in r)
        self.snets[net].append(('rect', layer, r))
        return r

    def write(self, path):
        D = []
        D += ['VERSION 5.8 ;', 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;', f'DESIGN {self.design} ;', 'UNITS DISTANCE MICRONS 1000 ;',
              f'DIEAREA ( {self.die[0]} {self.die[1]} ) ( {self.die[2]} {self.die[3]} ) ;']
        if self.vias:
            D.append(f'VIAS {len(self.vias)} ;')
            for k, L in self.vias.items():
                D.append(f'- {k}')
                for l, r in L:
                    D.append(f'  + RECT {l} ( {r[0]} {r[1]} ) ( {r[2]} {r[3]} )')
                D[-1] += ' ;'
            D.append('END VIAS')
        if self.comps:
            D.append(f'COMPONENTS {len(self.comps)} ;')
            for i, c, x, y, o in self.comps:
                D.append(f'- {i} {c} + FIXED ( {x} {y} ) {o} ;')
            D.append('END COMPONENTS')
        if self.pins:
            D.append(f'PINS {len(self.pins)} ;')
            for p in self.pins:
                s = f"- {p['name']} + NET {p['net']}"
                if p.get('special'):
                    s += ' + SPECIAL'
                s += f" + DIRECTION {p.get('dir', 'INOUT')} + USE {p.get('use', 'SIGNAL')}"
                for l, r in p['shapes']:
                    s += f'\n  + PORT\n  + LAYER {l} ( {r[0] - p["x"]} {r[1] - p["y"]} ) ( {r[2] - p["x"]} {r[3] - p["y"]} )\n  + FIXED ( {p["x"]} {p["y"]} ) N'
                D.append(s + ' ;')
            D.append('END PINS')
        if self.blockages:
            D.append(f'BLOCKAGES {len(self.blockages)} ;')
            for l, r in self.blockages:
                D.append(f'- LAYER {l} RECT ( {r[0]} {r[1]} ) ( {r[2]} {r[3]} ) ;')
            D.append('END BLOCKAGES')
        if self.snets:
            D.append(f'SPECIALNETS {len(self.snets)} ;')
            for n, L in self.snets.items():
                s = f'- {n}'
                for iname, pin in self.nets.get(n, []):
                    s += f' ( {iname} {pin} )'
                first = True
                for it in L:
                    if self.style == 'rect':
                        if it[0] == 'rect':
                            _, l, r = it
                            s += f'\n  + RECT {l} ( {r[0]} {r[1]} ) ( {r[2]} {r[3]} )'
                        else:
                            _, key, x, y = it
                            s += f'\n  + VIA {key} ( {x} {y} )'
                        continue
                    kw = '+ ROUTED' if first else 'NEW'
                    first = False
                    if it[0] == 'rect':
                        _, l, r = it
                        w = r[2] - r[0]; h = r[3] - r[1]
                        if w >= h:
                            if (r[1] + r[3]) % 2:
                                raise ValueError(f'odd rect {r}')
                            yc = (r[1] + r[3]) // 2
                            s += f'\n  {kw} {l} {h} + SHAPE STRIPE ( {r[0]} {yc} ) ( {r[2]} * )'
                        else:
                            if (r[0] + r[2]) % 2:
                                raise ValueError(f'odd rect {r}')
                            xc = (r[0] + r[2]) // 2
                            s += f'\n  {kw} {l} {w} + SHAPE STRIPE ( {xc} {r[1]} ) ( * {r[3]} )'
                    else:
                        _, key, x, y = it
                        lo = self.vias[key][0][0]
                        s += f'\n  {kw} {lo} 0 + SHAPE STRIPE ( {x} {y} ) {key}'
                s += f'\n  + USE {self.snet_use.get(n, "SIGNAL")} ;'
                D.append(s)
            D.append('END SPECIALNETS')
        D.append('END DESIGN')
        open(path, 'w').write('\n'.join(D) + '\n')
