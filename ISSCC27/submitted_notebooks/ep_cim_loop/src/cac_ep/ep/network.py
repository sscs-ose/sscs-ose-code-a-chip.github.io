"""EPNetwork: the dual-rail RRAM crossbar (DRN) trained with equilibrium propagation and the Oh 2023 sign rule.

The "parameters" are integer conductance levels L (one per cell); there is no autograd. One training step is
    eq = net.equilibrium(x, t)   # free + nudged circuits solved together (Newton, warm start)
    net.update(eq)               # every trainable cell moves one level: -sgn(|dV_nudge| - |dV_free|)
Several independent runs (bits x seeds) are carried on the leading axis n_runs; they all see the same images.
"""
import itertools

import numpy as np
import torch

from circuit import G_WIN, NONE, W1, W2, Layout, init_G, row_drive
from solver import cell_voltage, solve

LAY = Layout(n_in=49, n_hid=30, n_out=3, rows=128, cols=64)     # 107 × 61 사용 → 128 × 64 (원본 train.py 와 같은 배치)


def levels_init(lay, seed, lmax):
    """학습 셀: 35 % → lmax, 65 % → 0. 나머지 칸은 0 (쓰지 않음)."""
    m = (lay.kind == W1) | (lay.kind == W2)
    L = np.zeros((lay.rows, lay.cols))
    L[m] = np.where(np.random.default_rng(seed).random(int(m.sum())) < 0.35, lmax, 0)
    return L


