"""Locate explicit notebook roots without searching ancestors or needing a checkout.

The export contains its own opentcad and examples packages. In the repository,
start Jupyter at the root or examples/microrobot. In an export, start in the
project folder. No package is downloaded or installed by this helper.
"""
from pathlib import Path
import sys


def activate():
    here = Path(__file__).resolve().parent
    root = here if (here / "submission.json").is_file() else here.parents[1]
    app = root / "examples/microrobot"
    if not (root / "opentcad/__init__.py").is_file() or not (app / "run.py").is_file():
        raise RuntimeError("Open the complete project folder, not a notebook copied alone")
    sys.path.insert(0, str(root))
    return root, app
