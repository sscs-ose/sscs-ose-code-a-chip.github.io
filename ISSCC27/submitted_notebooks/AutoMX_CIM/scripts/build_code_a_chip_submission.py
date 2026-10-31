"""Export a portable, evidence-backed Code-a-Chip notebook; never run third-party PRs."""
from pathlib import Path
import ast, copy, gzip, json, shutil, textwrap
import nbformat as nbf
from scripts import code_a_chip_review_cells as cells

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'submission/ISSCC27/submitted_notebooks/automx_cim'

def export(dest=DEST):
    dest=Path(dest);dest.mkdir(parents=True,exist_ok=True)
    location=json.loads((ROOT/'docs/code_a_chip_study_location.json').read_text())
    # Keep the study paired with its frozen source session even after a later native Run All.
    work=Path(location['source_session']);study=Path(location['study'])
    if json.loads((study/'summary.json').read_text())['status']!='NATIVE_STUDY_COMPLETED':
        raise ValueError('Native study must complete before export')
    changes=[]
    def clean(value):
        if isinstance(value,dict):
            return {k:clean(v) for k,v in value.items() if not any(s in k.lower() for s in ('sha256','digest','hash'))}
        if isinstance(value,list):return [clean(v) for v in value]
        if isinstance(value,str):
            for prefix,label in [(str(work),'<native-session>'),(str(study),'<study-session>'),
                                 (str(ROOT),'<source-checkout>'),('/home/nam','<user-home>'),('/media/nam','<data-volume>')]:
                value=value.replace(prefix,label)
        return value
    def write_json(rel,value):
        p=dest/rel;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(clean(value),indent=2)+'\n')
    def text_file(source,rel):
        original=Path(source).read_text();text=clean(original)
        if text!=original:changes.append(rel)
        p=dest/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
    def binary(source,rel):
        p=dest/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,p)
    fit=json.loads((work/'calibration.json').read_text())
    protocol=json.loads((study/'protocol.json').read_text())
    if protocol['calibration']!=fit or not protocol['calibration_frozen']:
        raise ValueError('Study calibration does not match its declared source session')
    mha=json.loads((work/'mha_end_to_end.json').read_text())
    challenge=json.loads((study/'challenge.json').read_text())
    cases=[];mapping={}
    def add_case(label,cohort,path):
        p=Path(path);relative=f'data/cases/{label}'
        text_file(p,relative+'/summary.json')
        for log in ('rtl.log','ngspice.log'):
            text_file(p.parent/log,relative+'/'+log)
        # Include the exact requested stimulus separately from the simulator summary.
        text_file(p.parent/'case.json',relative+'/case.json')
        mapping[str(p)]=label
        cases.append({'id':label,'cohort':cohort,'summary':relative+'/summary.json',
            'stimulus':relative+'/case.json','rtl_log':relative+'/rtl.log','ngspice_log':relative+'/ngspice.log'})
    calibration_ids=[]
    for i,ref in enumerate(fit['source_cases'].values(),1):
        label=f'calibration_{i:02}';add_case(label,'calibration',ref['path']);calibration_ids.append(label)
    for job in mha['jobs']:
        path=job['case']['path']
        if path not in mapping:
            count=sum(r['cohort']=='projection' for r in cases)+1
            add_case(f'projection_{count:02}','projection',path)
    for row in challenge['patterns']:add_case(row['label'],'challenge',row['case'])
    factorial=[]
    for condition in json.loads((study/'factorial.json').read_text())['conditions']:
        row=copy.deepcopy(condition);row.pop('mode',None)
        for job in row['jobs']:
            rel=f"data/pex/c{row['load_ff']}_pwm{row['pwm_unit_ps']}/{job['case']}"
            text_file(job['log'],rel+'.log');text_file(job['deck'],rel+'.spice')
            job['log']=rel+'.log';job['deck']=rel+'.spice'
        factorial.append(row)
    factorial.sort(key=lambda d:(d['load_ff'],d['pwm_unit_ps']))
    physical={}
    for key,source in [('geometry','gds_audit/geometry.json'),('power','power/power.json'),
                       ('drc','gds_audit/drc_summary.json'),('timing_log','timing/timing.native.log'),
                       ('lvs_log','signal_lvs/netgen.log'),('synthesis_log','sar_synthesis/sar_synthesis.native.log')]:
        relative='data/physical/'+Path(source).name
        if not (work/source).is_file():raise FileNotFoundError(work/source)
        text_file(work/source,relative);physical[key]=relative
    wave_path=next(j['case']['path'] for j in mha['jobs'] if mapping[j['case']['path']]=='projection_01')
    binary(Path(wave_path).parent/'coupled.raw','data/coupled.raw')
    for source,name in [('render_top/top.png','top'),('render_01_core_acquisition/01_core_acquisition.png','core_acquisition'),
                        ('render_02_conditioner_mux/02_conditioner_mux.png','conditioner_mux'),
                        ('render_03_adc_reference/03_adc_reference.png','adc_reference')]:
        binary(work/source,f'figures/{name}.png')
    gds=dest/'layout/top.gds.gz';gds.parent.mkdir(exist_ok=True)
    with (work/'streamout/automx_cim_mixed_signal_proto.gds').open('rb') as inp,gds.open('wb') as out:
        with gzip.GzipFile(filename='',mode='wb',fileobj=out,mtime=0,compresslevel=6) as compressed:
            shutil.copyfileobj(inp,compressed)
    ip=ROOT/'third_party/SKY130_SAR_ADC1'
    for source in (ip/'mixed_signal_partition/verilog/rtl').glob('*.v'):
        binary(source,'rtl/'+source.name)
    binary(ip/'LICENSE','licenses/SKY130_SAR_ADC1_LICENSE')
    for library in ('sky130_fd_sc_hd','sky130_fd_pr'):
        binary(ROOT/'docs/licenses'/(library+'_LICENSE'),'licenses/'+library+'_LICENSE')
    text_file(ROOT/'docs/code_a_chip_pdk_provenance.json','data/pdk_provenance.json')
    # Apache text is standard; this copy applies only to this newly authored package code.
    binary(ip/'LICENSE','LICENSE')
    provenance=json.loads((ip/'mixed_signal_partition/provenance.json').read_text())
    write_json('data/provenance.json',{'analog_session':work.name,'study_session':study.name,
        'protocol_before_challenge':True,'protocol':clean(json.loads((study/'protocol.json').read_text())),
        'upstream_sar':{'repository':provenance['repository'],'commit':provenance['commit']},
        'transcript_path_redactions':changes,
        'redaction_policy':'Only host path prefixes are replaced; numerical measurements and RTL state rows are unchanged.',
        'measurements':'Existing native records; fresh execution occurs only where the notebook invokes a tool.'})
    write_json('data/evidence.json',{'cases':cases,'calibration_ids':calibration_ids,'factorial':factorial,
        'mha':{'activation_x2':mha['activation_x2'],'weights':mha['weights'],
               'recorded_output':mha['output'],
               'jobs':[{'stage':j['stage'],'row':j['row'],'column':j['column'],'case':mapping[j['case']['path']]} for j in mha['jobs']]},
        'waveform':{'case':'projection_01','path':'data/coupled.raw'},'physical':physical})
    team=dest/'TEAM.json'
    if not team.exists():write_json('TEAM.json',{'team_name':'','authors':[], 'affiliation':'','contact_email':'',
        'status':'Complete verified author/contact details before public submission.'})
    write_docs(dest,provenance)
    book=make_notebook()
    # Keep every existing review cell/output, then add the whole native notebook.
    existing=dest/'AutoMX_CIM_Code_a_Chip.ipynb'
    if existing.is_file():
        old=nbf.read(existing,4);prior={c.id:c for c in old.cells}
        for i,c in enumerate(book.cells):
            if c.id in prior and c.cell_type==prior[c.id].cell_type:
                previous_source=prior[c.id].source
                prefix='%%design_review '+c.id+'\n'
                if previous_source.startswith(prefix):previous_source=previous_source[len(prefix):]
                if c.source==previous_source:
                    book.cells[i]=copy.deepcopy(prior[c.id]);book.cells[i].source=c.source
    from scripts.code_a_chip_full_lab import append_full_lab,write_lab_data
    original=nbf.read(ROOT/'AutoMX_CIM_Sky130_MHA.ipynb',4)
    book,lab_manifest,lab_outputs=append_full_lab(book,original)
    from scripts.code_a_chip_design_argument import organize_design_argument
    book=organize_design_argument(book)
    lab_manifest['policy']='Every original cell is included. Native code execution order and source bodies are preserved; text and analysis are arranged by design stage.'
    lab_manifest['mapping_order']='original_source_notebook_order'
    lab_manifest['combined_reading_order']='data/design_argument_cells.json'
    write_lab_data(dest,lab_manifest,lab_outputs)
    write_json('data/design_argument_cells.json',{
        'edition':'unified_design_argument','retained_previous_cells':book.metadata['automx_review']['retained_previous_cells'],
        'chapters':book.metadata['automx_review']['argument_chapters'],
        'native_code_order_preserved':True,
        'cells':[{'index':i+1,'id':c.id,'cell_type':c.cell_type} for i,c in enumerate(book.cells)]})
    nbf.write(book,existing)
    print('Exported',dest,'| cells',len(book.cells),'| recorded conversions',len(cases),
          '| package MB',round(sum(p.stat().st_size for p in dest.rglob('*') if p.is_file())/1e6,2))
    return dest

