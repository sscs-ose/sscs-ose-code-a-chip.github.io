"""Weave all retained experiment cells into one evidence-led design argument."""
import copy,textwrap
import nbformat as nbf

REVIEW_BOOTSTRAP=r'''
from IPython.core.magic import register_cell_magic
import types as _argument_types, sys as _argument_sys

# Analysis and native implementation have separate globals. This lets their
# actual cells be interleaved without overwriting calibration, paths or helpers.
_design_review_module=_argument_types.ModuleType('automx_design_review')
_argument_sys.modules[_design_review_module.__name__]=_design_review_module
_design_review_namespace=_design_review_module.__dict__

@register_cell_magic
def design_review(line,cell):
    """Execute the complete analysis implementation visibly written in this cell."""
    key=line.strip()
    exec(compile(cell,'<design-review:'+key+'>','exec'),_design_review_namespace)
'''

ARGUMENT_RESULTS=r'''
# Recompute the links between observations and decisions from measured evidence.
protocol=record('data/provenance.json')['protocol']
declared_fit=protocol['calibration']
if not protocol['calibration_frozen'] or protocol['prior_pattern_overlap']!=0:
    raise AssertionError('Study must declare frozen calibration and independent challenge')
if not np.allclose(FROZEN,[declared_fit['slope_codes_per_integer_sum'],declared_fit['offset_code']],
                   rtol=0,atol=1e-10):
    raise AssertionError('Recomputed calibration differs from the predeclared frozen fit')
if len(CAL_IDS)!=3 or len(HOLD_IDS)!=38 or len(jobs)!=32:
    raise AssertionError('Unexpected calibration, holdout or application population')
assert gaps[200,100]<0 and gaps[200,50]>0 and gaps[800,100]>0
assert all(r['decoded']==r['truth'] for r in observations)
assert MHA_QUANT==0 and np.isclose(MHA_FLOAT,relative_l2(ref_float,output))

decisions=[
 {'stage':'Transfer diagnosis','observation':f'{gaps[200,100]*1000:+.4f} mV gap',
  'decision':'Check the physical ordering before assigning scalar thresholds',
  'evidence':'Eight matched-pattern PEX logs; primary response at column 0 / 1.9 ns'},
 {'stage':'Controlled intervention','observation':f'{gaps[200,50]*1000:+.4f} mV with PWM-only change; interaction {interaction*1000:+.4f} mV',
  'decision':'Evaluate pulse duration separately from capacitance; retain both single-factor alternatives',
  'evidence':'Same pair, same extracted core, same TT condition; complete 2×2 factorial'},
 {'stage':'Independent decoding','observation':f'{len(HOLD_IDS)} holdouts; 0 integer mismatches; max residual {max(abs(r["residual"]) for r in observations):.6f}',
  'decision':'Freeze the three-point ADC fit and carry raw residuals into validation',
  'evidence':'41 coupled transistor/RTL conversion records, disjoint physical payloads'},
 {'stage':'Application reconstruction','observation':f'{len(jobs)} transactions; L2 quantized {MHA_QUANT:.6f}; floating {MHA_FLOAT:.6f}',
  'decision':'Separate measured decoding agreement from context quantization error',
  'evidence':'Q/K/V/O request mapping, independent CPU attention and two references'},
 {'stage':'Physical handoff','observation':f'{geometry["cells"]} GDS cells; setup {setup:+.2f} ns; hold {hold:+.2f} ns',
  'decision':'Attach geometry, connectivity and digital timing evidence to the exported top',
  'evidence':'Declared routed-design input; GDS, Netgen/rail reports and extracted digital TT STA'}]
table(['Design step','Measured observation','Decision supported'],
      [[r['stage'],r['observation'],r['decision']] for r in decisions])
argument={'status':'SUPPORTED_BY_MEASURED_EVIDENCE','calibration_matches_predeclared_fit':True,
          'decisions':decisions,'context_shape':{'tokens':2,'dimensions':4,'heads':2},
          'physical_column_reused':0,'digital_runtime':'CPU attention/softmax',
          'pex_and_coupled_conversion_are_separate_experiments':True,
          'historical_two_plus_two_is_separate_from_final_partition':True,
          'drc_report_status':drc['status']}
(OUT/'design_argument.json').write_text(json.dumps(argument,indent=2)+'\n')

fig,axes=plt.subplots(1,5,figsize=(15,3))
for ax,row in zip(axes,decisions):
    ax.set_axis_off()
    ax.text(.02,.95,row['stage'],ha='left',va='top',weight='bold',fontsize=10,color='#174a72')
    # Wrap labels explicitly for portable, readable exported figures.
    import textwrap
    ax.text(.02,.73,'\n'.join(textwrap.wrap(row['observation'],27)),ha='left',va='top',fontsize=9)
    ax.text(.02,.35,'\n'.join(textwrap.wrap(row['decision'],29)),ha='left',va='top',fontsize=8,color='#475569')
fig.suptitle('Measured observation → design decision → next independent check',fontsize=13)
savefig('design_argument.png')
print('Design argument verified against the predeclared protocol and measured records.')
'''


