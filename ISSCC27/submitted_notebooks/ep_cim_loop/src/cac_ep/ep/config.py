"""Training settings. The defaults are the values that produced the submitted weights (nostab_5bit.npz, seed 0)."""
from dataclasses import asdict, dataclass

from circuit import R_ON


@dataclass
class EPConfig:
    # --- what to train: one run per (bits, seed). Runs are independent and see the same image order.
    bits: tuple = (5,)               # RRAM levels per cell = 2^bits
    seeds: tuple = (0,)              # initial-level seed
    epochs: int = 10
    # --- circuit
    beta: float = 3.812e-05          # nudge current [A]
    g_bz: float = 0.0                # stabilizer conductance [S]; 0 = removed (README §12)
    a: float = 0.3                   # input amplitude [V] (x+- = Vcm +- a)
    r_on: float = R_ON               # 1T1R series resistance [ohm]
    v_b: float = 0.3                 # clamp rail offset [V]
    r_ser: float = 100.0             # diode branch series resistance [ohm]
    out_clamp: bool = False          # diode on the output nodes too (False: only hidden nodes are tanh-like)
    # --- research options (all off = the submitted setting)
    th1: float = 0.0                 # first-stage decision threshold [V] (weight-update circuit offset)
    th2: float = 0.0                 # last-stage decision threshold [V]
    freeze1: bool = False            # do not update first-stage cells
    xbar_sig: float = 0.0            # free / nudge crossbar cell mismatch (relative sigma, fixed per run)
    # --- data
    n_val: int = 1000                # images taken from the training set for validation; 0 = evaluate on test
    n_train: int = 0                 # 0 = all remaining training images
    n_test: int = 0                  # 0 = all 3,097
    eval_every: int = 1500           # evaluate every this many images; 0 = once per epoch
    stop_step: int = 0               # >0: stop after this many training images, keep the weights there, no evaluation on the way
    # --- run
    device: str = 'cpu'              # the submitted run and the notebook use cpu
    tag: str = 'run'

    def to_dict(self):
        return asdict(self)
