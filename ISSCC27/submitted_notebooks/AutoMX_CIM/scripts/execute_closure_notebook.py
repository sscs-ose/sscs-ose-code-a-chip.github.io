"""Execute every cell in the isolated candidate and retain failure checkpoints."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,os,resource,time
import nbformat
from nbclient import NotebookClient

def execute(root):
    root=Path(root).resolve();os.chdir(root);os.environ['AUTOMX_BUNDLE_DIR']=str(root)
    soft,hard=resource.getrlimit(resource.RLIMIT_NOFILE);resource.setrlimit(resource.RLIMIT_NOFILE,(min(hard,max(soft,8192)),hard))
    source=root/'AutoMX_CIM_Code_a_Chip.closure.ipynb';book=nbformat.read(source,4)
    for cell in book.cells:
        if cell.cell_type=='code':cell.outputs=[];cell.execution_count=None
    work=root/'experiments/closure_20261028';work.mkdir(parents=True,exist_ok=True);receipt=work/'notebook_execution.json';start=time.monotonic()
    state={'status':'RUNNING','started_utc':datetime.now(timezone.utc).isoformat(),'source':str(source),'root':str(root)}
    def save():
        state['elapsed_s']=time.monotonic()-start;tmp=receipt.with_suffix('.tmp');tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.replace(receipt)
    def begin(cell,cell_index,**kwargs):
        if cell.cell_type=='code':
            state['last_started_cell']=cell.id;state['last_started_index']=cell_index;save();print('START',cell_index,cell.id,flush=True)
    def done(cell,cell_index,**kwargs):
        if cell.cell_type=='code':
            state['last_completed_cell']=cell.id;save();print('DONE',cell_index,cell.id,flush=True)
            if cell_index%10==0:nbformat.write(book,root/'AutoMX_CIM_Code_a_Chip.closure.executing.ipynb')
    try:
        NotebookClient(book,timeout=3900,timeout_func=lambda c:14400 if c.id in ('closure-electrical-run','closure-pulse-run') else 3900,
            kernel_name='python3',allow_errors=False,resources={'metadata':{'path':str(root)}},on_cell_start=begin,on_cell_executed=done).execute()
        state['status']='ALL_CODE_CELLS_EXECUTED'
    except Exception as error:
        state['status']='FAILED';state['error']=str(error)[-2500:];raise
    finally:
        output=root/'AutoMX_CIM_Code_a_Chip.closure.executed.ipynb';nbformat.write(book,output)
        code=[c for c in book.cells if c.cell_type=='code'];state.update(output=str(output),code_cells=len(code),
            executed_cells=sum(c.execution_count is not None for c in code),empty_output_cells=[c.id for c in code if not c.outputs],
            errors=[{'cell':c.id,'name':o.ename,'value':o.evalue} for c in code for o in c.outputs if o.output_type=='error'])
        save();print('NOTEBOOK_EXECUTION',json.dumps(state),flush=True)
    return state

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args();execute(a.root)
