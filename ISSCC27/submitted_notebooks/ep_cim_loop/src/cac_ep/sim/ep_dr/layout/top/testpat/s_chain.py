"""testpat — contact·via chain 구조 셀 (10/28). build(ly) -> list[Struct]. import 때 파일을 쓰거나 실행하지 않는다.

셀 (이름 tp_ch_<kind>, 고리 수 N = cut 개수, 기본 200):
  tp_ch_poly   licon  poly ↔ li1     (npc 가 poly licon 전체를 0.10 이상 감쌈)
  tp_ch_ndiff  licon  n+ diff ↔ li1  (hvi 없음, p-sub 위, nsdm)
  tp_ch_pdiff  licon  p+ diff ↔ li1  (nwell 안, psdm, ntap → VDD 패드)
  tp_ch_mcon   mcon   li1 ↔ met1
  tp_ch_via1   via1   met1 ↔ met2
  tp_ch_via2   via2   met2 ↔ met3
cut 은 최소 크기 (licon·mcon 0.17, via1 0.15, via2 0.20). 아래층 막대 (cut i·i+1, i 짝수) 와 위층 막대 (i 홀수) 를 번갈아 잇고,
nx 열 × ny 행 (ny 짝수, 4 이상) 으로 뱀처럼 접는다 → 사슬 양 끝 (cut 0, cut N-1) 이 모두 서쪽 열 (col 0) 의 맨 아래·맨 위 행.

배치 (x 는 서쪽 끝 = 0, 셀 폭 W 기본 40.0):
  x 0–1.0      서쪽 met3 신호 패드 a (맨 아래 행 높이), b (맨 위 행 높이)
  x 1.5–2.5    b 쪽 met3 이음선 위 met3_res (70/13) 표지, met3 폭 0.5 전체에 꼭 맞게 → W 0.5 × L 1.0
  x 3.5        사슬 끝 위층 → met3 via 쌓기 (via2 사슬은 위층이 met3 라 없음)
  x 4.5 –      사슬 (col 0 중심 x 4.5)
  x W-2.0      p-tap (기판 → VSS), met3 로 동쪽 변 VSS 패드 (W-1–W)
  tp_ch_pdiff: 사슬 동쪽 1.5 µm 에 ntap (nwell 안) → met3 → 동쪽 VDD 패드 (맨 위 행 높이)
LVS: 사슬은 a·b 를 한 넷으로 만드는 도선이라 그대로면 포트 단락. b 쪽 met3 에 met3_res 표지를 두어 넷을 나누고 CDL 에
  R0 a b $[res_generic_m3] $W=0.5u $L=1u 한 줄을 둔다. 이 R 은 사슬 저항이 아니라 LVS 용 표지 (측정 때는 a–b = 사슬 + met3 0.5×1.0 토막).
  덱 (sky130_tp.lvs.pvl RES_PROPERTIES): W = 표지와 met3 단자가 겹치는 변 길이 / 2 = (0.5 + 0.5) / 2, L = 면적 / W = 0.5 / 0.5.
도우미 (tpcommon 에 없는 것, 이 모듈 안): chain(), _ptap(), _tap_up(), drc_lite() (klayout Region 으로 폭·간격·감쌈·면적만 미리 보는 간이 검사).
쓰임: from s_chain import build ; 단독 시험: python s_chain.py [--no-run]
"""
import json
import sys

import klayout.db as db

from tpcommon import *

W_DEF = 40.0
N_DEF = 200
X_RES = (1.5, 2.5)          # met3_res 표지 x 범위 (L = 1.0)
RES_W = PIN_H               # 이음선 met3 폭 = 패드 높이 0.5 → 표지 W
XJ = 3.5                    # 사슬 끝 via 쌓기 x
X0 = 4.5                    # col 0 cut 중심 x
Y0 = 0.5                    # row 0 cut 중심 y (VSS 패드 h 1.0 의 아래 끝 = 0)
XPT = 2.0                   # p-tap 중심 = W - XPT

