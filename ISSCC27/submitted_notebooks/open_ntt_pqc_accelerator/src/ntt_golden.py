

from typing import List


DIL_Q = 8380417   # Dilithium modulus
DIL_N = 256
DIL_ROOT = 1753   # primitive 512th root of unity (2n-th) mod DIL_Q

KY_Q = 3329       # Kyber modulus
KY_N = 256
KY_ROOT = 17      # primitive 256th root of unity mod KY_Q


# ---------------------------------------------------------------------------
# Basic modular arithmetic
# ---------------------------------------------------------------------------
def modexp(base: int, exp: int, q: int) -> int:
    """Modular exponentiation."""
    result = 1
    base %= q
    while exp > 0:
        if exp & 1:
            result = (result * base) % q
        exp >>= 1
        base = (base * base) % q
    return result


def modinv(a: int, q: int) -> int:
    """Modular inverse via Fermat (q prime)."""
    return modexp(a, q - 2, q)


def bit_reverse(i: int, bits: int) -> int:
    r = 0
    for _ in range(bits):
        r = (r << 1) | (i & 1)
        i >>= 1
    return r


# ---------------------------------------------------------------------------
# Schoolbook negacyclic reference: multiply in Z_q[x] / (x^n + 1)
# ---------------------------------------------------------------------------
def poly_mul_negacyclic(a: List[int], b: List[int], q: int) -> List[int]:
    n = len(a)
    tmp = [0] * (2 * n)
    for i in range(n):
        ai = a[i]
        if ai == 0:
            continue
        for j in range(n):
            tmp[i + j] = (tmp[i + j] + ai * b[j]) % q
    out = [0] * n
    for i in range(n):
        # x^n = -1  ->  fold high half back with a sign flip
        out[i] = (tmp[i] - tmp[i + n]) % q
    return out


# ---------------------------------------------------------------------------
# Complete NTT (Dilithium style): in-place Cooley-Tukey, output in
# bit-reversed order. Twiddles are powers of the 2n-th root in bit-reversed
# order (the standard "merged" negacyclic NTT, no separate pre-weighting).
# ---------------------------------------------------------------------------
def _zetas_complete(root: int, n: int, q: int) -> List[int]:
    bits = n.bit_length() - 1  # log2(n)
    return [modexp(root, bit_reverse(i, bits), q) for i in range(n)]


def ntt_complete(a: List[int], q: int, root: int) -> List[int]:
    a = list(a)
    n = len(a)
    zetas = _zetas_complete(root, n, q)
    k = 0
    length = n // 2
    while length >= 1:
        start = 0
        while start < n:
            k += 1
            zeta = zetas[k]
            for j in range(start, start + length):
                t = (zeta * a[j + length]) % q
                a[j + length] = (a[j] - t) % q
                a[j] = (a[j] + t) % q
            start += 2 * length
        length >>= 1
    return a


def intt_complete(a: List[int], q: int, root: int) -> List[int]:
    a = list(a)
    n = len(a)
    zetas = _zetas_complete(root, n, q)
    k = n
    length = 1
    while length < n:
        start = 0
        while start < n:
            k -= 1
            zeta = (-zetas[k]) % q  # inverse butterfly uses -zeta
            for j in range(start, start + length):
                t = a[j]
                a[j] = (t + a[j + length]) % q
                a[j + length] = (t - a[j + length]) % q
                a[j + length] = (zeta * a[j + length]) % q
            start += 2 * length
        length <<= 1
    ninv = modinv(n, q)
    return [(x * ninv) % q for x in a]


def poly_mul_ntt_complete(a: List[int], b: List[int], q: int, root: int) -> List[int]:
    fa = ntt_complete(a, q, root)
    fb = ntt_complete(b, q, root)
    fc = [(x * y) % q for x, y in zip(fa, fb)]
    return intt_complete(fc, q, root)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import random
    random.seed(0)

    # Dilithium complete NTT round-trip + convolution check
    n, q, root = DIL_N, DIL_Q, DIL_ROOT
    a = [random.randrange(q) for _ in range(n)]
    b = [random.randrange(q) for _ in range(n)]

    rt = intt_complete(ntt_complete(a, q, root), q, root)
    assert rt == a, "Dilithium INTT(NTT(a)) round-trip FAILED"

    ref = poly_mul_negacyclic(a, b, q)
    got = poly_mul_ntt_complete(a, b, q, root)
    assert ref == got, "Dilithium NTT convolution != schoolbook negacyclic"

    print("Dilithium complete NTT: round-trip OK, convolution OK  (n=%d q=%d)" % (n, q))
    print("All golden-model self-tests PASSED.")
