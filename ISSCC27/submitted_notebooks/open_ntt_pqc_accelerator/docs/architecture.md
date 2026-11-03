# OpenNTT Architecture

OpenNTT is a hardware accelerator for the Number Theoretic Transform (NTT), the
computational bottleneck of the NIST post-quantum lattice standards ML-DSA
(Dilithium) and ML-KEM (Kyber). This document describes the design that the
Jupyter notebook builds, verifies, and hardens to a Sky130 layout.

## 1. Background

Lattice cryptography multiplies polynomials in the ring `R_q = Z_q[x] / (x^n + 1)`.
A naive polynomial multiply is `O(n^2)` modular multiplications. The NTT is an
FFT over the finite field `Z_q`; it turns polynomial multiplication into a
point-wise product, reducing the cost to `O(n log n)`:

```
c = INTT( NTT(a) ∘ NTT(b) )
```

Two parameter sets are targeted:

| Mode      | q         | n   | NTT type   | Notes                          |
|-----------|-----------|-----|------------|--------------------------------|
| Dilithium | 8380417   | 256 | complete   | 512 divides q-1, radix-2, 8 layers |
| Kyber     | 3329      | 256 | incomplete | only 256 divides q-1, 7 layers, degree-1 base multiply |

The complete Dilithium NTT is implemented first because it is the cleaner
radix-2 Cooley-Tukey structure. Kyber reuses the same datapath with a different
modulus, twiddle table, and one fewer layer plus a base-case multiply.

## 2. Modular multiplication

The critical arithmetic cell is the modular multiplier. Hardware avoids division
by using **Montgomery reduction** with `R = 2^32`:

```
T = a * b
m = (T mod R) * QPRIME mod R          # QPRIME = (-q^{-1}) mod R
u = (T + m*q) / R
if u >= q: u -= q                     # result in [0, q)
```

`mod_mul(a, b) = a * b * R^{-1} mod q`. Twiddle factors are stored pre-scaled
into the Montgomery domain (multiplied by `R`), so that
`mod_mul(zeta_mont, x) == (zeta * x) mod q` with no extra conversion.

For Dilithium, `QPRIME = 4236238847` (equivalently `2^32 - 58728449`, matching
the Dilithium reference constant).

## 3. Butterfly

The Cooley-Tukey (decimation-in-time) butterfly is:

```
t          = mod_mul(zeta, a[j+len])
a[j+len]   = mod_sub(a[j], t)          # (a[j] - t) mod q
a[j]       = mod_add(a[j], t)          # (a[j] + t) mod q
```

`mod_add` / `mod_sub` are conditional additions/subtractions of `q`.

## 4. Module hierarchy

```
ntt_top
├── mod_mul       Montgomery modular multiplier (critical cell)
├── butterfly     mod_mul + mod_add + mod_sub
├── coeff_ram     256 x 24-bit coefficient memory
├── twiddle_rom   256 x 24-bit zetas, Montgomery domain, bit-reversed order
└── ntt_ctrl      FSM + address / twiddle-index generator
```

Coefficient width is 24 bits (`q-1 < 2^23`, with one bit of headroom).

## 5. Schedule (baseline)

The baseline uses a single butterfly and a single-port coefficient memory,
taking roughly four cycles per butterfly (read two operands, compute, write two
results). With `n = 256` there are `(n/2) * log2(n) = 1024` butterflies, so a
full NTT is on the order of 4096 cycles. Throughput-oriented variants (dual-bank
memory, deeper pipelining, multiple butterfly units) are explored later for the
area/throughput Pareto study.

## 6. Verification strategy

Every hardware block is checked against `src/ntt_golden.py`, a pure-Python
reference that performs the identical Montgomery operation sequence. cocotb
drives random and known-answer vectors into the RTL and compares against the
golden model. The golden model itself is validated against a schoolbook
negacyclic multiply and against NTT round-trip identity.

## 7. Flow

1. Python golden model (`src/ntt_golden.py`).
2. RTL (`src/*.v`).
3. Functional verification (cocotb + Icarus Verilog).
4. Synthesis and PPA (Yosys + OpenLane2, Sky130).
5. Place-and-route to GDS (OpenLane2), viewed in KLayout.
6. SPICE characterization of the Montgomery cell across PVT corners (ngspice).
