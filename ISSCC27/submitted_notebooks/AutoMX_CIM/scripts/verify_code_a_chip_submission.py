"""Execute an extracted copy with no source imports, preserving real cell output."""
from pathlib import Path
import argparse, json, os, shutil, sys, tempfile, time
import nbformat
from nbclient import NotebookClient

def verify(source,native='on',base=None):
    base=Path(base or tempfile.gettempdir());base.mkdir(parents=True,exist_ok=True)
    clean=Path(tempfile.mkdtemp(prefix='automx_clean_',dir=base))
    package=clean/'automx_cim';shutil.copytree(source,package)
    path=package/'AutoMX_CIM_Code_a_Chip.ipynb'
    book=nbformat.read(path,4)
    for c in book.cells:
        if c.cell_type=='code':c.outputs=[];c.execution_count=None
    # Only public package data are available to the notebook. No project import.
    os.environ['AUTOMX_REVIEW_NATIVE']=native
    os.environ['AUTOMX_FULL_NATIVE']='off'
    os.environ.pop('AUTOMX_REVIEW_DIR',None)
    os.environ.pop('PYTHONPATH',None)
    started=time.monotonic()
    try:
        NotebookClient(book,timeout=180,kernel_name='python3',
            resources={'metadata':{'path':str(package)}}).execute()
    finally:nbformat.write(book,path)
    code=[c for c in book.cells if c.cell_type=='code']
    errors=[o for c in code for o in c.outputs if o.output_type=='error']
    if errors or any(c.execution_count is None for c in code):raise AssertionError('Incomplete execution')
    # The study result precedes the full laboratory in the extended edition.
    result_cell=next(c for c in code if c.id=='results')
    text=''.join(o.text for o in result_cell.outputs if o.output_type=='stream')
    result=json.JSONDecoder().raw_decode(text.lstrip())[0]
    if result['unique_holdout']!=38 or result['integer_decode_mismatches']!=0:
        raise AssertionError('Holdout result changed')
    if native=='on' and result['fresh_native_rtl_cases']!=41:raise AssertionError('Missing live RTL evidence')
    if native=='on' and not result['fresh_klayout_render']:raise AssertionError('Missing live KLayout render')
    laboratory=None
    if any(c.id=='full-lab-inventory' for c in code):
        inventory=next(c for c in code if c.id=='full-lab-inventory')
        output=''.join(o.text for o in inventory.outputs if o.output_type=='stream')
        laboratory=json.JSONDecoder().raw_decode(output.lstrip())[0]
        if laboratory['processed_native_code_cells']!=89 or laboratory['original_cells_included']!=200:
            raise AssertionError('Original laboratory content is incomplete')
    argument=None
    if any(c.id=='argument-verdict' for c in code):
        verdict=next(c for c in code if c.id=='argument-verdict')
        text=''.join(o.text for o in verdict.outputs if o.output_type=='stream')
        if 'Design argument verified against the predeclared protocol and measured records.' not in text:
            raise AssertionError('Missing measured design-argument verification')
        if not any('image/png' in o.get('data',{}) for o in verdict.outputs):
            raise AssertionError('Missing recomputed design-argument figure')
        argument={'status':'PASS','chapters':book.metadata['automx_review']['argument_chapters'],
                  'retained_previous_cells':book.metadata['automx_review']['retained_previous_cells'],
                  'native_code_order_preserved':book.metadata['automx_review']['native_code_order_preserved']}
    receipt={'status':'PASS','mode':native,'clean_folder':str(clean),
        'notebook':str(path),'code_cells':len(code),'elapsed_s':time.monotonic()-started,
        'results':result,'native_laboratory':laboratory,'design_argument':argument}
    (clean/'verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2),flush=True)
    return receipt

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--native',choices=['on','off','auto'],default='on');parser.add_argument('--base',type=Path)
    args=parser.parse_args();verify(args.source,args.native,args.base)
