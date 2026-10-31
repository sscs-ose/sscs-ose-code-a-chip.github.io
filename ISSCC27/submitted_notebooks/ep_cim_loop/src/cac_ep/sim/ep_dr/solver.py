"""DRN 크로스바 평형 (DC) — batched Newton, float64 (README §5).

미지수: 은닉 열 h± 와 출력 행 y± 의 전압 (Vcm 기준). 나머지 행·열은 고정이다.
  셀:      I = G·V_REF·sinh(V_cell/V_REF), V_cell = V − I·R_on  (V = V_행 − V_열, R_on = 0 이면 직렬 저항 없음)
  다이오드: 노드마다 level-1 (IS, N) + 직렬 R_ser 두 가지를 clamp 레일 Vcm ∓ V_B 로 (circuit.py 주석)
  nudge:   출력 행에 전류 i_nudge 를 넣는다
수렴하지 않으면 멈춘다 — 이전 판 solver 는 고정 반복에 수렴 확인이 없었다 (../ep_demo/python/ep_train.py:37-38).
"""
import math

import torch

from circuit import D_IS, D_N, D_RS, V_B, V_REF, VT


def cell_iv(G, V, r_on=0.0):
    """셀 전류 I 와 dI/dV (G, V 같은 모양)."""
    if r_on == 0:
        x = V / V_REF
        return G * V_REF * torch.sinh(x), G * torch.cosh(x)
    # I = G·Vr·sinh((V − I·R)/Vr) 를 I 에 대해 Newton (h(I) 가 단조 감소라 근이 하나)
    I = G * V_REF * torch.sinh(V / V_REF) / (1 + G * r_on * torch.cosh(V / V_REF))
    for _ in range(60):
        u = (V - I * r_on) / V_REF
        dI = (G * V_REF * torch.sinh(u) - I) / (-G * r_on * torch.cosh(u) - 1)
        I = I - dI
        if dI.abs().max() < 1e-19:
            break
    else:
        raise RuntimeError(f'셀 R_on 반복 미수렴 (max dI {dI.abs().max():.2e} A)')
    g = G * torch.cosh((V - I * r_on) / V_REF)
    return I, g / (1 + r_on * g)


def _omega(z):
    """Wright omega ω(z): ω + ln ω = z (= W(e^z)). 큰 z 에서도 넘치지 않는다.
    초기값이 근의 왼쪽이라 Newton 이 단조로 수렴한다 (f 가 오목·증가).
    허용치 1e-13: z ≈ −11 (V ≈ 0) 에서 w + ln w − z 의 상쇄 오차가 약 2e-15 라 그보다 엄하게는 못 간다."""
    w = torch.where(z > 1, z - torch.log(z.clamp(min=1.0)), torch.sigmoid(z.clamp(max=1.0)))
    for _ in range(60):
        dw = (w + torch.log(w) - z) / (1 + 1 / w)
        w = w - dw
        if (dw.abs() / w).max() < 1e-13:
            return w
    raise RuntimeError('다이오드 ω 반복 미수렴')


def branch_iv(v, r_ser=D_RS):
    """다이오드 + 직렬 R_ser 한 가지에 순방향 v 를 걸 때 전류와 dI/dV.
    i = Is·(exp((v − i·R)/(N·Vt)) − 1) → i = (N·Vt/R)·ω(z) − Is, z = ln(Is·R/(N·Vt)) + (v + Is·R)/(N·Vt)."""
    nvt = D_N * VT
    w = _omega(math.log(D_IS * r_ser / nvt) + (v + D_IS * r_ser) / nvt)
    return nvt / r_ser * w - D_IS, w / (r_ser * (1 + w))


def diode_iv(V, v_b=V_B, r_ser=D_RS):
    """노드 전압 V (Vcm 기준) 에서 두 가지로 나가는 전류와 dI/dV.
    위 가지 (노드 → rail_up = −v_b) 순방향 V + v_b, 아래 가지 (rail_dn = +v_b → 노드) 순방향 v_b − V."""
    ip, gp = branch_iv(V + v_b, r_ser)
    im, gm = branch_iv(v_b - V, r_ser)
    return ip - im, gp + gm


