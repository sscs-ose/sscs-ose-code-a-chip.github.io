# Simulated leakage of the session HMAC (B4, 24/10)

`scripts/run_leakage_hmac.sh 2000 4.0`: fixed-vs-random TVLA on the register-transition model of `hmac_sha256_fixed`
(chip configuration, sliding SHA-256 schedule), one trace per HMAC-SHA-256 of a random 28-byte frame message, key fixed
or random (`golden/leakage_hmac.py`, `tb/tb_hmac_leak.sv`). Every digest of the simulation equals Python's hmac.

| | value |
|:---|:---|
| traces (fixed / random key) | 2,000 (997 / 1,003) |
| cycles per HMAC | 264 (as measured on the board, Fig. 5 of the paper) |
| cycles with \|t\| > 4.5 | 126 of 264 |
| largest \|t\| | 60.4 |
| negative control (random vs random) | largest \|t\| 2.36, 0 cycles over 4.5 |
| per compression (66 cycles each): cycles over 4.5 / largest \|t\| | 62 / 60.4, 5 / 28.0, 54 / 56.0, 5 / 35.7 |

The leakage concentrates in the compressions of K xor ipad and K xor opad, which depend on the key alone and repeat
identically in every HMAC under the same K. Model only (register transitions plus Gaussian noise of 4 bit flips), no
glitches, no measured power; it shows that the HMAC engine is unprotected, not how many traces an attack would need.
