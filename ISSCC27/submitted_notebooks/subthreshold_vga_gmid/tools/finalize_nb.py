#!/usr/bin/env python3
"""Make subthreshold_vga_gmid.ipynb render the same in every viewer (Jupyter, JupyterLab, VS Code, GitHub, Colab, simple previewers).

  python tools/finalize_nb.py [subthreshold_vga_gmid.ipynb]      (idempotent; run_nb.py calls it after every save)

 1. Output text (markdown, html, plain text, stream) is stored as ONE string instead of a list of lines. Both forms are
    valid nbformat and Jupyter reads either, but a previewer that does not join the list prints the lines separated by
    commas and shows every table as one run-on paragraph.
 2. The images that markdown cells link by path (![..](images/x.png)) are embedded in the cell as data URIs. A relative
    link works only when the viewer can reach the images/ folder next to the notebook (it does not on Colab, and not in
    a previewer that was given only the .ipynb file); an embedded image always shows. The files in images/ stay, and the
    README still links them.
SPDX-License-Identifier: Apache-2.0
"""
import base64, json, re, sys
from pathlib import Path

LINK = re.compile(r"!\[([^\]]*)\]\((images/[A-Za-z0-9_./-]+\.png)\)")
TEXT = ("text/markdown", "text/html", "text/plain", "text/latex", "image/svg+xml")


def finalize(path):
    path = Path(path).resolve(); root = path.parent
    nb = json.loads(path.read_text(encoding="utf-8")); joined = embedded = 0
    for c in nb["cells"]:
        if c["cell_type"] == "markdown":
            src = "".join(c["source"])
            def emb(m):
                f = root / m.group(2)
                if not f.exists():
                    sys.exit(f"{path.name}: {m.group(2)} is linked but missing")
                return f"![{m.group(1)}](data:image/png;base64,{base64.b64encode(f.read_bytes()).decode()})"
            new = LINK.sub(emb, src)
            if new != src:
                c["source"] = new.splitlines(keepends=True); embedded += 1
        for o in c.get("outputs", []):
            if o["output_type"] == "stream" and isinstance(o["text"], list):
                o["text"] = "".join(o["text"]); joined += 1
            for k in TEXT:
                if isinstance(o.get("data", {}).get(k), list):
                    o["data"][k] = "".join(o["data"][k]); joined += 1
    path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return joined, embedded


if __name__ == "__main__":
    j, e = finalize(sys.argv[1] if len(sys.argv) > 1 else "subthreshold_vga_gmid.ipynb")
    print(f"finalize_nb: {j} output fields joined, {e} cells got embedded images")
