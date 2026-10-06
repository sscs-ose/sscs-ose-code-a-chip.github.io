"""
Stimulus/response file I/O and testbench rendering helpers.

Vector files are plain text, one signed decimal raw fixed-point sample per
line -- the same format the Verilator C++ harness and the Icarus testbench
both read/write, so the two simulation paths are interchangeable.
"""
import tempfile
from pathlib import Path

import numpy as np
from jinja2 import Environment, FileSystemLoader

import paths

TB_DIR = Path(paths.TB_DIR)
RENDER_DIR = Path(tempfile.gettempdir()) / "precisionfit_tb"

INPUT_HEADER = "# raw signed fixed-point input samples, one per line\n"


def write_input_vectors(x_fixed: np.ndarray, path) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for v in x_fixed:
            f.write(f"{int(v)}\n")
    return str(path)


def read_output_vectors(path) -> np.ndarray:
    with open(path) as f:
        values = [int(line.strip()) for line in f if line.strip()]
    return np.array(values, dtype=np.int64)


def render_icarus_tb(module_name: str, in_width: int, out_width: int,
                     render_dir=None) -> str:
    """Render the Icarus testbench for one DUT configuration and return its path."""
    render_dir = Path(render_dir) if render_dir else RENDER_DIR
    render_dir.mkdir(parents=True, exist_ok=True)

    env = Environment(loader=FileSystemLoader(str(TB_DIR)),
                      trim_blocks=True, lstrip_blocks=True,
                      keep_trailing_newline=True)
    tmpl = env.get_template("fir_tb.v.j2")
    text = tmpl.render(module_name=module_name, in_width=in_width,
                       out_width=out_width)

    out_path = render_dir / f"{module_name}_tb.v"
    out_path.write_text(text)
    return str(out_path)
