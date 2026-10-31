"""Add every native notebook cell to the competition notebook without deleting content."""
from pathlib import Path
import copy,json,textwrap
import nbformat as nbf

LAB_CONFIG=r'''
from IPython.core.magic import register_cell_magic
from IPython.display import display as _lab_display
import json as _lab_json, os as _lab_os, sys as _lab_sys
from pathlib import Path as _LabPath

_lab_package = (_design_review_namespace['BASE']
                if '_design_review_namespace' in globals() else BASE)
_lab_output = (_design_review_namespace['OUT']
               if '_design_review_namespace' in globals() else OUT)
_lab_records = _lab_json.loads((_lab_package/'data/native_lab_outputs.json').read_text())
_lab_manifest = _lab_json.loads((_lab_package/'data/native_lab_cells.json').read_text())
_lab_mode = _lab_os.environ.get('AUTOMX_FULL_NATIVE','off').lower()
if _lab_mode not in ('on','off'): raise ValueError('AUTOMX_FULL_NATIVE must be on or off')
_lab_state = {'mode':_lab_mode,'replayed':[],'executed':[],
              'source_cells':_lab_manifest['source_cells'],
              'source_code_cells':_lab_manifest['source_code_cells']}

if _lab_mode=='on':
    _lab_root_text=_lab_os.environ.get('AUTOMX_CIM_ROOT','')
    if not _lab_root_text or not (_LabPath(_lab_root_text)/'configs/sky130_mha_tiny.json').is_file():
        raise FileNotFoundError('For a full native run, set AUTOMX_CIM_ROOT to the design checkout with PDK/routed inputs.')
    # A new native output directory belongs to this execution, never a previous run.
    _lab_os.environ['AUTOMX_RUNALL_CACHE']=str(_lab_output/'full_native')
    _lab_os.environ['AUTOMX_RUNALL_TAG']='full_native'

@register_cell_magic
def native_lab(line,cell):
    """Keep original code visible; run it natively or display attributed recorded output."""
    key=line.strip()
    if key not in _lab_records: raise ValueError('Unknown native notebook cell: '+key)
    if _lab_state['mode']=='on':
        result=get_ipython().run_cell(cell,store_history=False)
        error=result.error_before_exec or result.error_in_exec
        if error is not None: raise error
        _lab_state['executed'].append(key)
        return
    outputs=_lab_records[key]
    if outputs:
        print('RECORDED NATIVE OUTPUT | '+key+' | acquired in the verified native laboratory session')
    # Coalesce adjacent streams while preserving order and all transcript text.
    pending=[]; pending_name=None
    def flush_stream():
        nonlocal pending,pending_name
        if pending:
            target=_lab_sys.stderr if pending_name=='stderr' else _lab_sys.stdout
            target.write(''.join(pending));target.flush();pending=[]
    for output in outputs:
        kind=output['output_type']
        if kind=='stream':
            name=output.get('name','stdout')
            if pending and name!=pending_name: flush_stream()
            pending_name=name;pending.append(output['text'])
        else:
            flush_stream()
            if kind in ('display_data','execute_result'):
                _lab_display(output['data'],raw=True,metadata=output.get('metadata',{}))
            elif kind=='error':
                print('RECORDED ERROR:',output['ename'],output['evalue'])
                print('\n'.join(output.get('traceback',[])))
            else: raise ValueError('Unsupported saved output type: '+kind)
    flush_stream()
    _lab_state['replayed'].append(key)

print('Full laboratory:',_lab_manifest['source_cells'],'original cells,',
      _lab_manifest['source_code_cells'],'original code cells,',
      _lab_manifest['source_code_lines'],'lines of original code.')
print('Mode:', 'fresh native execution' if _lab_mode=='on' else
      'recorded native logs/figures; complete source code remains visible in every cell')
'''

