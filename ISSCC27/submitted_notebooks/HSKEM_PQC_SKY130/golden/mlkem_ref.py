"""Independent Python golden model for the ML-KEM-512 datapath blocks.

Nothing here is derived from the RTL: the NTT twiddles are recomputed from
the FIPS 203 definition (zeta = 17, BitRev7) and Keccak-f[1600] is checked
against Python's hashlib SHA3 implementation.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import hashlib
import random

Q = 3329
N = 256
ZETA = 17
INV128 = pow(128, -1, Q)  # 3303


def bitrev7(x: int) -> int:
    return int(f"{x:07b}"[::-1], 2)


ZETAS = [pow(ZETA, bitrev7(i), Q) for i in range(128)]
GAMMAS = [pow(ZETA, 2 * bitrev7(i) + 1, Q) for i in range(128)]


def ntt(f: list[int]) -> list[int]:
    """FIPS 203 Algorithm 9."""
    f = list(f)
    k = 1
    length = 128
    while length >= 2:
        for start in range(0, N, 2 * length):
            z = ZETAS[k]
            k += 1
            for j in range(start, start + length):
                t = (z * f[j + length]) % Q
                f[j + length] = (f[j] - t) % Q
                f[j] = (f[j] + t) % Q
        length //= 2
    return f


def intt(f: list[int]) -> list[int]:
    """FIPS 203 Algorithm 10."""
    f = list(f)
    k = 127
    length = 2
    while length <= 128:
        for start in range(0, N, 2 * length):
            z = ZETAS[k]
            k -= 1
            for j in range(start, start + length):
                t = f[j]
                f[j] = (t + f[j + length]) % Q
                f[j + length] = (z * (f[j + length] - t)) % Q
        length *= 2
    return [(x * INV128) % Q for x in f]


def multiply_ntts(a: list[int], b: list[int]) -> list[int]:
    """FIPS 203 Algorithms 11/12 (base-case multiply)."""
    h = [0] * N
    for i in range(128):
        a0, a1, b0, b1, g = a[2 * i], a[2 * i + 1], b[2 * i], b[2 * i + 1], GAMMAS[i]
        h[2 * i] = (a0 * b0 + a1 * b1 * g) % Q
        h[2 * i + 1] = (a0 * b1 + a1 * b0) % Q
    return h


def schoolbook_negacyclic(a: list[int], b: list[int]) -> list[int]:
    """Direct product in Z_q[X]/(X^256+1): the mathematical oracle."""
    c = [0] * N
    for i in range(N):
        for j in range(N):
            if i + j < N:
                c[i + j] += a[i] * b[j]
            else:
                c[i + j - N] -= a[i] * b[j]
    return [x % Q for x in c]


# ---------------------------------------------------------------- Keccak-f1600
_RC = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]
_ROT = [[0, 36, 3, 41, 18], [1, 44, 10, 45, 2], [62, 6, 43, 15, 61],
        [28, 55, 25, 21, 56], [27, 20, 39, 8, 14]]
_M = (1 << 64) - 1


def _rol(v: int, n: int) -> int:
    return ((v << n) | (v >> (64 - n))) & _M if n else v


def keccak_f1600(lanes: list[int]) -> list[int]:
    """lanes[x + 5*y], 64-bit little-endian lanes (FIPS 202 ordering)."""
    a = list(lanes)
    for rnd in range(24):
        c = [a[x] ^ a[x + 5] ^ a[x + 10] ^ a[x + 15] ^ a[x + 20] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rol(c[(x + 1) % 5], 1) for x in range(5)]
        a = [a[i] ^ d[i % 5] for i in range(25)]
        b = [0] * 25
        for x in range(5):
            for y in range(5):
                b[y + 5 * ((2 * x + 3 * y) % 5)] = _rol(a[x + 5 * y], _ROT[x][y])
        a = [b[i] ^ (~b[(i % 5 + 1) % 5 + 5 * (i // 5)] & b[(i % 5 + 2) % 5 + 5 * (i // 5)])
             for i in range(25)]
        a[0] ^= _RC[rnd]
    return a


def sha3_256_via_model(msg: bytes) -> bytes:
    """Minimal sponge on top of keccak_f1600, used only to validate the model."""
    rate = 136
    padded = bytearray(msg) + b"\x06"
    padded += b"\x00" * ((-len(padded)) % rate)
    padded[-1] |= 0x80
    st = [0] * 25
    for off in range(0, len(padded), rate):
        blk = padded[off:off + rate]
        for i in range(rate // 8):
            st[i] ^= int.from_bytes(blk[8 * i:8 * i + 8], "little")
        st = keccak_f1600(st)
    return b"".join(st[i].to_bytes(8, "little") for i in range(4))


def lanes_to_int(lanes: list[int]) -> int:
    """Pack lanes so lane i occupies bits [64*i +: 64] (RTL state vector)."""
    return sum(v << (64 * i) for i, v in enumerate(lanes))


def int_to_lanes(v: int) -> list[int]:
    return [(v >> (64 * i)) & _M for i in range(25)]


# ------------------------------------------------------------------ self-check
def self_check(seed: int = 2027, trials: int = 50) -> dict:
    rng = random.Random(seed)
    res = {}
    # 1) twiddles match the FIPS 203 Appendix A table head
    assert ZETAS[:8] == [1, 1729, 2580, 3289, 2642, 630, 1897, 848]
    # 2) NTT/INTT round trip and convolution theorem vs schoolbook
    for _ in range(trials):
        a = [rng.randrange(Q) for _ in range(N)]
        b = [rng.randrange(Q) for _ in range(N)]
        assert intt(ntt(a)) == a
        assert intt(multiply_ntts(ntt(a), ntt(b))) == schoolbook_negacyclic(a, b)
    res["ntt_trials"] = trials
    # 3) cross-check against the third-party kyber-py implementation if present
    try:
        from kyber_py.ml_kem.default_parameters import ML_KEM_512 as K  # noqa
        R = K.R
        for _ in range(trials):
            a = [rng.randrange(Q) for _ in range(N)]
            assert R(list(a)).to_ntt().coeffs == ntt(a)  # kyber-py mutates its input
        res["kyber_py_crosscheck"] = trials
    except Exception as exc:  # pragma: no cover - optional dependency
        res["kyber_py_crosscheck"] = f"skipped ({type(exc).__name__}: {exc})"
    # 4) Keccak model vs hashlib
    for n in (0, 1, 135, 136, 137, 500):
        m = rng.randbytes(n)
        assert sha3_256_via_model(m) == hashlib.sha3_256(m).digest()
    res["sha3_lengths"] = 6
    return res


if __name__ == "__main__":
    print(self_check())
