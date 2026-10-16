"""Bit-accurate golden model of the ApproxHDC-Forge datapath (see DESIGN.md).

Every definition here is what the RTL must reproduce bit for bit:

* Random vectors are *rematerialized*, never stored: bit j of a vector is bit (j % 32)
  of mix32(key(tag, f, j // 32)). mix32 uses only shifts, XORs and two constant adds.
* ID_f      = hash(tag=0, f)
* L_q       = L0 XOR flip_q,  L0 = hash(tag=2, f=0),
              flip_q[j] = bitrev12(j) < q * 2048 // (Q - 1)   (12 = log2 of D_MAX)
* T         = hash(tag=1, f=0): tie-break vector for bundling and binarization.
* encode    : acc_j = sum_f ID_f[j] ^ L_{x_f}[j];  q_j = 1 if acc_j > F/2, 0 if < F/2, else T_j
* distance  : sum over 8-bit groups (bits 8k..8k+7) of g(popcount(group of q ^ proto)),
              where g depends on the similarity variant (see VARIANTS).
* classify  : argmin distance; ties go to the lowest class index.
* counters  : signed, saturating to [-2^(w-1), 2^(w-1)-1], updated with bipolar(q) = 2q - 1.
* binarize  : proto_j = 1 if cnt_j > 0, 0 if cnt_j < 0, T_j if cnt_j == 0.
* stochastic: with update exponent k, counter j only moves if mask_j = 1, where
              mask = AND_{i<k} hash(tag=3, f=u mod 1024, word=4*(j//32)+i) and u counts
              learning events (one per bundle-all sample / per error-driven mistake).
              Each counter therefore moves with probability 2^-k (k = 0: always).
* recipe    : 'bundle' hardware: one bundle-all pass. 'error' hardware: one bundle-all
              warm-up pass, then error-driven passes (error-driven from scratch is unstable).

Because hashes are keyed by the global bit index, a design with dimension D is exactly
the first D bits of the D_MAX design, and the slice width P never changes the math
(it only changes area and latency).
"""
from dataclasses import dataclass

import numpy as np

D_MAX = 4096
LOG2_DMAX = 12
M32 = np.uint64(0xFFFFFFFF)
TAG_ID, TAG_TIE, TAG_LEVEL, TAG_MASK = 0, 1, 2, 3


# ----------------------------------------------------------------------------- hashing
def _xorshift(x):
    x = x ^ ((x << np.uint64(13)) & M32)
    x = x ^ (x >> np.uint64(17))
    x = x ^ ((x << np.uint64(5)) & M32)
    return x


def mix32(x):
    """Hardware-cheap 32-bit mixer: 3 xorshift rounds separated by 2 constant adds."""
    x = np.asarray(x, dtype=np.uint64) & M32
    x = _xorshift(x)
    x = (x + np.uint64(0x9E3779B9)) & M32
    x = _xorshift(x)
    x = (x + np.uint64(0x7F4A7C15)) & M32
    return _xorshift(x)


def hash_key(seed, tag, f, word):
    """32-bit key: seed[31:28] | tag[27:26] | f[25:16] | word[15:0]."""
    return ((np.uint64(seed & 0xF) << np.uint64(28)) | (np.uint64(tag & 0x3) << np.uint64(26))
            | (np.asarray(f, dtype=np.uint64) << np.uint64(16)) | np.asarray(word, dtype=np.uint64))