LAB_INVENTORY=r'''
_lab_seen=_lab_state['executed'] if _lab_state['mode']=='on' else _lab_state['replayed']
_lab_expected=[r['original_id'] for r in _lab_manifest['cells'] if r['cell_type']=='code']
if _lab_seen!=_lab_expected: raise AssertionError('Missing, reordered or duplicate native laboratory cells')
_lab_report={
    'status':'COMPLETE',
    'mode':'fresh_native' if _lab_state['mode']=='on' else 'attributed_recorded_native',
    'original_cells_included':_lab_state['source_cells'],
    'original_code_cells_included':_lab_state['source_code_cells'],
    'original_code_lines':_lab_manifest['source_code_lines'],
    'processed_native_code_cells':len(_lab_seen),
    'original_nonempty_output_cells':sum(bool(v) for v in _lab_records.values()),
    'original_embedded_figures':sum('image/png' in o.get('data',{})
                                   for group in _lab_records.values() for o in group)}
(_lab_output/'native_lab_results.json').write_text(_lab_json.dumps(_lab_report,indent=2)+'\n')
print(_lab_json.dumps(_lab_report,indent=2))
'''

def append_full_lab(review,source):
    """Return a combined notebook, preserving all existing cells and original bodies."""
    book=copy.deepcopy(review)
    if any('automx_native_origin' in c.metadata for c in book.cells):
        raise ValueError('Already merged: start from the unmerged review notebook')
    entries=[];outputs={}
    for i,c in enumerate(source.cells):
        entries.append({'original_index':i,'original_id':c.id,'combined_id':'native-'+c.id,
                        'cell_type':c.cell_type,'source_lines':len(c.source.splitlines())})
        if c.cell_type=='code':outputs[c.id]=copy.deepcopy(c.outputs)
    manifest={'source_notebook':'AutoMX_CIM_Sky130_MHA.ipynb','source_cells':len(source.cells),
              'source_code_cells':len(outputs),'source_code_lines':sum(
                  len(c.source.splitlines()) for c in source.cells if c.cell_type=='code'),
              'policy':'Every original cell is included in original order. Only a native_lab magic line is added to code cells.',
              'cells':entries}
    book.cells.insert(0,nbf.v4.new_markdown_cell(textwrap.dedent(f'''\
        # Extended edition — complete design laboratory included

        This edition adds the **entire {len(source.cells)}-cell native design notebook**
        to the original 33-cell competition study. All original text, code bodies,
        saved figures and native transcripts are retained. The native laboratory
        contributes **{len(outputs)} code cells / {manifest['source_code_lines']:,} lines**
        covering numerical modeling, scheduling, circuit generation, PEX, calibration,
        decoder recovery, RTL, analog/SAR/MHA integration, synthesis and physical top.

        | Reading route | What it contains |
        |---|---|
        | Part I — competition study, immediately below | Design question, 2×2 ablation, independent ADC challenge, MHA, fresh Icarus/KLayout checks |
        | [Part II — complete laboratory](#complete-native-laboratory) | Every original cell and its implementation; native logs and figures at their corresponding cells |
        | [Numerical foundation](#lab-numerical) | MHA reference, quantization/export and tile scheduling |
        | [Circuit and physical construction](#lab-circuit) | Generated transistor circuits, layout, DRC/LVS/PEX recipes and transfer model |
        | [Measured failure and recovery](#lab-recovery) | Transfer reversal, load/PWM changes, calibration, independent holdout and 2+2 decoding |
        | [Coupled analog/SAR/MHA](#lab-coupled) | Complete visible implementations, native conversions, calibration and application output |
        | [Synthesis and mixed-signal top](#lab-physical) | Yosys, OpenROAD, KLayout, Netgen, rail checks, routing RC and STA |
        | [Server orchestration](#lab-orchestration) | Original execution recipes and final artifacts |

        **Run All keeps two acquisition modes explicit.** Part I recomputes analysis
        and runs Icarus/KLayout when available. Part II defaults to displaying the
        supplied, attributed native transcripts and figures beside the complete
        original code. To execute those full native bodies instead, start Jupyter
        with `AUTOMX_FULL_NATIVE=on` and `AUTOMX_CIM_ROOT` pointing to the prepared
        source checkout. Both modes create new output directories; recorded tool
        transcripts are never labeled as a newly executed analog run.

        ---

        ## Part I — competition study
        ''').strip(),id='extended-edition'))
    book.cells.append(nbf.v4.new_markdown_cell(textwrap.dedent('''\
        <a id="complete-native-laboratory"></a>

        # Part II — complete native design laboratory

        The following cells retain the original notebook in its original order,
        including all implementations and technical explanations. The introductory
        theory is followed by numerical/reference work, circuit/layout experiments,
        transfer and decoder investigations, then the current integrated flow.

        **Default output below: recorded native measurements.** Each nonempty
        recorded output is labeled at the cell where it was originally acquired.
        Definition-only cells stay silent. `%%native_lab` is an added execution-mode
        wrapper; everything after that first line is the unchanged original source.
        `AUTOMX_FULL_NATIVE=on` executes that source and prints new tool output.
        ''').strip(),id='full-lab-guide'))
    book.cells.append(nbf.v4.new_code_cell(textwrap.dedent(LAB_CONFIG).strip()+'\n',id='full-lab-config'))
    chapters={
        'restored-archive-013':('lab-numerical','Numerical foundation and scheduling',
            'The reference, numerical/export contracts and schedule establish the arithmetic used by later circuit and application checks.'),
        'restored-archive-022':('lab-circuit','Circuit generation, layout and extraction',
            'Follow the actual generator and tool implementations from transistor cells through the four-row core and extracted transfer experiments.'),
        'story-transfer_error-guide':('lab-recovery','Measured failure, calibration and decoder recovery',
            'Read stimulus, raw native voltage logs and error counts together; the following interventions build the basis for the later coupled conversion tests.'),
        'combined-modern':('lab-coupled','Full implementation of coupled analog / SAR / MHA',
            'The implementations below expose the simulator harness, SAR partition, calibration, conversion transactions and application reconstruction in full.'),
        'new-769a8093':('lab-physical','Synthesis and the integrated physical top',
            'Continue from RTL synthesis to physical exports, GDS geometry, rendering, signal connectivity, supply connectivity and extracted digital timing.'),
        'combined-orchestration-appendix':('lab-orchestration','Server orchestration and artifact production',
            'The original orchestration recipes remain here, followed by the native tool ledger and final results.')}
    for original in source.cells:
        if original.id in chapters:
            anchor,title,description=chapters[original.id]
            book.cells.append(nbf.v4.new_markdown_cell(
                f'<a id="{anchor}"></a>\n\n## {title}\n\n{description}',id='chapter-'+anchor))
        c=copy.deepcopy(original);c.id='native-'+original.id
        c.metadata['automx_native_origin']={'original_id':original.id,'original_cell_type':original.cell_type}
        if c.cell_type=='code':c.source='%%native_lab '+original.id+'\n'+original.source
        book.cells.append(c)
    book.cells.append(nbf.v4.new_markdown_cell('''## Complete laboratory coverage

The next cell checks that every original code cell was encountered exactly once
in source order. It records whether this execution displayed supplied measurements
or ran the native bodies, and reports the retained source/figure counts.''',id='full-lab-inventory-guide'))
    book.cells.append(nbf.v4.new_code_cell(textwrap.dedent(LAB_INVENTORY).strip()+'\n',id='full-lab-inventory'))
    book.metadata['automx_review']['edition']='extended_complete_lab'
    book.metadata['automx_review']['review_cells']=len(review.cells)
    book.metadata['automx_review']['native_source_cells']=len(source.cells)
    book.metadata['automx_review']['native_source_code_cells']=len(outputs)
    nbf.validate(book)
    return book,manifest,outputs

def write_lab_data(dest,manifest,outputs):
    data=Path(dest)/'data';data.mkdir(parents=True,exist_ok=True)
    (data/'native_lab_cells.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (data/'native_lab_outputs.json').write_text(json.dumps(outputs,ensure_ascii=False)+'\n')
