import json, sys

p = r"D:\harness_proj\OpenROAD-Flow\FlashAttention_accelerator\temp_sense_genCollab.ipynb"
nb = json.load(open(p, encoding="utf-8"))
print("nbformat", nb.get("nbformat"), nb.get("nbformat_minor"))
print("cells", len(nb["cells"]))
for i, c in enumerate(nb["cells"]):
    src = "".join(c["source"])
    if c["cell_type"] == "markdown":
        heads = [l for l in src.splitlines() if l.startswith("#") or l.startswith(">")]
        print(f"--- [{i}] MD ---")
        print(("\n".join(heads) if heads else src[:300]).replace("\n", " | "))
    else:
        print(f"--- [{i}] CODE ({len(src)} chars) ---")
        print(src[:200].replace("\n", " | "))
