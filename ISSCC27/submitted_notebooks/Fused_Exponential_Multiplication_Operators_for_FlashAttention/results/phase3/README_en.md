# Phase 3 — GLUE / Flan-T5 accuracy (100 examples per task)

**English** | [中文](README_zh.md)

## 1. Method

Every `T5Attention.forward` call is replaced by a FlashAttention-2 kernel with ExpMul weights;
the rest of the model (LayerNorm, FFN, embeddings) is untouched:

```python
q, k, v = shape(self.q(hs)), shape(self.k(kv)), shape(self.v(kv))
position_bias = compute_bias(...) + mask
s = q @ k^T + position_bias
m = s.max(-1, keepdim=True)
w = ExpMul(s - m, 1)                 # bit-exact replica of src/expmul.hpp
o = (w @ v) / w.sum(-1)              # same o/l normalisation as the kernel
attn_output = self.o(o)
```

- Scoring: teacher forcing, `score(label) = Σ log p(label_tokens, EOS | prompt)`; the highest
  score wins, so no autoregressive decoding is needed.
- Variants: `fp32`, `fp32_exp` (Algorithm 3, exponent-only), `fp32_mi` (mantissa-interpolated),
  `bf16`, `bf16_mi`.
- Data: GLUE validation split, `shuffle(seed=20250520).select(range(100))`, parquet from
  hf-mirror.
- Model: `google/flan-t5-base` (248 M parameters), local safetensors, 8 CPU threads.

## 2. Results (completed tasks)

| Task | fp32 | fp32_exp | fp32_mi | bf16 | bf16_mi |
|---|---|---|---|---|---|
| SST-2 (acc) | 81.0 | 79.0 | **82.0** | 81.0 | 81.0 |
| MNLI-m (acc) | 37.0 | 36.0 | 37.0 | 37.0 | 37.0 |
| MNLI-mm (acc) | 28.0 | 29.0 | 29.0 | 29.0 | 29.0 |

F1 scores are written to `glue_results.csv`; the evaluation continues on the build machine for the
remaining seven tasks.

## 3. How to read this table (important)

1. **The absolute levels are not comparable with Table I of the paper.** The paper uses the
   few-shot PromptBench protocol and a larger Flan-T5, reaching 87.5 on MNLI; here the setting is
   **zero-shot with the base model and 100 examples per task**, which gives 37 % on MNLI
   (three-way random is 33 %), i.e. neither the prompt nor the model scale matches.
2. **The differences between variants are at most 2 points, while the 95 % binomial confidence
   interval for n = 100 is about ±8 points.** The difference between ExpMul and FP32 is therefore
   within noise: the direction agrees with the paper, but the result is **statistically
   inconclusive**.
3. The observed trend is `fp32_mi` ≈ `fp32` (even +1 on SST-2) and `fp32_exp` 2 points lower on
   SST-2, consistent with the kernel errors of Phase 2 (2–5 % for MI, 15–22 % for exponent-only).
4. A ±1 % conclusion of the kind reported in the paper would require `flan-t5-large`/`xl`, the
   few-shot PromptBench templates and at least 1000 examples per task (to bring the confidence
   interval below ±3 points). The script is parameterised, so only the model and the sample count
   need to change.

## 4. Reproduction

```bash
cd $HOME/flashattn_expmul
HF_HUB_OFFLINE=1 venv/bin/python t5_glue.py \
    --model models/flan-t5-base --data_dir data/glue --n 100 \
    --variants fp32 fp32_exp fp32_mi bf16 bf16_mi --out results/phase3
```

Artifacts: `results/phase3/glue_results.csv`, `phase3_glue.png` (produced by
`model/plot_phase34.py`).
