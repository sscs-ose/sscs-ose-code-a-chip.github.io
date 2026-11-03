"""ring oscillator 구조 셀 tp_ro (10/28) — sky130_fd_sc_hvl 5 V 표준 셀, 배선은 직접 그림.
사용자 요청: "ring 오실레이터는 들어가야하고". (처음 맡긴 하위 에이전트가 파일 없이 멈춰 조립 담당이 직접 씀.)

회로 (CDL 과 같음):
  NAND2 (A = fb, B = en) → inv_1 × 86 → fb   : 반전 단 87 (홀수) → en = 1 일 때 발진, en = 0 이면 멈춤 (NAND 출력 1 고정)
  fb → inv_1 (분리 buffer) → ck0 → dfrtp_1 × 8 (단마다 Q → inv_1 → D 로 ÷2, 다음 단 CLK = 앞 단 Q, RESET_B = rstb 공통) → q8 → buf_4 → out (÷256)
줄 배치 (줄 높이 4.07, 짝수 줄 R0 · 홀수 줄 R180 → 줄 경계마다 VSS / VDD 를 이웃 줄과 나눔, digital/hvl_cells_test.py 와 같은 met1 띠 ±0.625):
  줄 0     NAND + inv 20 (왼 → 오) + fill_1
  줄 1–3   inv 22 씩 (뱀: 1 은 오 → 왼, 2 는 왼 → 오, 3 은 오 → 왼). 줄 3 의 마지막 inv 출력 = fb
  줄 4–11  분주 한 단씩 (R0 줄: dfrtp → inv / R180 줄: inv ← dfrtp), 줄 4 맨 앞에 분리 buffer inv
  줄 12    buf_4 (출력)
배선: 이웃 inv 는 li1 다리 (Y → 다음 A, 틈 0.22), 줄 끝 넘김·되먹임·단 사이 = met2 세로, 단 안 Q̄ (inv Y → D) = met3 가로 (y 1.2),
  rstb = met3 가로 (줄마다 y 2.85) + 서쪽 met3 기둥, 전원 = 줄 경계 met1 띠 → 동쪽 met2 기둥 (VSS·VDD) → met3 동쪽 패드.
  핀 패드: 서쪽 en · rstb · out (met3), 동쪽 VSS · VDD (met3). 셀 폭 40.0 (tpcommon 약속).
쓰임: build(ly) → [tp_ro]. 단독 시험: /home/dave/work/projects/sern_hog_classab_opamp/sim/.venv/bin/python s_ro.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tpcommon import Struct, load_hvl, hvl_subckts, HVL_CDL, g, nm, db, write_standalone, run     # noqa: E402

RH = 4.07                 # 줄 높이
XR0 = 3.0                 # 줄 서쪽 끝
U = 0.48                  # 셀 폭 단위 (fill_1)
RW = 66 * U               # 줄 폭 31.68
Y0 = 0.70                 # 줄 0 아래 경계 (띠 −0.625 가 y ≥ 0 이 되게)
N_RO = [20, 22, 22, 22]   # 줄마다 inv 수 (줄 0 은 NAND 뒤)
N_DIV = 8
XS = 1.44                 # 분주 단 시작 x (XR0 기준)
SP_VSS, SP_VDD = (35.3, 36.1), (36.5, 37.3)     # 동쪽 전원 기둥 (met2)
XW = 40.0                 # 셀 동쪽 끝
FB_X = 2.2                # 되먹임 fb 세로 met2
RST_X = (1.6, 1.9)        # rstb 서쪽 기둥 (met3)
W = dict(inv_1=1.44, nand2_1=2.40, dfrtp_1=15.36, buf_4=4.80, fill_1=0.48, fill_2=0.96, fill_4=1.92, fill_8=3.84)


def _pins():
    t = HVL_CDL.read_text()
    return {n: re.search(r'^\.SUBCKT sky130_fd_sc_hvl__%s (.*)$' % n, t, re.M).group(1).split() for n in ('inv_1', 'nand2_1', 'dfrtp_1', 'buf_4')}


def build(ly):
    hv = load_hvl(ly)
    PIN = _pins()
    s = Struct(ly, 'tp_ro', source='layout/top/testpat/s_ro.py (sky130_fd_sc_hvl 셀, volare c6d73a35)')
    cdl, inst = [], [0]
    yr = lambda r: g(Y0 + r * RH)

    def place(name, r, x, conn=None):
        """셀 name 을 줄 r, 서쪽 끝 x (블록 좌표) 에. 반환: 셀 안 좌표 → 블록 좌표 함수."""
        w = W[name]
        if r % 2 == 0:
            s.c.insert(db.CellInstArray(hv[name].cell_index(), db.Trans(0, False, nm(g(x)), nm(yr(r)))))
            f = lambda xl, yl: (g(x + xl), g(yr(r) + yl))
        else:
            s.c.insert(db.CellInstArray(hv[name].cell_index(), db.Trans(2, False, nm(g(x + w)), nm(g(yr(r) + RH)))))
            f = lambda xl, yl: (g(x + w - xl), g(yr(r) + RH - yl))
        if conn is not None:
            pw = {'VGND': 'VSS', 'VNB': 'VSS', 'VPWR': 'VDD', 'VPB': 'VDD'}
            cdl.append(f'X{inst[0]} ' + ' '.join(pw.get(p, conn.get(p, '?')) for p in PIN[name]) + f' sky130_fd_sc_hvl__{name}')
            assert '?' not in cdl[-1], cdl[-1]
            inst[0] += 1
        return f

    def fill(r, x, units):
        for nme, u in (('fill_8', 8), ('fill_4', 4), ('fill_2', 2), ('fill_1', 1)):
            while units >= u:
                place(nme, r, x); x = g(x + u * U); units -= u
        return x

    def pick(p, top='met2'):
        """핀 li1 위 (x, y) 에 mcon + met1 패드 (+ via1 + met2, + via2 + met3)."""
        x, y = p
        s.cut('mcon', x, y, 0.17)
        if top == 'met1':
            s.box('met1', x - 0.145, y - 0.145, x + 0.145, y + 0.145); return
        s.box('met1', x - 0.16, y - 0.16, x + 0.16, y + 0.16)
        s.cut('via1', x, y, 0.15)
        h2 = 0.185 if top == 'met3' else 0.16
        s.box('met2', x - h2, y - h2, x + h2, y + h2)
        if top == 'met3':
            s.cut('via2', x, y, 0.20); s.box('met3', x - 0.25, y - 0.25, x + 0.25, y + 0.25)

    def v12(x, y):                                    # met1 → met2 via (패드 포함)
        s.box('met1', x - 0.16, y - 0.16, x + 0.16, y + 0.16); s.cut('via1', x, y, 0.15); s.box('met2', x - 0.16, y - 0.16, x + 0.16, y + 0.16)

    def v23(x, y):                                    # met2 → met3 via
        s.box('met2', x - 0.185, y - 0.185, x + 0.185, y + 0.185); s.cut('via2', x, y, 0.20); s.box('met3', x - 0.25, y - 0.25, x + 0.25, y + 0.25)

    def m(lay, a, b, w):                              # 두 점 사이 곧은 선 (가로 또는 세로)
        (x0, y0), (x1, y1) = a, b
        assert abs(x0 - x1) < 1e-9 or abs(y0 - y1) < 1e-9, (a, b)
        h = w / 2
        s.box(lay, min(x0, x1) - h, min(y0, y1) - h, max(x0, x1) + h, max(y0, y1) + h)

    def lbridge(f_y, f_a):                            # li1 다리 (셀 안 좌표 → 블록 좌표 함수 둘): 앞 셀 Y (1.20) ~ 다음 셀 A (0.25)
        (xa, ya), (xb, yb) = f_y(1.20, 1.55), f_a(0.25, 1.935)
        s.box('li1', xa, ya, xb, yb)

    # ── ring (줄 0–3)
    k = 0                                             # inv 번호 (1…86), 넷 n0 = NAND 출력, n86 = fb
    fN = place('nand2_1', 0, XR0, dict(A='fb', B='en', Y='n0'))
    prev = None                                       # 앞 inv 의 좌표 함수
    turn = {}
    for r, n in enumerate(N_RO):
        x_start = XR0 + (W['nand2_1'] if r == 0 else 0.0)
        for i in range(n):
            k += 1
            x = (x_start + i * W['inv_1']) if r % 2 == 0 else (XR0 + RW - (i + 1) * W['inv_1'])
            f = place('inv_1', r, x, dict(A=f'n{k - 1}', Y=('fb' if k == sum(N_RO) else f'n{k}')))
            if i == 0 and r == 0:
                # NAND Y → inv1 A: met1 꺾임 (NAND A 핀이 사이에 있어 li1 다리를 못 씀)
                py, pa = fN(1.345, 2.60), f(0.48, 1.74)
                pick(py, 'met1'); pick(pa, 'met1')
                m('met1', py, (pa[0], py[1]), 0.29); m('met1', (pa[0], py[1]), pa, 0.29)
            elif i == 0:
                turn[r] = f                           # 줄 넘김: 앞 줄 마지막 inv Y → 이 줄 첫 inv A (met2 세로)
                fy = prev
                if r % 2 == 1:                        # 동쪽 끝 넘김 (x 겹치는 곳)
                    xa = f(0.705 if r == 1 else 0.29, 0)[0]
                else:
                    xa = f(0.29, 0)[0]
                xl_prev = (xa - fy(0, 0)[0]) if (r - 1) % 2 == 0 else (fy(0, 0)[0] - xa)
                py = fy(xl_prev, 2.90); pa = f(f(0, 0)[0] - xa if r % 2 == 1 else xa - f(0, 0)[0], 1.74)
                assert abs(py[0] - pa[0]) < 1e-6, (r, py, pa)
                pick(py); pick(pa); m('met2', py, pa, 0.2)
            else:
                lbridge(prev, f)
            prev = f
    assert k == 86 and (1 + k) % 2 == 1, '반전 단 수는 홀수'
    fill(0, XR0 + W['nand2_1'] + N_RO[0] * W['inv_1'], 66 - 5 - 3 * N_RO[0])
    # fb: 줄 3 마지막 inv Y (서쪽 끝) → met1 → fb 세로 met2 (x 2.2) → 줄 0 NAND A, 줄 4 분리 buffer A
    pfb = prev(1.15, 2.90)
    pick(pfb, 'met1'); m('met1', pfb, (FB_X, pfb[1]), 0.29); v12(FB_X, pfb[1])
    pA = fN(2.125, 1.69); pick(pA); m('met2', (FB_X, pA[1]), pA, 0.2); m('met2', (FB_X, pA[1]), (FB_X, pfb[1]), 0.2)
    # en: 서쪽 패드 → via 쌓기 (x 1.5) → met1 → NAND B
    pB = fN(0.57, 1.74); pick(pB, 'met1')
    s.via(1.5, pB[1], 'met1', 'met3'); m('met1', (1.5, pB[1]), pB, 0.29)
    s.box('met3', 0.0, pB[1] - 0.25, 1.75, pB[1] + 0.25); s.sig_pin('en', pB[1])

    # ── 분주 (줄 4–11) + 출력 (줄 12)
    r0 = len(N_RO)
    fbuf = place('inv_1', r0, XR0, dict(A='fb', Y='ck0'))
    pa = fbuf(0.48, 1.74); pick(pa); m('met2', (FB_X, pfb[1]), (FB_X, pa[1]), 0.2); m('met2', (FB_X, pa[1]), pa, 0.2)
    rst_ys, prevQ = [], None
    for d in range(N_DIV):
        r = r0 + d
        xs = XR0 + XS
        clk = 'ck0' if d == 0 else f'q{d}'
        if r % 2 == 0:
            fD = place('dfrtp_1', r, xs, dict(CLK=clk, D=f'qb{d + 1}', RESET_B='rstb', Q=f'q{d + 1}'))
            fI = place('inv_1', r, xs + W['dfrtp_1'], dict(A=f'q{d + 1}', Y=f'qb{d + 1}'))
            lbridge_q = (fD(15.10, 1.55), fI(0.25, 1.935))
        else:
            fI = place('inv_1', r, xs, dict(A=f'q{d + 1}', Y=f'qb{d + 1}'))
            fD = place('dfrtp_1', r, xs + W['inv_1'], dict(CLK=clk, D=f'qb{d + 1}', RESET_B='rstb', Q=f'q{d + 1}'))
            lbridge_q = (fD(15.10, 1.55), fI(0.25, 1.935))
        s.box('li1', *lbridge_q[0], *lbridge_q[1])                     # Q → toggle inv A (li1 다리)
        if d > 0:
            fill(r, XR0, 3)
        fill(r, xs + W['dfrtp_1'] + W['inv_1'], 66 - 3 - 35)
        # CLK
        pc = fD(0.725, 1.70)
        if d == 0:                                                      # buffer Y → CLK (met1 꺾임)
            py = fbuf(1.15, 2.90); pick(py, 'met1'); pick(pc, 'met1')
            m('met1', py, (pc[0], py[1]), 0.29); m('met1', (pc[0], py[1]), pc, 0.29)
        else:                                                           # 앞 줄 Q → 이 줄 CLK (met2 세로 + 가로)
            pick(pc); m('met2', prevQ, (prevQ[0], pc[1]), 0.2); m('met2', (prevQ[0], pc[1]), pc, 0.2)
        # Q pickup (다음 줄로 올라감)
        pq = fD(15.12, 1.95); pick(pq)
        # Q̄: inv Y → D (met3 가로)
        pd, piy = fD(3.58, 1.20), fI(1.18, 1.20)
        pick(pd, 'met3'); pick(piy, 'met3'); m('met3', pd, piy, 0.3)
        # RESET_B: li1 핀 (2.695–3.235 × 1.62–2.49) 위 끝에 mcon (y 2.405) — 셀 안 met1 줄 (x 2.015–9.985, y 1.92–2.15) 은
        # RESET_B 가 아닌 내부 넷이라 피함 (첫 판 잡 721321 에서 rstb 가 내부 넷과 단락). met1 을 위로 늘려 via1·via2 (y 2.85) → met3 가로 → 서쪽 rstb 기둥
        prb = fD(2.965, 2.405)
        s.cut('mcon', prb[0], prb[1], 0.17)
        pr2 = fD(2.965, 2.85)
        ya, yb = sorted((fD(0, 2.29)[1], fD(0, 3.01)[1]))
        s.box('met1', prb[0] - 0.145, ya, prb[0] + 0.145, yb)
        s.cut('via1', pr2[0], pr2[1], 0.15); v23(*pr2)
        m('met3', (RST_X[0], pr2[1]), pr2, 0.3); rst_ys.append(pr2[1])
        prevQ = pq
    # rstb 기둥 + 서쪽 패드
    s.box('met3', RST_X[0], min(rst_ys) - 0.15, RST_X[1], max(rst_ys) + 0.15)
    s.box('met3', 0.0, rst_ys[0] - 0.25, RST_X[1], rst_ys[0] + 0.25); s.sig_pin('rstb', rst_ys[0])
    # 출력 줄
    r = r0 + N_DIV
    assert r % 2 == 0
    fill(r, XR0, 3)
    fB = place('buf_4', r, XR0 + XS, dict(A=f'q{N_DIV}', X='out'))
    fill(r, XR0 + XS + W['buf_4'], 66 - 3 - 10)
    pa = fB(4.05, 1.95); pick(pa); m('met2', prevQ, (prevQ[0], pa[1]), 0.2); m('met2', (prevQ[0], pa[1]), pa, 0.2)
    px = fB(0.50, 1.665); pick(px, 'met3'); s.box('met3', 0.0, px[1] - 0.25, px[0] + 0.25, px[1] + 0.25); s.sig_pin('out', px[1])

    # ── 전원: 줄 경계 met1 띠 (±0.625) → 동쪽 met2 기둥 → met3 동쪽 패드
    nb = r + 1
    for b in range(nb + 1):
        yb = yr(b)
        s.box('met1', XR0, yb - 0.625, SP_VDD[1], yb + 0.625)
        sp = SP_VSS if b % 2 == 0 else SP_VDD
        for dy in (-0.25, 0.25):
            s.cut('via1', (sp[0] + sp[1]) / 2, yb + dy, 0.15)
    for sp in (SP_VSS, SP_VDD):
        s.box('met2', sp[0], yr(0) - 0.625, sp[1], yr(nb) + 0.625)
    for net, sp, y in (('VSS', SP_VSS, yr(0) + 2.0), ('VDD', SP_VDD, yr(1) + 2.0)):
        xc = g((sp[0] + sp[1]) / 2)
        s.cut('via2', xc, y, 0.20); s.box('met3', xc - 0.25, y - 0.25, XW, y + 0.25)
        s.pwr_pin(net, XW, y)
    s.cdl = cdl
    s.extra = hvl_subckts(['inv_1', 'nand2_1', 'dfrtp_1', 'buf_4'])
    s.contents = (f'ring oscillator (hvl 5 V): NAND2 enable + inv_1 × {k} = 반전 {k + 1} 단, 분리 inv → dfrtp_1 × {N_DIV} (÷{2 ** N_DIV}) → buf_4; '
                  f'핀 en (1 = 발진), rstb (0 = 분주 reset), out (÷{2 ** N_DIV})')
    return [s.check()]


if __name__ == '__main__':
    ly = db.Layout(); ly.dbu = 0.001
    S = build(ly)
    for st in S:
        print(st.name, st.bbox(), st.ports, len(st.cdl), 'inst')
    write_standalone(ly, S, 'tp_ro_t')
    if '--no-run' not in sys.argv:
        run('tp_ro_t')
