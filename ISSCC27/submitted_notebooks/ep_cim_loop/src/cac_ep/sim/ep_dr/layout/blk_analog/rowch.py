"""두 줄 + 가운데 통로 셀 엔진 (10/28, blk_analog) — write buffer·nudge 주입기·bias 같은 작은 아날로그 셀.
소자 그리기 = ep_demo/layout/devlib.py 의 mos()/tap() 그대로 (DRC 통과 이력, import 만). 그 위 배선만 여기서:
  아래 줄 = NMOS (p-tap 띠 위, 소스 스트랩이 아래), 위 줄 = PMOS (n-well, n-tap 띠 아래, mos() 를 셀로 그려 위아래 뒤집어 넣음 → 게이트가 통로 쪽).
  vss·vdd 소스 = 탭 띠에 met1 로 바로. 나머지 단자 (S·D 스트랩, 게이트 패드) = via1 → met2 세로 줄기 → via2 → 통로의 met3 가로 트랙 (넷마다 하나).
  게이트 패드는 소자 왼쪽 밖 (li1 스트랩을 늘림) — 핑거 1 개 소자에서도 S·D 줄기와 부딪히지 않게.
  N 줄기와 P 줄기가 같은 x (0.5 µm 안) 에 오면 N 넷 트랙 < P 넷 트랙 이어야 → 트랙 순서 = 위상 정렬.
  탭 띠 = met1 + met2 + met3 (via 배열) → 전원 핀은 met3 띠.
좌표 µm (devlib 와 같게, 5 nm 격자). 셀 왼쪽 아래 근처 = (0, 0) (p-tap 띠 아래 끝).
"""
import klayout.db as db

import blk_common  # noqa: F401  (devlib 경로)
from devlib import Cell, mos, tap, gate_pad, P1, g as gs

GAP = 1.10            # 같은 줄 소자 사이 (왼쪽 게이트 패드 + li1 0.17 · met2 줄기 0.5 간격)
STUB_W, STUB_P = 0.30, 0.50
TR_W, TR_P = 0.34, 0.64
GPX = 0.55            # 게이트 패드 = 소자 diff 왼쪽 끝에서 이만큼 왼쪽


def dev(name, typ, W, L, nf, d, g, s, b=None, **kw):
    return dict(name=name, typ=typ, W=W, L=L, nf=nf, d=d, g=g, s=s, b=b or ('vss' if typ == 'n' else 'vdd'), **kw)


def v12(C, net, x, y):
    C.box(net, 'm1', x - P1 / 2, y - P1 / 2, x + P1 / 2, y + P1 / 2)
    C.cut(net, 'via', x, y, 0.15)
    C.box(net, 'm2', x - P1 / 2, y - P1 / 2, x + P1 / 2, y + P1 / 2)


def v2pad(C, net, x, y):
    C.box(net, 'm2', x - 0.185, y - 0.185, x + 0.185, y + 0.185)
    C.cut(net, 'via2', x, y, 0.20)


def v123(C, net, x, y):
    C.box(net, 'm1', x - 0.165, y - 0.165, x + 0.165, y + 0.165)
    C.cut(net, 'via', x, y, 0.15)
    C.box(net, 'm2', x - 0.185, y - 0.185, x + 0.185, y + 0.185)
    C.cut(net, 'via2', x, y, 0.20)


def band(C, kind, x1, x2, yc, net):
    """탭 띠 + met2·met3 띠 (via1·via2 0.6 µm 간격). 반환 met3 띠 (x1, y1, x2, y2)."""
    tap(C, kind, x1, x2, yc, net)
    C.box(net, 'm2', x1, yc - 0.25, x2, yc + 0.25)
    C.box(net, 'm3', x1, yc - 0.25, x2, yc + 0.25)
    n = int((x2 - x1 - 0.6) / 0.6) + 1
    xs0 = x1 + (x2 - x1 - (n - 1) * 0.6) / 2
    for k in range(n):
        C.cut(net, 'via', xs0 + k * 0.6, yc, 0.15)
        C.cut(net, 'via2', xs0 + k * 0.6, yc, 0.20)
    return (x1, yc - 0.25, x2, yc + 0.25)