# kind: 아래층 lo, 위층 hi, cut 층, cut 크기, (옆 감쌈, 끝 감쌈) — 끝 감쌈은 막대 길이 방향 양 끝 = "one of two adjacent sides" 규칙
KINDS = {
    'poly':  dict(lo='poly', hi='li1', cut='licon', s=0.17, lo_e=(0.05, 0.08), hi_e=(0.0, 0.08), p=0.60,
                  what='licon–poly (poly ↔ li1, npc)'),
    'ndiff': dict(lo='diff', hi='li1', cut='licon', s=0.17, lo_e=(0.04, 0.06), hi_e=(0.0, 0.08), p=0.60,
                  imp='nsdm', what='licon–n+ diff (diff ↔ li1, nsdm, p-sub, hvi 없음)'),
    'pdiff': dict(lo='diff', hi='li1', cut='licon', s=0.17, lo_e=(0.04, 0.06), hi_e=(0.0, 0.08), p=0.60,
                  imp='psdm', nwell=True, what='licon–p+ diff (diff ↔ li1, psdm, nwell + ntap → VDD, hvi 없음)'),
    'mcon':  dict(lo='li1', hi='met1', cut='mcon', s=0.17, lo_e=(0.0, 0.0), hi_e=(0.03, 0.06), p=0.50,
                  what='mcon (li1 ↔ met1)'),
    'via1':  dict(lo='met1', hi='met2', cut='via1', s=0.15, lo_e=(0.055, 0.085), hi_e=(0.055, 0.085), p=0.50,
                  what='via1 (met1 ↔ met2)'),
    'via2':  dict(lo='met2', hi='met3', cut='via2', s=0.20, lo_e=(0.04, 0.085), hi_e=(0.065, 0.065), p=0.65,
                  what='via2 (met2 ↔ met3)'),
}
NWELL_ENC = 0.30            # nwell 이 p+ diff·ntap 을 감쌈 (규칙 0.18)
IMP_ENC = 0.125             # nsdm·psdm 이 diff·tap 을 감쌈
NPC_ENC = 0.10              # npc 가 poly licon 을 감쌈


def _fmt(v):
    return f'{round(v, 4):g}u'


def _plan(N, nx_max):
    """N 개 cut → (nx, ny). ny 는 4 이상 짝수 (양 끝이 서쪽, a·b 패드 간격 ≥ 1.0), nx ≤ nx_max, N = nx·ny."""
    for ny in range(4, N + 1, 2):
        if N % ny == 0 and N // ny <= nx_max:
            return N // ny, ny
    raise ValueError(f'N={N}: nx ≤ {nx_max}, ny 짝수 ≥ 4 로 나눌 수 없음 (N 을 4·ny 배수로)')


def _tap_up(s, kind, x, y):
    """탭 하나 (0.5 정사각, licon 1 개) + 감쌈 implant + li 0.35 + li → met3 via 쌓기. kind 'p' = p-tap (psdm), 'n' = ntap (nsdm)."""
    s.box('tap', x - 0.25, y - 0.25, x + 0.25, y + 0.25)
    imp = 'psdm' if kind == 'p' else 'nsdm'
    s.box(imp, x - 0.25 - IMP_ENC, y - 0.25 - IMP_ENC, x + 0.25 + IMP_ENC, y + 0.25 + IMP_ENC)
    s.cut('licon', x, y, 0.17)
    s.box('li1', x - 0.175, y - 0.175, x + 0.175, y + 0.175)
    s.via(x, y, 'li1', 'met3')


def _ptap(s, W, y):
    """기판 p-tap → 동쪽 변 VSS 패드."""
    xt = g(W - XPT)
    _tap_up(s, 'p', xt, y)
    s.box('met3', xt - 0.25, y - 0.25, W - PWR_W, y + 0.25)
    s.pwr_pin('VSS', W, y)


