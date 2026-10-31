# Numerical settings of the closure benches

Bench: F2 design, `tt`/1.8 V/27 °C, sequence 0.9 → 0.6 → 1.2 → 0.9, early-window held error (mV), 2026-10-31.

| setting | cycle 1 (0.6) | cycle 2 (1.2) | cycle 3 (0.9) |
|---|---:|---:|---:|
| tmax 20 ps, reltol 1e-4 | −7.4323 | 5.0077 | −1.7196 |
| tmax 10 ps, reltol 1e-4 (**default**) | −7.4157 | 4.9935 | −1.7207 |
| tmax 5 ps, reltol 1e-4 | −7.4137 | 4.9964 | −1.7213 |
| tmax 20 ps, reltol 1e-5 | −7.4234 | 5.0023 | −1.7198 |
| tmax 5 ps, reltol 1e-5 | −7.4138 | 4.9961 | −1.7213 |
| tmax 100 ps, reltol 1e-5 | −7.4278 | 5.0023 | −1.7199 |
| tmax 100 ps, reltol 1e-6, abstol 1e-15 | −7.4156 | 4.9982 | −1.7211 |

The default differs from the finest settings by ≤ 0.003 mV on these raw values. Run time is dominated by loading the
SKY130 library (~17 s per ngspice invocation), not by the transient. With the bootstrapped switch, 10 ps / 1e-4
produced 0.1–0.14 mV jumps between neighbouring levels at cold corners that 5 ps / 1e-5 removes; all closure runs use
5 ps / 1e-5. The finer-numerics rerun of the selected design is a supporting check (amendment A9) and appears in the
final closure result only if it was run.