def function_source(path,name):
    text=path.read_text();tree=ast.parse(text)
    node=next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name)
    return ast.get_source_segment(text,node)

def make_notebook():
    book=nbf.v4.new_notebook(metadata={'kernelspec':{'display_name':'Python 3 (env_mamba compatible)',
        'language':'python','name':'python3'},'language_info':{'name':'python','version':'3.11'},
        'automx_review':{'schema':1,'analog_data':'recorded native measurements','native_tools':'fresh if available'}})
    def md(cid,text):book.cells.append(nbf.v4.new_markdown_cell(textwrap.dedent(text).strip(),id=cid))
    def code(cid,text):book.cells.append(nbf.v4.new_code_cell(cells.code(text),id=cid))
    md('title',r'''# AutoMX-CIM: from a failed bitline transfer to measured attention projections

**A reproducible SKY130 mixed-signal design investigation · Code-a-Chip ISSCC 2027**

Can a small ternary compute-in-memory core feed an actual SAR control loop and produce the correct attention projections? We follow a physical failure from bitline voltage to application output. Two patterns with sums 11 and 12 initially reverse their voltage ordering. A matched 2×2 load/PWM experiment separates the interventions; an independently calibrated transistor/RTL partition then supplies all Q/K/V/O projections of a tiny attention layer.

**Measured result:** 3 calibration conversions, **38 distinct holdout conversions with zero integer decoding mismatches**, and 32 projection transactions. The tiny-MHA output matches the reference with the same context quantization; relative L2 against floating context is **0.114477**. The notebook exposes raw residuals and waveforms before rounding, checks intentional record errors, and connects the result to top GDS, signal connectivity and digital timing.

**Contribution:** an inspectable experiment and verification flow across ternary CIM, acquisition, SAR and MHA, including a controlled physical ablation and frozen-calibration challenge. The SAR core is reused with attribution; novelty is in the integration and investigation.

Team and contact are supplied in [`TEAM.json`](TEAM.json). Original notebook analysis and package code: Apache-2.0; reused SAR RTL retains its upstream Apache-2.0 notices.''')
    md('reading-route',r'''## How to read and run

The short route is **question → measured failure → controlled change → independent decoding → MHA → layout**. Read the figures and result tables; every supporting implementation remains in its cell.

Run **Restart Kernel & Run All** from this folder. Python 3.11, NumPy, Matplotlib and Jupyter suffice for the measurement analysis. No private source checkout, PDK download or internet access is needed. A new temporary output folder is created every time. If installed, Icarus and KLayout additionally run **fresh digital state replay and GDS inspection/rendering**. Set `AUTOMX_REVIEW_NATIVE=on` to require both tools, or `off` for analysis only.

Analog/PEX records are supplied measurements, clearly labeled when read. Fresh transistor simulation, synthesis, physical export, extraction and timing belong to the complete native laboratory notebook `AutoMX_CIM_Sky130_MHA.ipynb` in the source project. This review does not label stored analog logs as a new simulator run.''')
    md('theory',r'''## 1. Design question and numerical contract

For each head, $Q=XW_Q$, $K=XW_K$, $V=XW_V$ and $H=\operatorname{softmax}(QK^T/\sqrt{d_h})V$. The output is $Y=\operatorname{Concat}(H_h)W_O$. We map **Q/K/V/O projections** to CIM conversion measurements and compute attention/softmax on the CPU.

The four-row physical core uses ternary weights $w_r\in\{-1,0,1\}$ and signed E2M1 activation integers $a_r=2x_r$. Its arithmetic contract is $s=\sum_r a_rw_r$, with projection result $s/2$. PWM chooses the activation sign and magnitude. Differential charge accumulation gives the intuition $\Delta V\approx\int(I_P-I_N)dt/C_{eff}$; transistor saturation and activity make a measured transfer necessary.

**Mixed-signal flow:** numerical specification → analog/digital partition → transistor schematic and RTL → separate analog layout/PEX and digital synthesis/routing → integrated top → co-simulation, connectivity, RC/STA and view checks. The experiment below follows this feedback loop through an actual failure.

The conversion partition uses transistor CIM/acquisition/conditioner and ADC input switches/comparator, upstream SAR/decoder/OSR RTL, and a charge-equivalent CDAC with ideal bottom drivers. One physical column is reused. The application is a deterministic **2-token × 4-dimension, 2-head** test.''')
    code('setup',cells.SETUP)
    code('architecture',cells.ARCHITECTURE)
    md('evidence-schema',r'''## 2. Verify the evidence before scoring the design

Each conversion includes its requested stimulus, native ngspice log, native Icarus state log and conversion summary. Recompute the integer reference from activation and weights, verify the 12-bit code in its 16-bit word, and compare all 15 RTL fields across all 16 measured states. Reset and priming states are kept separately. Calibration and holdout are disjoint by **full physical payload**, not just sum value.''')
    code('validate-evidence',cells.VALIDATOR)
    md('negative-method','''### Does the checker notice an error?

The next cell deliberately corrupts copies of valid records. It must reject every mutation. These are software checker controls; they are distinct from the measured analog transfer failure studied next.''')
    code('negative-controls',cells.NEGATIVE)
    md('factorial-method',r'''## 3. Diagnose the physical failure: separate load from PWM

Keep both stimuli, PEX netlist, TT/1.8 V/25 °C, and sample time **1.9 ns** fixed. Change bitline load (200/800 fF) and PWM unit (50/100 ps) in a 2×2 experiment. The primary response is the signed **column-0 gap** $g=V(s=12)-V(s=11)$.

The original 200 fF/100 ps and 800 fF/50 ps conditions are prior verified native measurements. The two missing conditions were newly simulated for this study under a protocol written before measurement. All four are now supplied as recorded data. Each condition contains the same two physical patterns; this is a matched-pair diagnostic, not a full code-range sweep.

Read the actual `.measure` rows from ngspice logs, verify them against receipts, then compute load effects at fixed PWM, PWM effects at fixed load, and their interaction.''')
    code('factorial-result',cells.FACTORIAL)
    md('factorial-decision',r'''### What changed the design decision?

A negative gap means these two increasing sums have reversed voltage ordering at the chosen sample time. A positive gap permits a threshold between this pair. **Either intervention alone restores ordering for this pair:** shortening PWM at 200 fF produces +29.2472 mV; increasing load at 100 ps produces +30.7722 mV. Combining the changes gives +19.5577 mV, so the effects are not additive. The load effect is −9.6895 mV at 50 ps but +505.0266 mV at 100 ps; the difference is a −514.7161 mV interaction. Thus the data support considering the shorter pulse before automatically paying for four times the load. This pair alone does not select a globally optimal operating point or establish energy savings.

This PEX investigation motivates how the operating point is selected. The following directly coupled CIM/ADC experiment is a separate schematic/partition measurement, connected by the same integer-sum contract; its ADC codes are not inferred from this two-pattern PEX table.''')
    md('calibration-method',r'''## 4. Freeze calibration, then decode unseen physical patterns

Fit $d=\alpha s+\beta$ using only three independent calibration patterns at $s=0,-8,+8$. Freeze the fit. Decode every held-out conversion as $\widehat s=\operatorname{round}((d-\beta)/\alpha)$ and retain the **unrounded residual**. Codes are produced by the coupled transistor/RTL conversion, not by fitting the holdout labels.

The first holdout cohort contains 30 distinct physical patterns used by 32 MHA transactions. The second contains eight additional patterns chosen before their native execution. All eight are disjoint from the original 33 calibration/projection patterns. No fitting or retuning uses their results.''')
    code('calibration-holdout',cells.CALIBRATION)
    md('challenge-method',r'''### Same sum, different switching activity

The new challenge includes low/high-activity patterns at the same sums ±3, a high-activity zero, ±5 and mixed ternary signs. Activity is $\sum_r|a_rw_r|$. Equal sums can produce different analog trajectories: retain raw ADC code differences even when rounded integer decoding agrees.''')
    code('challenge-result',cells.CHALLENGE)
    md('mha-method',r'''## 5. Rebuild the application from conversion records

Assemble Q/K/V from measured decoded sums divided by two. Compute each attention head independently, quantize the resulting context to signed E2M1 values, and obtain O from its own measured projection conversions. Check each record against its requested row and weight column.

Use **two references**: an independently calculated pipeline with the same context quantization, and the pipeline with floating context. Their difference separates context quantization from decoding agreement.''')
    code('mha-recompute',cells.MHA)
    md('waveform-method',r'''## 6. Inspect the analog/digital boundary

Read the supplied real-valued ngspice ASCII raw file directly. Show ADC input, CDAC top nodes, comparator/sample phases, start/EOC and output word on aligned time axes. The plot uses one recorded projection conversion and verifies that its final waveform code agrees with its conversion record.''')
    raw=function_source(ROOT/'scripts/flow2_waveforms.py','read_raw')
    code('raw-reader',raw)
    code('waveform',cells.WAVEFORM_PLOT)
    md('rtl-method',r'''### Fresh open-source tool check: the actual SAR RTL

Compile the bundled upstream SAR/decoder/OSR/core RTL with Icarus. Feed each recorded analog comparator decision to a fresh simulator process. Compare **all internal control outputs**, including CDAC controls and EOC, with every recorded state. This independently executes the digital side of the partition; the analog decisions remain the supplied measured inputs. Native command output follows directly from `subprocess` in the cell.''')
    tb=function_source(ROOT/'scripts/flow2_rtl_spice_cosim.py','testbench')
    code('rtl-testbench',tb+'\n\nTESTBENCH=testbench()')
    code('rtl-native',cells.NATIVE_RTL)
    md('physical-method',r'''## 7. Connect the experiment to the physical top

The native lab exports a routed mixed-signal top, checks cell geometry against the routed design, checks signal/rail connectivity, extracts routing RC and evaluates constrained digital TT timing at 25 MHz. The table below reads those reports and parses the actual STA summary. GDS renderings show the core/acquisition, conditioner and ADC region as well as the full top.

These reports describe the scope of their individual checks. The enabled-rule DRC attempt has an incomplete status; positive timing or geometry checks do not convert it into a clean DRC result.''')
    code('physical-reports',cells.PHYSICAL)
    md('klayout-method','''### Fresh KLayout inspection and rendering

The package contains the actual compressed top GDS. When KLayout is available, the following cell decompresses it into the new output folder, opens the named top, checks its cell count and renders a new PNG. The entire KLayout script is visible below.''')
    code('klayout-script',"KLAYOUT_SCRIPT = r'''\n"+cells.code(cells.KLAYOUT_SCRIPT)+"'''\n")
    code('klayout-native',cells.KLAYOUT)
    md('results-method','''## 8. Results generated by this run

The following summary is computed from the evidence and the checks above. All plots and fresh tool logs are saved beside `review_results.json` in this run's new output directory.''')
    code('results',cells.SUMMARY)
    md('takeaways',r'''## Reusable design lessons

1. **Test the physical transfer before trusting the arithmetic abstraction.** Two different patterns can reverse voltage ordering despite increasing integer sums.
2. **Change one factor at a time, then measure interaction.** The complete load/PWM experiment supports a specific operating-point decision.
3. **Lock calibration and retain residuals.** Integer agreement is strongest when accompanied by independent stimuli, native traces and visible unrounded error.
4. **Carry the measurement to application output.** Distinguish exact agreement with the quantized reference from the remaining floating-context error.

The reusable artifacts are the stimulus/record schema, code/trace checker, matched-factor experiment, and measured-projection MHA reconstruction. Reused SAR circuitry is credited below; the integration does not claim a new SAR topology or measured silicon performance.''')
    md('references',r'''## Sources and attribution

- [SKY130_SAR-ADC1](https://github.com/efabless/SKY130_SAR-ADC1), pinned revision `892272208df28b6c7620101e129a9d8dd95ebab7`: reused SAR control, decoder, OSR and source ADC circuit. Upstream notices are retained in `rtl/` and `licenses/`.
- [SKY130 PDK](https://skywater-pdk.readthedocs.io/en/main/): transistor models, process definitions and physical verification context for the native experiment. Models are not redistributed here.
- [ngspice](https://ngspice.sourceforge.io/docs.html), [Icarus Verilog](https://steveicarus.github.io/iverilog/), [Yosys](https://yosyshq.readthedocs.io/projects/yosys/en/latest/), [OpenROAD](https://openroad.readthedocs.io/en/latest/), [KLayout](https://www.klayout.de/doc/) and [Netgen](https://github.com/RTimothyEdwards/netgen): open tools used by the native lab and/or this review.
- Vaswani et al., [Attention Is All You Need](https://arxiv.org/abs/1706.03762): attention reference equations.
- [Code-a-Chip program](https://github.com/sscs-ose/sscs-ose-code-a-chip.github.io#program-rules): notebook-driven reproducible design and educational contribution.

See `NOTICE.md` for attribution and measurement provenance, `README.md` for commands, and `TEAM.json` for author/contact metadata.''')
    nbf.validate(book)
    return book

