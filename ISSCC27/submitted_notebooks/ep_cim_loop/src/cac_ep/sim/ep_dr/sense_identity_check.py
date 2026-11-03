# tanh 5 bit 체크포인트 (seed 0, L_best / L_final), 학습 표본 2,000장: free·nudge 한 번씩 풀어
# (1) first stage: |h| < a 인지, 항등식 bit = 정확 bit 인지
# (2) last stage: 수식 근사 bit = 정확 bit 인지
#     D' = nudge 방향 (y_k+ 는 +t_k, y_k− 는 −t_k, 정답에서 앎),  S' = sign(y_f − h_f) (free 크로스바 노드 둘 비교)
import sys, json, numpy as np, torch
sys.path.insert(0, '/home/dave/work/projects/isscc_cac/sim/ep_dr')
from circuit import G_WIN, W1, W2, init_G, row_drive
from data import load_task
from solver import solve, cell_voltage
from train import LAY
dev = torch.device('cuda'); X, y = load_task('train'); X, y = X[:2000], y[:2000]
T = np.where(np.eye(LAY.n_out)[y] > 0, 1.0, -1.0)
R = '/home/dave/work/projects/isscc_cac/sim/ep_dr/out/runs/tanh5_seed0/'
c = json.load(open(R + 'config.json')); z = np.load(R + 'ckpt.npz')
kind = torch.as_tensor(LAY.kind, device=dev)
m1, m2 = kind == W1, kind == W2
base = torch.as_tensor(init_G(LAY, np.random.default_rng(0), '2023', c['g_bz'])[0], device=dev)
ry = torch.as_tensor(LAY.r_y, device=dev); ch = torch.as_tensor(LAY.c_h, device=dev)
for name in ('L_best', 'L_final'):
    L = torch.as_tensor(z[name][0].astype(float), device=dev)
    G = torch.where(m1 | m2, G_WIN[0] + L * (G_WIN[1] - G_WIN[0]) / 31, base)
    s = dict(h_max=0., agree1=0, n1=0, dy_sign=0, ny=0, agreeS=0, agreeD=0, agree2=0, agree2m=0, n2=0, ratio=[])
    for i0 in range(0, len(X), 500):
        u = torch.as_tensor(row_drive(LAY, X[i0:i0 + 500], c['a']), device=dev); B = len(u)
        inj = torch.zeros(2 * B, len(LAY.r_y), dtype=torch.float64, device=dev)
        t = torch.as_tensor(T[i0:i0 + 500], device=dev)
        inj[B:, 0::2], inj[B:, 1::2] = c['beta'] * t, -c['beta'] * t
        uu = torch.cat([u, u]); Gb = G.expand(2 * B, -1, -1)
        vh, vy, _ = solve(LAY, Gb, uu, i_nudge=inj, r_on=c['r_on'], v_b=c['v_b'], r_ser=c['r_ser'], out_diode=False)
        V = cell_voltage(LAY, uu, vh, vy); f, n = V[:B], V[B:]
        exact = (n.abs() - f.abs()) >= 0                                   # 정확 bit (b ≥ 0 → 내림)
        s['h_max'] = max(s['h_max'], vh.abs().max().item())
        # first stage: sign(n−f) XNOR sign(x)
        ident1 = ((n - f) >= 0) == (u.unsqueeze(2).expand_as(n) >= 0)
        s['agree1'] += (ident1 == exact)[:, m1].sum().item(); s['n1'] += m1.sum().item() * B
        # last stage
        dy = vy[B:] - vy[:B]; dh = vh[B:] - vh[:B]                           # (B, 6), (B, 60)
        pred = torch.stack([t, -t], 2).reshape(B, -1)                         # y_k+ → +t_k, y_k− → −t_k
        s['dy_sign'] += ((dy >= 0) == (pred > 0)).sum().item(); s['ny'] += dy.numel()
        f2, n2 = f[:, ry][:, :, ch], n[:, ry][:, :, ch]; ex2 = exact[:, ry][:, :, ch]
        Dex, Sex = (n2 - f2) >= 0, (n2 + f2) >= 0
        Dp = (pred > 0).unsqueeze(2).expand_as(n2)                            # 정답에서 아는 방향
        Dm = (dy >= 0).unsqueeze(2).expand_as(n2)                             # y_n,k 대 y_f,k 비교 (노드 둘)
        Sp = f2 >= 0                                                          # y_f,k 대 h_f,j 비교 (노드 둘)
        s['agreeD'] += (Dp == Dex).sum().item(); s['agreeS'] += (Sp == Sex).sum().item()
        s['agree2'] += ((Dp == Sp) == ex2).sum().item(); s['agree2m'] += ((Dm == Sp) == ex2).sum().item()
        s['n2'] += ex2.numel()
        # 비교기 하나 더: sign(n) (y_n 대 h_n). 같으면 정확, 다르면 (부호 뒤집힘) 정책으로
        Sn = n2 >= 0; flip = Sn != Sp
        s.setdefault('flip', 0); s.setdefault('flip_dec', 0); s.setdefault('pol_dec', 0); s.setdefault('pol_inc', 0)
        s['flip'] += flip.sum().item(); s['flip_dec'] += (flip & ex2).sum().item()
        s['pol_dec'] += (torch.where(flip, torch.ones_like(ex2), Dp == Sp) == ex2).sum().item()
        s['pol_inc'] += (torch.where(flip, torch.zeros_like(ex2), Dp == Sp) == ex2).sum().item()
        # 저항 평균: (y_n + y_f)/2 대 h_f  (h_n ≈ h_f 근사)
        ym = (vy[B:] + vy[:B]) / 2
        Savg = (ym[:, :, None] - vh[:B][:, None, :]) >= 0
        s.setdefault('avgS', 0); s.setdefault('avg2', 0)
        s['avgS'] += (Savg == Sex).sum().item(); s['avg2'] += ((Dp == Savg) == ex2).sum().item()
        s['ratio'].append((dy.abs().unsqueeze(2) / dh.abs().unsqueeze(1).clamp(min=1e-12)).flatten())
        s.setdefault('dh', []).append(dh.abs().flatten()); s.setdefault('dy', []).append(dy.abs().flatten())
    r = torch.cat(s['ratio']); dh_a, dy_a = torch.cat(s['dh']) * 1e3, torch.cat(s['dy']) * 1e3
    print(f"{name}: |Δh| 중앙 {dh_a.median():.3f} mV (10 % 분위 {dh_a.quantile(0.1):.3f}), |Δy| 중앙 {dy_a.median():.2f} mV (10 % 분위 {dy_a.quantile(0.1):.2f})")
    print(f"{name}: |h| 최대 {s['h_max']:.3f} V (a = {c['a']}) | first stage 항등식 일치 {100*s['agree1']/s['n1']:.3f} %")
    print(f"  Δy 부호 = 정답 방향 {100*s['dy_sign']/s['ny']:.2f} % | |Δy_k|/|Δh_j| 중앙 {r.median():.1f}, 1 % 분위 {r.quantile(0.01):.2f}")
    print(f"  last stage: D'(정답 방향) = D {100*s['agreeD']/s['n2']:.2f} %, S'(free 부호) = S {100*s['agreeS']/s['n2']:.2f} %")
    print(f"  last stage bit 일치: 정답 방향 XNOR free 부호 {100*s['agree2']/s['n2']:.2f} %, y_n 대 y_f 비교 XNOR free 부호 {100*s['agree2m']/s['n2']:.2f} %")
    print(f"  부호 뒤집힌 셀 {100*s['flip']/s['n2']:.2f} %, 그중 정답이 내림 {100*s['flip_dec']/max(s['flip'],1):.1f} % | "
          f"비교기 2개 + 뒤집힘 → 내림 {100*s['pol_dec']/s['n2']:.2f} %, → 올림 {100*s['pol_inc']/s['n2']:.2f} %")
    print(f"  저항 평균 (y_n + y_f)/2 대 h_f: S 일치 {100*s['avgS']/s['n2']:.3f} %, bit 일치 {100*s['avg2']/s['n2']:.3f} %")
