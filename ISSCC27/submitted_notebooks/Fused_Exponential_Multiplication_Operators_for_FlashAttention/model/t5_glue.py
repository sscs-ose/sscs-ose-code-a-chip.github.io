#!/usr/bin/env python3
"""t5_glue.py -- Flan-T5 / GLUE accuracy with ExpMul attention (phase 3).

Replaces every T5Attention with a FlashAttention-2 style kernel whose softmax
weights come from the paper's ExpMul operator (Alg.3 / official mantissa-
interpolation variant), then measures GLUE accuracy/F1/Pearson.

Only 100 examples per task (fixed seed) are used, per the quick-validation
request; the 95% binomial confidence interval for n=100 is +-~7-9 pp, so
differences below that are not statistically meaningful.

Usage (on the Linux box):
    python t5_glue.py --model google/flan-t5-base --n 100 \
        --variants fp32 fp32_exp fp32_mi bf16 bf16_mi --out results/phase3
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
import types

import numpy as np
import torch
from datasets import load_dataset
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

# ---------------------------------------------------------------------------
#  ExpMul weights in torch (bit-exact with src/expmul.hpp)
#    x <= 0, V = 1  ->  weight = e^x
# ---------------------------------------------------------------------------
def expmul_weights(x: torch.Tensor, mode: str) -> torch.Tensor:
    xc = torch.clamp(x.float(), -15.0, 0.0)
    xh = torch.floor(xc * 1024.0 + 0.5)
    xh = torch.clamp(xh, -15360.0, 0.0).to(torch.int64)
    p = -(xh + (xh >> 1) - (xh >> 4))            # -x*log2(e), Q6.10
    if mode == "exp_only":
        L = (p + 512) >> 10
        bits = (127 - L) << 23
        return bits.to(torch.int32).view(torch.float32)
    # mantissa interpolation: bits(1.0) - (-x*log2e)*2^23
    D = p << 13
    bits = (0x3F800000 - D).clamp(min=0)
    return bits.to(torch.int32).view(torch.float32)


def fa2_expmul_attention(q, k, v, bias, mode):
    """q,k,v: [b,h,L,dk] (any dtype); bias: additive mask/position bias or None."""
    qf, kf, vf = q.float(), k.float(), v.float()
    s = torch.matmul(qf, kf.transpose(-1, -2))
    if bias is not None:
        s = s + bias.float()
    m = s.max(dim=-1, keepdim=True).values
    w = expmul_weights(s - m, mode)
    if bias is not None:
        w = torch.where(bias <= -1e8, torch.zeros_like(w), w)
    o = torch.matmul(w, vf) / w.sum(dim=-1, keepdim=True).clamp_min(1e-30)
    return o.to(q.dtype)


def fa2_exact_attention(q, k, v, bias):
    qf, kf, vf = q.float(), k.float(), v.float()
    s = torch.matmul(qf, kf.transpose(-1, -2))
    if bias is not None:
        s = s + bias.float()
    w = torch.exp(s - s.max(dim=-1, keepdim=True).values)
    if bias is not None:
        w = torch.where(bias <= -1e8, torch.zeros_like(w), w)
    o = torch.matmul(w, vf) / w.sum(dim=-1, keepdim=True).clamp_min(1e-30)
    return o.to(q.dtype)


# ---------------------------------------------------------------------------
#  T5Attention replacement (mirrors transformers 4.44 T5Attention.forward)
# ---------------------------------------------------------------------------
def make_forward(mode: str):
    """Faithful copy of transformers 4.44.2 T5Attention.forward, with
    softmax+AV replaced by the FlashAttention-2 / ExpMul kernel."""
    def forward(self, hidden_states, mask=None, key_value_states=None,
                position_bias=None, past_key_value=None, layer_head_mask=None,
                query_length=None, use_cache=False, output_attentions=False,
                **kwargs):
        if past_key_value is not None:
            raise NotImplementedError("incremental decoding is not used here")
        batch_size, seq_length = hidden_states.shape[:2]
        real_seq_length = seq_length
        key_length = real_seq_length if key_value_states is None else key_value_states.shape[1]

        def shape(states):
            return states.view(batch_size, -1, self.n_heads,
                               self.key_value_proj_dim).transpose(1, 2)

        q = shape(self.q(hidden_states))
        kv_src = key_value_states if key_value_states is not None else hidden_states
        k = shape(self.k(kv_src))
        v = shape(self.v(kv_src))

        if position_bias is None:
            if not self.has_relative_attention_bias:
                position_bias = torch.zeros((1, self.n_heads, real_seq_length, key_length),
                                            device=q.device, dtype=q.dtype)
            else:
                position_bias = self.compute_bias(real_seq_length, key_length,
                                                  device=q.device)
            if mask is not None:
                position_bias = position_bias + mask

        if self.pruned_heads:
            m = torch.ones(position_bias.shape[1])
            m[list(self.pruned_heads)] = 0
            position_bias = position_bias[:, m.bool()]

        if mode == "exact":
            out = fa2_exact_attention(q, k, v, position_bias)
        else:
            out = fa2_expmul_attention(q, k, v, position_bias, mode)

        attn_output = out.transpose(1, 2).contiguous().view(batch_size, -1, self.inner_dim)
        attn_output = self.o(attn_output)
        present = (k, v) if (self.is_decoder and use_cache) else None
        return (attn_output, present, position_bias)

    return forward


def attention_modules(model):
    from transformers.models.t5.modeling_t5 import T5Attention
    return [m for m in model.modules() if isinstance(m, T5Attention)]


def set_mode(model, mode: str, originals: dict):
    for m in attention_modules(model):
        if m not in originals:
            originals[m] = m.forward
        if mode in ("off", None):
            m.forward = originals[m]
        else:
            m.forward = types.MethodType(make_forward(mode), m)


# ---------------------------------------------------------------------------
#  GLUE task definitions
# ---------------------------------------------------------------------------
def _clip(s, n=400):
    return " ".join(str(s).split())[:n]


TASKS = {
    "sst2": dict(hf=("glue", "sst2"), split="validation",
                 text=lambda e: f"sst2 sentence: {_clip(e['sentence'])}",
                 labels=["negative", "positive"], kind="cls", f1="binary"),
    "mnli-m": dict(hf=("glue", "mnli"), split="validation_matched",
                   text=lambda e: f"mnli hypothesis: {_clip(e['hypothesis'])} premise: {_clip(e['premise'])}",
                   labels=["entailment", "neutral", "contradiction"], kind="cls", f1="macro"),
    "mnli-mm": dict(hf=("glue", "mnli"), split="validation_mismatched",
                    text=lambda e: f"mnli hypothesis: {_clip(e['hypothesis'])} premise: {_clip(e['premise'])}",
                    labels=["entailment", "neutral", "contradiction"], kind="cls", f1="macro"),
    "qqp": dict(hf=("glue", "qqp"), split="validation",
                text=lambda e: f"qqp question1: {_clip(e['question1'])} question2: {_clip(e['question2'])}",
                labels=["not duplicate", "duplicate"], kind="cls", f1="binary"),
    "qnli": dict(hf=("glue", "qnli"), split="validation",
                 text=lambda e: f"qnli question: {_clip(e['question'])} sentence: {_clip(e['sentence'])}",
                 labels=["entailment", "not entailment"], kind="cls", f1="binary"),
    "cola": dict(hf=("glue", "cola"), split="validation",
                 text=lambda e: f"cola sentence: {_clip(e['sentence'])}",
                 labels=["unacceptable", "acceptable"], kind="cls", f1="binary"),
    "mrpc": dict(hf=("glue", "mrpc"), split="validation",
                 text=lambda e: f"mrpc sentence1: {_clip(e['sentence1'])} sentence2: {_clip(e['sentence2'])}",
                 labels=["not equivalent", "equivalent"], kind="cls", f1="binary"),
    "rte": dict(hf=("glue", "rte"), split="validation",
                text=lambda e: f"rte sentence1: {_clip(e['sentence1'])} sentence2: {_clip(e['sentence2'])}",
                labels=["entailment", "not entailment"], kind="cls", f1="binary"),
    "wnli": dict(hf=("glue", "wnli"), split="validation",
                 text=lambda e: f"wnli sentence1: {_clip(e['sentence1'])} sentence2: {_clip(e['sentence2'])}",
                 labels=["entailment", "not entailment"], kind="cls", f1="binary"),
    "stsb": dict(hf=("glue", "stsb"), split="validation",
                 text=lambda e: f"stsb sentence1: {_clip(e['sentence1'])} sentence2: {_clip(e['sentence2'])}",
                 labels=["0", "1", "2", "3", "4", "5"], kind="reg"),
}


def load_task(name: str, n: int, seed: int, data_dir: str | None = None):
    spec = TASKS[name]
    if data_dir:
        fname = {"mnli-m": "mnli_m.parquet", "mnli-mm": "mnli_mm.parquet"}.get(
            name, f"{name}.parquet")
        ds = load_dataset("parquet", data_files=os.path.join(data_dir, fname),
                          split="train")
    else:
        ds = load_dataset(*spec["hf"], split=spec["split"])
    ds = ds.shuffle(seed=seed).select(range(min(n, len(ds))))
    prompts = [spec["text"](e) for e in ds]
    gold = np.array([e["label"] for e in ds])
    return prompts, gold, spec


def score_label(model, tok, prompts, label, device, max_len=256, batch=25):
    """sum log p(label tokens + EOS | prompt), one value per prompt."""
    ids = tok(label, add_special_tokens=False).input_ids
    tgt_ids = ids + [model.config.eos_token_id]
    dec_in = [model.config.pad_token_id] + tgt_ids[:-1]
    out = []
    for i in range(0, len(prompts), batch):
        chunk = prompts[i:i + batch]
        enc = tok(chunk, return_tensors="pt", padding=True, truncation=True,
                  max_length=max_len).to(device)
        b = len(chunk)
        dec = torch.tensor([dec_in] * b, dtype=torch.long, device=device)
        tgt = torch.tensor([tgt_ids] * b, dtype=torch.long, device=device)
        with torch.no_grad():
            logits = model(input_ids=enc.input_ids,
                           attention_mask=enc.attention_mask,
                           decoder_input_ids=dec,
                           use_cache=False).logits
        logp = torch.log_softmax(logits.float(), dim=-1)
        s = logp.gather(2, tgt.unsqueeze(-1)).squeeze(-1).sum(dim=-1)
        out.append(s.cpu())
    return torch.cat(out).numpy()


def metrics(spec, gold, pred):
    if spec["kind"] == "reg":
        p = np.asarray(pred, dtype=float)
        g = np.asarray(gold, dtype=float)
        return {"pearson": float(np.corrcoef(p, g)[0, 1])}
    acc = float(np.mean(pred == gold))
    res = {"accuracy": acc}
    if spec.get("f1") == "binary":
        tp = np.sum((pred == 1) & (gold == 1))
        fp = np.sum((pred == 1) & (gold == 0))
        fn = np.sum((pred == 0) & (gold == 1))
        res["f1"] = float(2 * tp / max(2 * tp + fp + fn, 1))
    elif spec.get("f1") == "macro":
        f1s = []
        for c in range(len(spec["labels"])):
            tp = np.sum((pred == c) & (gold == c))
            fp = np.sum((pred == c) & (gold != c))
            fn = np.sum((pred != c) & (gold == c))
            f1s.append(2 * tp / max(2 * tp + fp + fn, 1))
        res["f1"] = float(np.mean(f1s))
    return res


def evaluate(model, tok, spec, prompts, gold, device, max_len=256):
    scores = [score_label(model, tok, prompts, lab, device, max_len)
              for lab in spec["labels"]]
    if spec["kind"] == "reg":
        probs = torch.softmax(torch.tensor(np.stack(scores)), dim=0).numpy()
        pred = (probs * np.arange(len(spec["labels"]))[:, None]).sum(0)
    else:
        pred = np.argmax(np.stack(scores), axis=0)
    return metrics(spec, gold, pred), pred


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="google/flan-t5-base")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=20250520)
    ap.add_argument("--tasks", nargs="*", default=list(TASKS.keys()))
    ap.add_argument("--variants", nargs="*",
                    default=["fp32", "fp32_exp", "fp32_mi", "bf16", "bf16_mi"])
    ap.add_argument("--out", default="results/phase3")
    ap.add_argument("--data_dir", default=None,
                    help="local dir with GLUE parquet files (offline)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    torch.set_num_threads(os.cpu_count() or 8)
    device = "cpu"
    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForSeq2SeqLM.from_pretrained(a.model, torch_dtype=torch.float32)
    model.eval()
    originals = {}
    print(f"model={a.model}  params={sum(p.numel() for p in model.parameters())/1e6:.0f}M  "
          f"threads={torch.get_num_threads()}", flush=True)

    rows = []
    t0 = time.time()
    for task in a.tasks:
        prompts, gold, spec = load_task(task, a.n, a.seed, a.data_dir)
        for var in a.variants:
            dtype = torch.bfloat16 if var.startswith("bf16") else torch.float32
            mode = "off"
            if var.endswith("_exp"):
                mode = "exp_only"
            elif var.endswith("_mi"):
                mode = "mi"
            model.to(dtype)
            set_mode(model, mode, originals)
            tt = time.time()
            m, pred = evaluate(model, tok, spec, prompts, gold, device)
            rows.append(dict(task=task, variant=var, n=len(prompts),
                             **{k: round(v, 4) for k, v in m.items()}))
            print(f"  {task:7s} {var:8s} " +
                  "  ".join(f"{k}={v:.4f}" for k, v in m.items()) +
                  f"   ({time.time()-tt:.1f}s)", flush=True)
        set_mode(model, "off", originals)
        model.to(torch.float32)
        # incremental dump so a crash does not lose the results
        with open(os.path.join(a.out, "glue_results.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(f"total {time.time()-t0:.1f}s", flush=True)

    with open(os.path.join(a.out, "glue_results.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(a.out, "phase3_meta.json"), "w") as f:
        json.dump(dict(model=a.model, n=a.n, seed=a.seed, variants=a.variants,
                       tasks=a.tasks, threads=torch.get_num_threads()), f, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