def write_docs(dest,provenance):
    (dest/'requirements.txt').write_text('numpy>=1.26,<3\nmatplotlib>=3.8,<4\njupyterlab>=4,<5\nnbclient>=0.10,<1\nnbformat>=5.9,<6\nipykernel>=6,<8\n')
    (dest/'environment.yml').write_text('name: automx-review\nchannels: [conda-forge]\ndependencies:\n  - python=3.11\n  - numpy>=1.26,<3\n  - matplotlib>=3.8,<4\n  - jupyterlab>=4,<5\n  - nbclient>=0.10,<1\n  - nbformat>=5.9,<6\n  - ipykernel>=6,<8\n')
    (dest/'README.md').write_text(textwrap.dedent('''\
        # AutoMX-CIM — Code-a-Chip ISSCC 2027

        Start with [AutoMX_CIM_Code_a_Chip.ipynb](AutoMX_CIM_Code_a_Chip.ipynb).
        It follows a measured bitline ordering failure through a controlled 2×2
        load/PWM experiment, independent ADC decoding and a tiny-MHA result.
        The unified edition has 260 cells / 109 code cells. It retains all 244
        cells of the previous extended notebook and weaves the competition
        study into the original laboratory at the corresponding design stages.
        All 200 original native cells, including all 89 native code bodies,
        technical explanations, figures and tool transcripts remain included.

        ## One design argument

        1. Specify arithmetic, scale, physical dimensions and the interface.
        2. Establish the circuit, layout/extraction and transfer fixture.
        3. Observe a failed voltage ordering, then isolate load and PWM effects.
        4. Investigate decoding, acquisition and the historical 2+2 alternative.
        5. Validate the coupled conversion with frozen calibration and holdout.
        6. Reconstruct MHA from measured transactions and two references.
        7. Attach synthesis, GDS, connectivity and digital timing evidence.
        8. Compute which design decisions the observations actually support.

        The native baseline/candidate logs now precede the factorial comparison.
        Independent ADC validation follows the conversion implementation; MHA
        follows that validation. Earlier reading guides are retained in Appendix B.

        | Evidence | Result |
        |---|---|
        | Frozen independent calibration | 3 patterns |
        | Projection + new challenge holdout | 30 + 8 distinct patterns; 0 integer mismatches |
        | MHA | 32 projection transactions; relative L2 0 against same-quantization reference |
        | Floating-context comparison | Relative L2 0.114477 |
        | Physical top | Actual GDS, native renders, geometry/connectivity and digital timing reports |

        ## Run All

        Extract/copy this entire folder, then work from it:

        ```bash
        conda env create -f environment.yml
        conda activate automx-review
        jupyter lab AutoMX_CIM_Code_a_Chip.ipynb
        ```

        Use **Restart Kernel & Run All**. Existing `env_mamba` also works.
        No PDK or source project is needed for review analysis. Dependencies can
        also be installed with `python -m pip install -r requirements.txt`.
        The notebook creates a new temporary output directory for every run.

        Icarus Verilog and KLayout are optional native checks (`apt install
        iverilog klayout` on Debian/Ubuntu). Both are exercised if available.
        `AUTOMX_REVIEW_NATIVE=on` requires both; `off` runs only Python analysis.
        Qt uses the offscreen backend for a fresh KLayout render.

        Interleaved native cells display attributed recorded output by default. Every
        original source body remains visible below an added `%%native_lab`
        execution-mode line; no original cell is removed. Definition-only cells
        stay silent. To execute the full native bodies using the prepared source
        checkout, start Jupyter with:

        ```bash
        export AUTOMX_CIM_ROOT=/path/to/AutoMX-CIM
        export AUTOMX_FULL_NATIVE=on
        jupyter lab AutoMX_CIM_Code_a_Chip.ipynb
        ```

        This mode requires the native PDK, tools and routed design inputs
        declared in the original configuration. A new native output folder is
        created under the current review run; it does not reuse recorded output.

        `%%design_review` executes the complete analysis body shown in that cell
        in a shared analysis namespace. `%%native_lab` selects recorded output
        or fresh native execution for its visible original body. Keeping their
        globals separate prevents interleaved steps from overwriting calibration,
        output paths or helper functions. Both implementations are in the notebook.

        A headless execution from this directory:

        ```bash
        python - <<'PY'
        from pathlib import Path
        import nbformat
        from nbclient import NotebookClient
        p = Path('AutoMX_CIM_Code_a_Chip.ipynb')
        book = nbformat.read(p, 4)
        NotebookClient(book, timeout=180, kernel_name='python3',
                       resources={'metadata': {'path': str(Path.cwd())}}).execute()
        nbformat.write(book, 'AutoMX_CIM_Code_a_Chip.executed.ipynb')
        PY
        ```

        ## What is rerun?

        Python recomputes checks, calibration, ablation effects, residuals, MHA,
        figures and the result summary from supplied native data. If available,
        Icarus freshly executes the SAR digital RTL on recorded analog decisions;
        KLayout freshly reads/renders the actual supplied GDS. Neither operation
        represents a new transistor simulation. Stored logs are labeled recorded.

        The full native experiment is interleaved by design stage, retaining every
        cell from `AutoMX_CIM_Sky130_MHA.ipynb` in the AutoMX-CIM source project.
        It contains the original implementation,
        transistor simulation, synthesis, physical exports, extraction and
        timing flow, using its declared PDK and routed design inputs. The public
        review package deliberately carries the exact measurements needed for
        an independent inspection without those large development dependencies.

        ## Files and attribution

        `data/` contains 41 conversion records, native logs, one full waveform,
        all eight PEX logs/decks and physical reports. `layout/top.gds.gz` is the
        actual top GDS; `rtl/` contains the four reused SAR digital sources.
        Analysis/helper implementations are written directly in notebook cells.
        `data/native_lab_cells.json` maps every original cell to the extended
        notebook; `data/native_lab_outputs.json` carries its original outputs.
        `data/design_argument_cells.json` records the unified reading order.
        Each run writes `design_argument.json` and `design_argument.png` beside
        the recomputed measurement results in its new temporary output folder.
        See [NOTICE.md](NOTICE.md), [LICENSE](LICENSE), and
        [data/provenance.json](data/provenance.json). DRC status is preserved as
        incomplete; no clean DRC claim is made.

        Complete `TEAM.json` with real author, institution and contact details
        before public submission. No personal identity has been inferred.
        ''').strip()+'\n')
    (dest/'NOTICE.md').write_text(textwrap.dedent(f'''\
        # Attribution and provenance

        Original review notebook analysis, evidence exporter and explanatory
        content added for this package are provided under Apache-2.0. This is
        not a relicensing of the entire AutoMX-CIM development repository.

        Bundled SAR RTL is from {provenance['repository']} at revision
        `{provenance['commit']}`. Its Apache-2.0 license and existing copyright
        headers are retained. SAR/CDAC/comparator circuit work is attributed to
        that upstream project. AutoMX-CIM's contribution here is the CIM/readout
        integration, experimental protocol, verification and application trace.

        SKY130 models/process and standard-cell libraries were inputs to the
        native experiment. The top GDS includes SKY130 standard-cell/device
        geometry. The corresponding sky130_fd_sc_hd and sky130_fd_pr license
        texts are included in licenses/; pinned library revisions and upstream
        repositories are recorded in data/pdk_provenance.json. This package
        does not redistribute the PDK simulation models.
        Tool authors retain their respective licenses. See notebook references.

        Logs are recorded native measurements. Only host-specific path prefixes
        are replaced by descriptive tokens in exported text; numerical rows and
        RTL states are unchanged. Affected paths are listed in provenance.json.
        The interleaved complete native laboratory preserves its original
        source and output contents, including original acquisition paths; those
        are recorded historical transcripts, not portable runtime dependencies
        for the default review route. Every replayed output is explicitly labeled.
        The waveform and GDS preserve their scientific/design contents. Native
        review tool output is generated by the visible subprocess calls.

        The original two PEX conditions were acquired in the prior verified
        native session; two missing factorial conditions and eight challenge
        conversions were acquired in the new study. The interrupted first
        factorial attempt was retained externally; the completed attempt
        supplies the measurements. No challenge result was used for refitting.
        ''').strip()+'\n')

if __name__=='__main__':export()
