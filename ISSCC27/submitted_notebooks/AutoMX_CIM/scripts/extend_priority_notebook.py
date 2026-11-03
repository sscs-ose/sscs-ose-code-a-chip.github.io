"""Add source-visible application experiments while retaining every laboratory cell."""
from pathlib import Path
import argparse,copy,json
import nbformat as nbf

def build(root,output):
    root=Path(root).resolve();book=nbf.read(root/'AutoMX_CIM_Code_a_Chip.ipynb',4)
    book.cells=[c for c in book.cells if not c.id.startswith('priority-')]
    # Bind the corrected physical input pair before native configuration starts.
    for c in book.cells:
        if c.cell_type=='code' and c.id=='mha-ip-binding-source':
            c.source=c.source.replace('.inn_analog(AINN), .inp_analog(AINP)','.inn_analog(AINP), .inp_analog(AINN)')
    by_id={c.id:c for c in book.cells}
    if 'standalone-runtime' in by_id:
        by_id['standalone-runtime'].source='%%standalone_runtime\n'+(root/'scripts/standalone_runtime.py').read_text()+"\nprint('Runtime: five hard macros and source-matched physical views',flush=True)\n"
    def md(ident,text):return nbf.v4.new_markdown_cell(text,id='priority-'+ident)
    def code(ident,text):return nbf.v4.new_code_cell(text,id='priority-'+ident)
    # The readout source is now explicit before the physical flow uses it.
    early=[md('readout-contract', '''## Readout implementation and ADC polarity

**Implementation:** Preserve the programmable 304-threshold interface while replacing the linear scan with an upper-bound binary search. `BINARY_DECODE=0` retains the 38-clock comparison; the default uses at most six comparisons. The calibration checks, raw mode, fault state and ready/valid contract remain part of the same controller.

**Inputs → outputs and downstream use:** Host weight masks and calibration thresholds, MXFP4 X2 activations, and ADC word/EOC enter the controller. It emits PWM (Pulse-Width Modulation), sample/hold/select controls and four signed projection outputs. The following source is used by synthesis, full-top RTL verification and the later exhaustive decoder comparison. The conditioner-to-ADC differential pair is crossed in the top binding so increasing signed sums produce increasing raw codes; the native application campaign measures this orientation.'''),
        code('readout-source','READOUT_RTL = '+repr((root/'rtl/automx_cim_readout_seq.sv').read_text())+'''
from pathlib import Path
_priority_root=Path(__import__('os').environ.get('AUTOMX_BUNDLE_DIR','.')).resolve()
for _relative in ('rtl/automx_cim_readout_seq.sv','ip/automx_mha/rtl/automx_cim_readout_seq.sv'):
    (_priority_root/_relative).write_text(READOUT_RTL)
print('Readout RTL: binary upper bound, 38 thresholds/bank, eight banks; linear baseline retained')
''')]
    early[-1].source+='\nPRIORITY_MIXED_TOP_RTL = '+repr((root/'inputs/automx_cim_mixed_signal_proto.sv').read_text())+"\nfor _relative in ('inputs/automx_cim_mixed_signal_proto.sv','ip/automx_mha/rtl/automx_cim_mixed_signal_proto.sv'):\n    (_priority_root/_relative).write_text(PRIORITY_MIXED_TOP_RTL)\nprint('ADC input pair: conditioner AINN -> ADC inp; AINP -> ADC inn')\n"
    idx=next(i for i,c in enumerate(book.cells) if c.id=='native-runall-config')
    book.cells[idx:idx]=early
    cells=[md('application-intro','''<a id="results-real-application"></a>
## From wearable sensor data to a hardware attention decision

The next experiments turn the existing two-token, four-channel, two-head IP into a six-class human-activity application. They compare the deployed arithmetic, actual RTL, a serial ternary digital backend, and a bounded native CIM/SAR campaign. Feature extraction, the 12-to-4 token embedding and the classifier are software; Q/K/V, attention, context quantization and O are the hardware candidate.

The [UCI HAR dataset](https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones), by Reyes-Ortiz, Anguita, Ghio, Oneto and Parra, is used under CC BY 4.0. Subject identities separate training, validation and test. Deployment weights and calibration are frozen before their respective held-out evaluations. Dataset-wide RTL coverage and native circuit frame coverage are reported separately.'''),
        md('module-method','''**Implementation:** Register a notebook module for each source block so its functions have separate global variables. Each source block is visible in the notebook and also writes the same implementation to the bundled path used by subprocesses. This keeps training, the independent reference and native simulation from accidentally sharing or overwriting format constants.

**Inputs → outputs and downstream use:** A source cell and its module name produce an executable Python module and the identical source file. The following experiment cells call these exact implementations and save new outputs under this run's empty directory.'''),
        code('module-loader','''from IPython.core.magic import register_cell_magic
from IPython.display import Markdown,display
from pathlib import Path
import sys,types
PRIORITY_ROOT=Path(__import__('os').environ.get('AUTOMX_BUNDLE_DIR','.')).resolve()
PRIORITY_WORK=Path(_design_review_namespace['OUT'])/'priority_application'
PRIORITY_WORK.mkdir(parents=True,exist_ok=False)
PRIORITY_MODULES={}
PRIORITY_PATHS={'har':'automx_cim/application_har.py','decoder':'scripts/verify_binary_decoder.py','rtl':'scripts/verify_har_application_rtl.py','costs':'scripts/measure_priority_costs.py','worker':'scripts/portable_cim_sar.py','native':'scripts/run_har_native.py','replay':'scripts/replay_har_native_rtl.py','power':'scripts/measure_activity_power.py','summary':'scripts/summarize_priority_implementation.py'}
@register_cell_magic
def priority_module(line,cell):
    name=line.strip();path=PRIORITY_ROOT/PRIORITY_PATHS[name]
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(cell)
    module=types.ModuleType('automx_priority_'+name);module.__file__=str(path)
    sys.modules[module.__name__]=module
    exec(compile(cell,str(path),'exec'),module.__dict__)
    PRIORITY_MODULES[name]=module
    print('Source ready:',path.relative_to(PRIORITY_ROOT))
print('Application outputs:',PRIORITY_WORK)
'''),
        md('dataset-method','''**Implementation:** Locate the attributed UCI HAR input dataset, or download and unpack its official archive. No previous application measurements supply predictions or ADC words.

**Inputs → outputs and downstream use:** Inertial text files, labels and subject IDs become the input to deterministic half-window summaries. The model cell fits normalization only on training subjects.'''),
        code('dataset','''import urllib.request,zipfile
_har=PRIORITY_ROOT/'data/uci_har'
if not (_har/'UCI HAR Dataset/train/subject_train.txt').is_file():
    _har.mkdir(parents=True,exist_ok=True);_archive=_har/'uci_har.zip'
    if not _archive.is_file():
        with urllib.request.urlopen('https://archive.ics.uci.edu/static/public/240/human+activity+recognition+using+smartphones.zip',timeout=90) as _response:
            _archive.write_bytes(_response.read())
    with zipfile.ZipFile(_archive) as _zip:
        assert _zip.testzip() is None;_zip.extractall(_har)
    for _child in _har.glob('*.zip'):
        if _child!=_archive:
            with zipfile.ZipFile(_child) as _zip:_zip.extractall(_har)
print('Dataset: six activities; train/test subjects disjoint; two 64-reading halves per window')
''')]
    descriptions={
      'har':'''**Implementation:** `load_features` computes mean/RMS sensor summaries. `quantize` implements the supported alphabet with a straight-through training gradient. `TinyAttention` matches the four ternary projections and the IP's fixed-point probabilities/context; its embedding and classifier remain software. `train` selects checkpoints with validation subjects. `metrics` reports classification errors. `run` freezes deployment parameters before test evaluation and compares every output to the independent integer reference.

**Inputs → outputs and downstream use:** Training windows and subject IDs produce float/quantized checkpoints, an explicit deployment contract, test metrics, and packed hardware input/output vectors. QAT means Quantization-Aware Training; X2 stores twice the activation value as an integer. The three QAT seeds are fixed in advance.''',
      'decoder':'''**Implementation:** `verify` exercises actual linear/binary decoder state machines over every ADC code, eight banks and three independent ordered table families, then measures a matched integrated MHA frame. `run` executes Icarus and retains its output. Boundary codes, threshold equality and partial-sum accumulation are checked.

**Inputs → outputs and downstream use:** The declared readout RTL and generated threshold families produce 98,304 comparisons, cycle bounds and a latency comparison. Functional ADC response timing is held equal; these cycle measurements are not concurrent transistor simulation.''',
      'rtl':'''**Implementation:** `verify` exports the independent probability/context reference and runs every application input through the MHA, the real two-phase mixed top with functional ADC responses, and the serial sign/add baseline. `command` retains actual simulator output and stops on a failed check.

**Inputs → outputs and downstream use:** Frozen weights and application vectors produce observed hardware outputs, mismatch counts and frame latency records. The same ready/valid outputs are backpressured on both backends. Native analog evidence follows separately.''',
      'costs':'''**Implementation:** `measure` synthesizes the preserved linear readout, binary readout, serial ternary projector and complete digital attention baseline with the same pinned Yosys/ABC image and SKY130 TT Liberty. Conditional sign/add implements ternary multiplication.

**Inputs → outputs and downstream use:** RTL and one cell library produce mapped netlists, raw tool logs and area/cell-count tables. TT is the typical process/voltage/temperature corner. Mapped area is kept distinct from routed footprint and power.''',
      'worker':'''**Implementation:** `SharedSpice` exchanges electrical states with native ngspice; `RTL` clocks the actual upstream SAR logic. `coupled_deck` constructs the connected CIM, acquisition, conditioner, ADC sampler/comparator and CDAC partition, with the corrected differential input pair. `simulate` collects fresh EOC, ADC word, waveforms and supply/bridge energy. CDAC means Capacitive Digital-to-Analog Converter; EOC means End Of Conversion.

**Inputs → outputs and downstream use:** Actual activation/weight/column stimuli produce an independently resolved ADC code and current waveform. The partition uses schematic CIM/conditioner, ideal activation drivers and electrical bridges; its scope is not complete-chip transistor/PEX signoff. The original partition experiment earlier in the notebook retains its original orientation.''',
      'native':'''**Implementation:** `Native.many` runs new independent native jobs and deduplicates identical physical stimuli within this run. `payload` records the complete activation/weight/column contract. `run` measures all 39 reachable levels in eight banks, freezes 304 midpoint thresholds, then projects two preselected application frames using the measured ADC responses. Context reconstruction uses the same fixed-point contract as the RTL reference.

**Inputs → outputs and downstream use:** Separate calibration cases and frozen application vectors produce 312 calibration executions, 128 logical frame conversions, raw waveforms, measured Q/K/V/O tensors and transaction-tagged ADC words. Unique simulator jobs are reported separately from logical energy/latency accounting.''',
      'replay':'''**Implementation:** `replay` drives the actual MHA/readout hierarchy with the newly measured ADC words and EOC durations. Before each response it checks activation bits, all weight masks, physical column and row phase against the native stimulus. The classifier consumes the observed output rows.

**Inputs → outputs and downstream use:** Fresh native records, derived thresholds and the independent expected tensors produce a frame-level hardware comparison and activity predictions. This is measurement-driven response replay, not a simultaneous whole-chip transistor simulation.''',
      'power':'''**Implementation:** `measure` simulates the actual routed gate netlists on the same two native-backed application frames, verifies their outputs, records fresh VCD activity and uses the extracted SPEFs in OpenSTA. `run_command` preserves tool logs and rejects failed simulations. The original readout and digital baseline are reusable source-matched physical IP inputs; neither contributes an old activity/power result.

**Inputs → outputs and downstream use:** Newly measured ADC responses, deployment vectors, physical gate netlists and RC produce per-block activity annotation, active-window power and energy/frame. The warm benchmark advances the boot counter before calibration; it never forces active-window data or outputs. Results exclude parent CTS/IO, analog supplies, SAR digital control and external driver generation. These are child-digital estimates, not complete-system measured energy. Annotation coverage and exclusions remain visible.''',
      'summary':'''**Implementation:** `summarize` regenerates the application confusion matrix, cost/latency figures, paired confidence intervals and a resumable report from this run's records. The bootstrap resamples subjects to preserve dependence between overlapping windows.

**Inputs → outputs and downstream use:** Frozen evaluation records produce figures and a measured conclusion. Learned versus retrained uniform attention is judged with the paired interval; a small point-estimate difference alone is not treated as decisive.'''}
    def module(name,relative):
        cells.extend([md(name+'-method',descriptions[name]),code(name+'-source','%%priority_module '+name+'\n'+(root/relative).read_text())])
    module('har','automx_cim/application_har.py')
    cells.append(code('har-run', '''HAR_REPORT=PRIORITY_MODULES['har'].run(PRIORITY_ROOT,PRIORITY_WORK/'application')
display(Markdown('| Model | Accuracy / % | Macro-F1 / % |\\n|---|---:|---:|\\n'+'\\n'.join(f"| {name} | {m['accuracy']*100:.3f} | {m['macro_f1']*100:.3f} |" for name,m in HAR_REPORT['models'].items())))
'''))
    cells.extend([md('digital-method','''**Implementation:** A resident-weight digital projector selects zero, positive or negative activation and accumulates one term per clock. `automx_mha_digital_top` connects it to the identical MHA datapath. It provides a matched ternary baseline without general-purpose projection multipliers.

**Inputs → outputs and downstream use:** The same ternary masks and X2 activations produce four signed outputs under the same backend handshake. The following RTL is used by simulation and synthesis.'''),
        code('digital-source','DIGITAL_TERNARY_RTL = '+repr((root/'ip/automx_mha/rtl/automx_ternary_projection_digital.sv').read_text())+"\n(PRIORITY_ROOT/'ip/automx_mha/rtl/automx_ternary_projection_digital.sv').write_text(DIGITAL_TERNARY_RTL)\nprint('Digital backend: resident ternary weights; serial sign/add; shared MHA datapath')\n")])
    module('decoder','scripts/verify_binary_decoder.py')
    cells.append(code('decoder-run',"DECODER_REPORT=PRIORITY_MODULES['decoder'].verify(PRIORITY_ROOT,PRIORITY_WORK/'decoder')\nprint('Exhaustive comparisons:',DECODER_REPORT['cases'],'| frame latency / us:',[v['latency_us'] for v in DECODER_REPORT['frame_latency']])\n"))
    module('rtl','scripts/verify_har_application_rtl.py')
    cells.append(code('rtl-run',"APPLICATION_RTL=PRIORITY_MODULES['rtl'].verify(PRIORITY_ROOT,PRIORITY_WORK/'application',PRIORITY_WORK/'application_rtl')\nprint('Application RTL:',APPLICATION_RTL['frames_per_path'],'frames per path; all output comparisons passed')\n"))
    module('costs','scripts/measure_priority_costs.py')
    cells.append(code('costs-run',"PRIORITY_COSTS=PRIORITY_MODULES['costs'].measure(PRIORITY_ROOT,PRIORITY_WORK/'costs')\ndisplay(Markdown('| Design | Mapped cells | Mapped area / um² |\\n|---|---:|---:|\\n'+'\\n'.join(f\"| {r['design']} | {r['mapped_cells']} | {r['mapped_area_um2']:.3f} |\" for r in PRIORITY_COSTS)))\n"))
    module('worker','scripts/portable_cim_sar.py');module('native','scripts/run_har_native.py')
    cells.append(code('native-run',"NATIVE_APPLICATION=PRIORITY_MODULES['native'].run(PRIORITY_ROOT,PRIORITY_WORK/'application',PRIORITY_WORK/'native_application',jobs=8)\nassert NATIVE_APPLICATION['status']=='PASS'\nprint('Native application:',len(NATIVE_APPLICATION['frames']),'frames;',NATIVE_APPLICATION['logical_conversions'],'ADC transactions;',NATIVE_APPLICATION['partial_decode_mismatches'],'partial errors')\n"))
    module('replay','scripts/replay_har_native_rtl.py')
    cells.append(code('replay-run',"NATIVE_REPLAY=PRIORITY_MODULES['replay'].replay(PRIORITY_ROOT,PRIORITY_WORK/'application',PRIORITY_WORK/'native_application',PRIORITY_WORK/'application_rtl',PRIORITY_WORK/'native_replay')\n"))
    module('power','scripts/measure_activity_power.py')
    cells.append(code('power-run', '''ACTIVITY_POWER=PRIORITY_MODULES['power'].measure(PRIORITY_ROOT,PRIORITY_WORK,PRIORITY_WORK/'activity_power')
display(Markdown('| Variant | Native-backed frames | Warm gate latency / us | Estimated child-digital energy / nJ per frame |\\n|---|---:|---:|---:|\\n'+'\\n'.join(f"| {r['variant']} | {r['frames']} | {r['activity_window_s']/r['frames']*1e6:.3f} | {r['child_digital_energy_per_frame_j']*1e9:.3f} |" for r in ACTIVITY_POWER['results'])))
import matplotlib.pyplot as plt
_power_rows=ACTIVITY_POWER['results']
_figure,_axis=plt.subplots(figsize=(8,4))
_axis.bar([r['variant'] for r in _power_rows],[r['child_digital_energy_per_frame_j']*1e9 for r in _power_rows],color=['#c0392b','#148f77','#2874a6'])
_axis.set_yscale('log');_axis.set(ylabel='Estimated child-digital energy / nJ per frame (log)',title='Matched native-backed frames; routed gates and extracted RC')
_figure.tight_layout();plt.show();plt.close(_figure)
print('Power scope: readout + MHA or digital attention baseline; analog/SAR-digital, parent CTS/IO and startup excluded')
'''))
    module('summary','scripts/summarize_priority_implementation.py')
    cells.append(code('results',"PRIORITY_SUMMARY=PRIORITY_MODULES['summary'].summarize(PRIORITY_ROOT,PRIORITY_WORK)\nfrom IPython.display import Image,display\ndisplay(Image(filename=str(PRIORITY_WORK/'figures/application_results.png')))\ndisplay(Image(filename=str(PRIORITY_WORK/'figures/controller_comparison.png')))\nprint('Native ADC transaction identity checks:',NATIVE_REPLAY['native_transaction_identity_checked'],'| RTL output mismatches:',NATIVE_REPLAY['mismatches'])\n"))
    idx=next(i for i,c in enumerate(book.cells) if c.id=='references');book.cells[idx:idx]=cells
    for c in book.cells:
        if c.id=='output-results-map':c.source+='\n[Real sensor application, controller optimization and matched digital baseline](#results-real-application)\n'
    book.metadata['priority_application']={'date':'2026-10-28','task':'UCI HAR, six activities, subject-disjoint','measurement_scope':'native circuit subset + exact RTL + matched digital sign/add','preserved_previous_cells':True}
    nbf.write(book,output);print('CANDIDATE_NOTEBOOK',output,'cells',len(book.cells),'code',sum(c.cell_type=='code' for c in book.cells))
    return book

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.root,a.output)
