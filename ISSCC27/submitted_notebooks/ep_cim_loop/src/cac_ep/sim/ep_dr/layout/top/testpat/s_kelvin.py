"""Kelvin 4 단자 sheet 저항 구조 셀 (10/28) — test pattern 용. 셀 이름 tp_kv_<종류>_<l|s>.

구조 하나 = 한 줄 저항을 직렬 3 토막으로 (서 → 동):
    F1 머리 — 이음 토막 (R0) — S1 머리 — 재는 몸통 (R1) — S2 머리 — 이음 토막 (R2) — F2 머리
  머리마다 접촉 (+ via 쌓기) → met3 팔 (아래로) → met3 레인 (서쪽) → 서쪽 변 met3 패드 f1·s1·s2·f2.
  레인은 줄 아래: f1 이 줄에 가장 가깝고 f2 가 가장 아래. 레인 k 는 x 0 … 머리 k 까지만 가므로 팔·레인이 서로 건너지 않음
  (met3 저항도 같은 met3 로 그대로 됨). 기판 p-tap 은 동쪽 끝 → VSS 패드 (동쪽 변). PD 는 nwell + ntap → VDD 패드 (동쪽 변).
  힘 (force) 전류는 f1 → f2, 전압은 s1 − s2 → R1 = Rs · L / W (머리 끝 효과는 l·s 두 판의 차로 뺌).

종류 (KINDS): poly 정밀 저항 res_high_po_0p35·1p41 (rpm), res_xhigh_po_0p35·1p41 (urpm), RES_GENERIC_ND (n+ diff, hvi 밖),
  RES_GENERIC_PD (p+ diff in nwell), res_generic_m1·m2·m3 (금속 표지 68/13·69/13·70/13, 몸통은 세로 줄로 접음).
LVS 덱 (testpat/sky130_tp.lvs.pvl) 계산과 같게:
  - poly: 몸통 = (poly_res 에 닿는 poly) ∩ psdm ∩ npc − li1 → 머리 li1 이 poly 폭 전체 × 머리 길이를 덮음. W = 0.35/1.41, L = 몸통 길이.
  - diff·금속: 몸통 = 표지 (65/13·68/13 …) 자체 → 표지를 diff/금속 폭에 꼭 맞게. W = 단자와 겹치는 변 / 2 = 폭, L = 면적 / W.
    접은 금속 몸통은 폭 W 상자 (세로 줄 + 꺾임 이음) 를 겹치지 않게 이어 L = Σ 상자 길이 (nm 까지 정확).
DRC 를 위해 지킨 것 (rev 0.0_2.12): rpm/urpm 폭 ≥ 1.27, rpm·psdm 이 몸통을 0.2 감쌈, npc 0.1, 정밀 몸통 ≥ 0.66 (이음 토막 2.0),
  bar licon 0.19 × 2.0 (머리 2.16, WU rbank 값), poly_res ↔ tap ≥ 0.48, rpm 안에 사각 licon 없음 (tap 은 rpm 밖),
  diff 머리 0.5 · licon 2 개 (clamp_d2r 값), 금속 표지는 금속 폭에 꼭 맞게 (m*.res 경고), p-tap 은 파이프라인 시험 셀과 같은 꼴.
CDL 표기 (이미 MATCH 된 것과 같게): poly `R0 a b $SUB=VSS $[res_xhigh_po_0p35] w=0.350u l=2.000u`,
  diff `R0 a b 240 $[RES_GENERIC_ND] $W=1u $L=2u`, 금속 `R0 a b $[res_generic_m1] $W=0.4u $L=2u`.
쓰임: build(ly) → list[Struct] (import 때 파일 쓰기·실행 없음).
단독 시험: /home/dave/work/projects/sern_hog_classab_opamp/sim/.venv/bin/python s_kelvin.py [t1 t2 t3 tneg]
  t1 = poly 4 종 (l), t2 = ND·PD·m1·m2·m3 (l), t3 = 모든 s 판, tneg = m1 (l) 에 재는 몸통 L 을 10 % 틀린 CDL (MISMATCH 가 나와야 함).
"""
import sys

from tpcommon import Struct, write_standalone, submit, wait, summary, g, OUT

