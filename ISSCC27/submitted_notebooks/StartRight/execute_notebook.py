"""Execute the notebook in a new kernel using this Python environment."""
from pathlib import Path
import hashlib,json,os,platform,sys,time
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

HERE=Path(__file__).resolve().parent

def main():
    path=HERE/'StartRight.ipynb'
    notebook=nbformat.read(path,as_version=4)
    nbformat.validate(notebook)
    for variable,relative in [('JUPYTER_RUNTIME_DIR','jupyter-runtime'),('IPYTHONDIR','ipython')]:
        folder=HERE/'.cache'/relative;folder.mkdir(parents=True,exist_ok=True)
        os.environ.setdefault(variable,str(folder))
    manager=KernelManager(kernel_name='python3')
    manager.kernel_spec.argv=[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}']
    start=time.monotonic()
    client=NotebookClient(notebook,km=manager,timeout=300,allow_errors=False,resources={'metadata':{'path':str(HERE)}})
    client.on_cell_executed=lambda cell,cell_index,**kw:print('Executed cell',cell_index,flush=True)
    client.execute(cleanup_kc=True)
    nbformat.validate(notebook)
    nbformat.write(notebook,path)
    codes=[c for c in notebook.cells if c.cell_type=='code']
    assert all(c.execution_count is not None for c in codes)
    assert not any(o.output_type=='error' for c in codes for o in c.outputs)
    sources=['startright.py','circuits.py','pilot.py','widlar_pilot.py','widlar_confirm.py','loaded_startup.py','measurements.py','execute_notebook.py']
    record={'status':'passed','scope':'Actual new Jupyter kernel launched with the current Python executable on the recorded platform. Nominal verifier cases freshly simulated; notebook qualification sections read saved data. This record does not establish support for untested platforms or Colab.','python':sys.version.split()[0],'isolated_python':sys.prefix!=sys.base_prefix,'platform':platform.platform(),'code_cells':len(codes),'elapsed_seconds':time.monotonic()-start,'notebook_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'notebook_code_sha256':hashlib.sha256(json.dumps([c.source for c in codes]).encode()).hexdigest(),'source_hashes':{f:hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in sources}}
    folder=HERE/'results/reproduction';folder.mkdir(exist_ok=True)
    (folder/'notebook_execution.json').write_text(json.dumps(record,indent=2))
    print('PASS: actual Jupyter kernel executed',len(codes),'code cells.',flush=True)

if __name__=='__main__':main()
