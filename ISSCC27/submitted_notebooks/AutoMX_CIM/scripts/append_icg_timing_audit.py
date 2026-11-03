"""Execute and append a self-contained source-visible ICG timing audit."""
from pathlib import Path
import argparse,json,os,time
import nbformat as nb
from nbclient import NotebookClient

def make_cells(root):
    root=Path(root).resolve()
    body=(root/'scripts/check_calibration_gate_timing.py').read_text().split("if __name__=='__main__':",1)[0]
    body=body.replace('def run(root,work,sdc=None):','def check_calibration_gate_timing(root,work,sdc=None):')
    body+="\nprint('ICG timing audit source ready: mapped GATE setup/hold with routed RC')\n"
    return [nb.v4.new_markdown_cell('''### Verify the mapped clock-gate enable path

**Implementation:** `check_calibration_gate_timing(root, work, sdc=None)` locates the actual `sky130_fd_sc_hd__dlclkp_1` integrated clock-gating cell (ICG), reads the child clock-tree-synthesis constraints (CTS/SDC), its mapped gate netlist and extracted standard parasitic exchange format (SPEF) network, and checks the `GATE` pin with OpenSTA. SKY130 describes these enable constraints as `setup_rising` and `hold_rising` arcs. Targeting the actual pin ensures the report contains a measured path. This is the physical enable-timing check for the calibration-storage decision, independent of its clock-edge and power checks.

**Inputs → outputs and downstream use:** The source-matched routed readout and its CTS SDC produce a fresh native transcript and minimum setup/hold slack at the ICG enable pin. Nonnegative slack permits the calibration-data gating implementation; a missing timing path or negative slack fails the audit.''',id='closure-icg-timing-method'),
        nb.v4.new_code_cell(body,id='closure-icg-timing-source'),
        nb.v4.new_code_cell('''from pathlib import Path
import os,json
_audit_root=Path(os.environ.get('AUTOMX_BUNDLE_DIR','.')).resolve()
_audit_run=max((_audit_root/'runs').glob('fresh_*'))
ICG_ENABLE_TIMING=check_calibration_gate_timing(_audit_root,_audit_run/'electrical_closure/icg_enable_timing')
assert ICG_ENABLE_TIMING['status']=='PASS'
print('Calibration ICG enable: setup {:.6f} ns; hold {:.6f} ns'.format(ICG_ENABLE_TIMING['setup_slack_ns'],ICG_ENABLE_TIMING['hold_slack_ns']))
''',id='closure-icg-timing-run')]

def append(root):
    root=Path(root).resolve();folder=root/'experiments/closure_20261028';receipt=folder/'notebook_execution.json'
    record=json.loads(receipt.read_text());assert record['status']=='ALL_CODE_CELLS_EXECUTED'
    book=nb.read(record['output'],4)
    assert not any(c.id=='closure-icg-timing-source' for c in book.cells)
    additions=make_cells(root)
    # The two new cells execute against this fresh run; no saved output is
    # injected. Their code is self-contained for subsequent top-to-bottom use.
    start=time.monotonic();audit_book=nb.v4.new_notebook(cells=additions)
    NotebookClient(audit_book,timeout=300,kernel_name='python3',allow_errors=False,resources={'metadata':{'path':str(root)}}).execute()
    assert all(c.execution_count is not None and c.outputs for c in audit_book.cells if c.cell_type=='code')
    index=next(i for i,c in enumerate(book.cells) if c.id=='closure-results-method');book.cells[index:index]=audit_book.cells
    nb.validate(book)
    nb.write(book,record['output']);nb.write(book,root/'AutoMX_CIM_Code_a_Chip.closure.ipynb')
    record['execution_phases']=[{'phase':'fresh full laboratory','code_cells':record['code_cells'],'elapsed_s':record['elapsed_s']},
        {'phase':'independent mapped-enable audit','code_cells':2,'elapsed_s':time.monotonic()-start,'fresh_measurement':True}]
    record['code_cells']+=2;record['executed_cells']+=2;record['elapsed_s']+=time.monotonic()-start
    record['total_cells']=len(book.cells);receipt.write_text(json.dumps(record,indent=2)+'\n')
    print('SOURCE_VISIBLE_ICG_AUDIT_APPENDED',len(book.cells),record['code_cells'],flush=True)
    return record

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args();append(a.root)
