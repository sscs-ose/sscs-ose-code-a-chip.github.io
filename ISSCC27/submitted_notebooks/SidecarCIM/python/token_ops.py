"""Edge study B: weight-stationary MVM counts per generated token (batch 1, decode).

Counts only (no energy). Each linear layer y = x W with W (d_in, d_out) is mapped on tiles of
R rows x 8 columns (R = 32, the SidecarCIM macro, and R = 128); one tile MVM = one R-input,
8-output dot-product block. Per token: tiles = ceil(d_in / R) * ceil(d_out / 8); a partial
tile still costs one MVM (utilization = d_in*d_out / (tiles*R*8)).
Layer shapes are read from the real module tree (model built from its HF config on the meta
device, no weights). "quantized" = the layers SidecarCIM runs in the studies (GPT-2 mlp.c_fc,
GPT-Neo/TinyStories mlp.c_fc, Qwen mlp.gate_proj + up_proj); "all_linear" = every nn.Linear /
Conv1D incl. the LM head; "body" = all_linear without the LM head.
"by_type" splits all_linear into the wholemodel.py layer types (attn_qkv, attn_o, mlp_in, mlp_down)
plus lm_head, so per-token energy can cover the whole model (body = all but lm_head).
Attention score / value products (q.K^T, p.V against the KV cache) are activation x activation,
not weight-stationary: listed only as MACs per token at a few context lengths (GPT-Neo local
layers cap the context at the window size).
Usage: python token_ops.py   -> out/token_ops.json
"""
import json
import math

from golden import ROOT, SPEC

OUT = ROOT / "python" / "out"
N_OUT = SPEC["array"]["n_outputs"]
ROWS = (SPEC["array"]["n_inputs"], 128)
CTXS = (128, 512, 1024)
MODELS = [  # (key, HF id, quantized-layer name suffixes, note)
    ("gpt2", "gpt2", ("mlp.c_fc",), "GPT-2 small (124M)"),
    ("tinystories-1m", "roneneldan/TinyStories-1M", ("mlp.c_fc",), "GPT-Neo, TinyStories"),
    ("tinystories-3m", "roneneldan/TinyStories-3M", ("mlp.c_fc",), "GPT-Neo, TinyStories"),
    ("tinystories-8m", "roneneldan/TinyStories-8M", ("mlp.c_fc",), "GPT-Neo, TinyStories"),
    ("tinystories-33m", "roneneldan/TinyStories-33M", ("mlp.c_fc",), "GPT-Neo, TinyStories"),
    ("qwen2.5-0.5b", "Qwen/Qwen2.5-0.5B", ("mlp.gate_proj", "mlp.up_proj"),
     "Qwen2.5-0.5B (reference, not edge)"),
    ("smollm2-135m", "HuggingFaceTB/SmolLM2-135M", ("mlp.gate_proj", "mlp.up_proj"),
     "SmolLM2-135M (Llama)"),
    ("smollm2-360m", "HuggingFaceTB/SmolLM2-360M", ("mlp.gate_proj", "mlp.up_proj"),
     "SmolLM2-360M (Llama)"),
    ("smollm2-1.7b", "HuggingFaceTB/SmolLM2-1.7B", ("mlp.gate_proj", "mlp.up_proj"),
     "SmolLM2-1.7B (Llama)"),
]


def tiles(d_in, d_out, rows, cols=N_OUT):
    return math.ceil(d_in / rows) * math.ceil(d_out / cols)


def linear_shapes(model):
    """[(name, d_in, d_out)] for every nn.Linear and HF Conv1D, in module order."""
    import torch
    out = []
    for name, m in model.named_modules():
        if isinstance(m, torch.nn.Linear):
            out.append((name, m.in_features, m.out_features))
        elif type(m).__name__ == "Conv1D":            # GPT-2: weight (d_in, d_out)
            out.append((name, m.weight.shape[0], m.weight.shape[1]))
    return out


def count(shapes):
    """Per-token totals for a list of (name, d_in, d_out)."""
    r = {"layers": len(shapes), "macs": sum(a * b for _, a, b in shapes)}
    for R in ROWS:
        t = sum(tiles(a, b, R) for _, a, b in shapes)
        r[f"mvm_{R}x{N_OUT}"] = t
        r[f"util_{R}x{N_OUT}"] = round(r["macs"] / (t * R * N_OUT), 4) if t else None
    return r


