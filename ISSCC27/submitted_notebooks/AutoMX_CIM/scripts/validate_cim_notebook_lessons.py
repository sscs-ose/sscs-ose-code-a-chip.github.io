"""Execute newly added lesson cells without repeating the unchanged cold flow."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import json
import time
import nbformat
from nbclient import NotebookClient

def validate(root):
    root=Path(root).resolve()
    book=nbformat.read(root/'AutoMX_CIM_Code_a_Chip.ipynb',4)
    from scripts.enrich_cim_notebook import definitions
    baseline=root/'attempts/notebook_before_cell_lessons_20261025/AutoMX_CIM_Code_a_Chip.ipynb'
    old=nbformat.read(baseline,4) if baseline.is_file() else None
    by_id={c.id:c for c in book.cells}
    for i,cell in enumerate(book.cells):
        if cell.cell_type=='code' and definitions(cell.source):
            assert i and book.cells[i-1].metadata.get('automx_explains')==cell.id,cell.id
    if old is not None:
        for cell in old.cells:
            assert cell.id in by_id
            if cell.cell_type=='code':
                assert by_id[cell.id].source==cell.source,cell.id
                assert by_id[cell.id].outputs==cell.outputs,cell.id
    folder=root/'education_checks'/datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
    folder.mkdir(parents=True)
    preamble=nbformat.v4.new_code_cell('from pathlib import Path\n%matplotlib inline\n'
        '_design_review_namespace={"BUNDLE":Path('+repr(str(root))+'),"OUT":Path('+repr(str(folder))+')}\n',
        id='lesson-validation-context')
    cells=copy.deepcopy([c for c in book.cells if c.cell_type=='code' and c.id.startswith('cim-edu-')])
    subset=nbformat.v4.new_notebook(cells=[preamble,*cells])
    for cell in subset.cells:cell.outputs=[];cell.execution_count=None
    nbformat.write(subset,folder/'lessons.ipynb')
    started=time.monotonic();status='FAILED'
    def begin(cell,cell_index,**kwargs):print('LESSON_START',cell_index,cell.id,flush=True)
    def done(cell,cell_index,**kwargs):print('LESSON_DONE',cell_index,cell.id,flush=True)
    try:
        NotebookClient(subset,timeout=150,kernel_name='python3',allow_errors=False,
            resources={'metadata':{'path':str(root)}},on_cell_start=begin,on_cell_executed=done).execute()
        status='PASSED'
    finally:
        path=folder/'lessons.executed.ipynb';nbformat.write(subset,path)
        report={'status':status,'validation_mode':'lesson_subset; existing native code and outputs preserved',
            'checked_utc':datetime.now(timezone.utc).isoformat(),'elapsed_s':time.monotonic()-started,
            'notebook':str(path),'lesson_code_cells':len(cells),
            'original_code_cells_preserved':sum(c.cell_type=='code' for c in old.cells) if old else None,
            'total_notebook_cells':len(book.cells),'function_guides':sum('automx_explains' in c.metadata for c in book.cells),
            'errors':[{'cell':c.id,'error':o.ename,'value':o.evalue} for c in subset.cells for o in c.outputs if o.output_type=='error']}
        (root/'docs/cim_lessons_validation_20261025.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2),flush=True)
    if status=='PASSED':
        executed={c.id:c for c in subset.cells[1:]}
        for cell in book.cells:
            if cell.id in executed:
                cell.outputs=executed[cell.id].outputs;cell.execution_count=executed[cell.id].execution_count
        book.metadata['cim_cell_to_macro']['validation']=report
        nbformat.validate(book);nbformat.write(book,root/'AutoMX_CIM_Code_a_Chip.ipynb')
    return report

if __name__=='__main__':
    import sys
    root=Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:sys.path.insert(0,str(root))
    validate(root)