SRC = 'layout/top/testpat/s_kelvin.py'
CELL_W = 40.0                 # 셀 폭 (동쪽 끝 = VSS·VDD 패드 끝)
X0 = 2.0                      # 줄 서쪽 끝
Y_LINE = 4.75                 # 줄 중심 y
LANE_DY0, LANE_P, LANE_H = 1.5, 1.0, 0.5    # 첫 레인 (f1) 은 줄 중심에서 1.5 아래, 레인 간격 1.0, 레인 높이 = 패드 높이
ARM_W = 0.4                   # met3 팔 폭
TAP_X = 38.0                  # p-tap 중심 x
LINK = 2.0                    # 이음 토막 길이 (poly 정밀 최소 0.66 이상)
HEAD = dict(poly=2.16, diff=0.5, metal=0.8)  # 머리 길이: poly = bar licon 2.0 + 0.08 × 2, diff = clamp 머리, 금속 = via 패드 + 여유
BODY = dict(poly=dict(l=20.0, s=10.0), diff=dict(l=20.0, s=10.0), metal=dict(l=28, s=14))   # 금속은 세로 줄 수 (짝수)
MEANDER_H = 8.0               # 금속 세로 줄 길이

KINDS = {
    'hpo0p35': dict(fam='poly', W=0.35, imp='rpm', model='res_high_po_0p35', rs=320.0),
    'hpo1p41': dict(fam='poly', W=1.41, imp='rpm', model='res_high_po_1p41', rs=320.0),
    'xpo0p35': dict(fam='poly', W=0.35, imp='urpm', model='res_xhigh_po_0p35', rs=2000.0),
    'xpo1p41': dict(fam='poly', W=1.41, imp='urpm', model='res_xhigh_po_1p41', rs=2000.0),
    'nd': dict(fam='diff', W=1.0, model='RES_GENERIC_ND', rs=120.0),
    'pd': dict(fam='diff', W=1.0, model='RES_GENERIC_PD', rs=197.0),
    'm1': dict(fam='metal', W=0.4, sp=0.4, lay='met1', mark='met1_res', model='res_generic_m1', rs=0.125),
    'm2': dict(fam='metal', W=0.4, sp=0.4, lay='met2', mark='met2_res', model='res_generic_m2', rs=0.125),
    'm3': dict(fam='metal', W=0.4, sp=0.4, lay='met3', mark='met3_res', model='res_generic_m3', rs=0.047),
}
ORDER = ['hpo0p35', 'hpo1p41', 'xpo0p35', 'xpo1p41', 'nd', 'pd', 'm1', 'm2', 'm3']
PORTS = ['f1', 's1', 's2', 'f2']


def fmt(v):
    return f'{v:.3f}'.rstrip('0').rstrip('.')


def ohm(r):
    return f'{r / 1e3:.1f} kΩ' if r >= 1e3 else f'{r:.1f} Ω'


def _tap(s, yt):
    """기판 p-tap (VSS): tap 1.0 × 0.5, licon 2 개, li1 → met3 via 쌓기 → 동쪽 변 VSS 패드."""
    s.box('tap', TAP_X - 0.5, yt - 0.25, TAP_X + 0.5, yt + 0.25)
    s.box('psdm', TAP_X - 0.625, yt - 0.375, TAP_X + 0.625, yt + 0.375)
    s.box('li1', TAP_X - 0.5, yt - 0.25, TAP_X + 0.5, yt + 0.25)
    for dx in (-0.24, 0.24):
        s.cut('licon', TAP_X + dx, yt, 0.17)
    s.via(TAP_X, yt, 'li1', 'met3')
    s.box('met3', TAP_X - 0.25, yt - 0.25, CELL_W, yt + 0.25)
    s.pwr_pin('VSS', CELL_W, yt)