def fix_cuts(C, r):
    """핑거 폭이 0.01 µm 배수가 아니면 (예 0.715) devlib 의 S/D licon·mcon 가운데가 2.5 nm 에 걸려 크기 0.165/0.175 가 된다
    (10/28 bias_beta 첫 판 licon.1·mcon.1·mcon.2). 그 소자의 S/D 컨택만 지우고 5 nm 격자 가운데로 다시 그린다."""
    nm = lambda v: int(round(v * 1000))
    yb, yt = nm(r['yb']), nm(r['yt'])
    if (yt - yb) % 10 == 0:
        return
    box = db.Box(nm(r['x0']), yb, nm(r['x1']), yt)
    for lay in ('licon', 'mcon'):
        sh = C.c.shapes(C.li[lay])
        for s in [s for s in sh.each_overlapping(box)]:
            sh.erase(s)
    usable = (yt - yb) - 290
    nct = max(1, usable // 360 + 1)
    off = int(round((usable - (nct - 1) * 360) / 2 / 5.0)) * 5
    for xc in r['srcs'] + r['drns']:
        x = nm(xc)
        for t in range(nct):
            yy = yb + 145 + off + t * 360
            for lay in ('licon', 'mcon'):
                sh = C.c.shapes(C.li[lay]); sh.insert(db.Box(x - 85, yy - 85, x + 85, yy + 85))


class RowCh:
    """nrow·prow = dev() 목록 (왼쪽부터). x 는 자동 (GAP) 또는 d['x'] 로 고정. direct=True 소자는 단자 배선을 밖에서 (cb)."""

    def __init__(self, ly, name):
        self.ly, self.C = ly, Cell(ly, name)
        self.C.li['lbl_m3'] = ly.layer(70, 5)
        self.stubs = []          # (net, x, y_term, side)  side 'n' (위로) / 'p' (아래로)
        self.span = {}           # net → [x 목록]  트랙 길이
        self.devs = []

    # ---------- 줄 그리기
    def place_n(self, devs, x0=0.4, y0=0.55):
        C = self.C; x = x0 + GAP
        out = []
        for d in devs:
            if 'x' in d:
                x = d['x']
            r = mos(C, 'n', x, y0, d['W'], d['L'], d['nf'], d['s'], d['d'], d['g'])
            fix_cuts(C, r)
            r['dev'] = d; r['side'] = 'n'
            out.append(r); self.devs.append(r)
            x = r['x1'] + GAP
        self.nrow = out
        return out

    def place_p(self, devs, y_nt, x0=0.4):
        """PMOS 줄: n-tap 띠 가운데 y_nt. 소자 local y=0 이 y_nt − 0.30 (mos() 를 하위 셀에 그려 M0 로 넣음)."""
        x = x0 + GAP
        out = []
        for k, d in enumerate(devs):
            if 'x' in d:
                x = d['x']
            sub = Cell(self.ly, f"{self.C.c.name}_p{k}_{d['name']}")
            r = mos(sub, 'p', 0, 0, d['W'], d['L'], d['nf'], d['s'], d['d'], d['g'])
            fix_cuts(sub, r)
            yo = y_nt - 0.30
            self.C.c.insert(db.CellInstArray(sub.c.cell_index(), db.Trans(db.Trans.M0, int(round(x * 1000)), int(round(yo * 1000)))))
            m = lambda yl: gs(yo - yl)
            rr = dict(r, x0=x + r['x0'], x1=x + r['x1'], ys=m(r['ys']), yd=m(r['yd']), gy=m(r['gy']),
                      yb=m(r['yt']), yt=m(r['yb']), y0=m(r['y1']), y1=m(r['y0']),
                      srcs=[gs(x + v) for v in r['srcs']], drns=[gs(x + v) for v in r['drns']], gxs=[gs(x + v) for v in r['gxs']],
                      dev=d, side='p', sub=sub)
            out.append(rr); self.devs.append(rr)
            x = rr['x1'] + GAP
        self.prow = out
        return out

    # ---------- 단자
    def gate_left(self, r):
        """게이트 li1 스트랩을 소자 왼쪽 밖으로 늘려 패드 (mcon + met1) + via1. 반환 (x, y)."""
        C, d = self.C, r['dev']
        xg = gs(r['x0'] - GPX); gy = r['gy']
        C.box(d['g'], 'li1', xg - 0.17, gy - 0.18, r['gxs'][0], gy + 0.18)          # 첫 핑거 가운데까지 (L 이 크면 스트랩이 더 안쪽에서 시작)
        C.cut(d['g'], 'mcon', xg, gy)
        C.box(d['g'], 'm1', xg - 0.17, gy - 0.17, xg + 0.17, gy + 0.17)
        C.cut(d['g'], 'via', xg, gy, 0.15)
        C.box(d['g'], 'm2', xg - P1 / 2, gy - P1 / 2, xg + P1 / 2, gy + P1 / 2)
        return xg, gy

    def rail_bridge(self, r, tap_y):
        """소스 = 전원: 소스 스트랩 → 탭 띠 met1 (스트랩 x 범위 전체)."""
        a, b = min(r['srcs']) - 0.115, max(r['srcs']) + 0.115
        y1, y2 = sorted((r['ys'], tap_y))
        self.C.box(r['dev']['s'], 'm1', a, y1, b, y2)

    def stub(self, net, x, y, side, pad=True):
        if pad:
            v12(self.C, net, x, y)
        self.stubs.append((net, gs(x), y, side))

    def auto_terms(self, r, rails=('vss', 'vdd'), skip=(), s_col=0, d_col=-1, tap_y=None):
        """보통 소자: S (전원이면 탭에, 아니면 줄기), D 줄기, G (왼쪽 패드) 줄기. 줄기 x = S 는 s_col 번째 소스 줄, D 는 d_col 번째 드레인 줄."""
        d = r['dev']; side = r['side']
        if 's' not in skip:
            if d['s'] in rails:
                self.rail_bridge(r, tap_y)
            else:
                self.stub(d['s'], r['srcs'][s_col], r['ys'], side)
        if 'd' not in skip and r['drns']:
            self.stub(d['d'], r['drns'][d_col], r['yd'], side)
        if 'g' not in skip:
            xg, gy = self.gate_left(r)
            self.stub(d['g'], xg, gy, side, pad=False)

    # ---------- 트랙
    def solve_tracks(self, y_lo, extra_nets=(), order_hint=(), share=False, xext=None):
        """통로 트랙 배정. N 줄기 (아래에서 올라옴) 넷 a, P 줄기 넷 b 가 x 로 STUB_P 안이면 트랙(a) < 트랙(b)."""
        nets = []
        for n, *_ in self.stubs:
            if n not in nets:
                nets.append(n)
        for n in extra_nets:
            if n not in nets:
                nets.append(n)
        before = {n: set() for n in nets}               # before[b] = a 들 (a 가 b 보다 아래)
        ns = [s for s in self.stubs if s[3] == 'n']; ps = [s for s in self.stubs if s[3] == 'p']
        for a, xa, *_ in ns:
            for b, xb, *_ in ps:
                if a != b and abs(xa - xb) < STUB_P - 1e-6:
                    before[b].add(a)
        order, done = [], set()
        pri = {n: i for i, n in enumerate(order_hint)}
        while len(order) < len(nets):
            ready = [n for n in nets if n not in done and before[n] <= done]
            if not ready:
                raise RuntimeError(f'트랙 순서 순환: {[(n, before[n] - done) for n in nets if n not in done]}')
            n = min(ready, key=lambda n: (pri.get(n, 1e9), nets.index(n)))
            order.append(n); done.add(n)
        if not share:
            self.track_y = {n: gs(y_lo + TR_W / 2 + k * TR_P) for k, n in enumerate(order)}
            return self.track_y
        # 줄 나눠 쓰기: x 범위가 겹치지 않는 넷끼리 같은 줄 (위상 순서 지키며 가장 낮은 빈 줄)
        span = {}
        for n, x, *_ in self.stubs:
            a, b = span.get(n, (x, x)); span[n] = (min(a, x), max(b, x))
        for n, (ea, eb) in (xext or {}).items():
            a, b = span.get(n, (ea, eb)); span[n] = (min(a, ea), max(b, eb))
        rows, rowof = [], {}
        for n in order:
            a, b = span[n][0] - 0.25, span[n][1] + 0.25
            k = max([rowof[p] + 1 for p in before[n]] + [0])
            while k < len(rows) and any(not (b + 0.6 < c or a - 0.6 > d) for c, d in rows[k]):
                k += 1
            if k == len(rows):
                rows.append([])
            rows[k].append((a, b)); rowof[n] = k
        self.track_y = {n: gs(y_lo + TR_W / 2 + rowof[n] * TR_P) for n in order}
        self.nrows = len(rows)
        return self.track_y

    def draw_stubs_tracks(self, xext=None):
        """줄기 met2 + 트랙 끝 via2, 트랙 met3 (줄기 x 범위, xext[넷] = (x 왼쪽, x 오른쪽) 로 늘림)."""
        C = self.C
        xs = {}
        for n, x, y, side in self.stubs:
            yt = self.track_y[n]
            C.box(n, 'm2', x - STUB_W / 2, min(y, yt), x + STUB_W / 2, max(y, yt))
            v2pad(C, n, x, yt)
            xs.setdefault(n, []).append(x)
        for n, yt in self.track_y.items():
            v = xs.get(n, [])
            a = min(v) - 0.25 if v else None; b = max(v) + 0.25 if v else None
            if xext and n in xext:
                ea, eb = xext[n]
                a = ea if a is None else min(a, ea); b = eb if b is None else max(b, eb)
            C.box(n, 'm3', a, yt - TR_W / 2, b, yt + TR_W / 2)
        return xs
