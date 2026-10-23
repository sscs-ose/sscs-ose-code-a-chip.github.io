"""Complete ML-KEM-512 (FIPS 203) reference built on the golden NTT.

Written from the FIPS 203 algorithm listings (Alg. 3-18) using only Python's
hashlib for SHA3/SHAKE. `acvp_check()` validates it against the official NIST
ACVP ML-KEM-512 vectors (keyGen, encapsulation, decapsulation) shipped in
golden/acvp/.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import hashlib
import json
import pathlib

from mlkem_ref import GAMMAS, N, Q, intt, ntt  # noqa: F401  (GAMMAS via multiply_ntts)
from mlkem_ref import multiply_ntts

K, ETA1, ETA2, DU, DV = 2, 3, 2, 10, 4  # ML-KEM-512 parameter set


# ------------------------------------------------------------ hash functions
def G(x: bytes) -> tuple[bytes, bytes]:
    h = hashlib.sha3_512(x).digest()
    return h[:32], h[32:]


def H(x: bytes) -> bytes:
    return hashlib.sha3_256(x).digest()


def J(x: bytes) -> bytes:
    return hashlib.shake_256(x).digest(32)


def PRF(eta: int, s: bytes, b: int) -> bytes:
    return hashlib.shake_256(s + bytes([b])).digest(64 * eta)


# ----------------------------------------------------- encoding / sampling
def bytes_to_bits(b: bytes) -> list[int]:
    return [(byte >> i) & 1 for byte in b for i in range(8)]


def bits_to_bytes(bits: list[int]) -> bytes:
    return bytes(sum(bits[8 * i + j] << j for j in range(8)) for i in range(len(bits) // 8))


def byte_encode(f: list[int], d: int) -> bytes:              # Alg. 5
    bits = []
    for a in f:
        bits += [(a >> j) & 1 for j in range(d)]
    return bits_to_bytes(bits)


def byte_decode(b: bytes, d: int) -> list[int]:              # Alg. 6
    bits = bytes_to_bits(b)
    m = (1 << d) if d < 12 else Q
    return [sum(bits[i * d + j] << j for j in range(d)) % m for i in range(N)]


def compress(x: int, d: int) -> int:                         # round(2^d x / q) mod 2^d
    return ((x << (d + 1)) + Q) // (2 * Q) % (1 << d)


def decompress(y: int, d: int) -> int:                       # round(q y / 2^d)
    return (Q * y * 2 + (1 << d)) >> (d + 1)


def sample_ntt(seed: bytes) -> list[int]:                    # Alg. 7
    need, stream = 840, b""
    while True:
        stream = hashlib.shake_128(seed).digest(need)
        a, i = [], 0
        while len(a) < N and i + 3 <= len(stream):
            c0, c1, c2 = stream[i], stream[i + 1], stream[i + 2]
            d1, d2 = c0 + 256 * (c1 % 16), c1 // 16 + 16 * c2
            if d1 < Q:
                a.append(d1)
            if d2 < Q and len(a) < N:
                a.append(d2)
            i += 3
        if len(a) == N:
            return a
        need *= 2  # extremely rare: squeeze more


def sample_cbd(b: bytes, eta: int) -> list[int]:             # Alg. 8
    bits = bytes_to_bits(b)
    return [(sum(bits[2 * i * eta + j] for j in range(eta))
             - sum(bits[2 * i * eta + eta + j] for j in range(eta))) % Q for i in range(N)]


def add(a, b):
    return [(x + y) % Q for x, y in zip(a, b)]


def sub(a, b):
    return [(x - y) % Q for x, y in zip(a, b)]


def matrix(rho: bytes) -> list[list[list[int]]]:
    return [[sample_ntt(rho + bytes([j, i])) for j in range(K)] for i in range(K)]


# ------------------------------------------------------------------ K-PKE
def kpke_keygen(d: bytes) -> tuple[bytes, bytes]:            # Alg. 13
    rho, sigma = G(d + bytes([K]))
    A = matrix(rho)
    n = 0
    s, e = [], []
    for _ in range(K):
        s.append(sample_cbd(PRF(ETA1, sigma, n), ETA1)); n += 1
    for _ in range(K):
        e.append(sample_cbd(PRF(ETA1, sigma, n), ETA1)); n += 1
    s_hat, e_hat = [ntt(x) for x in s], [ntt(x) for x in e]
    t_hat = []
    for i in range(K):
        acc = [0] * N
        for j in range(K):
            acc = add(acc, multiply_ntts(A[i][j], s_hat[j]))
        t_hat.append(add(acc, e_hat[i]))
    ek = b"".join(byte_encode(t, 12) for t in t_hat) + rho
    dk = b"".join(byte_encode(s, 12) for s in s_hat)
    return ek, dk


def kpke_encrypt(ek: bytes, m: bytes, r: bytes) -> bytes:    # Alg. 14
    t_hat = [byte_decode(ek[384 * i:384 * (i + 1)], 12) for i in range(K)]
    rho = ek[384 * K:]
    A = matrix(rho)
    n = 0
    y, e1 = [], []
    for _ in range(K):
        y.append(sample_cbd(PRF(ETA1, r, n), ETA1)); n += 1
    for _ in range(K):
        e1.append(sample_cbd(PRF(ETA2, r, n), ETA2)); n += 1
    e2 = sample_cbd(PRF(ETA2, r, n), ETA2)
    y_hat = [ntt(x) for x in y]
    u = []
    for i in range(K):                                       # u = NTT^-1(A^T y) + e1
        acc = [0] * N
        for j in range(K):
            acc = add(acc, multiply_ntts(A[j][i], y_hat[j]))
        u.append(add(intt(acc), e1[i]))
    mu = [decompress(b, 1) for b in byte_decode(m, 1)]
    acc = [0] * N
    for j in range(K):
        acc = add(acc, multiply_ntts(t_hat[j], y_hat[j]))
    v = add(add(intt(acc), e2), mu)
    c1 = b"".join(byte_encode([compress(x, DU) for x in ui], DU) for ui in u)
    c2 = byte_encode([compress(x, DV) for x in v], DV)
    return c1 + c2


def kpke_decrypt(dk: bytes, c: bytes) -> bytes:              # Alg. 15
    c1, c2 = c[:32 * DU * K], c[32 * DU * K:]
    u = [[decompress(x, DU) for x in byte_decode(c1[32 * DU * i:32 * DU * (i + 1)], DU)] for i in range(K)]
    v = [decompress(x, DV) for x in byte_decode(c2, DV)]
    s_hat = [byte_decode(dk[384 * i:384 * (i + 1)], 12) for i in range(K)]
    acc = [0] * N
    for i in range(K):
        acc = add(acc, multiply_ntts(s_hat[i], ntt(u[i])))
    w = sub(v, intt(acc))
    return byte_encode([compress(x, 1) for x in w], 1)


# ----------------------------------------------------------------- ML-KEM
def keygen_internal(d: bytes, z: bytes) -> tuple[bytes, bytes]:   # Alg. 16
    ek, dk_pke = kpke_keygen(d)
    return ek, dk_pke + ek + H(ek) + z


def encaps_internal(ek: bytes, m: bytes) -> tuple[bytes, bytes]:  # Alg. 17
    key, r = G(m + H(ek))
    return key, kpke_encrypt(ek, m, r)


def decaps_internal(dk: bytes, c: bytes) -> bytes:                # Alg. 18
    dk_pke, ek = dk[:384 * K], dk[384 * K:768 * K + 32]
    h, z = dk[768 * K + 32:768 * K + 64], dk[768 * K + 64:]
    m2 = kpke_decrypt(dk_pke, c)
    key2, r2 = G(m2 + h)
    k_bar = J(z + c)
    return key2 if kpke_encrypt(ek, m2, r2) == c else k_bar


# ------------------------------------------------------------------- ACVP
def acvp_check(folder: pathlib.Path | str | None = None) -> dict:
    folder = pathlib.Path(folder or pathlib.Path(__file__).with_name("acvp"))
    x = bytes.fromhex
    res = {"keyGen": [0, 0], "encapsulation": [0, 0], "decapsulation": [0, 0]}
    kg = json.loads((folder / "mlkem512_keygen.json").read_text())
    for t in kg:
        ek, dk = keygen_internal(x(t["d"]), x(t["z"]))
        res["keyGen"][0] += (ek == x(t["ek"]) and dk == x(t["dk"]))
        res["keyGen"][1] += 1
    ed = json.loads((folder / "mlkem512_encapdecap.json").read_text())
    for t in ed["encapsulation"]:
        key, c = encaps_internal(x(t["ek"]), x(t["m"]))
        res["encapsulation"][0] += (key == x(t["k"]) and c == x(t["c"]))
        res["encapsulation"][1] += 1
    for t in ed["decapsulation"]:
        res["decapsulation"][0] += (decaps_internal(x(t["dk"]), x(t["c"])) == x(t["k"]))
        res["decapsulation"][1] += 1
    return {k: f"{p}/{n}" for k, (p, n) in res.items()}


if __name__ == "__main__":
    print(acvp_check())
