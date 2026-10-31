"""Execute the student launch notebook in fresh kernels."""

import argparse
from pathlib import Path
import sys

import nbformat
from jupyter_client import KernelManager
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
WIDGET_MIME = "application/vnd.jupyter.widget-view+json"


def execute(notebook, directory: Path):
    """Run using this interpreter, regardless of the user's registered kernels."""
    manager = KernelManager(kernel_name="python3")
    manager.kernel_spec.argv = [
        sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}",
    ]
    client = NotebookClient(notebook, km=manager, timeout=180,
                            resources={"metadata": {"path": str(directory)}})
    # An explicitly supplied manager is caller-owned; always shut it down.
    try:
        client.execute()
    finally:
        if manager.has_kernel:
            manager.shutdown_kernel(now=True)
    nbformat.validate(notebook)
    return notebook


def summarize(notebook) -> dict[str, int]:
    """Count direct visual outputs and images serialized inside widget state."""
    cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    outputs = [output for cell in cells for output in cell.outputs]
    state = notebook.metadata.get("widgets", {}).get(
        "application/vnd.jupyter.widget-state+json", {}).get("state", {})
    widget_outputs = [output for model in state.values()
                      for output in model.get("state", {}).get("outputs", [])]
    return {
        "code_cells": len(cells),
        "errors": sum(output.output_type == "error" for output in outputs),
        "png_outputs": sum("image/png" in output.get("data", {}) for output in outputs),
        "widget_views": sum(WIDGET_MIME in output.get("data", {}) for output in outputs),
        "widget_pngs": sum("image/png" in output.get("data", {}) for output in widget_outputs),
        "svg_widgets": sum("<svg" in model.get("state", {}).get("value", "")
                           for model in state.values() if isinstance(model.get("state", {}).get("value", ""), str)),
    }


def main() -> None:
    """Validate without modifying source; optionally save an executed artifact."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional executed notebook artifact path")
    args = parser.parse_args()
    source = ROOT / "notebooks" / "00_launch_visualizer.ipynb"
    if args.output and args.output.resolve() == source:
        parser.error("Use a separate output path; the source notebook must remain clean.")
    notebook = nbformat.read(source, as_version=4)
    nbformat.validate(notebook)
    # The launch code cell must work without any notebook preamble.
    final_source = next(cell.source for cell in reversed(notebook.cells) if cell.cell_type == "code")
    print("Executing full notebook in a fresh kernel...", flush=True)
    execute(notebook, source.parent)
    counts = summarize(notebook)
    if counts["errors"] or not counts["widget_views"] or not counts["svg_widgets"]:
        raise RuntimeError(f"Missing expected notebook output: {counts}")
    print("Full notebook:", counts, flush=True)
    final = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(final_source)])
    print("Executing final demo alone in a second fresh kernel...", flush=True)
    execute(final, source.parent)
    final_counts = summarize(final)
    if final_counts["errors"] or not final_counts["widget_views"] or not final_counts["svg_widgets"]:
        raise RuntimeError(f"Standalone demo did not render: {final_counts}")
    print("Standalone demo:", final_counts, flush=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        nbformat.write(notebook, args.output)
    print("Notebook validation passed. Source notebook unchanged.")


if __name__ == "__main__":
    main()
