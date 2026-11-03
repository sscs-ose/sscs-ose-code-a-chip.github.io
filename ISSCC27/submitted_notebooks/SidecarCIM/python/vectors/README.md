# Test vectors

`python/vectors.py` writes every file in this folder; do not edit or
regenerate them elsewhere. Load one with `d = np.load(f)`. All values are
unsigned codes as the macro sees them, and `y` is the reference result from
`python/golden.py`, with the sizes and bit widths taken from `spec/spec.yaml`.
The seeds are fixed, so a rerun gives the same arrays.

## 4-bit dense core

`corners.npz` (34 edge cases, with `names`), `random.npz` (10,000 cases, seed
2026) and `real_layer.npz` (4,096 GPT-2 `h.0.mlp.c_fc` tiles with their
`ln_2` activations) hold `w` uint8 (cases, n_inputs, n_outputs), `x` uint8
(cases, n_inputs) and `y` int32 (cases, n_outputs), with
`y[c] = golden.dcim_dot(w[c], x[c], 4, 4) = x[c] @ w[c]`. The real-layer file
also carries `tile_row`, `tile_col`, `token`, `zw` and `zx`, only so a case can
be traced back to the layer. `outlier_stats.json` is a small preview of the
weight-outlier counts and 4-bit error on a short calibration paragraph; it is
not a test vector.

`real_layer.npz` is the naive W4A4 encoding (no migration, calibrated on the
hand-written paragraph in `vectors.py`). `w4a4_{corners,random,real_layer}.npz`
(`python vectors.py w4a4`, also written by the full run) hold W4A4 + migration
+ clip, the encoding of the 4-bit accuracy row and of the gate-level power of
`dcim_core_ff`: GPT-2 `h.0.mlp.c_fc` through `novelty_study.encode_pick2` as
for W6A4 below (alpha 0.95, as `alternatives.json` picks for h.0), the same
4,096 (tile, token) cases as `w6a4_real_layer.npz`, x codes 0 to 15 with zero
point 8. `w4a4_corners` and `w4a4_random` equal `corners` and `random` array
for array; they exist so the testbench can run the set with
`DCIM_VEC_PREFIX=w4a4_`.

## 8-bit dense core and SidecarCIM

`dense8_{corners,random,real_layer}.npz` have the same keys at
WBITS = ABITS = 8 (42 corners, 10,000 random, 4,096 tiles of the W8A8
encoding), with `y = dcim_dot(w, x, 8, 8)`.

`sidecar_{corners,random,real_layer}.npz` are for `rtl/sidecarcim_top.v`.
They add `idx` uint8 (cases, k, n_outputs), the slot row, `val` int16
(cases, k, n_outputs), a signed 12-bit slot value with 0 for an unused slot,
and `S` uint8 (cases, n_outputs), the shift. VB is the spec
`outlier.weight_bits` = 12, so `val` is in -2048..2047 and S in 0..11. The
result is `y = golden.sidecarcim_dot(w, x, idx, val, S, 4, 4) =
(dcim_dot << S) + sidecar_dot`, raw and signed, which fits 26 bits. There are
26 corner cases (with `names`; every slot sees -2048 and +2047, and S = 11
meets the dense maximum), 10,000 random cases and 4,096 real-layer tiles of the
SidecarCIM encoding of `h.0.mlp.c_fc` (top-2 |w|, alpha 1.0, weight clip,
calibration on 512 WikiText-2 training tokens, x from the first 2,048 test
tokens). In the real tiles S is 3 to 7 and no slot sits at the 12-bit limit.
The slot row keeps its dense code `zw`, because both paths add, as in the
hardware.

## 3-bit S sets (`SBITS=3`)

`python vectors.py s3` writes these, and so does the full run.

- `sidecar_s3_corners.npz` (26) and `sidecar_s3_random.npz` (10,000, seed
  2026) use the same generators and format as `sidecar_*` with S limited to
  0..7. The corner `S7_dense_max_side_max` (all w 15, all x 15, slots +2047,
  S 7) gives the maximum y, 983,010, and `S7_dense_max_side_min` gives
  860,160. `y = golden.sidecarcim_dot(..., sbits=3)`, with a merged width of
  22 bits at K = 2.
- `sidecar_s3_real_layer.npz` (4,096) holds the same arrays as
  `sidecar_real_layer.npz`, whose S is already 3 to 7, with y rechecked at
  `sbits=3`.

## Dense W6A4, W7A4, W8A4 and W4A8

`w6a4_*`, `w7a4_*`, `w8a4_*` and `w4a8_*` (each `corners`, `random`,
`real_layer`) have the keys, dtypes and meaning of `dense8_*`, for
`dcim_core` with WBITS = 6, 7 or 8 and ABITS = 4, or WBITS = 4 and ABITS = 8.
`y = golden.dcim_dot(w, x, wbits, abits)`, raw and unsigned. There are 36,
37, 38 and 38 corners with `names`, 10,000 random cases each (seed 2026) and
4,096 real-layer cases each. The real-layer cases are GPT-2 `h.0.mlp.c_fc`
encoded the way the accuracy runs encode the same scheme: migration with
alpha picked on the calibration layer error (1.0 for W6A4, W7A4 and W8A4,
0.85 for W4A8), a per-output-channel weight scale with the weight-clip search
and a per-tensor activation scale, calibrated on 512 WikiText-2 training
tokens with x from the first 2,048 test tokens. `zw` and `zx` let you check
the signed tile dot, `y - (zw*sum(x) + zx*sum(w) - 32*zx*zw)`, which was
checked when the files were written. `python vectors.py dense_extra` writes
the W7A4 and W4A8 sets alone.

## Figure arrays

`python/out/arrays.npz` is not a vector file. `python/extras.py arrays`
writes it: the per-channel activation abs-max over std of GPT-2 `h.0` and
Qwen on the 512-token calibration slice, and the per-tile-column 3-sigma
count histograms of GPT-2 (bins 0..15) before and after alpha-1.0 migration,
for `h.0` and all 12 layers.
