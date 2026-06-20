import shutil

from typing import List
from pathlib import Path


def move_spec_files(
    src: str | Path, 
    dst: str | Path,
    specs: List[str],
    step: str,
):
    """
    Move files listed in `specs` from src to dst, and rename each one
    by appending '_{step}' before the suffix.

    Example if step='pre':
        runs/ngspice/gain.txt -> results/gain_pre.txt
    """
    src_dir, dst_dir = Path(src), Path(dst)

    if not src_dir.is_dir():
        raise NotADirectoryError(f"Source directory does not exist: {src_dir}")
    dst_dir.mkdir(parents=True, exist_ok=True)

    for spec in specs:
        src_file = src_dir / spec
        if not src_file.is_file():
            print(f"Skip, file not found: {src_file}")
            continue
        dst_name = f"{src_file.stem}_{step}{src_file.suffix}"
        dst_file = dst_dir / dst_name
        shutil.move(str(src_file), str(dst_file))