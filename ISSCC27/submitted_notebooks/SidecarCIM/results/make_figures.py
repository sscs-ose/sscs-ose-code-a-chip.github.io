"""Regenerate every accuracy- and cost-side figure and table:
python make_figures.py   (architecture figures: make_arch_figures.py)"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# power split and clock-gating tables first: findings.md reads them
for m in ("make_power_split", "make_clockgating", "make_edge",
          "make_tables"):
    importlib.import_module(m).main()