class EPNetwork:
    """Crossbar network for one or more runs (bits x seeds).

    Args:
        cfg: EPConfig. Uses bits, seeds, g_bz, a, r_on, v_b, r_ser, out_clamp, th1, th2, freeze1, xbar_sig, device.
        lay: physical layout (default LAY, 128 x 64).

    Attributes:
        runs: list of (bits, seed), one per entry of the leading axis.
        L: (n_runs, rows, cols) float64 tensor of conductance levels in [0, 2^bits - 1].
    """

    def __init__(self, cfg, lay=LAY):
        self.cfg, self.lay = cfg, lay
        self.dev = dev = torch.device(cfg.device)
        self.runs = list(itertools.product(cfg.bits, cfg.seeds))
        B = self.n_runs = len(self.runs)
        self.lmax = torch.tensor([2 ** n - 1 for n, _ in self.runs], device=dev, dtype=torch.float64).view(B, 1, 1)
        self.dg = (G_WIN[1] - G_WIN[0]) / self.lmax
        self.m = torch.as_tensor((lay.kind == W1) | (lay.kind == W2), device=dev)              # 학습 셀
        self.conn = torch.as_tensor(lay.kind != NONE, device=dev)                             # 연결된 셀
        self.base = torch.as_tensor(init_G(lay, np.random.default_rng(0), '2023', cfg.g_bz)[0], device=dev)  # 고정 칸 (G_bz·HRS)
        mW1 = torch.as_tensor(lay.kind == W1, device=dev)
        self.th = torch.where(mW1, cfg.th1, cfg.th2)                                         # 셀마다 판정 경계 (stage 별)
        self.mu = self.m & ~mW1 if cfg.freeze1 else self.m                                   # 갱신하는 셀
        if cfg.xbar_sig:                                                                     # free·nudge 배열 컨덕턴스 차이 (실행마다 고정)
            gen = torch.Generator().manual_seed(777 + cfg.seeds[0])
            self.ef, self.en = (1 + cfg.xbar_sig * torch.randn((B, lay.rows, lay.cols), generator=gen,
                                                               dtype=torch.float64).to(dev) * self.m for _ in range(2))
        else:
            self.ef = self.en = torch.ones((), dtype=torch.float64, device=dev)
        self.reset_parameters()

    # --- parameters
    def reset_parameters(self):
        """Initial levels: per trainable cell 35 % top level, 65 % bottom level (same placement for any bits, given a seed)."""
        self.L = torch.stack([torch.as_tensor(levels_init(self.lay, s, 2 ** n - 1), device=self.dev) for n, s in self.runs])
        self.prev = None                                                                     # Newton warm start (v_h, v_y)

    def conductance(self, L=None):
        """Levels -> conductance G = G_min + L * dG [S]; fixed cells (G_bz, HRS) keep their value. (n_runs, rows, cols)."""
        L = self.L if L is None else L
        return torch.where(self.m, G_WIN[0] + L * self.dg, self.base)

    def state_dict(self):
        return {'L': self.L.clone(), 'runs': list(self.runs)}

    def load_state_dict(self, sd):
        """Accepts state_dict() output or an int16 array such as ckpt.npz['L_best']."""
        L = sd['L'] if isinstance(sd, dict) else sd
        L = torch.as_tensor(np.asarray(L, dtype=np.float64) if not torch.is_tensor(L) else L, dtype=torch.float64,
                            device=self.dev)
        assert L.shape == self.L.shape, f'{tuple(L.shape)} != {tuple(self.L.shape)}'
        self.L = L.clone()

    # --- inference
    def _solve(self, G, u, **kw):
        c = self.cfg
        return solve(self.lay, G, u, r_on=c.r_on, v_b=c.v_b, r_ser=c.r_ser, out_diode=c.out_clamp, **kw)

    def solve_free(self, x, L=None):
        """Free circuit for images x (n, n_in) in +-1, all runs at once.
        Returns u (n_runs * n, rows), G (n_runs * n, rows, cols), v_h, v_y; row index = run * n + image."""
        n = len(x)
        u = torch.as_tensor(row_drive(self.lay, x, self.cfg.a), device=self.dev).repeat(self.n_runs, 1)
        G = (self.conductance(L) * self.ef).repeat_interleave(n, 0)
        vh, vy, _ = self._solve(G, u)
        return u, G, vh, vy

    @torch.no_grad()
    def forward(self, x, L=None, chunk=None):
        """Output y+ - y- of the free circuit [V], (n_runs, n, n_out). The predicted class is argmax over the last axis."""
        chunk = chunk or max(1, 1024 // self.n_runs)
        out = []
        for i0 in range(0, len(x), chunk):
            _, _, _, vy = self.solve_free(x[i0:i0 + chunk], L)
            out.append((vy[:, 0::2] - vy[:, 1::2]).view(self.n_runs, -1, len(self.lay.r_y) // 2))
        return torch.cat(out, 1)

    __call__ = forward

    # --- training
    @torch.no_grad()
    def equilibrium(self, x, t):
        """Free and nudged circuits for one image, solved in one call (2 * n_runs circuits).

        x: (1, n_in) input in +-1. t: (n_out,) target in +-1 V. The nudge injects +beta*t into y+ and -beta*t into y-.
        Because |y+ - y-| < 1 V in this circuit, the error sign equals t, so the nudge does not wait for the free result;
        a RuntimeError is raised if that assumption breaks.
        Returns dict: u, vh, vy (2 * n_runs rows: free first, then nudge), d = free y+ - y- (n_runs, n_out),
        V = cell voltages (2 * n_runs, rows, cols), b = |dV_nudge| - |dV_free| (n_runs, rows, cols).
        """
        B, c = self.n_runs, self.cfg
        u = torch.as_tensor(row_drive(self.lay, x, c.a), device=self.dev).expand(2 * B, -1)
        inj = torch.zeros(2 * B, len(self.lay.r_y), dtype=torch.float64, device=self.dev)
        t = torch.as_tensor(t, device=self.dev)
        inj[B:, 0::2], inj[B:, 1::2] = c.beta * t, -c.beta * t
        G = self.conductance()
        vh, vy = self.prev = self._solve(torch.cat([G * self.ef, G * self.en]), u, i_nudge=inj, v0=self.prev)[:2]
        d = vy[:B, 0::2] - vy[:B, 1::2]
        if d.abs().max() >= 1:
            raise RuntimeError(f'|y+ − y−| = {d.abs().max():.3f} V ≥ 1 V → e ≠ t, 한 번에 풀 수 없음')
        V = cell_voltage(self.lay, u, vh, vy)
        return dict(u=u, vh=vh, vy=vy, d=d, V=V, b=V[B:].abs() - V[:B].abs())

    @torch.no_grad()
    def update(self, eq):
        """Sign rule (the optimizer step): each updated cell moves -sgn(b) by one level, b >= th counts as +
        (th = 0 is Oh 2023, b = 0 -> +). Levels stop at [0, 2^bits - 1]."""
        b = eq['b']
        self.L = torch.where(self.mu, torch.minimum((self.L - torch.where(b >= self.th, 1.0, -1.0)).clamp(min=0), self.lmax),
                             self.L)