def chain(ly, kind, N=None, W=W_DEF, name=None):
    """chain 구조 셀 하나. N = cut 개수 (nx·ny, ny 짝수 ≥ 4). 반환 Struct (check() 통과)."""
    k = KINDS[kind]
    N = N or N_DEF
    name = name or f'tp_ch_{kind}'
    p, cs = k['p'], k['s']
    h = cs / 2
    nw = bool(k.get('nwell'))
    xe = W - (5.5 if nw else 3.5)                       # 마지막 열 cut 중심 x 의 한계 (p-tap·ntap 과 떨어지게)
    nx_max = int((xe - X0) / p + 1e-9) + 1
    nx, ny = _plan(N, nx_max)
    s = Struct(ly, name, source='layout/top/testpat/s_chain.py')
    s.N, s.nx, s.ny, s.pitch = N, nx, ny, p

    # cut 경로 (뱀): 짝수 행 서→동, 홀수 행 동→서
    path = []
    for r in range(ny):
        cols = range(nx) if r % 2 == 0 else range(nx - 1, -1, -1)
        path += [(g(X0 + c * p), g(Y0 + r * p)) for c in cols]
    assert len(path) == N
    for (x, y) in path:
        s.cut(k['cut'], x, y, cs)
    lo_reg = db.Region()
    for i in range(N - 1):
        (x1, y1), (x2, y2) = path[i], path[i + 1]
        lay, (es, ee) = (k['lo'], k['lo_e']) if i % 2 == 0 else (k['hi'], k['hi_e'])
        if y1 == y2:                                        # 가로 막대
            b = s.box(lay, min(x1, x2) - h - ee, y1 - h - es, max(x1, x2) + h + ee, y1 + h + es)
        else:                                               # 행 끝에서 꺾는 세로 막대
            b = s.box(lay, x1 - h - es, min(y1, y2) - h - ee, x1 + h + es, max(y1, y2) + h + ee)
        if lay == k['lo']:
            lo_reg.insert(b)

    # 양 끝: 위층 토막 → (via 쌓기) → met3 이음선 → 서쪽 패드. b 쪽 이음선에 met3_res 표지.
    hs, he = k['hi_e']
    ends = {'a': path[0], 'b': path[-1]}
    for port, (x, y) in ends.items():
        assert abs(x - X0) < 1e-9
        s.box(k['hi'], XJ, y - h - hs, x + h + he, y + h + hs)
        if k['hi'] != 'met3':
            s.via(XJ, y, k['hi'], 'met3')
        s.box('met3', 0.0, y - RES_W / 2, XJ + 0.25, y + RES_W / 2)
        s.sig_pin(port, y)
        if port == 'b':
            s.box('met3_res', X_RES[0], y - RES_W / 2, X_RES[1], y + RES_W / 2)

    # 층마다 덧붙임
    lb = lo_reg.bbox()
    lx0, ly0, lx1, ly1 = lb.left / 1000, lb.bottom / 1000, lb.right / 1000, lb.top / 1000
    xl = max(x for x, _ in path)
    if kind == 'poly':
        s.box('npc', X0 - h - NPC_ENC, Y0 - h - NPC_ENC, xl + h + NPC_ENC, path[-1][1] + h + NPC_ENC)
    if 'imp' in k:
        s.box(k['imp'], lx0 - IMP_ENC, ly0 - IMP_ENC, lx1 + IMP_ENC, ly1 + IMP_ENC)
    y_top = path[-1][1]
    if nw:
        xn = g(xl + 1.5)
        _tap_up(s, 'n', xn, y_top)
        s.box('nwell', lx0 - NWELL_ENC, ly0 - NWELL_ENC, xn + 0.25 + NWELL_ENC, max(ly1, y_top + 0.25) + NWELL_ENC)
        s.box('met3', xn - 0.25, y_top - 0.25, W - PWR_W, y_top + 0.25)
        s.pwr_pin('VDD', W, y_top)
    _ptap(s, W, Y0)

    R_W, R_L = RES_W, (X_RES[1] - X_RES[0])
    s.res_wl = (R_W, R_L)
    s.cdl = [f'* R0 = LVS 용 met3_res 표지 (사슬 자체가 아님): a·b 가 사슬로 한 넷이 되는 것을 나눔',
             f'R0 a b $[res_generic_m3] $W={_fmt(R_W)} $L={_fmt(R_L)}']
    s.contents = (f"{k['what']} chain, N = {N} cut ({k['cut']} {cs:.2f}), {nx} × {ny} 뱀, pitch {p:.2f}; "
                  f"a–b = 사슬, b 쪽 met3_res 표지 W {R_W:g} × L {R_L:g} (LVS 용)")
    return s.check()


