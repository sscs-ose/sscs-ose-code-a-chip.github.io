"""Execute the complete demo from a fresh kernel and preserve review outputs.

Run from the demo virtual environment: .venv/bin/python tools/execute_notebook.py
The notebook controls simulator/PDK requirements and all design settings.
"""
from pathlib import Path
import os
import nbformat
from nbclient import NotebookClient
from nbformat.sign import NotebookNotary


def main():
    root = Path(__file__).resolve().parents[1]
    path = root / 'serdes_demo.ipynb'
    notebook = nbformat.read(path, as_version=4)
    sources = [(cell.cell_type, cell.source) for cell in notebook.cells]
    artifacts = root / 'artifacts'
    artifacts.mkdir(exist_ok=True)

    def checkpoint(cell, cell_index, **kwargs):
        print(f'Executed cell {cell_index}: {cell.source.splitlines()[0]}', flush=True)
        nbformat.write(notebook, artifacts / 'full_flow_checkpoint.ipynb')

    # Jupyter API: execute the cells in order in a fresh kernel.
    NotebookClient(notebook, timeout=int(os.environ.get('SILK_DEMO_CELL_TIMEOUT', '3600')), kernel_name='python3',
                   resources={'metadata': {'path': str(root)}},
                   on_cell_executed=checkpoint).execute()
    nbformat.validate(notebook)
    # Preserve edits made in Jupyter while this longer execution was running.
    current = nbformat.read(path, as_version=4)
    if sources != [(cell.cell_type, cell.source) for cell in current.cells]:
        raise RuntimeError('Notebook source changed during execution; checkpoint retained, original not overwritten.')
    for cell in notebook.cells:
        if cell.cell_type == 'code' and cell.source.strip():
            if cell.execution_count is None or any(o.output_type == 'error' for o in cell.outputs):
                raise RuntimeError('Notebook did not complete every code cell successfully.')
    # These outputs were just executed locally; trust the saved native viewer.
    NotebookNotary().sign(notebook)
    nbformat.write(notebook, artifacts / 'serdes_demo_full.executed.ipynb')
    nbformat.write(notebook, path)
    print('Saved complete executed notebook.', flush=True)


if __name__ == '__main__':
    main()
