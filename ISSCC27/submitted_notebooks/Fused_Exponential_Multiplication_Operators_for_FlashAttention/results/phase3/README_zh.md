# 阶段 3：GLUE / Flan-T5 精度（每任务 100 条）

[English](README_en.md) | **中文**

## 1. 方法

把 `T5Attention.forward` 整体替换为 FA2 + ExpMul 的 torch 实现，其它部分（LayerNorm、FFN、
embedding）不动：

```python
q, k, v = shape(self.q(hs)), shape(self.k(kv)), shape(self.v(kv))
position_bias = compute_bias(...) + mask
s = q @ k^T + position_bias
m = s.max(-1, keepdim=True)
w = ExpMul(s - m, 1)                 # 位精确复刻 src/expmul.hpp
o = (w @ v) / w.sum(-1)              # 与 kernel 的 o/l 归一化一致
attn_output = self.o(o)
```

- 打分：teacher forcing，`score(label) = Σ log p(label_tokens, EOS | prompt)`，取最大者，不做自回归。
- 变体：`fp32` / `fp32_exp`（Alg.3 指数域）/ `fp32_mi`（尾数插值）/ `bf16` / `bf16_mi`。
- 数据：GLUE 验证集，`shuffle(seed=20250520).select(range(100))`，parquet 从 hf-mirror 取。
- 模型：`google/flan-t5-base`（248M 参数），本地 safetensors，CPU 8 线程。

## 2. 结果（已完成部分）

| 任务 | fp32 | fp32_exp | fp32_mi | bf16 | bf16_mi |
|---|---|---|---|---|---|
| SST-2 (acc) | 81.0 | 79.0 | **82.0** | 81.0 | 81.0 |
| MNLI-m (acc) | 37.0 | 36.0 | 37.0 | 37.0 | 37.0 |
| MNLI-mm (acc) | 28.0 | 29.0 | 29.0 | 29.0 | 29.0 |

（同时输出 F1，见 `glue_results.csv`；评测仍在构建机上继续跑其余 7 个任务。）

## 3. 怎么读这张表（重要）

1. **绝对水平不能和论文 Table I 比**。论文用 PromptBench 的 few-shot 协议 + 更大的
   Flan-T5，MNLI 到 87.5；这里是 **zero-shot、base 模型、每任务 100 条**，
   MNLI 只有 37%（三分类随机 33%），说明 prompt/模型规模都不匹配。
2. **相对差异 ≤ 2 个点，而 n=100 的二项 95% 置信区间约 ±8 个点**——即
   “ExpMul 与 FP32 的差异在噪声内”，方向上与论文一致，但**统计上不可判定**。
3. 目测趋势：`fp32_mi` ≈ `fp32`（SST-2 甚至 +1），`fp32_exp` 在 SST-2 上 −2 点，
   与阶段 2 的 kernel 误差（mi 2–5%、exp 15–22%）方向一致。
4. 要做成论文那种 ±1% 的结论，需要：flan-t5-large/xl、PromptBench 的 few-shot 模板、
   每任务 ≥1000 条（CI 才能压到 ±3 点以内）。脚本已参数化，换模型/样本数即可。

## 4. 复现

```bash
cd $HOME/flashattn_expmul
HF_HUB_OFFLINE=1 venv/bin/python t5_glue.py \
    --model models/flan-t5-base --data_dir data/glue --n 100 \
    --variants fp32 fp32_exp fp32_mi bf16 bf16_mi --out results/phase3
```

产物：`results/phase3/glue_results.csv`、`phase3_glue.png`（`model/plot_phase34.py`）。