def hash_bits(seed, tag, f, D=D_MAX):
    """Rematerialized D-bit vector(s) for feature index/indices f -> uint8 array [..., D]."""
    f = np.atleast_1d(np.asarray(f, dtype=np.uint64))
    words = np.arange(D // 32, dtype=np.uint64)
    h = mix32(hash_key(seed, tag, f[:, None], words[None, :]))          # [nf, D/32]
    bits = (h[..., None] >> np.arange(32, dtype=np.uint64)) & np.uint64(1)
    return bits.reshape(len(f), D).astype(np.uint8)


def update_mask(seed, u, k, D):
    """Stochastic-update mask for learning event u: each bit is 1 with probability 2^-k."""
    words = np.arange(D // 32, dtype=np.uint64)
    m = np.full(D // 32, 0xFFFFFFFF, dtype=np.uint64)
    for i in range(k):
        m &= mix32(hash_key(seed, TAG_MASK, u % 1024, 4 * words + np.uint64(i)))
    bits = (m[:, None] >> np.arange(32, dtype=np.uint64)) & np.uint64(1)
    return bits.reshape(D).astype(np.int16)


def bitrev(j, nbits=LOG2_DMAX):
    j = np.asarray(j, dtype=np.int64)
    r = np.zeros_like(j)
    for b in range(nbits):
        r |= ((j >> b) & 1) << (nbits - 1 - b)
    return r


@dataclass(frozen=True)
class ItemMemory:
    """The vectors the hardware regenerates on the fly (materialized here for speed)."""
    ID: np.ndarray      # [F, D_MAX]
    L: np.ndarray       # [Q, D_MAX]
    T: np.ndarray       # [D_MAX]


def item_memory(F, Q, seed=0):
    ID = hash_bits(seed, TAG_ID, np.arange(F))
    T = hash_bits(seed, TAG_TIE, 0)[0]
    L0 = hash_bits(seed, TAG_LEVEL, 0)[0]
    rank = bitrev(np.arange(D_MAX))
    thr = np.arange(Q) * (D_MAX // 2) // (Q - 1)
    L = L0[None, :] ^ (rank[None, :] < thr[:, None]).astype(np.uint8)
    return ItemMemory(ID, L, T)


# ---------------------------------------------------------------------------- encoding
def encode(Xq, im, chunk=1024):
    """Xq [N, F] int levels -> query hypervectors [N, D_MAX] uint8 bits (majority bundling)."""
    N, F = Xq.shape
    out = np.empty((N, D_MAX), dtype=np.uint8)
    for a in range(0, N, chunk):
        x = Xq[a:a + chunk]
        acc = np.zeros((len(x), D_MAX), dtype=np.int16)
        for f in range(F):
            acc += im.ID[f][None, :] ^ im.L[x[:, f]]
        twice = 2 * acc
        q = (twice > F).astype(np.uint8)
        tie = twice == F
        q[tie] = np.broadcast_to(im.T, q.shape)[tie]
        out[a:a + chunk] = q
    return out


def pack(bits):
    """[..., D] bits -> [..., D/8] bytes; byte k holds the 8-bit group (bits 8k..8k+7)."""
    return np.packbits(bits, axis=-1, bitorder="little")


# ------------------------------------------------------------------ similarity variants
_PC8 = np.array([bin(i).count("1") for i in range(256)], dtype=np.int32)

VARIANTS = {
    # name: (description, knob values, group function on the 0..8 group count)
    "exact": ("exact popcount", [0], lambda c, k: c),
    "trunc": ("drop k LSBs of each 8-bit group count", [0, 1, 2, 3], lambda c, k: c >> k),
    "satcomp": ("saturating 8:k compressor, group count clipped to 2^k-1",
                [4, 3, 2, 1], lambda c, k: np.minimum(c, (1 << k) - 1)),
    "sampled": ("only the first D' = D*k/8 dimensions are compared",
                [8, 6, 4, 3, 2], lambda c, k: c),
}


@dataclass(frozen=True)
class Similarity:
    variant: str = "exact"
    knob: int = 0

    def lut(self):
        _, _, g = VARIANTS[self.variant]
        return g(_PC8, self.knob).astype(np.int32)

    def n_groups(self, D):
        return D // 8 * self.knob // 8 if self.variant == "sampled" else D // 8

    def distance(self, qp, protop):
        """qp [..., D/8], protop [C, D/8] packed -> distances [..., C]."""
        G = self.n_groups(protop.shape[-1] * 8)
        x = qp[..., None, :G] ^ protop[:, :G]
        return self.lut()[x].sum(-1)

    def __str__(self):
        return self.variant if self.variant == "exact" else f"{self.variant}({self.knob})"


def classify(qp, protop, sim):
    return np.argmin(sim.distance(qp, protop), axis=-1)   # argmin -> lowest index on ties


# ------------------------------------------------------------------- online learning
class OnlineLearner:
    """Saturating-counter prototypes with bundle-all or error-driven updates."""

    def __init__(self, C, D, w, mode, T, sim=Similarity(), k=0, seed=0):
        assert mode in ("bundle", "error")
        self.C, self.D, self.w, self.mode, self.sim = C, D, w, mode, sim
        self.k, self.seed, self.u = k, seed, 0
        self.lo, self.hi = -(1 << (w - 1)), (1 << (w - 1)) - 1
        self.T = T[:D].astype(bool)
        self.cnt = np.zeros((C, D), dtype=np.int16)
        self.proto = np.repeat(self.T[None, :], C, 0).astype(np.uint8)
        self.protop = pack(self.proto)

    def _add(self, c, b):
        np.clip(self.cnt[c] + b, self.lo, self.hi, out=self.cnt[c])
        p = (self.cnt[c] > 0) | ((self.cnt[c] == 0) & self.T)
        self.proto[c] = p
        self.protop[c] = pack(p.astype(np.uint8))

    def _bipolar(self, q):
        b = 2 * q.astype(np.int16) - 1
        if self.k:
            b = b * update_mask(self.seed, self.u, self.k, self.D)
        self.u += 1
        return b

    def step(self, q, qp, y):
        """Test-then-train on one sample: predict with current prototypes, then learn."""
        pred = int(classify(qp, self.protop, self.sim))
        if self.mode == "bundle":
            self._add(y, self._bipolar(q))
        elif pred != y:
            b = self._bipolar(q)
            self._add(y, b)
            self._add(pred, -b)
        return pred

    def predict(self, Qp, sim=None):
        return classify(Qp, self.protop, sim or self.sim)


def train(Q, y, D, w, mode, T, sim=Similarity(), k=0, seed=0, error_epochs=3, callback=None):
    """Standard recipe: bundle-all pass, then (mode='error') error-driven passes.

    Q are [N, D_MAX] query bits (prefix D is used). The stream order is seeded.
    callback(learner, n_seen, pred, y) is called after every step (for learning curves).
    """
    Qd = np.ascontiguousarray(Q[:, :D]); Qp = pack(Qd)
    rng = np.random.default_rng(1000 + seed)
    L = OnlineLearner(len(np.unique(y)), D, w, "bundle", T, sim, k, seed)
    passes = ["bundle"] + (["error"] * error_epochs if mode == "error" else [])
    n = 0
    for m in passes:
        L.mode = m
        for i in rng.permutation(len(y)):
            pred = L.step(Qd[i], Qp[i], y[i])
            n += 1
            if callback:
                callback(L, n, pred, y[i])
    return L
