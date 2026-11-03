"""Execute the bundled notebook from a fresh kernel and preserve each attempt."""
from pathlib import Path
from datetime import datetime, timezone
import json, os, resource, shutil, time
import nbformat
from nbclient import NotebookClient

# Larger laboratory runs keep more native-tool/Jupyter descriptors alive.
soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
resource.setrlimit(resource.RLIMIT_NOFILE,
                  (min(hard_limit, max(soft_limit, 8192)), hard_limit))

root = Path(__file__).resolve().parent
if not (root / 'standalone.json').is_file():
    root = root.parent
os.chdir(root)
os.environ['AUTOMX_BUNDLE_DIR'] = str(root)
stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
archive = root / 'attempts' / stamp
archive.mkdir(parents=True)
for name in ('AutoMX_CIM_Code_a_Chip.ipynb', 'AutoMX_CIM_Code_a_Chip.executed.ipynb', 'standalone_execution.json'):
    if (root / name).is_file():
        shutil.copyfile(root / name, archive / ('previous_' + name))
book = nbformat.read(root / 'AutoMX_CIM_Code_a_Chip.ipynb', 4)
for cell in book.cells:
    if cell.cell_type == 'code':
        cell.outputs = []
        cell.execution_count = None
started = time.monotonic()
status = 'FAILED'

def begin(cell, cell_index, **kwargs):
    if cell.cell_type == 'code':
        print(datetime.now(timezone.utc).isoformat(), 'JUPYTER_START', cell_index, cell.id, flush=True)

def done(cell, cell_index, **kwargs):
    if cell.cell_type == 'code':
        print('JUPYTER_DONE', cell_index, cell.id, flush=True)
        if cell_index % 5 == 0:
            nbformat.write(book, root / 'AutoMX_CIM_Code_a_Chip.executing.ipynb')

try:
    NotebookClient(book, timeout=3900,
                   timeout_func=lambda cell: 14400 if cell.id in ('closure-electrical-run', 'closure-pulse-run') else 3900,
                   kernel_name='python3', allow_errors=False,
                   resources={'metadata': {'path': str(root)}},
                   on_cell_start=begin, on_cell_executed=done).execute()
    status = 'ALL_CODE_CELLS_EXECUTED'
finally:
    path = root / 'AutoMX_CIM_Code_a_Chip.executed.ipynb'
    nbformat.write(book, path)
    cells = [c for c in book.cells if c.cell_type == 'code']
    report = {'status': status, 'notebook': str(path), 'elapsed_s': time.monotonic() - started,
              'code_cells': len(cells),
              'executed_cells': sum(c.execution_count is not None for c in cells),
              'empty_output_cells': [c.id for c in cells if not c.outputs],
              'errors': [{'cell': c.id, 'name': o.ename, 'value': o.evalue}
                         for c in cells for o in c.outputs if o.output_type == 'error']}
    (root / 'standalone_execution.json').write_text(json.dumps(report, indent=2) + '\n')
    shutil.copyfile(path, archive / path.name)
    shutil.copyfile(root / 'standalone_execution.json', archive / 'standalone_execution.json')
    if status == 'ALL_CODE_CELLS_EXECUTED' and not report['errors'] and not report['empty_output_cells']:
        shutil.copyfile(path, root / 'AutoMX_CIM_Code_a_Chip.ipynb')
        if any(c.id == 'closure-results' for c in book.cells):
            closure_receipt = root / 'experiments/closure_20261028/notebook_execution.json'
            closure_receipt.parent.mkdir(parents=True, exist_ok=True)
            closure_receipt.write_text(json.dumps({**report, 'output': str(path),
                'source': str(root / 'AutoMX_CIM_Code_a_Chip.ipynb'), 'root': str(root)}, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)
