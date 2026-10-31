"""추론 정확도: free 크로스바 + 실제 입력 구동 (행마다 NMOS 2:1 스위치, ±a 레일 패드) 으로 MNIST test 전체를 SPICE DC 쓸기.
../spice_check.py write_deck 과 같은 크로스바 소자 (Vcm = 0 V, .temp 25) 에서 입력 행만 이상 전원 → 스위치로 바꿈.
- 스위치 게이트: 입력 i 마다 gp_i = 2.5·(1 + s_i)/2, gm_i = 2.5·(1 − s_i)/2 (0 / VDD). x_i+ 행은 gp → +a 쪽, x_i− 행은 반대.
- bias 행은 레일에 바로. 행이 이제 미지 노드라 양 끝 고정으로 빼던 셀 (입력 행 × stabilizer·남는 열, HRS) 도 넣는다.
- 행·열 TG (꺼짐) 와 weight update 회로는 넣지 않는다 (sys1 에서 꺼진 TG 가 노드에 주는 차 0.00 µV).
쓰임: python infer_deck.py write --key 5b_s0 --w_drv 1000 --name inf_s0   /   python infer_deck.py compare --name inf_s0
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
ap.add_argument('--name', default='inf_s0')
ap.add_argument('--weights', default=str(HERE.parent / 'out' / 'weights' / 'nostab_5bit.npz'),
                help='10/25 부터 stabilizer 없는 판 (README §12). 이전 판 = tanh5_5bit.npz')
ap.add_argument('--key', default='5b_s0')
ap.add_argument('--state', default='best')
ap.add_argument('--w_drv', type=float, default=1000.0)
ap.add_argument('--r_pad', type=float, default=0.0)
ap.add_argument('--n', type=int, default=0, help='test 앞 n 장만 (0 = 전부, 10/30 Xyce 1,000 장 대조)')
ap.add_argument('--lib', default=f'{OLY}/ep_demo/char/models/sky130_5v_tt.lib.spice')
a = ap.parse_args()
W = np.load(a.weights)
LAY = layout_of(W)                                               # stabilizer 있는 판 / 없는 판 (README §12)
info = {i['key']: i for i in json.loads(str(W['info']))}[a.key]
c = info['config']
G = W[f'{a.key}/G_{a.state}']
X, y = load_task('t10k')
if a.n:
    X, y = X[:a.n], y[:a.n]

if a.task == 'write':
    nf = max(1, int(round(a.w_drv / 5)))
    L = [f"* {a.name}: free crossbar + NMOS 2:1 input switches (W {a.w_drv:g} um), {a.key} {a.state}, MNIST test {len(y)}",
         '.option post=0 ingold=2 numdgt=10 measdgt=10 nomod',
         '.option relv=1e-9 relvdc=1e-9 absvdc=1e-12 reli=1e-9 absi=1e-15 itl1=2000 itl2=2000',
         '.temp 25', f".lib '{a.lib}' tt",
         f'.model dlv1 d (level=1 is={D_IS} n={D_N} rs=0)',
         f"Vrup vrup 0 {-c['v_b']}", f"Vrdn vrdn 0 {c['v_b']}", "Vss vss 0 -2.5", 'Vdum dum 0 0',
         f"Vraip raip0 0 {c['a']}", f"Vraim raim0 0 {-c['a']}"]
    L += ([f"Rpadp raip0 raip {a.r_pad:g}", f"Rpadm raim0 raim {a.r_pad:g}"] if a.r_pad > 0
          else ["Vpadp raip raip0 0", "Vpadm raim raim0 0"])
    rn = lambda r: '0' if r == LAY.r_s else f'r{r}'
    cn = lambda cc: f'c{cc}' if cc in LAY.c_h else '0'
    for i in range(LAY.n_in):
        L += [f"Vgp{i} gp{i} 0 '2.5*(1+s{i})/2'", f"Vgm{i} gm{i} 0 '2.5*(1-s{i})/2'"]
        for r, (g_up, g_dn) in ((LAY.r_x[2 * i], (f'gp{i}', f'gm{i}')), (LAY.r_x[2 * i + 1], (f'gm{i}', f'gp{i}'))):
            L += [f"XDp{r} {rn(r)} {g_up} raip vss {NF} w={a.w_drv:g} l=0.5 nf={nf}",
                  f"XDm{r} {rn(r)} {g_dn} raim vss {NF} w={a.w_drv:g} l=0.5 nf={nf}"]
    L += [f"Vb{LAY.r_b[0]} {rn(LAY.r_b[0])} raip 0", f"Vb{LAY.r_b[1]} {rn(LAY.r_b[1])} raim 0"]
    for r, cc in zip(*np.nonzero(LAY.kind != NONE)):
        A, B = rn(r), cn(cc)
        if A == '0' and B == '0':
            continue
        if c['r_on']:
            L.append(f"R_{r}_{cc} {A} m{r}_{cc} {c['r_on']}")
            A = f'm{r}_{cc}'
        L.append(f"G_{r}_{cc} {A} {B} CUR='{G[r, cc]:.12e}*{V_REF}*sinh((V({A})-V({B}))/{V_REF})'")
    nodes = [cn(cc) for cc in LAY.c_h] + ([] if c['no_out_clamp'] else [rn(r) for r in LAY.r_y])
    for nd in nodes:
        L += [f"Rda_{nd} {nd} da_{nd} {c['r_ser']}", f"Da_{nd} da_{nd} vrup dlv1",
              f"Db_{nd} vrdn db_{nd} dlv1", f"Rdb_{nd} db_{nd} {nd} {c['r_ser']}"]
    L += [f'.measure dc y{j} find v({rn(r)}) at=0' for j, r in enumerate(LAY.r_y)]
    L += [f'.measure dc x{k} find v({rn(r)}) at=0' for k, r in enumerate(LAY.r_x[:4])]   # 입력 행 전압 몇 개 (강하 확인)
    L += ['.data d', '+ ' + ' '.join(f's{i}' for i in range(LAY.n_in))]
    L += ['+ ' + ' '.join(f'{v:g}' for v in si) for si in X]
    L += ['.enddata', '.dc Vdum 0 0 1 sweep data=d', '.end']
    (HERE / 'decks').mkdir(exist_ok=True)
    (HERE / 'decks' / f'{a.name}.sp').write_text('\n'.join(L) + '\n')
    print(f'{a.name}.sp: {len(L)} 줄, 표본 {len(y)}')
else:
    m = parse_ms0(HERE / 'out' / f'{a.name}.ms0')
    vy = np.stack([m[f'y{j}'] for j in range(len(LAY.r_y))], 1)
    d_sp = vy[:, 0::2] - vy[:, 1::2]
    u = torch.as_tensor(row_drive(LAY, X, c['a']))
    vh, vyp, _ = solve(LAY, torch.as_tensor(G)[None].expand(len(y), -1, -1), u, r_on=c['r_on'], v_b=c['v_b'], r_ser=c['r_ser'],
                       out_diode=not c['no_out_clamp'])
    d_py = (vyp[:, 0::2] - vyp[:, 1::2]).numpy()
    acc_sp, acc_py = (d_sp.argmax(1) == y).mean(), (d_py.argmax(1) == y).mean()
    xr = np.stack([m[f'x{k}'] for k in range(4)], 1)
    print(f"{a.name}: test {len(y)} 장, 정확도 SPICE (실제 입력 스위치) {100*acc_sp:.2f} % / Python (이상 입력) {100*acc_py:.2f} %, "
          f"판정이 다른 표본 {(d_sp.argmax(1) != d_py.argmax(1)).sum()}, 출력 차 |Δ(y+−y−)| 최대 {np.abs(d_sp - d_py).max()*1e3:.2f} mV, "
          f"입력 행 |V| 범위 {np.abs(xr).min():.4f}–{np.abs(xr).max():.4f} V (이상 {c['a']})")
