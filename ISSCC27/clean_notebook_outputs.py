#!/usr/bin/env python3
"""
clean_notebook_outputs.py - make a Colab-saved notebook small and GitHub-friendly.

Keeps: printed results, tables, plots (PNG).
Drops: LibreLane's per-step rich-console log (thousands of ANSI HTML lines),
       ipywidgets progress bars, Colab download JavaScript, and metadata.widgets
       (which makes GitHub refuse to render the notebook).

Usage:  python3 clean_notebook_outputs.py  in.ipynb  [out.ipynb]
"""
import json, re, sys
from pathlib import Path

KEEP_STDERR = re.compile(r"INFO:__librelane__:(Starting a new run|Saving views|Flow complete)|ERROR|Traceback")

def clean(nb):
    nb.get("metadata", {}).pop("widgets", None)
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        kept = []
        # a cell that floods the notebook with rich-console HTML/text frames (LibreLane tables/log lines)
        n_rich = sum(1 for o in cell.get("outputs", [])
                     if o.get("output_type") == "display_data"
                     and set(o.get("data", {})) <= {"text/html", "text/plain"})
        flood = n_rich > 200
        for o in cell.get("outputs", []):
            t = o.get("output_type")
            if t in ("display_data", "execute_result"):
                data = o.get("data", {})
                if "application/vnd.jupyter.widget-view+json" in data:
                    continue                                    # progress-bar widgets
                if "application/javascript" in data:
                    continue                                    # files.download() payloads
                plain = "".join(data.get("text/plain", []))
                if set(data) <= {"text/html", "text/plain"} and ("\x1b[" in plain or flood):
                    continue                                    # rich/ANSI console log lines and tables
            elif t == "stream" and o.get("name") == "stderr":
                text = "".join(o.get("text", []))
                if not KEEP_STDERR.search(text):
                    continue                                    # warnings / progress noise
            kept.append(o)
        cell["outputs"] = kept
    return nb

if __name__ == "__main__":
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_name(src.stem + "_clean.ipynb")
    nb = clean(json.loads(src.read_text(encoding="utf-8")))
    dst.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{src.name}: {src.stat().st_size/1e6:.1f} MB -> {dst.name}: {dst.stat().st_size/1e6:.2f} MB")
