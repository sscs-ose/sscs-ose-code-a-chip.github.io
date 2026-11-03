"""infer_deck.py 사본 + 배열 선 저항 (10/28, 사용자 "배열 선 저항 확인과 met3·met4 덧대는 줄 … 까지 해야 다 완성되는 거 아니야?").
infer_deck.py 는 행·열 선을 저항 0 으로 둔다. 여기서는 행 선 (met2 0.42 µm) 과 열 선 (met1 0.24 µm) 을 셀마다 한 토막씩 저항 사슬로 바꾼다.
- 배치 (layout/floorplan_opt_D3.json, gen_arr_1t1r_w3.py): 행 r 은 y 방향 r 번째, 열 c 는 x 방향 c 번째. 입력 구동 = 서쪽 (열 0 쪽 끝),
  row MUX·출력 읽기 = 동쪽 (열 63 쪽 끝), 열 MUX·은닉 clamp = 남쪽 (행 0 쪽 끝).
- 셀 (r, c) 은 행 r 의 c 번째 탭 ↔ 열 c 의 r 번째 탭 사이. 입력·bias 행은 스위치 출력 → R_drv (입력 구동 블록 안 배선) → 서쪽 끝.
- 남는 열은 남쪽 끝에서 Vcm. 안 쓰는 행 (WL off) 은 셀이 없어 열 사슬을 쓰는 행까지만 둔다.
- 기본값: 행 끝-끝 97.4 Ω (64 × 5.115 µm / 0.42 µm × 0.125 Ω/sq), 열 227 Ω (128 × 3.41 µm / 0.24 µm × 0.125 Ω/sq),
  R_drv 15 Ω (입력 구동 경로 1.7–15 Ω 중 가장 긴 값을 모든 행에).
쓰임: python infer_deck_wire.py write --key 5b_s0 --name infw_ns_s0   /   python infer_deck_wire.py compare --name infw_ns_s0 --ref inf_ns_s0
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from circuit import D_IS, D_N, NONE, V_REF, row_drive   # noqa: E402
from data import load_task                               # noqa: E402
from solver import solve                                 # noqa: E402
from spice_check import parse_ms0                        # noqa: E402
from train import layout_of                                    # noqa: E402

OLY = '/home/grads/s/seokjindaveoh/work'
NF = 'sky130_fd_pr__nfet_g5v0d10v5'
ap = argparse.ArgumentParser()
ap.add_argument('task', choices=['write', 'compare'])
ap.add_argument('--name', default='infw_ns_s0')
ap.add_argument('--weights', default=str(HERE.parent / 'out' / 'weights' / 'nostab_5bit.npz'))
ap.add_argument('--key', default='5b_s0')
ap.add_argument('--state', default='best')
ap.add_argument('--w_drv', type=float, default=1000.0)
ap.add_argument('--r_row', type=float, default=97.4, help='행 선 끝-끝 [Ω] (물리 열 수로 나눠 토막)')
ap.add_argument('--r_col', type=float, default=227.0, help='열 선 끝-끝 [Ω] (물리 행 수로 나눠 토막)')
ap.add_argument('--r_drv', type=float, default=15.0, help='스위치 출력 → 행 서쪽 끝 [Ω]')
ap.add_argument('--ref', default='inf_ns_s0', help='compare: 선 저항 없는 SPICE 결과 (같은 가중치)')
ap.add_argument('--diode', choices=['card', 'real'], default='card',
                help='은닉 clamp 다이오드: card = 덱 level-1 카드, real = SKY130 diode_pd2nw_11v0 (clamp_d2r 매크로 면적 2.548 µm² · 둘레 7.97 µm)')
ap.add_argument('--v_cl', type=float, default=None, help='clamp rail 크기 [V] (rail_up = −v_cl, rail_dn = +v_cl). 기본 = 학습 v_b')
ap.add_argument('--r_rail', type=float, default=0.0,
                help='입력 rail 패드 → 입력 구동 블록 [Ω] (VRAILP·VRAILM 각각, 최상위 배선. 10/28 route 보고: 선 길이 합 8.6·9.5 Ω)')
ap.add_argument('--lib', default=f'{OLY}/ep_demo/char/models/sky130_5v_tt.lib.spice')
a = ap.parse_args()
W = np.load(a.weights)
LAY = layout_of(W)
info = {i['key']: i for i in json.loads(str(W['info']))}[a.key]
c = info['config']
G = W[f'{a.key}/G_{a.state}']
X, y = load_task('t10k')
NR, NC = LAY.r_used, LAY.cols
rt = lambda r, k: f'rw{r}_{k}'                     # 행 r 의 k 번째 탭 (k = 열 번호)
ct = lambda cc, j: f'cw{cc}_{j}'                   # 열 cc 의 j 번째 탭 (j = 행 번호)
cn = lambda cc: f'c{cc}' if cc in LAY.c_h else '0'  # 열 남쪽 끝: 은닉 열 = clamp 노드, 남는 열 = Vcm
yo = lambda r: rt(r, NC - 1)                       # 출력 행을 읽는 끝 = 동쪽
v_cl = c['v_b'] if a.v_cl is None else a.v_cl
DMOD = 'dlv1' if a.diode == 'card' else 'sky130_fd_pr__diode_pd2nw_11v0 area=2.548e12 pj=7.97e6'   # SPICE 는 area·pj 를 1e-12·1e-6 배로 읽음 (clamp_diode_check.py)

if a.task == 'write':
    nf = max(1, int(round(a.w_drv / 5)))
    s_r, s_c = a.r_row / LAY.cols, a.r_col / LAY.rows
    L = [f"* {a.name}: free crossbar + input switches (W {a.w_drv:g} um) + wire R (row {a.r_row:g}, col {a.r_col:g}, drive {a.r_drv:g} ohm), "
         f"{a.key} {a.state}, MNIST test {len(y)}",
         '.option post=0 ingold=2 numdgt=10 measdgt=10 nomod',
         '.option relv=1e-9 relvdc=1e-9 absvdc=1e-12 reli=1e-9 absi=1e-15 itl1=2000 itl2=2000',
         '.temp 25', f".lib '{a.lib}' tt",
         f'.model dlv1 d (level=1 is={D_IS} n={D_N} rs=0)',
         f"Vrup vrup 0 {-v_cl:g}", f"Vrdn vrdn 0 {v_cl:g}", "Vss vss 0 -2.5", 'Vdum dum 0 0',
         f"Vraip raip0 0 {c['a']}", f"Vraim raim0 0 {-c['a']}",
         f"Rrailp raip0 raip {max(a.r_rail, 1e-6):g}", f"Rrailm raim0 raim {max(a.r_rail, 1e-6):g}"]
    if a.diode == 'real':
        L.insert(5, f".include '{OLY}/ep_dr/real_circuit/models/sky130_fd_pr__diode_pd2nw_11v0.model.spice'")
    for i in range(LAY.n_in):
        L += [f"Vgp{i} gp{i} 0 '2.5*(1+s{i})/2'", f"Vgm{i} gm{i} 0 '2.5*(1-s{i})/2'"]
        for r, (g_up, g_dn) in ((LAY.r_x[2 * i], (f'gp{i}', f'gm{i}')), (LAY.r_x[2 * i + 1], (f'gm{i}', f'gp{i}'))):
            L += [f"XDp{r} r{r} {g_up} raip vss {NF} w={a.w_drv:g} l=0.5 nf={nf}",
                  f"XDm{r} r{r} {g_dn} raim vss {NF} w={a.w_drv:g} l=0.5 nf={nf}"]
    L += [f"Vb{LAY.r_b[0]} r{LAY.r_b[0]} raip 0", f"Vb{LAY.r_b[1]} r{LAY.r_b[1]} raim 0"]
    driven = list(LAY.r_x) + list(LAY.r_b)
    if LAY.r_s is not None:
        L.append(f"Vst r{LAY.r_s} 0 0"); driven.append(LAY.r_s)
    L += [f"Rdrv{r} r{r} {rt(r, 0)} {a.r_drv + s_r / 2:.6g}" for r in driven]        # 서쪽 끝 → 첫 셀 (토막 반)
    L += [f"Rr{r}_{k} {rt(r, k)} {rt(r, k + 1)} {s_r:.6g}" for r in range(NR) for k in range(NC - 1)]
    L += [f"Rce{cc} {cn(cc)} {ct(cc, 0)} {s_c / 2:.6g}" for cc in range(NC)]           # 남쪽 끝 → 첫 셀
    L += [f"Rc{cc}_{j} {ct(cc, j)} {ct(cc, j + 1)} {s_c:.6g}" for cc in range(NC) for j in range(NR - 1)]
    for r, cc in zip(*np.nonzero(LAY.kind != NONE)):
        A, B = rt(r, cc), ct(cc, r)
        if c['r_on']:
            L.append(f"R_{r}_{cc} {A} m{r}_{cc} {c['r_on']}")
            A = f'm{r}_{cc}'
        L.append(f"G_{r}_{cc} {A} {B} CUR='{G[r, cc]:.12e}*{V_REF}*sinh((V({A})-V({B}))/{V_REF})'")
    nodes = [cn(cc) for cc in LAY.c_h] + ([] if c['no_out_clamp'] else [yo(r) for r in LAY.r_y])
    for nd in nodes:
        L += [f"Rda_{nd} {nd} da_{nd} {c['r_ser']}", f"Da_{nd} da_{nd} vrup {DMOD}",
              f"Db_{nd} vrdn db_{nd} {DMOD}", f"Rdb_{nd} db_{nd} {nd} {c['r_ser']}"]
    L += [f'.measure dc y{j} find v({yo(r)}) at=0' for j, r in enumerate(LAY.r_y)]
    L += [f'.measure dc x{k} find v({rt(r, 0)}) at=0' for k, r in enumerate(LAY.r_x[:4])]
    L += ['.measure dc irp find i(Vraip) at=0', '.measure dc irm find i(Vraim) at=0',
          '.measure dc vrp find v(raip) at=0', '.measure dc vrm find v(raim) at=0']   # rail 전류·블록 쪽 rail 전압
    # 선 위 전압 차: 입력 행 서쪽 끝 − 동쪽 끝, 은닉 열 남쪽 clamp 노드 − 맨 위 셀 탭, 출력 행 동쪽 − 서쪽
    L += [f"Edx{k} edx{k} 0 VOL='V({rt(r, 0)})-V({rt(r, NC - 1)})'" for k, r in enumerate(LAY.r_x)]
    L += [f"Edh{m} edh{m} 0 VOL='V({cn(cc)})-V({ct(cc, NR - 1)})'" for m, cc in enumerate(LAY.c_h)]
    L += [f"Edy{j} edy{j} 0 VOL='V({yo(r)})-V({rt(r, 0)})'" for j, r in enumerate(LAY.r_y)]
    L += [f'.measure dc dx{k} find v(edx{k}) at=0' for k in range(len(LAY.r_x))]
    L += [f'.measure dc dh{m} find v(edh{m}) at=0' for m in range(len(LAY.c_h))]
    L += [f'.measure dc dy{j} find v(edy{j}) at=0' for j in range(len(LAY.r_y))]
    L += ['.data d', '+ ' + ' '.join(f's{i}' for i in range(LAY.n_in))]
    L += ['+ ' + ' '.join(f'{v:g}' for v in si) for si in X]
    L += ['.enddata', '.dc Vdum 0 0 1 sweep data=d', '.end']
    (HERE / 'decks').mkdir(exist_ok=True)
    (HERE / 'decks' / f'{a.name}.sp').write_text('\n'.join(L) + '\n')
    print(f'{a.name}.sp: {len(L)} 줄, 표본 {len(y)}, 토막 행 {s_r:.3f} Ω · 열 {s_c:.3f} Ω')
else:
    m = parse_ms0(HERE / 'out' / f'{a.name}.ms0')
    ny = len(LAY.r_y)
    dif = lambda mm: (lambda v: v[:, 0::2] - v[:, 1::2])(np.stack([mm[f'y{j}'] for j in range(ny)], 1))
    d_sp = dif(m)
    d_ref = dif(parse_ms0(HERE / 'out' / f'{a.ref}.ms0'))
    u = torch.as_tensor(row_drive(LAY, X, c['a']))
    vh, vyp, _ = solve(LAY, torch.as_tensor(G)[None].expand(len(y), -1, -1), u, r_on=c['r_on'], v_b=c['v_b'], r_ser=c['r_ser'],
                       out_diode=not c['no_out_clamp'])
    d_py = (vyp[:, 0::2] - vyp[:, 1::2]).numpy()
    acc = lambda d: 100 * (d.argmax(1) == y).mean()
    big = lambda key, n: np.abs(np.stack([m[f'{key}{i}'] for i in range(n)], 1))
    print(f"{a.name}: test {len(y)} 장, 정확도 SPICE 선 저항 {acc(d_sp):.2f} % / 선 저항 없음 {acc(d_ref):.2f} % / Python {acc(d_py):.2f} %")
    print(f"  판정이 다른 표본: 선 저항 없음 대비 {(d_sp.argmax(1) != d_ref.argmax(1)).sum()}, Python 대비 {(d_sp.argmax(1) != d_py.argmax(1)).sum()}")
    print(f"  출력 차 (y+ − y−) 변화 최대 {np.abs(d_sp - d_ref).max()*1e3:.2f} mV (선 저항 없음 대비), 출력 차 크기 중앙값 {np.median(np.abs(d_ref))*1e3:.1f} mV")
    print(f"  선 위 전압 차 최대: 입력 행 {big('dx', len(LAY.r_x)).max()*1e3:.2f} mV, 은닉 열 {big('dh', len(LAY.c_h)).max()*1e3:.2f} mV, "
          f"출력 행 {big('dy', ny).max()*1e3:.2f} mV (입력 진폭 {c['a']*1e3:.0f} mV)")
    if 'irp' in m:
        print(f"  rail 전류 |I| 최대 VRAILP {np.abs(m['irp']).max()*1e3:.2f} mA · VRAILM {np.abs(m['irm']).max()*1e3:.2f} mA, "
              f"블록 쪽 rail 강하 최대 {np.abs(m['vrp'] - c['a']).max()*1e3:.2f} · {np.abs(m['vrm'] + c['a']).max()*1e3:.2f} mV")
