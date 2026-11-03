#!/usr/bin/env python3
"""Insert a language switch line into each README_{en,zh}.md pair."""
from __future__ import annotations

import io

DIRS = [
    "results/phase1",
    "results/phase2",
    "results/phase3",
    "results/phase4",
    "results/visuals",
]

for d in DIRS:
    for lang in ("en", "zh"):
        path = f"{d}/README_{lang}.md"
        s = io.open(path, encoding="utf-8").read()
        if "README_en.md" in s.split("\n")[0:4].__str__():
            continue
        lines = s.split("\n")
        idx = next(i for i, line in enumerate(lines) if line.startswith("# "))
        switch = ("**English** | [中文](README_zh.md)" if lang == "en"
                  else "[English](README_en.md) | **中文**")
        lines.insert(idx + 1, "\n" + switch)
        io.open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
        print("updated", path)