def attn_macs(cfg, mt):
    """q.K^T + p.V MACs per generated token at context lengths CTXS (KV cache, batch 1)."""
    L = cfg.num_hidden_layers
    nh = cfg.num_attention_heads
    hd = getattr(cfg, "head_dim", None) or cfg.hidden_size // nh
    out = {}
    for c in CTXS:
        tot = 0
        for i in range(L):
            ctx = c
            if mt == "gpt_neo" and cfg.attention_layers[i] == "local":
                ctx = min(c, cfg.window_size)
            tot += 2 * nh * hd * ctx                  # q.K^T and p.V, all heads
        out[str(c)] = tot
    return out


def model_counts(hf_id, qsuf):
    import torch
    from transformers import AutoConfig, AutoModelForCausalLM
    cfg = AutoConfig.from_pretrained(hf_id)
    with torch.device("meta"):
        model = AutoModelForCausalLM.from_config(cfg)
    shapes = linear_shapes(model)
    head = [s for s in shapes if s[0].endswith("lm_head")]
    assert len(head) == 1
    quant = [s for s in shapes if s[0].endswith(qsuf)]
    body = [s for s in shapes if s not in head]
    kinds = {}
    for n, a, b in shapes:
        k = n.split(".")[-1] if not n.endswith("lm_head") else "lm_head"
        kinds.setdefault(f"{k} ({a}x{b})", []).append(n)
    return {"config": {"model_type": cfg.model_type, "hidden": cfg.hidden_size,
                       "layers": cfg.num_hidden_layers, "heads": cfg.num_attention_heads,
                       "vocab": cfg.vocab_size,
                       "params_total": sum(p.numel() for p in model.parameters()),
                       "params_linear": sum(a * b for _, a, b in shapes),
                       "tied_lm_head": bool(getattr(cfg, "tie_word_embeddings", False))},
            "layer_kinds": {k: len(v) for k, v in kinds.items()},
            "quantized": count(quant), "body_linear": count(body), "lm_head": count(head),
            "all_linear": count(shapes),
            "quantized_share_of_all_mvm_32x8": round(count(quant)[f"mvm_32x{N_OUT}"] /
                                                     count(shapes)[f"mvm_32x{N_OUT}"], 4),
            "by_type": {t: count([s for s in shapes if layer_type(s[0]) == t])
                        for t in ("attn_qkv", "attn_o", "mlp_in", "mlp_down", "lm_head")},
            "attention_kv_macs_per_token": attn_macs(cfg, cfg.model_type)}


def layer_type(name):
    """wholemodel.py layer type of a linear module (lm_head separate)."""
    if name.endswith("lm_head"):
        return "lm_head"
    leaf = name.split(".")[-1]
    if leaf in ("c_attn", "q_proj", "k_proj", "v_proj"):
        return "attn_qkv"
    if leaf in ("o_proj", "out_proj") or name.endswith("attn.c_proj"):
        return "attn_o"
    if leaf in ("c_fc", "gate_proj", "up_proj"):
        return "mlp_in"
    assert leaf == "down_proj" or name.endswith("mlp.c_proj"), name
    return "mlp_down"


def _selftest():
    assert tiles(768, 3072, 32) == 24 * 384 and tiles(64, 256, 128) == 1 * 32
    assert tiles(33, 9, 32) == 4                     # partial tiles round up
    c = count([("a", 768, 3072)])
    assert c["mvm_32x8"] == 9216 and c["util_32x8"] == 1.0 and c["util_128x8"] == 1.0
    c = count([("a", 64, 256)])
    assert c["mvm_128x8"] == 32 and c["util_128x8"] == 0.5
    print("token_ops self-test passed")


def main():
    _selftest()
    res = {"method": __doc__.strip(), "tile_cols": N_OUT, "tile_rows": list(ROWS),
           "batch": 1, "models": {}}
    for key, hf_id, qsuf, note in MODELS:
        r = model_counts(hf_id, qsuf)
        r["hf_id"], r["note"], r["quantized_layers"] = hf_id, note, list(qsuf)
        res["models"][key] = r
        q, a = r["quantized"], r["all_linear"]
        print(f"{key:16s} quant {q['layers']:3d} lay {q['mvm_32x8']:>9,d} MVM32 "
              f"{q['mvm_128x8']:>8,d} MVM128 | all {a['layers']:3d} lay {a['mvm_32x8']:>9,d} "
              f"MVM32 {a['mvm_128x8']:>8,d} MVM128 (head {r['lm_head']['mvm_32x8']:,d}) "
              f"util128 {a['util_128x8']}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "token_ops.json").write_text(json.dumps(res, indent=1))
    print(f"saved {OUT / 'token_ops.json'}")


if __name__ == "__main__":
    main()
