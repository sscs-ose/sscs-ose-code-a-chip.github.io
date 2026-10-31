"""Execute every code cell in a fresh env_mamba Jupyter kernel, retaining outputs."""
from datetime import datetime,timezone
from pathlib import Path
import time
import nbformat
from nbclient import NotebookClient
from scripts.flow2_runall_support import item,save


def execute(root,notebook=None):
    root=Path(root).resolve();path=Path(notebook).resolve() if notebook else root/'AutoMX_CIM_Sky130_MHA.ipynb'
    book=nbformat.read(path,4);start=time.monotonic()
    def begin(cell,cell_index,**_):
        if cell.cell_type=='code':print('JUPYTER START',cell_index,cell.id,flush=True)
    client=NotebookClient(book,timeout=900,kernel_name='python3',allow_errors=False,
        resources={'metadata':{'path':str(root)}},on_cell_start=begin)
    for cell in book.cells:
        if cell.cell_type=='code':cell.outputs=[];cell.execution_count=None
    status='FAILED'
    try:
        client.execute();status='ALL_CODE_CELLS_EXECUTED'
    finally:
        nbformat.write(book,path)
        cells=[c for c in book.cells if c.cell_type=='code']
        report=dict(status=status,timestamp_utc=datetime.now(timezone.utc).isoformat(),
            elapsed_s=time.monotonic()-start,notebook=item(path),kernel='python3 (env_mamba)',
            code_cells=len(cells),executed_cells=sum(c.execution_count is not None for c in cells),
            errors=[dict(cell=c.id,error=o.get('ename'),value=o.get('evalue')) for c in cells for o in c.outputs if o.output_type=='error'],
            scope='Fresh kernel executes every active code cell. Native steps explicitly show fresh execution or hash-verified reuse with original logs.')
        receipt_name=('flow2_fresh_execution_20261023.json' if book.metadata.get('automx',{}).get('flow')=='flow2_fresh_inline_v3' else 'flow2_combined_inline_execution_20261023.json' if book.metadata.get('automx',{}).get('flow')=='flow2_combined_inline_v2' else 'flow2_runall_notebook_execution_20261023.json')
        report['flow']=book.metadata.get('automx',{}).get('flow')
        save(root/'docs'/receipt_name,report)
        archive=Path('/media/nam/EDABK/AutoMX_CIM_runall_20261023/notebook_attempts')/str(time.time_ns())
        archive.mkdir(parents=True);nbformat.write(book,archive/path.name);save(archive/'execution.json',report)
        if book.metadata.get('automx',{}).get('flow')=='flow2_fresh_inline_v3':save(path.parent/'execution.json',report)
        print({k:v for k,v in report.items() if k!='notebook'},flush=True)
    return report

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--notebook',type=Path)
    args=parser.parse_args()
    execute(Path(__file__).resolve().parents[1],args.notebook)
