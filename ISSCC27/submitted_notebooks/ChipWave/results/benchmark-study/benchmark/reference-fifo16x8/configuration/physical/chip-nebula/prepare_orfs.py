#!/usr/bin/env python3
"""Prepare a private, headless ORFS script overlay for the pinned tool build."""

from __future__ import annotations

import argparse
from pathlib import Path


def prepare(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    old_rcx = "  set_extraction_rules_file $::env(RCX_RULES)\n  extract_parasitics\n"
    new_rcx = "  extract_parasitics -ext_model_file $::env(RCX_RULES)\n"
    if old_rcx in text:
        text = text.replace(old_rcx, new_rcx, 1)
    elif new_rcx not in text:
        raise SystemExit(f"unsupported ORFS RCX block in {path}")

    old_gui = "if { [ord::openroad_gui_compiled] } {"
    new_gui = "if { 0 && [ord::openroad_gui_compiled] } {"
    if old_gui in text:
        text = text.replace(old_gui, new_gui, 1)
    elif new_gui not in text:
        raise SystemExit(f"unsupported ORFS final image block in {path}")

    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("final_outputs", type=Path)
    args = parser.parse_args()
    prepare(args.final_outputs)


if __name__ == "__main__":
    main()
