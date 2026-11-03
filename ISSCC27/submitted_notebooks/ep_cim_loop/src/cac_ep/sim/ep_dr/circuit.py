"""DRN 구조 dual-rail 크로스바 한 벌의 배치와 소자 값 (README §1, §3).

행: x± (입력 쌍) · bias± · stabilizer (Vcm) · y± (출력 쌍) · 남는 행 (WL off → 셀 연결 없음)
열: h± (은닉 쌍) · stabilizer (Vcm) · 남는 열 (Vcm 에 묶음)
쌍은 (+, −) 순서로 붙어 있다. 전압은 모두 Vcm 기준이다 (solver 는 Vcm = 0 으로 푼다).
"""
from dataclasses import dataclass

import numpy as np

# SKY130 ReRAM VA (sky130_fd_pr_reram__reram_cell.va, ../ep_demo/spec/spec.yaml:23-30)
# G 는 읽기 법칙 I = G·V_REF·sinh(V/V_REF) 의 계수 (작은 신호 컨덕턴스).
V_REF = 0.43
G_HRS = 0.2984e-6               # 프로그래밍하지 않은 셀 (안 쓰는 칸)
G_WIN = (3e-6, 100e-6)          # 학습 창 (P0b)
R_ON = 1200.0                   # 1T1R access nFET 직렬 저항 (WL 5 V)

# level-1 다이오드 카드 (README §8.7). 노드마다 두 가지 = 다이오드 (IS, N, 카드 rs 0) + 직렬 R_ser, clamp 레일로:
#   위 가지  노드 → R_ser → 다이오드 → rail_up = Vcm − V_B,   아래 가지  rail_dn = Vcm + V_B → 다이오드 → R_ser → 노드
#   V_B > 0 이면 레일이 교차해 켜짐 전압이 V_B 만큼 내려간다 (../ep_demo/spec/spec_level1_1004.yaml:46-47 의 rail_up −0.15 / rail_dn +0.15 와 같은 뜻).
#   D_RS 는 R_ser 기본값: V_B = 0, R_ser = 1 kΩ 이 이전 모형 (Vcm 으로 가는 anti-parallel 한 쌍, 카드 rs 1 kΩ) 과 같다.
D_IS, D_N, D_RS = 5e-10, 1.2, 1e3
V_B = 0.0
KQ = 1.3806226e-23 / 1.6021918e-19     # SPICE 상수 k/q
T_K = 298.15                            # 25 °C (SPICE 기본 TNOM·TEMP)
VT = KQ * T_K

# 셀 종류 (Layout.kind)
NONE, W1, W2, GBZ, HRS = 0, 1, 2, 3, 4


@dataclass
class Layout:
    n_in: int
    n_hid: int
    n_out: int
    rows: int                   # 물리 행
    cols: int                   # 물리 열
    bias: bool = True
    stab: bool = True           # stabilizer 행·열. 10/25 사용자 "빼도록 하게" (README §12) → False 배치 = 106 × 60 사용

    def __post_init__(self):
        r = 0
        self.r_x = np.arange(r, r + 2 * self.n_in); r += 2 * self.n_in
        self.r_b = np.arange(r, r + 2 * self.bias); r += 2 * self.bias
        self.r_s = r if self.stab else None; r += int(self.stab)
        self.r_y = np.arange(r, r + 2 * self.n_out); r += 2 * self.n_out
        assert r <= self.rows, f'쓰는 행 {r} > 물리 {self.rows}'
        self.r_used = r
        self.c_h = np.arange(2 * self.n_hid)
        self.c_s = 2 * self.n_hid if self.stab else None
        n_c = 2 * self.n_hid + int(self.stab)
        assert n_c <= self.cols, f'쓰는 열 {n_c} > 물리 {self.cols}'
        self.c_spare = np.arange(n_c, self.cols)

        k = np.full((self.rows, self.cols), NONE, np.int8)
        k[:r] = HRS                                         # 쓰는 행은 WL on → 모든 칸이 연결
        k[np.ix_(np.r_[self.r_x, self.r_b], self.c_h)] = W1
        k[np.ix_(self.r_y, self.c_h)] = W2
        if self.stab:
            k[self.r_s, self.c_h] = GBZ                     # hidden stabilizer (행)
            k[self.r_y, self.c_s] = GBZ                     # output stabilizer (열)
        self.kind = k


def init_G(lay, rng, mode='2023', g_bz=10e-6, batch=1):
    """(batch, rows, cols) 컨덕턴스 [S].
    mode '2023': 학습 셀마다 35 % 창 위 / 65 % 창 아래 (Oh 2023 초기화를 SKY130 창에 맞춤, README §3 #8)
    mode 'uniform': 학습 셀을 창 안 균등 (검증용)"""
    G = np.zeros((batch, lay.rows, lay.cols))
    G[:, lay.kind == HRS] = G_HRS
    G[:, lay.kind == GBZ] = g_bz
    m = (lay.kind == W1) | (lay.kind == W2)
    n = (batch, int(m.sum()))
    if mode == '2023':
        G[:, m] = np.where(rng.random(n) < 0.35, G_WIN[1], G_WIN[0])
    elif mode == 'uniform':
        G[:, m] = rng.uniform(*G_WIN, n)
    else:
        raise ValueError(mode)
    return G


def row_drive(lay, s, a):
    """입력 ±1 (B, n_in) → 고정 행 전압 (B, rows), Vcm 기준.
    x+ = +a·s, x− = −a·s, bias+ = +a, bias− = −a, 나머지 0 (stabilizer 행, 남는 행)."""
    s = np.asarray(s, float)
    u = np.zeros((len(s), lay.rows))
    u[:, lay.r_x[0::2]] = a * s
    u[:, lay.r_x[1::2]] = -a * s
    if lay.bias:
        u[:, lay.r_b[0]], u[:, lay.r_b[1]] = a, -a
    return u
