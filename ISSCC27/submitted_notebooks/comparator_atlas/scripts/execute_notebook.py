"""Execute the entry using this interpreter, without a global kernel installation."""

import argparse
from pathlib import Path
import sys

import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute an entry with the isolated project kernel")
    parser.add_argument("notebook", nargs="?", default="Comparator_Atlas.ipynb")
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    if args.timeout <= 0:
        raise ValueError("Cell timeout must be positive")
    path = (ROOT / args.notebook).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Notebook must be inside the project")
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    client = NotebookClient(
        notebook, timeout=args.timeout, kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
        on_cell_start=lambda cell, cell_index: print(
            f"Executing cell {cell_index + 1}/{len(notebook.cells)}: {cell.get('id', cell.cell_type)}",
            flush=True,
        ),
    )
    client.km = KernelManager(kernel_name="python3")
    client.km.kernel_spec.argv = [
        sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}",
    ]
    client.execute()
    nbformat.validate(notebook)
    nbformat.write(notebook, path)
    errors = [
        output for cell in notebook.cells if cell.cell_type == "code"
        for output in cell.get("outputs", []) if output.output_type == "error"
    ]
    if errors:
        raise RuntimeError(f"Notebook contains {len(errors)} error outputs")
    print(f"Executed and saved {path.name}")


if __name__ == "__main__":
    main()