def organize_design_argument(source):
    """Keep every input cell once; preserve native code order and every source body."""
    if source.metadata.get('automx_review',{}).get('edition')=='unified_design_argument':
        return copy.deepcopy(source)
    old=copy.deepcopy(source); byid={c.id:c for c in old.cells}
    if len(byid)!=len(old.cells):raise ValueError('Duplicate input cell IDs')
    native=[c for c in old.cells if 'automx_native_origin' in c.metadata]
    if not native:raise ValueError('Attach the complete native laboratory before organizing it')
    native_index={c.metadata['automx_native_origin']['original_id']:i for i,c in enumerate(native)}
    book=nbf.v4.new_notebook(metadata=copy.deepcopy(old.metadata));used=set()

    reference_ids={
        'extended-edition','reading-route','full-lab-guide',
        'chapter-lab-numerical','chapter-lab-circuit','chapter-lab-recovery',
        'chapter-lab-coupled','chapter-lab-physical','chapter-lab-orchestration',
        'native-combined-intro','native-competition-abstract','native-competition-results',
        'native-competition-route','native-theory-mha-cim','native-theory-notebook-map',
        'native-combined-history','native-restored-archive-000',
        'native-restored-archive-052','native-restored-archive-053',
        'native-restored-archive-102','native-restored-archive-103','native-restored-archive-105',
        'native-combined-modern','native-combined-orchestration-appendix'}

    def md(cid,text):
        book.cells.append(nbf.v4.new_markdown_cell(textwrap.dedent(text).strip(),id=cid))
    def take(*ids):
        for cid in ids:
            if cid in used:raise ValueError('Cell scheduled twice: '+cid)
            c=byid[cid];used.add(cid)
            if c.cell_type=='code' and 'automx_native_origin' not in c.metadata and cid not in ('full-lab-config','full-lab-inventory'):
                c.source='%%design_review '+cid+'\n'+c.source
                c.metadata['automx_review_origin']={'original_id':cid,'body_preserved':True}
            book.cells.append(c)
    def native_block(start,stop):
        for c in native[native_index[start]:native_index[stop]+1]:
            if c.id not in reference_ids:take(c.id)

    take('title')
    md('argument-roadmap',r'''## Read the design as a sequence of decisions

    **Central claim:** a usable CIM projection requires a physical transfer that can
    be interpreted, a conversion whose code is checked independently, and an
    application result reconstructed from those measured conversions. Each section
    below answers one of those questions and supplies the input to the next one.

    | Step | Question | Evidence that decides it |
    |---|---|---|
    | [1. Specification](#argument-specification) | What exactly must the hardware compute? | Signed integer sum, scale, physical/logical dimensions and interface contract |
    | [2. Circuit foundation](#argument-circuit) | What circuit and extracted model implement that contract? | Generator, layout/extraction recipes and explicit PEX stimuli |
    | [3. Failure → intervention](#argument-transfer) | Which physical change repairs the observed ordering? | Same-pattern baseline and complete load/PWM factorial |
    | [4. Readout investigation](#argument-readout) | Why does a voltage measurement need its own decoding checks? | Historical scalar/2+2 experiments, acquisition timing and protocol checks |
    | [5. Independent ADC validation](#argument-conversion) | Does a locked calibration decode new physical patterns? | Transistor/SAR records, checker controls and disjoint holdout |
    | [6. Application](#argument-application) | Do the measured conversions reconstruct attention projections? | Q/K/V/O mapping, waveforms, digital replay and two MHA references |
    | [7. Physical handoff](#argument-physical) | Which implementation artifacts support the result? | Synthesis, top GDS, geometry/connectivity and digital timing reports |
    | [8. Evidence to conclusion](#argument-conclusion) | Which decisions follow from the measurements? | Recomputed decision table and final results |

    Read the question and decision paragraphs plus figures first; the complete
    implementations and transcripts stay next to the experiment they support.
    Original experiment numbers remain in detailed subsections. Earlier introductory
    guides are retained together in an appendix so the main argument proceeds once.

    **Restart Kernel & Run All** from this folder. Analysis and fresh Icarus/KLayout
    checks use the supplied package. Native laboratory cells display explicitly
    labeled recorded output by default. `AUTOMX_FULL_NATIVE=on` executes their visible
    original code against the checkout selected by `AUTOMX_CIM_ROOT`. The analysis
    and native implementation use separate namespaces so they can be interleaved
    without changing one another's calibration or paths.''')
    book.cells.append(nbf.v4.new_code_cell(textwrap.dedent(REVIEW_BOOTSTRAP).strip()+'\n',id='argument-bootstrap'))
    take('setup','full-lab-config')

    md('argument-specification',r'''<a id="argument-specification"></a>

    # 1. Define the quantity that must survive every boundary

    The application calls matrix projections; the physical core receives PWM and
    ternary controls. The shared contract is the **signed integer sum**
    $s_c=\sum_r a_rw_{r,c}$, with $x_r=a_r/2$ and numerical projection $s_c/2$.
    We carry the requested activation and weight payload through every measurement.

    | Design quantity | Contract used in the measured end-to-end test |
    |---|---|
    | Physical array | Four rows; one of the four physical columns reused for each transaction |
    | Activations / weights | Signed E2M1 x2 integers / ternary −1, 0, +1 |
    | Application | Two tokens, four dimensions, two attention heads |
    | Analog/digital boundary | Held input → comparator decisions → SAR state → word / EOC |
    | Numerical checks | Integer decoding and a same-context-quantization MHA reference; floating context compared separately |

    The older logical 32×8 scheduler and larger numerical reference below establish
    encoding and scheduling methods. The measured physical demonstration has the
    smaller dimensions stated here. Sharing the arithmetic contract lets us relate
    those experiments without treating them as the same-sized implementation.

    **Decision:** agree on sign, scale, payload and handshake before judging analog
    accuracy. **Next test:** construct the circuit and measure its transfer.''')
    take('theory','architecture','native-theory-design-flow')
    native_block('runall-config','restored-archive-021')

    md('argument-circuit',r'''<a id="argument-circuit"></a>

    # 2. Establish the circuit and the measurement fixture

    The generator creates transistor cells, columns and the four-row core; the
    layout/extraction flow supplies the parasitic model used by the transfer study.
    Read the explicit pin ordering, precharge, bitline loads, PWM pulses and sample
    time as part of the experiment, alongside the circuit itself.

    A useful first hypothesis is that larger integer sums produce ordered
    differential voltages. The charge-over-capacitance model explains why load
    and pulse duration can matter, but the extracted simulation decides whether
    that hypothesis holds for real patterns.

    **Input to the next section:** the same extracted core, two specified patterns
    and a fixed 1.9 ns observation time. This makes a before/after comparison
    interpretable.''')
    take('native-theory-charge-sampling')
    native_block('restored-archive-022','restored-archive-036')

    md('argument-transfer',r'''<a id="argument-transfer"></a>

    # 3. Find a physical failure, then isolate the intervention

    **Question:** do sums 11 and 12 retain their expected voltage order under the
    original operating point? Define $g=\Delta V_{12}-\Delta V_{11}$ at column 0,
    1.9 ns. The native baseline below gives **−474.2544 mV** at 200 fF / 100 ps:
    the voltage ordering is reversed for this pair.

    The initial recovery changed both load and PWM and obtained a positive gap.
    That establishes a candidate, but it leaves two explanations entangled.
    Therefore we follow the original acquisition and candidate logs immediately
    with the complete **2×2 matched experiment**, changing one factor at a time.
    Both patterns, PEX, TT/1.8 V/25 °C and observation time remain fixed.''')
    native_block('restored-archive-037','story-candidate_result')
    take('factorial-method','factorial-result','factorial-decision')
    md('argument-transfer-decision',r'''### Decision 1 — the intervention is conditional on the operating point

    PWM shortening alone at 200 fF yields **+29.2472 mV**; increasing load alone at
    100 ps yields **+30.7722 mV**. Combining them yields **+19.5577 mV**, with a
    **−514.7161 mV interaction**. Thus the experiment supports considering the
    shorter pulse before automatically increasing capacitance fourfold. It also
    shows why the original two-condition comparison could not attribute the gain
    to one knob.

    The earlier 800 fF / 50 ps candidate and its implementation records remain
    above as acquired evidence. The new factorial is a diagnostic comparison;
    it does not retroactively change the circuit or operating point used by the
    subsequent coupled ADC experiment.

    **Next question:** does a repaired ordering for one pair provide enough
    information to decode other physical patterns? Test the readout separately.''')

    md('argument-readout',r'''<a id="argument-readout"></a>

    # 4. Investigate decoding, acquisition and transaction structure

    The historical experiments below broaden the question from one voltage gap
    to a decoder and its physical input. Their scalar-decoder investigation records
    52/128 errors, explores calibration/features, and studies a two-read **2+2**
    decomposition with its own calibration and holdout. Sampling load, hold timing,
    reset and transaction checks then connect the readout to its controller.

    These are distinct experiment families. A decoder trained for one acquisition
    or read partition belongs to that partition. The 2+2 branch is preserved as an
    explored alternative with its own reported results; the final coupled SAR/MHA
    experiment below directly measures its declared four-row input on one reused
    physical column.

    **Decision 2:** preserve the complete stimulus and acquisition contract, freeze
    calibration before holdout, and retain raw residuals as well as rounded sums.
    **Next test:** acquire actual coupled analog/SAR conversions and independently
    verify their codes, control states and EOC.''')
    native_block('restored-archive-049','combined-modern')

    md('argument-conversion',r'''<a id="argument-conversion"></a>

    # 5. Validate the coupled conversion before using it as arithmetic

    The implementations below instantiate transistor CIM/acquisition/conditioner,
    ADC input switches and comparator, and the upstream SAR/decoder/OSR RTL.
    A charge-equivalent CDAC closes the partition loop. Native conversion logs
    supply the observations; the following analysis reconstructs expected sums
    from requested payloads and checks word alignment, comparator rails, SAR
    states and end-of-conversion against the native transcripts.

    Three independent calibration patterns establish the fit. Thirty projection
    patterns and eight additional challenge patterns form disjoint holdout cohorts.
    Checker mutations test the checker itself; the physical transfer failure in
    Section 3 remains a separate measured phenomenon.''')
    take('native-theory-sar-interface')
    native_block('inline-geometry_common','runall-calibration')
    take('evidence-schema','validate-evidence','negative-method','negative-controls',
         'calibration-method','calibration-holdout','challenge-method','challenge-result')
    md('argument-conversion-decision',r'''### Decision 3 — accept decoded sums only after an independent frozen-fit test

    The locked three-point fit decodes **38/38 held-out patterns** correctly.
    Maximum absolute unrounded sum residual is **0.142672**. At equal sums ±3,
    increasing activity from 3 to 13 changes the measured code by two counts,
    even though integer decoding remains correct. The raw code and residual plot
    make that physical variation visible.

    These codes come from the coupled schematic/RTL partition. They are not
    values inferred from the two-pattern PEX table. The PEX experiment established
    a physical design question; this independent conversion experiment supplies
    the arithmetic observations used next by the application.''')

    md('argument-application',r'''<a id="argument-application"></a>

    # 6. Carry the measured arithmetic to the application output

    **Question:** do independently checked conversions remain correct when used
    as Q/K/V/O transactions? The native acquisition below supplies each requested
    projection. The reconstruction checks its activation row and weight column,
    then computes CPU attention from measured Q/K/V and requests O for the
    quantized measured context. Two transactions reuse already measured physical
    payloads: 32 requests correspond to 30 distinct projection patterns.

    The same-quantization reference tests decoding agreement. The floating-context
    reference exposes context quantization error. Waveforms connect the final code
    back to the analog/digital handshake, and fresh Icarus simulation checks the
    real SAR controls on the recorded comparator decisions.''')
    native_block('new-c49e894a','runall-mha-plots')
    take('mha-method','mha-recompute','waveform-method','raw-reader','waveform',
         'rtl-method','rtl-testbench','rtl-native')
    md('argument-application-decision',r'''### Decision 4 — report agreement and quantization separately

    Measured MHA matches the independently reconstructed same-quantization
    reference exactly. Relative L2 against floating context is **0.114477076**.
    Thus the result supports the measured projection path and identifies the
    remaining context-quantization difference explicitly. The tiny workload is
    the two-token / four-dimension / two-head case specified in Section 1.

    **Next test:** connect the design to its physical artifacts and read the
    geometry, connectivity and timing checks according to the question each answers.''')

    md('argument-physical',r'''<a id="argument-physical"></a>

    # 7. Attach physical implementation evidence to the functional result

    The following cells expose synthesis and the mixed-signal top handoff, using
    the declared routed database as the input to physical export. GDS geometry,
    signal matching, rail connectivity and extracted digital timing each check a
    different part of that handoff. The actual compressed top GDS can be read and
    rendered again with KLayout from this package.

    Keep the evidence paths separate: application codes come from the coupled
    partition; the exported top is supported by its own geometry/connectivity
    and timing reports. This preserves the connection between circuit behavior
    and implementation artifacts without substituting one check for another.''')
    take('native-theory-verification')
    native_block('new-769a8093','runall-timing')
    take('physical-method','physical-reports','klayout-method','klayout-script','klayout-native')

    md('argument-conclusion',r'''<a id="argument-conclusion"></a>

    # 8. Close the argument using the measured decisions

    The design progressed through three independent checks: diagnose a failing
    physical ordering and isolate the load/PWM effects; validate a frozen
    conversion mapping on disjoint patterns; reconstruct an application from
    those measured transactions. The physical top contributes its own exported
    geometry, connectivity and constrained digital timing evidence.

    The next table is computed from the records rather than copied from the
    explanatory paragraphs. It verifies the calibration against the predeclared
    study protocol and connects every observation to the decision it supports.''')
    verdict=nbf.v4.new_code_cell('%%design_review argument-verdict\n'+textwrap.dedent(ARGUMENT_RESULTS).strip()+'\n',id='argument-verdict')
    verdict.metadata['automx_argument_analysis']=True;book.cells.append(verdict)
    take('results-method','results','takeaways')
    md('argument-appendix-implementation',r'''# Appendix A — reproducible orchestration and native artifact ledger

    The central argument ends above. The retained orchestration cells below show
    how the server experiments, report collection and final native artifact ledger
    are assembled. Their original code order is preserved, so the full native
    execution path still encounters every original code cell exactly once.''')
    native_block('combined-orchestration-appendix','runall-manifest')
    take('full-lab-inventory-guide','full-lab-inventory')
    md('argument-appendix-guides',r'''# Appendix B — retained introductory guides and source context

    These original text cells are kept for completeness. They document earlier
    reading routes and experiment introductions. Their Part I/Part II labels and
    section maps refer to the earlier arrangement; the eight-question roadmap at
    the top is the current reading order. No original cell or implementation has
    been removed to create the unified argument.''')
    for c in old.cells:
        if c.id not in used and c.id!='references':take(c.id)
    take('references')
    if used!=set(byid):raise ValueError('Not every original cell was retained')
    expected=[c.id for c in native if c.cell_type=='code']
    actual=[c.id for c in book.cells if 'automx_native_origin' in c.metadata and c.cell_type=='code']
    if expected!=actual:raise ValueError('Native execution dependencies were reordered')
    book.metadata['automx_review'].update(edition='unified_design_argument',
        retained_previous_cells=len(old.cells),argument_chapters=8,
        analysis_namespace='automx_design_review',native_code_order_preserved=True)
    nbf.validate(book)
    return book