def solve(lay, G, u_rows, i_nudge=None, r_on=0.0, v0=None, tol=1e-12, max_iter=200, dv_max=0.2, v_b=V_B, r_ser=D_RS,
          out_diode=True):
    """G (B, R, C) [S], u_rows (B, R) 고정 행 전압 [V], i_nudge (B, 2·n_out) 출력 행 주입 전류 [A].
    v_b, r_ser: clamp 레일 오프셋 [V], 다이오드 직렬 저항 [Ω] (circuit.py 주석).
    out_diode=False 면 출력 노드에는 다이오드를 달지 않는다 (hidden 만 tanh, Oh 2023 neuron 배치).
    반환: v_h (B, 2·n_hid), v_y (B, 2·n_out), 반복 수.  v0 = (v_h, v_y) 로 시작점을 줄 수 있다."""
    G = torch.as_tensor(G, dtype=torch.float64)
    dev = G.device
    B = G.shape[0]
    u = torch.as_tensor(u_rows, dtype=torch.float64, device=dev)
    r_y = torch.as_tensor(lay.r_y, device=dev)
    c_h = torch.as_tensor(lay.c_h, device=dev)
    nh, ny = len(lay.c_h), len(lay.r_y)
    inj = torch.zeros(B, ny, dtype=torch.float64, device=dev) if i_nudge is None else \
        torch.as_tensor(i_nudge, dtype=torch.float64, device=dev)
    if v0 is None:
        vh = torch.zeros(B, nh, dtype=torch.float64, device=dev)
        vy = torch.zeros(B, ny, dtype=torch.float64, device=dev)
    else:
        vh, vy = (torch.as_tensor(x, dtype=torch.float64, device=dev).clone() for x in v0)

    for it in range(1, max_iter + 1):
        Vr = u.clone(); Vr[:, r_y] = vy
        Vc = torch.zeros(B, lay.cols, dtype=torch.float64, device=dev); Vc[:, c_h] = vh
        I, g = cell_iv(G, Vr[:, :, None] - Vc[:, None, :], r_on)      # 행 → 열 전류
        Ih, gh = diode_iv(vh, v_b, r_ser)
        Iy, gy = diode_iv(vy, v_b, r_ser) if out_diode else (torch.zeros_like(vy), torch.zeros_like(vy))
        F = torch.cat([I[:, :, c_h].sum(1) - Ih,                     # 은닉 열: 행에서 들어옴 − 다이오드
                       -I[:, r_y, :].sum(2) - Iy + inj], 1)          # 출력 행: 열로 나감 − 다이오드 + nudge
        Gyh = g[:, r_y][:, :, c_h]                                    # (B, ny, nh)
        J = torch.zeros(B, nh + ny, nh + ny, dtype=torch.float64, device=dev)
        J[:, :nh, :nh] = torch.diag_embed(-g[:, :, c_h].sum(1) - gh)
        J[:, nh:, nh:] = torch.diag_embed(-g[:, r_y, :].sum(2) - gy)
        J[:, :nh, nh:] = Gyh.transpose(1, 2)
        J[:, nh:, :nh] = Gyh
        dv = torch.linalg.solve(J, -F)
        dv = dv.clamp(-dv_max, dv_max)
        vh = vh + dv[:, :nh]
        vy = vy + dv[:, nh:]
        if dv.abs().max() < tol:
            return vh, vy, it
    raise RuntimeError(f'평형 미수렴: {max_iter}회, max |dv| {dv.abs().max():.2e} V')


def cell_voltage(lay, u_rows, vh, vy):
    """셀 양단 V_행 − V_열 (B, R, C) — sensing 이 보는 값 (R_on 포함)."""
    u = torch.as_tensor(u_rows, dtype=torch.float64, device=vh.device)
    Vr = u.clone(); Vr[:, torch.as_tensor(lay.r_y, device=vh.device)] = vy
    Vc = torch.zeros(len(u), lay.cols, dtype=torch.float64, device=vh.device)
    Vc[:, torch.as_tensor(lay.c_h, device=vh.device)] = vh
    return Vr[:, :, None] - Vc[:, None, :]