def build(ly, N=None, W=W_DEF, kinds=tuple(KINDS)):
    """chain 셀 전부 (같은 ly 에 다른 셀이 있어도 됨). N 은 정수 하나 또는 {kind: N}."""
    out = []
    for kd in kinds:
        n = N.get(kd) if isinstance(N, dict) else N
        out.append(chain(ly, kd, n, W))
    return out


_RULE = dict(poly=(0.15, 0.21), diff=(0.15, 0.27), tap=(0.15, 0.27), li1=(0.17, 0.17), met1=(0.14, 0.14),
             met2=(0.14, 0.14), met3=(0.30, 0.30), nsdm=(0.38, 0.38), psdm=(0.38, 0.38), npc=(0.27, 0.27),
             nwell=(0.84, 1.27))
_CUT = dict(licon=(0.17, 0.17), mcon=(0.17, 0.19), via1=(0.15, 0.17), via2=(0.20, 0.20))
_ENC = [('li1', 'licon', 0.0), ('poly', 'licon@poly', 0.05), ('npc', 'licon@poly', 0.10), ('diff', 'licon@diff', 0.04),
        ('tap', 'licon@tap', 0.12), ('li1', 'mcon', 0.0), ('met1', 'mcon', 0.03), ('met1', 'via1', 0.055),
        ('met2', 'via1', 0.055), ('met2', 'via2', 0.04), ('met3', 'via2', 0.065),
        ('nsdm', 'diff@nsdm', 0.125), ('psdm', 'diff@psdm', 0.125), ('nsdm', 'tap@nsdm', 0.125),
        ('psdm', 'tap@psdm', 0.125), ('nwell', 'diff@nwell', 0.18), ('nwell', 'tap@nsdm', 0.18)]
_AREA = dict(li1=0.0561, met1=0.083, met2=0.067, met3=0.24)