def kv(ly, key, ver):
    """Kelvin 구조 셀 하나. key = KINDS 이름, ver = 'l' (긴 몸통) / 's' (짧은 몸통)."""
    k = KINDS[key]
    fam, W = k['fam'], k['W']
    s = Struct(ly, f'tp_kv_{key}_{ver}', source=SRC)
    yl, hw = Y_LINE, k['W'] / 2
    hd = HEAD[fam]
    # ── 토막 x 구간
    if fam == 'metal':
        n, p = BODY['metal'][ver], W + k['sp']
        bx = g((n - 1) * p + W)                                  # 접은 몸통의 x 폭
        lb = g(n * MEANDER_H + (n - 1) * (p - W))                # 몸통 L (= 면적 / W)
    else:
        bx = lb = BODY[fam][ver]
    xs = [X0]
    for d in (hd, LINK, hd, bx, hd, LINK, hd):
        xs.append(g(xs[-1] + d))
    heads = [(xs[0], xs[1]), (xs[2], xs[3]), (xs[4], xs[5]), (xs[6], xs[7])]      # f1, s1, s2, f2
    bodies = [(xs[1], xs[2]), (xs[3], xs[4]), (xs[5], xs[6])]                      # R0, R1 (재는 몸통), R2
    Ls = [LINK, lb, LINK]
    x_e = xs[7]
    yb0, yb1 = g(yl - hw), g(yl + hw)

    if fam == 'poly':
        s.box('poly', X0, yb0, x_e, yb1)
        for (a, b) in bodies:
            s.box('poly_res', a, yb0, b, yb1)
        for (a, b) in heads:
            s.box('li1', a, yb0, b, yb1)                         # 머리 = poly 폭 전체를 li1 로 (덱 몸통 = poly − li1)
            ys = [yl] if W < 1.0 else [yl - 0.35, yl + 0.35]     # 1.41 은 bar 2 개 (옆 간격 0.51)
            for y in ys:
                s.box('licon', a + 0.08, y - 0.095, b - 0.08, y + 0.095)
        e = max(hw + 0.20, 0.65)                                  # rpm/urpm 폭 ≥ 1.27
        s.box(k['imp'], X0 - 0.20, yl - e, x_e + 0.20, yl + e)
        s.box('psdm', X0 - 0.20, yl - e, x_e + 0.20, yl + e)
        s.box('npc', X0 - 0.10, yb0 - 0.10, x_e + 0.10, yb1 + 0.10)
        lo = 'li1'
    elif fam == 'diff':
        s.box('diff', X0, yb0, x_e, yb1)
        for (a, b) in bodies:
            s.box('diff_res', a, yb0, b, yb1)
        for (a, b) in heads:
            xc = g((a + b) / 2)
            for dy in (-0.24, 0.24):
                s.cut('licon', xc, yl + dy, 0.17)
            s.box('li1', xc - 0.165, yl - 0.405, xc + 0.165, yl + 0.405)
        imp = 'nsdm' if key == 'nd' else 'psdm'
        s.box(imp, X0 - 0.125, yb0 - 0.125, x_e + 0.125, yb1 + 0.125)
        if key == 'pd':                                          # p+ diff 는 nwell 안, ntap → VDD
            xt0, xt1 = g(x_e + 0.8), g(x_e + 1.8)
            s.box('nwell', X0 - 0.40, yb0 - 0.40, xt1 + 0.40, yb1 + 0.40)
            s.box('tap', xt0, yl - 0.25, xt1, yl + 0.25)
            s.box('nsdm', xt0 - 0.125, yl - 0.375, xt1 + 0.125, yl + 0.375)
            s.box('li1', xt0, yl - 0.25, xt1, yl + 0.25)
            xtc = g((xt0 + xt1) / 2)
            for dx in (-0.24, 0.24):
                s.cut('licon', xtc + dx, yl, 0.17)
            s.via(xtc, yl, 'li1', 'met3')
            s.box('met3', xtc - 0.25, yl - 0.25, CELL_W, yl + 0.25)
        lo = 'li1'
    else:
        lay, mk = k['lay'], k['mark']
        for (a, b) in heads:
            s.box(lay, a, yb0, b, yb1)
        for (a, b) in (bodies[0], bodies[2]):                    # 곧은 이음 토막
            s.box(lay, a, yb0, b, yb1)
            s.box(mk, a, yb0, b, yb1)
        xb0 = bodies[1][0]
        yt = g(yb0 + MEANDER_H)
        for i in range(n):                                       # 세로 줄 i (짝수 = 위로, 홀수 = 아래로), 꺾임 이음은 위·아래 번갈아
            xi = g(xb0 + i * p)
            for r in [(xi, yb0, xi + W, yt)] + ([] if i == n - 1 else
                                                 [(xi + W, yt - W, g(xb0 + (i + 1) * p), yt) if i % 2 == 0 else
                                                  (xi + W, yb0, g(xb0 + (i + 1) * p), yb0 + W)]):
                s.box(lay, *r)
                s.box(mk, *r)
        assert abs(g(xb0 + (n - 1) * p + W) - bodies[1][1]) < 1e-6
        lo = None if lay == 'met3' else lay

    # ── 머리 → met3 팔 → 레인 → 서쪽 패드
    for j, (port, (a, b)) in enumerate(zip(PORTS, heads)):
        xc = g((a + b) / 2)
        if lo:
            s.via(xc, yl, lo, 'met3')
        y = g(yl - LANE_DY0 - j * LANE_P)
        s.box('met3', xc - ARM_W / 2, y - LANE_H / 2, xc + ARM_W / 2, yl)
        s.box('met3', 0.0, y - LANE_H / 2, xc + ARM_W / 2, y + LANE_H / 2)
        s.sig_pin(port, y)
    _tap(s, g(yl - LANE_DY0 - LANE_P))
    if key == 'pd':
        s.pwr_pin('VDD', CELL_W, yl)

    # ── CDL + 설명
    nets = [('f1', 's1'), ('s1', 's2'), ('s2', 'f2')]
    rr = [k['rs'] * L / W for L in Ls]
    for i, ((na, nb), L, r) in enumerate(zip(nets, Ls, rr)):
        if fam == 'poly':
            s.cdl.append(f"R{i} {na} {nb} $SUB=VSS $[{k['model']}] w={W:.3f}u l={L:.3f}u")
        elif fam == 'diff':
            s.cdl.append(f"R{i} {na} {nb} {r:.0f} $[{k['model']}] $W={fmt(W)}u $L={fmt(L)}u")
        else:
            s.cdl.append(f"R{i} {na} {nb} $[{k['model']}] $W={fmt(W)}u $L={fmt(L)}u")
    s.kv = dict(model=k['model'], W=W, L=Ls, R=[round(r, 2) for r in rr], rs=k['rs'])
    s.contents = (f"Kelvin 4 단자 {k['model']} W {fmt(W)}: R0 f1–s1 L {fmt(LINK)} / R1 s1–s2 (재는 몸통) L {fmt(lb)} "
                  f"≈ {ohm(rr[1])} ({k['rs']:g} Ω/□) / R2 s2–f2 L {fmt(LINK)}; 힘 f1→f2, 전압 s1−s2"
                  + ('; 몸통은 세로 줄 %d 개로 접음' % n if fam == 'metal' else ''))
    return s.check()


