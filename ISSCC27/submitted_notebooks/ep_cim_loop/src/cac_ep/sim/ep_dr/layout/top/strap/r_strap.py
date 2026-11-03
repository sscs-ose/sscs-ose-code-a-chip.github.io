"""덧대기 배열 선 저항 계산 — gen_arr_1t1r_w3s.py 의 도형 상수를 읽어 저항망을 풀고, 행·열 끝-끝 저항과 SPICE 용 셀 토막 저항을 낸다.
저항 값 근거 (공개 PDK 파일, SkyWater PDK Authors, Apache-2.0):
  volare sky130A (c6d73a35) libs.ref/sky130_fd_sc_hvl/techlef/sky130_fd_sc_hvl__rram__{nom,max}.tlef  — RRAM 공정판 tech LEF
  nom: met1·met2 0.125 Ω/sq, met3·met4 0.047 Ω/sq, via1 9.0 Ω (RRAM 판; 일반판은 4.5), via2·via3 3.41 Ω
  max: met1·met2 0.145, met3·met4 0.056, via1 30.0, via2·via3 8.0
  같은 값이 libs.tech/magic/sky130A.tech 의 resist (allm1 125, allm3 47 mΩ/sq)·contact (via3 3410 mΩ) 에도 있다.
모형: 금속은 길이 방향 1 차원 막대 (R = ρs·길이/폭), via 는 배열마다 병렬 (R/n) 로 한 점에 모음. 셀 안 met2 pad 를 지나는 짧은 옆길도 넣음.
쓰임: python r_strap.py [NR NC]  → 표 출력 + r_strap.json
"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

H = Path(__file__).resolve().parent
sp = importlib.util.spec_from_file_location('g', H / 'gen_arr_1t1r_w3s.py'); g = importlib.util.module_from_spec(sp); sp.loader.exec_module(g)
NR, NC = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (128, 64)
CORNER = dict(nom=dict(m12=0.125, m34=0.047, v1=9.0, v2=3.41, v3=3.41),
              max=dict(m12=0.145, m34=0.056, v1=30.0, v2=8.0, v3=8.0))


class Net:
    def __init__(s):
        s.n = 0; s.e = []

    def node(s):
        s.n += 1; return s.n - 1

    def r(s, a, b, R):
        s.e.append((a, b, R))

    def solve(s, src):
        G = np.zeros((s.n, s.n))
        for a, b, R in s.e:
            c = 1 / R; G[a, a] += c; G[b, b] += c; G[a, b] -= c; G[b, a] -= c
        G[src, :] = 0; G[src, src] = 1                         # src 를 0 V 로 묶고, 나머지 노드는 1 A 를 하나씩 넣는 대신 역행렬 한 번
        return G

    def rmat(s, src, sinks):
        G = s.solve(src); out = []
        for k in sinks:
            b = np.zeros(s.n); b[k] = 1.0                      # k 에 1 A 주입, src 로 빠짐 → V(k) = R(src, k)
            out.append(np.linalg.solve(G, b)[k])
        return np.array(out)


def chain(net, pos, rho, width_of):
    """pos (nm, 정렬) 에 노드를 두고 이웃끼리 막대 저항으로 잇는다. width_of(x0, x1) → 그 구간 폭 (nm)."""
    ids = [net.node() for _ in pos]
    for i in range(len(pos) - 1):
        dx = pos[i + 1] - pos[i]
        if dx > 0:
            net.r(ids[i], ids[i + 1], rho * dx / width_of(pos[i], pos[i + 1]))
        else:
            net.r(ids[i], ids[i + 1], 1e-9)
    return dict(zip(pos, ids))


def row(cr):
    xr = (NC - 1) * g.PX + 2665
    xw, xe = -g.EXT_L, xr + g.EXT_R                            # 행 띠 양 끝 (서쪽 = 입력 구동 핀, 동쪽 = row MUX)
    x3a, x3b, x3e = -g.EXT_L + g.INSET, xr - g.R3_XE_BACK, xr + g.EXT_R - g.INSET
    v0 = x3a + 100; nv = (x3e - 100 - 200 - v0) // g.V2R_P + 1
    xv = [v0 + 100 + g.V2R_P * k for k in range(nv)]           # via2 중심
    xt = [c * g.PX + 2505 for c in range(NC)]                  # 셀 riser 중심 = 셀이 행에 닿는 곳
    wb = g.ROW_BAND[1] - g.ROW_BAND[0]
    net = Net()
    p2 = sorted(set([xw, xe] + xv + xt))
    n2 = chain(net, p2, cr['m12'], lambda a, b: wb)
    p3 = sorted(set(xv + [x3b]))
    w3 = lambda a, b: (g.R3_Y[1] - g.R3_Y[0]) if b <= x3b else (g.R3_YE[1] - g.R3_YE[0])
    n3 = chain(net, p3, cr['m34'], w3)
    for x in xv:
        net.r(n2[x], n3[x], cr['v2'])
    taps = [n2[x] for x in xt]
    Rw = net.rmat(n2[xw], taps + [n2[xe]])                     # 서쪽 끝에서 각 셀·동쪽 끝까지
    Re = net.rmat(n2[xe], taps)
    L0 = (xe - xw) / 1000
    return dict(L_um=L0, R_ee=Rw[-1], R_w_tap=Rw[:-1], R_e_tap=Re, R_bare=cr['m12'] * (xe - xw) / wb, nvia2=nv * NR)


def col(cr):
    y0, y1 = -g.EXT_B, (NR - 1) * g.PY + 635                   # 열 met1 아래 끝 (핀, 열 MUX) · 위 끝
    yt = [r * g.PY + 490 for r in range(NR)]                   # 셀 source 막대 = 셀이 열에 닿는 곳
    ys1 = [r * g.PY + 825 for r in range(NR)]                  # 셀 안 via1 배열 중심 (110..1540)
    ys4 = [r * g.PY + 1250 for r in range(NR)]                 # via2·via3 배열 중심 (950..1550)
    yb1, yb4 = -1650, -1980                                    # 아래 끝 stack via1 중심 · via2/3 중심
    wc = g.COL_X[1] - g.COL_X[0]

    def w1(a, b):                                              # met1 폭: pad 구간은 pad 폭, 아니면 열선 0.24
        m = (a + b) / 2; rr = np.floor(m / g.PY); yl = m - rr * g.PY
        if 0 <= rr < NR and g.M1P[1] <= yl <= g.M1P[3]:
            return g.M1P[2] - g.M1P[0]
        if g.M1S[1] <= m <= g.M1S[3]:
            return g.M1S[2] - g.M1S[0]
        return wc
    net = Net()
    edges = [g.M1S[1], g.M1S[3]] + [r * g.PY + e for r in range(NR) for e in (g.M1P[1], g.M1P[3]) if r * g.PY + e <= y1]
    p1 = sorted(set([y0, y1, yb1] + yt + ys1 + edges))
    n1 = chain(net, p1, cr['m12'], w1)
    p4 = sorted(set([yb4] + ys4))
    n4 = chain(net, p4, cr['m34'], lambda a, b: g.C4_X[1] - g.C4_X[0])
    nv1, nv23 = len(g.V1C) * len(g.V1R), len(g.V23C) * len(g.V23R)
    nv1s, nv23s = len(g.V1SC) * len(g.V1SR), len(g.V23SC) * len(g.V23SR)
    rpad = cr['m12'] * (1250 - 825) / (g.M2P[2] - g.M2P[0])  # met2 pad 안 옆길 (via1 중심 → via2 중심)
    rpads = cr['m12'] * (1980 - 1650) / (g.M2S[2] - g.M2S[0])
    Rst = cr['v1'] / nv1 + rpad + cr['v2'] / nv23 + cr['v3'] / nv23
    Rsb = cr['v1'] / nv1s + rpads + cr['v2'] / nv23s + cr['v3'] / nv23s
    for a, b in zip(ys1, ys4):
        net.r(n1[a], n4[b], Rst)
    net.r(n1[yb1], n4[yb4], Rsb)
    taps = [n1[y] for y in yt]
    Rs = net.rmat(n1[y0], taps + [n1[y1]])
    return dict(L_um=(y1 - y0) / 1000, R_ee=Rs[-1], R_s_tap=Rs[:-1], R_bare=cr['m12'] * (y1 - y0) / wc, R_stack=Rst, R_stack_end=Rsb,
                nvia=(nv1, nv23, nv23), nvia_end=(nv1s, nv23s, nv23s))


def chain2(R):
    """SPICE 사슬 모형: 핀 → 셀 0 = R0, 셀 k → k+1 = r (모두 같음). 양 끝 (셀 0, 셀 N−1) 을 정확히 맞추고, 가운데 셀 오차를 함께 낸다."""
    k = np.arange(len(R)); R0 = R[0]; r = (R[-1] - R[0]) / (len(R) - 1)
    return r, R0, np.max(np.abs(R - (R0 + r * k)))


if __name__ == '__main__':
    out = {}
    for cn, cr in CORNER.items():
        rw, cl = row(cr), col(cr)
        ar, br, er = chain2(rw['R_w_tap']); ac, bc, ec = chain2(cl['R_s_tap'])
        Rtail = rw['R_ee'] - br - ar * (NC - 1)               # 셀 63 → 동쪽 끝
        bare_r, bare_c = cr['m12'] * g.PX / (g.ROW_BAND[1] - g.ROW_BAND[0]), cr['m12'] * g.PY / (g.COL_X[1] - g.COL_X[0])
        out[cn] = dict(row=dict(L_um=rw['L_um'], R_bare=rw['R_bare'], R_ee=rw['R_ee'], R_w_to_last=rw['R_w_tap'][-1], R_e_to_first=rw['R_e_tap'][0],
                                R_w_to_first=rw['R_w_tap'][0], r_cell=ar, R_end_W=br, R_end_E=Rtail, chain_err=er, r_cell_bare=bare_r),
                       col=dict(L_um=cl['L_um'], R_bare=cl['R_bare'], R_ee=cl['R_ee'], R_s_to_last=cl['R_s_tap'][-1], R_s_to_first=cl['R_s_tap'][0],
                                r_cell=ac, R_end_S=bc, chain_err=ec, r_cell_bare=bare_c, R_stack=cl['R_stack'], R_stack_end=cl['R_stack_end']))
        o = out[cn]
        print(f"[{cn}] 행 (길이 {rw['L_um']:.2f} µm): 덧대기 전 {rw['R_bare']:.1f} Ω → 끝-끝 {rw['R_ee']:.2f} Ω, 서쪽 핀→셀63 {o['row']['R_w_to_last']:.2f}, "
              f"동쪽 끝→셀0 {o['row']['R_e_to_first']:.2f}, 서쪽 핀→셀0 {o['row']['R_w_to_first']:.3f} | 사슬 모형: 서쪽 끝 {br:.3f} + 셀 토막 {ar:.4f} × {NC - 1} + 동쪽 끝 {Rtail:.3f} Ω (덧대기 전 셀 토막 {bare_r:.3f}), 가운데 셀 오차 ≤ {er:.3f} Ω")
        print(f"[{cn}] 열 (길이 {cl['L_um']:.2f} µm): 덧대기 전 {cl['R_bare']:.1f} Ω → 끝-끝 {cl['R_ee']:.2f} Ω, 남쪽 핀→셀127 {o['col']['R_s_to_last']:.2f}, "
              f"남쪽 핀→셀0 {o['col']['R_s_to_first']:.3f} | 사슬 모형: 남쪽 끝 {bc:.3f} + 셀 토막 {ac:.4f} × {NR - 1} Ω (덧대기 전 셀 토막 {bare_c:.3f}), 가운데 셀 오차 ≤ {ec:.3f} Ω, "
              f"stack 셀 {cl['R_stack']:.3f} / 아래 끝 {cl['R_stack_end']:.3f} Ω")
    (H / 'r_strap.json').write_text(json.dumps(out, indent=1, default=float) + '\n')


def ladder2(N, r_lo, r_hi, r_via, r_pin_lo, r_end=None):
    """SPICE 두 줄 사다리 확인용: 아래 금속 (셀마다 r_lo) · 덧댄 금속 (r_hi) · 셀마다 via 다리 r_via. 핀은 아래 금속 끝 (핀 → 셀 0 = r_pin_lo).
    r_end 가 있으면 핀 → 덧댄 금속 셀 0 노드로 가는 다리를 하나 더 (열 아래 끝 stack). 반환 = 핀 → 셀 N−1 (아래 금속) 저항."""
    net = Net(); pin = net.node(); lo = [net.node() for _ in range(N)]; hi = [net.node() for _ in range(N)]
    net.r(pin, lo[0], r_pin_lo)
    for i in range(N - 1):
        net.r(lo[i], lo[i + 1], r_lo); net.r(hi[i], hi[i + 1], r_hi)
    for i in range(N):
        net.r(lo[i], hi[i], r_via)
    if r_end:
        net.r(pin, hi[0], r_end)
    return net.rmat(pin, [lo[-1]])[0]


def spice_params(cr):
    nv2c = (row(cr)['nvia2'] / NR) / NC                        # 셀마다 via2 평균 개수
    rp = dict(r_m2=cr['m12'] * g.PX / (g.ROW_BAND[1] - g.ROW_BAND[0]), r_m3=cr['m34'] * g.PX / (g.R3_Y[1] - g.R3_Y[0]),
              r_via2=cr['v2'] / nv2c, r_pin_m2=cr['m12'] * (2505 + g.EXT_L) / (g.ROW_BAND[1] - g.ROW_BAND[0]))
    wpad = g.M1P[2] - g.M1P[0]; hp = g.M1P[3] - g.M1P[1]; wc = g.COL_X[1] - g.COL_X[0]
    nv1, nv23 = len(g.V1C) * len(g.V1R), len(g.V23C) * len(g.V23R)
    cp = dict(r_m1=cr['m12'] * ((g.PY - hp) / wc + hp / wpad), r_m4=cr['m34'] * g.PY / (g.C4_X[1] - g.C4_X[0]),
              r_stack=cr['v1'] / nv1 + cr['m12'] * 425 / (g.M2P[2] - g.M2P[0]) + 2 * cr['v2'] / nv23,
              r_pin_m1=cr['m12'] * (g.EXT_B + 490) / wc)
    nv1s, nv23s = len(g.V1SC) * len(g.V1SR), len(g.V23SC) * len(g.V23SR)
    cp['r_end'] = (cr['m12'] * ((g.M1S[1] + g.EXT_B) / wc + (-1650 - g.M1S[1]) / (g.M1S[2] - g.M1S[0]))   # 핀 → 아래 끝 via1 중심 (met1)
                   + cr['v1'] / nv1s + cr['m12'] * 330 / (g.M2S[2] - g.M2S[0]) + 2 * cr['v2'] / nv23s                     # stack
                   + cr['m34'] * (1980 + 1250) / (g.C4_X[1] - g.C4_X[0]))                                                # met4: 아래 끝 → 셀 0 stack
    return rp, cp


if __name__ == '__main__':
    for cn, cr in CORNER.items():
        rp, cp = spice_params(cr)
        Rr = ladder2(NC, rp['r_m2'], rp['r_m3'], rp['r_via2'], rp['r_pin_m2'])
        Rc = ladder2(NR, cp['r_m1'], cp['r_m4'], cp['r_stack'], cp['r_pin_m1'], cp['r_end'])
        print(f"[{cn}] SPICE 두 줄 사다리 — 행: met2 {rp['r_m2']:.4f} / met3 {rp['r_m3']:.4f} / via2 다리 {rp['r_via2']:.4f} Ω (셀마다), 핀→셀0 met2 {rp['r_pin_m2']:.3f} Ω "
              f"→ 서쪽 핀→셀63 {Rr:.2f} Ω")
        print(f"[{cn}] SPICE 두 줄 사다리 — 열: met1 {cp['r_m1']:.4f} / met4 {cp['r_m4']:.4f} / stack 다리 {cp['r_stack']:.4f} Ω (셀마다), 핀→셀0 met1 {cp['r_pin_m1']:.3f} Ω, "
              f"핀→met4 (아래 끝 stack) {cp['r_end']:.3f} Ω → 남쪽 핀→셀127 {Rc:.2f} Ω")
        d = json.loads((H / 'r_strap.json').read_text()); d[cn]['row']['ladder2'] = dict(rp, R_pin_to_last=Rr); d[cn]['col']['ladder2'] = dict(cp, R_pin_to_last=Rc)
        (H / 'r_strap.json').write_text(json.dumps(d, indent=1, default=float) + '\n')