def drc_lite(ly, cell):
    """폭·간격·cut 크기·감쌈·면적 → 위반 목록 [(규칙, 개수)]. 'one of two adjacent sides' 는 막대 끝 감쌈으로 맞춰 둠 (여기선 안 봄)."""
    R = {}
    for n, (l, d) in LAY.items():
        li = ly.find_layer(l, d)
        R[n] = db.Region(cell.begin_shapes_rec(li)).merged() if li is not None else db.Region()
    met3 = R['met3']
    bad = []

    def add(rule, ep):
        c = ep.count() if hasattr(ep, 'count') else ep
        if c:
            bad.append((rule, c))
    for n, (w, sp) in _RULE.items():
        add(f'{n}.width', R[n].width_check(nm(w)))
        add(f'{n}.space', R[n].space_check(nm(sp)))
    for n, (sz, sp) in _CUT.items():
        raw = db.Region(cell.begin_shapes_rec(ly.find_layer(*LAY[n]))) if ly.find_layer(*LAY[n]) is not None else db.Region()
        add(f'{n}.size', sum(1 for pg in raw.each() if not (pg.is_box() and pg.bbox().width() == nm(sz) == pg.bbox().height())))
        add(f'{n}.space', R[n].space_check(nm(sp)))
    lic = R['licon']
    sub = {'licon': lic, 'licon@poly': lic.interacting(R['poly']), 'licon@diff': lic.interacting(R['diff']),
           'licon@tap': lic.interacting(R['tap']), 'mcon': R['mcon'], 'via1': R['via1'], 'via2': R['via2'],
           'diff@nsdm': R['diff'].interacting(R['nsdm']), 'diff@psdm': R['diff'].interacting(R['psdm']),
           'tap@nsdm': R['tap'].interacting(R['nsdm']), 'tap@psdm': R['tap'].interacting(R['psdm']),
           'diff@nwell': R['diff'].interacting(R['nwell'])}
    for outer, inner, d in _ENC:
        a = sub[inner]
        if a.is_empty():
            continue
        if inner.startswith('tap@nsdm') and outer == 'nwell':
            a = a.interacting(R['nwell'])
        add(f'{outer}⊃{inner}.inside', (a - R[outer]).count())
        if d > 0:
            add(f'{outer}⊃{inner}.enc{d}', R[outer].enclosing_check(a, nm(d)))
    add('licon.poly+diff', lic.interacting(R['poly']).interacting(R['diff'] + R['tap']).count())
    add('nsdm∩psdm', (R['nsdm'] & R['psdm']).count())
    add('npc–licon@diff 0.09', R['npc'].separation_check(sub['licon@diff'] + sub['licon@tap'], nm(0.09)))
    add('diff–tap 0.27', R['diff'].separation_check(R['tap'], nm(0.27)))
    add('ndiff–nwell 0.34', sub['diff@nsdm'].separation_check(R['nwell'], nm(0.34)))
    add('ptap–nwell 0.13', sub['tap@psdm'].separation_check(R['nwell'], nm(0.13)))
    add('poly–tap/diff 0.19', R['poly'].separation_check(R['diff'] + R['tap'], nm(0.19)))
    for n, a in _AREA.items():
        add(f'{n}.area', sum(1 for pg in R[n].each() if pg.area() < a * 1e6 - 1))
    # met3_res: met3 안에 꼭 맞고 (밖으로 안 나감), 양쪽에 met3 조각 2 개
    mr = R['met3_res']
    add('m3.res.inside', (mr - met3).count())
    for pg in mr.each():
        pieces = (met3 - mr).interacting(db.Region(pg).sized(1))
        if pieces.count() != 2:
            bad.append(('m3.res.pieces', pieces.count()))
    return bad


def _main(argv):
    no_run = '--no-run' in argv
    ly = db.Layout(); ly.dbu = 0.001
    S = build(ly)
    ok = True
    for s in S:
        bad = drc_lite(ly, s.c)
        print(f'{s.name:12s} bbox {s.bbox()} N {s.N} ({s.nx}×{s.ny}, p {s.pitch}) ports {s.ports} R W·L {s.res_wl} '
              f'| drc_lite {bad or "OK"}')
        ok &= not bad
    groups = {'tp_ch_t1': [s for s in S if s.name in ('tp_ch_poly', 'tp_ch_ndiff', 'tp_ch_pdiff')],
              'tp_ch_t2': [s for s in S if s.name in ('tp_ch_mcon', 'tp_ch_via1', 'tp_ch_via2')]}
    for nme, grp in groups.items():
        T = write_standalone(ly, grp, nme)
        bad = drc_lite(ly, T)
        print(f'{nme}: drc_lite {bad or "OK"}')
        ok &= not bad
        (OUT / f'{nme}.json').write_text(json.dumps([s.info() for s in grp], ensure_ascii=False, indent=1))
    if no_run:
        return
    if not ok:
        print('drc_lite 위반 — 제출 안 함'); return
    jobs = {nme: submit(nme) for nme in groups}
    for nme, jid in jobs.items():
        bad, lvs = summary(wait(jid))
        print(f'[{nme}] job {jid}: DRC 밀도 말고 {len(bad)} 규칙 {bad[:20]} | LVS {lvs}')


if __name__ == '__main__':
    _main(sys.argv[1:])
