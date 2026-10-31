"""Validate the candidate in a fresh kernel without replacing the known-good notebook."""
from pathlib import Path
from datetime import datetime,timezone
import json,os,time
import nbformat
from nbclient import NotebookClient

def execute(root):
    import resource
    soft_limit,hard_limit=resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE,(min(hard_limit,max(soft_limit,8192)),hard_limit))
    root=Path(root).resolve();os.chdir(root);os.environ['AUTOMX_BUNDLE_DIR']=str(root)
    path=root/'AutoMX_CIM_Code_a_Chip.priority.ipynb';book=nbformat.read(path,4)
    for c in book.cells:
        if c.cell_type=='code':c.outputs=[];c.execution_count=None
    folder=root/'experiments/priority_20261028';folder.mkdir(parents=True,exist_ok=True)
    report_path=folder/'notebook_execution.json';start=time.monotonic()
    status={'status':'RUNNING','started_utc':datetime.now(timezone.utc).isoformat(),'source':str(path)}
    def save():
        status['elapsed_s']=time.monotonic()-start;report_path.write_text(json.dumps(status,indent=2)+'\n')
    def begin(cell,cell_index,**kwargs):
        if cell.cell_type=='code':
            status['last_started_cell']=cell.id;status['last_started_index']=cell_index;save()
            print(datetime.now(timezone.utc).isoformat(),'START',cell_index,cell.id,flush=True)
    def done(cell,cell_index,**kwargs):
        if cell.cell_type=='code':
            status['last_completed_cell']=cell.id;save()
            print('DONE',cell_index,cell.id,flush=True)
            if cell_index%10==0:nbformat.write(book,root/'AutoMX_CIM_Code_a_Chip.priority.executing.ipynb')
    try:
        NotebookClient(book,timeout=3900,kernel_name='python3',allow_errors=False,
          resources={'metadata':{'path':str(root)}},on_cell_start=begin,on_cell_executed=done).execute()
        status['status']='ALL_CODE_CELLS_EXECUTED'
    except Exception as e:
        status['status']='FAILED';status['exception']=str(e)[-2500:];raise
    finally:
        output=root/'AutoMX_CIM_Code_a_Chip.priority.executed.ipynb';nbformat.write(book,output)
        code=[c for c in book.cells if c.cell_type=='code']
        status.update(output=str(output),code_cells=len(code),executed_cells=sum(c.execution_count is not None for c in code),
           errors=[{'cell':c.id,'name':o.ename,'value':o.evalue} for c in code for o in c.outputs if o.output_type=='error'])
        save();print(json.dumps(status,indent=2),flush=True)
    return status

if __name__=='__main__':execute(Path(__file__).resolve().parents[1])
