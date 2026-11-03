"""Regenerate the current competition poster, abstract and reviewer guide."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from presentation.contest_materials import build


if __name__ == "__main__":
    build()
