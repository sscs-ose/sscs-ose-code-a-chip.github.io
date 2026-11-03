import pymupdf, os

pdf = r"D:\harness_proj\OpenROAD-Flow\FlashAttention_accelerator\paper\expmul_flashattn_2025.pdf"
outdir = r"D:\harness_proj\OpenROAD-Flow\FlashAttention_accelerator\paper\figures"
os.makedirs(outdir, exist_ok=True)
doc = pymupdf.open(pdf)
for pno in (4, 5):
    page = doc[pno]
    pix = page.get_pixmap(dpi=200)
    path = os.path.join(outdir, f"page{pno+1}.png")
    pix.save(path)
    print(path, pix.width, pix.height)
    for i, img in enumerate(page.get_images(full=True)):
        xref = img[0]
        info = doc.extract_image(xref)
        p = os.path.join(outdir, f"p{pno+1}_img{i}.{info['ext']}")
        open(p, "wb").write(info["image"])
        print("  ", p, info["width"], info["height"])