def build(ly, kinds=None, vers=('l', 's')):
    """Kelvin 구조 셀 전부 (기본: 9 종 × 긴·짧은 몸통 = 18 셀). 반환 순서 = 종류 순서, 같은 종류 안에서 l → s."""
    return [kv(ly, key, v) for key in (kinds or ORDER) for v in vers]


TESTS = {'t1': [f'{k}_l' for k in ORDER[:4]], 't2': [f'{k}_l' for k in ORDER[4:]], 't3': [f'{k}_s' for k in ORDER],
         'tneg': ['m1_l']}


def main(names):
    import klayout.db as db
    ly = db.Layout(); ly.dbu = 0.001
    by = {s.name[len('tp_kv_'):]: s for s in build(ly)}
    for s in by.values():
        print(f'{s.name:18s} {s.bbox()[2]:6.2f} x {s.bbox()[3]:6.2f}  {s.ports}  {s.cdl[1]}')
    jobs = []
    for t in names:
        tn = f'tp_kv_{t}'
        write_standalone(ly, [by[x] for x in TESTS[t]], tn)
        if t == 'tneg':                                          # 재는 몸통 L 을 10 % 길게 (음성 시험)
            cdl = (OUT / f'{tn}.cdl').read_text()
            good = by['m1_l'].cdl[1]
            L = by['m1_l'].kv['L'][1]
            bad = good.replace(f'$L={fmt(L)}u', f'$L={fmt(round(L * 1.1, 3))}u')
            assert bad != good and cdl.count(good) == 1
            (OUT / f'{tn}.cdl').write_text(cdl.replace(good, bad))
        jobs.append((tn, submit(tn)))
        print('submitted', tn, jobs[-1][1])
    for tn, jid in jobs:
        bad, lvs = summary(wait(jid))
        print(f'[{tn}] job {jid}: DRC 밀도 말고 {len(bad)} 규칙 {bad[:20]} | LVS {lvs}')


if __name__ == '__main__':
    main(sys.argv[1:] or ['t1', 't2', 't3', 'tneg'])
