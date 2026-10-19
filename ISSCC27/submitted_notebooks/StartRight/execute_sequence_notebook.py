"""Execute the notebook in a new kernel using this Python environment."""
from pathlib import Path
import argparse,ast,hashlib,json,os,platform,sys,time
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

HERE=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    routes=parser.add_mutually_exclusive_group()
    routes.add_argument('--reference',action='store_true',help='Execute the four-cell saved-data reference companion')
    args=parser.parse_args()
    path=HERE/('Reference_tradeoff.ipynb' if args.reference else 'StartRight.ipynb')
    notebook=nbformat.read(path,as_version=4)
    nbformat.validate(notebook)
    for cell in notebook.cells:
        if cell.cell_type=='code':ast.parse(cell.source)
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
    from reset_sequence import SOURCES
    from external_consumer import SOURCES as EXTERNAL_SOURCES
    from por_consumer import SOURCES as POR_SOURCES
    from reference_consumer import SOURCES as REFERENCE_SOURCES
    sources=['mechanism_lab.py','check_mechanism_lab.py','lesson_decision.py','check_lesson_decision.py','lesson_template.html','check_reference.py','reference_devices.py','reference_loop.py','reference_circuit.py','reference_consumer.py','reference_evidence.py','reference_figures.py','reference_sources.json','reference_reproduction_spec.json','reproduce_reference.py','application_circuit.py','guard_window.py','applicability_consumer.py','applicability_evidence.py','applicability_figures.py','applicability_spec.json','check_applicability.py','reproduce_applicability.py','guard_consumer.py','guard_circuit.py','guard_spec.json','guard_evidence.py','guard_policy.py','guard_figures.py','check_guard.py','reproduce_guard.py']+REFERENCE_SOURCES+SOURCES+EXTERNAL_SOURCES+POR_SOURCES+['por_evidence.py','por_figures.py','check_por.py','reproduce_por.py']+['scaling_evidence.py','reproduce_design.py']+['external_evidence.py','external_analysis.py','check_external.py','reproduce_external.py','execute_sequence_notebook.py','reproduce_sequence.py','sequence_evidence.py','sequence_figures.py','sequence_analysis.py','check_reset_contract.py']
    scope='Main notebook: six fresh latch simulations, then saved POR, guard and reference audits. No saved substitute is used for an incomplete fresh run.'
    if args.reference:scope='Actual four-cell new kernel. Saved reference characterization/startup/intact evidence is regenerated and remeasured. Requirement-first original/guard/reference/None choices and matched working costs are shown. No fresh transistor acquisition in this companion.'
    record={'status':'passed','notebook':path.name,'scope':scope,'python':sys.version.split()[0],'isolated_python':sys.prefix!=sys.base_prefix,'platform':platform.platform(),'code_cells':len(codes),'elapsed_seconds':time.monotonic()-start,'notebook_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'notebook_code_sha256':hashlib.sha256(json.dumps([c.source for c in codes]).encode()).hexdigest(),'source_hashes':{f:hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in sources}}
    folder=HERE/'results/reproduction';folder.mkdir(exist_ok=True)
    (folder/('reference_notebook_execution.json' if args.reference else 'teaching_notebook_execution.json')).write_text(json.dumps(record,indent=2))
    print('PASS: actual Jupyter kernel executed',len(codes),'code cells.',flush=True)

if __name__=='__main__':main()
