import fitz, sys, io

p = r"D:\harness_proj\OpenROAD-Flow\FlashAttention_accelerator\paper\expmul_flashattn_2025.pdf"
doc = fitz.open(p)
out = io.StringIO()
for i, page in enumerate(doc):
    out.write(f"\n===== PAGE {i+1} =====\n")
    out.write(page.get_text("text"))
txt = out.getvalue()
open(r"D:\harness_proj\OpenROAD-Flow\FlashAttention_accelerator\paper\paper_text.txt", "w", encoding="utf-8").write(txt)
print("pages", len(doc), "chars", len(txt))
print(txt[:1500])
