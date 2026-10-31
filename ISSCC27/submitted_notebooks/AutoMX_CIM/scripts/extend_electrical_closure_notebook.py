"""Preserve the full notebook and append a source-visible electrical/service study."""
from pathlib import Path
import argparse,ast,json
import nbformat as nb

FUNCTION_NOTES={
 'compact':'Elaborate every custom hierarchy with explicit port/node mapping, retain all PDK transistor leaves, verify 160-way MIM multiplicity, and emit the equivalent compact reference.',
 'completed_run_log':'Require the actual ngspice phase/completion marker and reject a truncated transcript.',
 'read_raw':'Parse ngspice vector names and numerical samples while retaining their native units.',
 'sample':'Interpolate a named measured vector at an explicitly specified time in seconds.',
 'sampling_witness':'Check measured high/low levels over a switching window; return the acquisition witness.',
 'control_block':'Generate the saved-vector and completion directives that make a native run inspectable.',
 'clean':'Normalize escaped Verilog/SPEF identifiers before matching physical connectivity.',
 'structural':'Read mapped cell models and pin-to-net connections; identify the driver of every output net.',
 'spef':'Read routed net connections, distributed capacitances and resistances into a common SI-unit representation.',
 'subcircuits':'Read transistor-cell port order and subcircuit bodies for the actual mapped-cell models.',
 'pin_caps':'Read input capacitances from Liberty to retain loads belonging to excluded quiet fanout cells.',
 'prepare':'Trace eight delivered-wordline cones, join child/parent RC, retain input loading, and measure propagated FF clock boundaries.',
 'deck':'Emit the transistor pulse experiment for one row, sign and activation code with its real physical loading.',
 'spice_worker':'Run the emitted pulse deck in shared ngspice, save requested raw vectors and require the full transient endpoint.',
 'SharedSpice.__init__':'Connect callbacks to the native simulator; retain source values, event times and the native transcript.',
 'SharedSpice.advance':'Advance analog time to the requested boundary, using fine steps around events and larger steps only during quiet intervals.',
 'bottom':'Compute differential CDAC bottom-plate voltages from the actual SAR trial state and capacitor weights.',
 'coupled_deck':'Connect compute/acquisition, conditioner, transistor comparator and CDAC bridge under one explicit electrical/timing profile.',
 'simulate':'Clock the live SAR RTL against measured transistor comparator decisions; record code, fresh EOC and supply waveforms.',
 'Session.__init__':'Create one native circuit session for a fixed process/supply/temperature condition and initialize its controls.',
 'Session.points':'Install a time/value waveform on an external electrical control source.',
 'Session.constant':'Drive a control source at a fixed electrical voltage for the next transaction.',
 'Session.configure':'Reprogram weight/activation controls and explicitly precharge/acquire/select the next measured conversion.',
 'get_session':'Reuse only a compatible fixed-condition native circuit session, avoiding repeated model startup.',
 'capture':'Measure the real integrated RTL phase/column schedule and START/EOC pins for six fixed application frames.',
 'case_key':'Normalize numeric representations into a stimulus identity so completed jobs can resume without duplicate acquisitions.',
 'Measurements.__init__':'Recover only readable, completed per-case native measurements from this experiment directory.',
 'Measurements.many':'Group compatible native jobs into bounded worker batches, retain per-case failures and return measured results in request order.',
 'profile':'Construct process, supply, temperature, core model and exact precharge/hold/select/START timing for one bank.',
 'case':'Construct a tagged two-row activation/weight transaction for one physical column.',
 'decode':'Apply upper-bound threshold lookup to a measured raw word and return its signed supported partial sum.',
 'replay':'Program real thresholds, replay native words through the MHA/readout, and check every request identity, timestamp and output.',
 'integrate':'Insert exact integration endpoints and integrate measured values over a named interval.',
 'measure_case':'Separate rail/reference energies into acquisition, conversion and whole-case windows from actual voltage/current samples.',
 'run_command':'Execute one native command, retain its complete transcript and reject a nonzero exit or explicit tool error.',
 'measure':'Generate output-checked routed-gate activity and estimate matched child-block power from Liberty/SPEF using OpenSTA 3.1.',
 'verify':'Run actual ngspice current/charge comparisons between 140 explicit MIMs and a parallel-multiplied subcircuit at TT, SS and FF conditions.',
 'group':'Group only identical MIM instances on the same terminal pair after the native multiplicity check passes; retain the physical-instance mapping.',
 'currents':'Solve internal resistor voltages with an independent sparse linear solver and return currents at all protected boundary nodes.',
 'reduce':'Eliminate storage-free internal resistor nodes, retain every device/C/interface terminal, and certify boundary-current equivalence before writing the reduced SPICE.',
 'native':'Run one native command to completion, retain the full transcript and return elapsed time after checking its exit status.',
 'build':'Construct the physical macro or its routing abstract from the declared inputs, check geometry/access, and return the view metadata used by integration.',
 'finish_views':'Check extracted ports and unique transistor LVS, then export the actual LEF and ordered distributed RC view.',
 'check_klayout':'Execute the independent bounded BEOL/off-grid rule deck and record its actual completed or timeout status.',
 'item':'Describe an existing file and size for the tool receipt without changing its contents.',
 'Flow.__init__':'Initialize the isolated physical experiment root, output map and completed-command receipts.',
 'Flow.run':'Execute a native tool command to completion, retain its transcript, and require declared output files before returning.',
 'render':'Export actual final-top overview/detail PNGs with fixed layer colors and compare two independently rendered overviews pixel for pixel.',
 'characterize':'Measure delivered-pulse width, voltage-time integral and peak from the numerical transient vectors.',
 'package':'Create a source/IP-view archive with functional checks, a declared frozen model fixture and retained upstream licenses.',
}

def function_table(source,description):
    rows=[]
    for node in ast.parse(source).body:
        methods=[(node.name,node)] if isinstance(node,ast.FunctionDef) else ([(node.name+'.'+m.name,m) for m in node.body if isinstance(m,ast.FunctionDef)] if isinstance(node,ast.ClassDef) else [])
        for name,method in methods:
            note=FUNCTION_NOTES.get(name)
            if note is None:
                assert name=='run',('Add a function explanation',name)
                note=description
            signature=ast.unparse(method.args).replace('|','&#124;')
            rows.append(f'| `{name}({signature})` | {note} |')
    return '\n\n| Function and parameters | Operation and downstream result |\n|---|---|\n'+'\n'.join(rows)

DESCRIPTIONS={
'parallel_mim':('scripts/group_parallel_mim.py','`verify` compares 140 explicit PDK MIM subcircuits with one parallel-multiplied instance at three electrical conditions. `group` combines only instances that share both terminals and every model parameter, preserving their parallel intrinsic resistor/capacitor behavior. The full extracted netlist and physical device inventory remain available; the compact simulation representation requires the declared zero-mismatch Monte Carlo switch.'),
'reduction':('scripts/reduce_pex_resistors.py','`reduce` eliminates only internal nodes attached exclusively to resistors. Every transistor, capacitor and interface terminal remains explicit. The star-to-mesh conductances preserve the network at those terminals; `currents` independently compares the original and reduced networks under eight boundary-voltage trials. This algebraic reduction removes solver nodes without replacing circuit responses or dropping physical capacitances.'),
'range_core':('scripts/build_physical_range_core.py','`build` draws a PDK MIM leaf, constructs the additional named bitline/ground geometry and emits its reference circuit. `finish_views` requires zero Magic DRC, complete ports and unique transistor LVS before exporting LEF and ordered distributed RC. `check_klayout` reports its independent bounded BEOL/off-grid check. `native` retains each completed tool transcript. Inputs are the original compute/acquisition source GDS and PDK; output is a newly built capacitor-loaded physical core, independently generated in this run.'),
'parent':('scripts/qualify_candidate_parent.py','`run` routes a fresh five-block parent using the selected source-matched readout/MHA views and newly built core. `Flow.run` records each completed tool command; `item` describes its file artifact. The checks include rails, extracted hierarchical TT timing, signal macro-boundary LVS and streamout geometry. Core transistor LVS belongs to the preceding macro experiment. This final physical parent supplies the RC and GDS used by the next pulse measurement and render.'),
'final_render':('scripts/render_closure_top.py','`render` writes the complete visible KLayout program, fixes the SKY130 layer palette, and creates final-top overview/detail images. Two independent overview exports must match every pixel. Inputs are this execution’s final parent GDS; outputs are PNGs, geometry/layer metadata and native transcripts.'),
'pwm_numerics':('scripts/verify_pwm_numerics.py','`characterize` measures width, voltage-time area and peak from actual vectors. `run` repeats four row/sign/size samples with finer transistor integration and compares the practical settings. The declared sampled tolerances concern numerical integration, not process yield or noise.'),
'waveforms':('scripts/flow2_waveforms.py','`read_raw` parses the actual ngspice time/vector records without replacing samples. `completed_run_log` checks the native completion marker, `sample` interpolates a named vector, `sampling_witness` checks a switching window, and `control_block` emits saved-vector directives. These helpers retain coordinate and unit information used by the following delivered-pulse measurement and V×I integrations. Input is a newly generated native raw file; output is named numerical arrays for contract/error/energy checks.'),
'physical':('scripts/measure_physical_pwm.py', 'The `structural`, `spef`, `subcircuits` and `pin_caps` readers reconstruct the mapped driver and its physical loading. `prepare` traces all eight wordline cones, keeps routed child/parent RC and obtains FF clock arrival/slew from STA. `deck`, `spice_worker` and `run` measure the transistor pulse and bound PWL reduction error to 2 mV. Inputs are source-matched netlist/SPEF/PDK and core-PEX loading; outputs are row/sign/magnitude waveforms, widths and contract checks for the next native conversion stage.'),
'worker':('scripts/qualified_cim_sar.py','`SharedSpice` supplies the live electrical bridge and limits integration steps near control boundaries. `coupled_deck` programs corner, supply, temperature, acquisition/hold/select timing and the measured pulse. `simulate` clocks the actual SAR RTL against transistor comparator decisions, checks a fresh EOC and stable word, and records supply currents. Inputs are a tagged ternary tile and timing/pulse profile; outputs are a native ADC word, decision trace and voltage/current waveform.'),
'stream':('scripts/qualified_cim_sar_stream.py','`Session.configure` reprograms weights and precharge/track/select/wordline controls between conversions while retaining one simulator process. `get_session` keeps operating conditions fixed within that process. `simulate` records each newly acquired conversion window. This reduces repeated model startup while preserving real circuit state and explicit reinitialization of each acquisition; no response table substitutes for the comparator/SAR loop.'),
'capture':('scripts/capture_readout_timing.py','`capture` runs six preselected activity frames through the real integrated RTL and records every phase/column precharge, launch, hold, select, START and EOC timestamp. It checks the observed ADC response in clocks, including the fixture detection cycle. Those 384 request records define the timing profiles used by the native application campaign.'),
'campaign':('scripts/run_electrical_qualification.py','`Measurements.many` launches bounded native batches and retains individual success/failure records. `profile` and `case` specify the electrical conditions and transaction. `run` measures 39 nominal levels in eight banks, freezes thresholds, then checks 96 same-sum checks (88 held-out patterns and eight anchor rechecks), 336 sampled PVT conversions, four settling policies and six activity frames. Each application request carries its actual RTL phase/column timing. Outputs are calibration, error/margin tables, native ADC words and tagged frame traces.'),
'replay':('scripts/replay_qualified_native_rtl.py','`replay` loads the newly measured thresholds and ADC words through the real MHA/readout. It checks every activation, weight mask, phase and column tag, corrects the fixture detection cycle, and compares actual precharge/launch/hold/select/START timestamps with each native case. Observed START-to-EOC must equal the rounded measured conversion duration; all six frame outputs must match.'),
'convergence':('scripts/verify_native_convergence.py','`run` independently pairs early/late, single-row/two-row core-PEX conversions with numerical shunts of 10^12 and 10^14 ohms and quiet timestep limits of 10 ns and 0.2 ns. It reports the raw-code difference; the sampled numerical bound is compared with the nominal decision margin rather than interpreted as noise or yield.'),
'energy':('scripts/analyze_conversion_energy.py','`integrate` interpolates exact interval endpoints before integrating measured V×I. `measure_case` separates acquisition, SAR START-to-EOC and whole-case windows and checks supply-energy consistency. `run` groups eight conversion windows into each four-output token projection. It keeps analog rails, reference-bridge work, controller/MHA estimates and idle ownership distinct.'),
'gatepower':('scripts/measure_clock_gating_power.py','`measure` generates fresh routed-gate VCDs for source-matched binary reference, isolated calibration-gated readout and digital attention. It programs real thresholds, checks native-backed output words and evaluates power with OpenSTA 3.1 and extracted RC. The comparison holds frames, response timing, supply and output readiness fixed; the warm measurement window is separate from boot and programming.'),
'clock':('scripts/check_calibration_clock_activity.py','`run` identifies all 3,648 threshold FF clock pins in the mapped netlists and counts their actual 0/1 VCD edges. This independent activity check catches a clock-based estimator that continues charging an inactive bank. Inputs are gate netlists/VCDs; outputs are weighted edge counts and a direct gating witness.'),
'attribution':('scripts/attribute_readout_power.py','`run` partitions routed readout instances into threshold data flops, clock distribution and remaining logic. It obtains disjoint OpenSTA per-instance power reports using the measured VCD. Group counts and sums expose the cost mechanism behind the clock-gating decision.'),
'comparison':('scripts/remeasure_activity_power.py','`run` uses one clock-aware OpenSTA version for linear, binary, isolated gated, digital and current-readout routed VCDs. It checks native-backed output equivalence and computes energy from each measured activity duration. The resulting table compares identical workloads and declares the child-digital ownership boundary.'),
'area':('scripts/measure_closure_area.py','`run` maps reference binary, isolated gated, current readout and upstream SAR digital control using the same Yosys/ABC image and TT Liberty. It reports actual mapped cell count/area, separately from analog macro footprint and the top rectangle.'),
'idle':('scripts/measure_idle_boot.py','`run` observes an unforced 8,192-clock mapped-readout boot and a retained idle interval. It also solves the always-biased transistor partition at the actual idle control levels and integrates the declared digital activity windows. Outputs identify cold, active, idle and reference-bridge terms for the sensor cadence.'),
'wake':('scripts/verify_idle_wake_service.py','`run` measures reset-to-ready, 304 accepted calibration writes and 16 weight-row transactions, then inserts six distinct retained idle intervals before real integrated RTL requests. It verifies every returned output. The measured programming times and payload sizes support calibration amortization without inventing a serial transport or CPU energy.'),
'service':('scripts/qualify_har_service.py','`run` freezes three validation-only corruption definitions, evaluates learned/uniform/identity controls, and links all 2,947 observed RTL outputs to software classification. It reconstructs 128-sample windows and measures 500 host preprocessing/embedding/head samples. The six class-selected examples retain classifier errors when hardware reproduces them correctly.'),
'second':('scripts/verify_second_configuration.py','`run` programs the unchanged IP for the existing retrained uniform-attention control by setting Q=0. Equal scores give exact 0.5/0.5 attention. It checks all frozen software predictions and six representative frames through four RTL paths, demonstrating a second supported configuration without retraining or changing the IP.'),
'quick':('scripts/quick_review.py','`run` recomputes the frozen deployment from input features on all test windows, verifies six frames per RTL path and reads the actual GDS hierarchy with KLayout. It counts this short check explicitly; training, native conversion and physical routing belong to Full Run All.'),
'package':('scripts/package_mha_ip.py','`package` exports the actual IP sources, numerical/protocol tests and source-matched macro views with their licenses. It builds a new source archive and an explicit inventory; no stored simulation responses are packaged as verification inputs. The next cell extracts and executes that archive in an isolated environment.'),
'clean':('scripts/verify_clean_ip_environment.py','`run` packages source-matched IP, extracts it outside the workspace, creates an isolated Python environment and installs the declared NumPy dependency. MHA, full-alphabet ternary and exhaustive decoder tests then execute from that extraction with no original-checkout import path.'),
'presentation':('scripts/summarize_electrical_closure.py','`run` reads the measured reports from this execution and regenerates six figures and four evidence tables. The figures connect ownership, pulse behavior, a real failure/recovery, cost, application outcome and sensor operation. Numerical comparisons retain their measurement/tool boundaries.')}

DESCRIPTIONS.update({
 'compact':('scripts/compact_core_reference.py','`compact` elaborates the complete hierarchical core into explicitly connected PDK leaves, then groups only identical parallel MIM intrinsic R-C models. Its local `emit` recursion maps each child port and namespaces each internal node; `node` preserves external pins and ground. A native 160-way multiplicity check at TT/SS/FF precedes writing the compact model. Input is the newly built full reference; output retains every transistor and intrinsic MIM R-C behavior with fewer solver nodes. MC0 means mismatch sampling is disabled. This is a reference schematic, with physical input loading and full PEX retained separately.'),
 'compact_native':('scripts/verify_compact_core_native.py','`run` creates four new native core/SAR jobs: zero and single-row input through the full hierarchical and compact reference. Its local `measure` executes the real SAR/comparator worker and reads the actual code and input voltage. The code difference bounds this sampled model comparison. The diagnostic ideal-400-ps stimulus is separate from final routed-PWM qualification.'),
 'routing_abstract':('scripts/build_core_routing_abstract.py','`build` preserves the original unchanged metal access interfaces, encloses the actual additional MIM geometry, and reserves its routing layers. It adds only an M5 ground access rectangle that KLayout verifies is covered by actual GDS metal. The validated transistor LVS establishes the internal ground network. The parent uses this access to connect its external rail while removing redundant parent PG stubs inside a hard-macro region containing no standard cells. PG means power/ground; native rail checks remain enabled. Inputs are the new physical views and original interface; output is the physical routing abstract, not a change to GDS. All cell function/source bodies appear below.')})

DESCRIPTIONS['candidate_eval']=('scripts/evaluate_routed_candidate.py','`run(root,pwm,core_views,work,jobs)` evaluates 28 fixed signed single-row inputs with the candidate’s actual delivered PWL and the declared compact transistor/MIM reference. `Measurements.many` executes the live analog comparator/real SAR loop; input sums are recorded only as reference labels. Missing pulses remain missing. The output table reports resolved raw codes and zero-input aliases. Only when the pulse gate passes, it acquires 312 calibration anchors and 96 fixed matched-sum cases, retaining invalid bank ordering instead of decoding through unsorted thresholds. The resulting decision can reject the candidate. It never bypasses the 64-case pulse or full-calibration adoption gates. PWL means piecewise-linear waveform; MIM means metal–insulator–metal capacitor.')
DESCRIPTIONS['export']=('scripts/export_current_measurements.py','`run(root,work,parent,render,electrical,evaluated=None)` copies the selected fresh-run GDS and deterministic overview/detail to `exports/`, records the actual native stimulus/counts in `LATEST_RUN.json`, and separately exports an evaluated candidate when present. GDS means Graphic Data System layout. Inputs are this run’s checked parent, render and native reports; outputs are the latest physical artifacts and a current-run measurement receipt. The headless runner separately audits complete notebook execution.')
DESCRIPTIONS['margin_budget']=('scripts/measure_margin_budget.py','`run(work)` reads the 96 measured same-sum cases, four settling policies and seven-condition transfer table. It computes each bank’s minimum observed raw-code guard, subtracts the worst additional sampled settling displacement and reports the remaining conditional guard. Noise/offset allocation is explicitly zero; this finite-pattern arithmetic budget is not a yield or ENOB claim. Inputs are this run’s native reports; outputs are `margin_budget.json` and the adjacent table used in the operating-policy discussion. ADC means analog-to-digital converter; TT means typical transistor corner; PVT means process, voltage and temperature.')

def prototype_profile(book,preserve_physical_sources=False):
    """Select the bounded, measured prototype study; retain every baseline cell."""
    omit=set() if preserve_physical_sources else {'parallel_mim','reduction','range_core','parent','pwm_numerics','compact','compact_native','routing_abstract','candidate_eval'}
    book.cells=[c for c in book.cells if not any(c.id=='closure-'+n+s for n in omit for s in ('-method','-source'))]
    cells={c.id:c for c in book.cells}
    cells['closure-pulse-method'].source='''<a id="closure-pulse"></a>
### Measure the electrical interface before interpreting a system result

The mapped-driver experiment measures all 64 row/sign/magnitude combinations with distributed child/parent RC and actual core-PEX input loading. The original binary reference supplies a six-code comparison. Every measured swing, edge count, width and bitline change is displayed, including failed checks. A short pulse lost in the routed driver invalidates a direct routed-PWM-to-calibration claim.

The following transistor/SAR campaign is a **timing-aligned ideal-50-ps stimulus experiment**. It uses the actual RTL precharge/hold/select/START schedule, live transistor comparator decisions and real SAR RTL. Its six-frame output result qualifies that stated partition. The independent delivered-pulse table shows whether the routed electrical interface meets it. Calibration clock gating is adopted on its own functional, physical and measured-power evidence; it does not repair pulse generation.'''
    cells['closure-pulse-run'].source='''_native_root=PRIORITY_WORK.parent/'full_native/full_native'
_manifest=json.loads((_native_root/'runall_manifest.json').read_text())
FINAL_PARENT={'outputs':{'gds':_manifest['views']['gds']}}
_parent_spefs=[Path(_manifest['views']['spef']['path'])]
_reference=CLOSURE_ROOT/'inputs/digital_benchmarks'
PWM_REFERENCE=CLOSURE_MODULES['physical'].run(CLOSURE_ROOT,_reference/'binary_reference',_reference/'reference_parent/timing/automx_cim_mixed_signal_proto.spef',CLOSURE_WORK/'pwm_reference',jobs=6,pilot=True)
PWM_FINAL=CLOSURE_MODULES['physical'].run(CLOSURE_ROOT,CLOSURE_ROOT/'inputs/digital_blocks/readout',_parent_spefs[0],CLOSURE_WORK/'pwm_final',jobs=8)
_checks=('zero_code_ok','nonzero_full_swing','single_pulse_ok','unselected_lines_quiet','strict_width_order','strict_bitline_order','bitline_polarity_ok')
print('Routed pulse qualification:', 'PASS' if all(PWM_FINAL[k] for k in _checks) else 'CONTRACT_FAILURE_MEASURED')
display(pd.DataFrame([{'check':k,'pass':PWM_FINAL[k]} for k in _checks]))
display(pd.DataFrame([{k:r[k] for k in ('row','negative','magnitude','width_ps','peak_v','rising_edges','bitline_differential_change_v')} for r in PWM_FINAL['measurements']]))
FINAL_RENDER=CLOSURE_MODULES['final_render'].render(CLOSURE_ROOT,FINAL_PARENT['outputs']['gds']['path'],CLOSURE_WORK/'final_top_render')
for _label in ('overview','detail'):display(Image(filename=FINAL_RENDER['images'][_label]))
'''
    cells['closure-native-method'].source='''<a id="closure-calibration"></a>
### Freeze calibration, test its transfer, then replay six activities

The ideal-50-ps pulse profile below isolates conversion, hold and calibration from the delivered-pulse discrepancy measured above. Measure 312 nominal anchors before 88 held-out decompositions and eight anchor rechecks. Seven transistor PVT conditions use five measured anchors and seven held-out patterns in four banks. The comparison of frozen TT thresholds with per-condition interpolation tests a calibration policy. Six first-occurring test frames, one per class, are fixed before circuit outcomes. Their 384 native ADC words are replayed through the real MHA/readout with request identities and timestamps checked.'''
    c=cells['closure-electrical-run']
    c.source=c.source.replace(",CLOSURE_WORK/'pwm_final/verification.json',jobs=8,core_pex=True,core_views=RANGE_CORE['views_dir']",',jobs=8,core_pex=False')
    cells['closure-convergence-run'].source=cells['closure-convergence-run'].source.replace(",pwm=CLOSURE_WORK/'pwm_final/verification.json',core_views=RANGE_CORE['views_dir']",'')
    for name in ('gating-run','service-run','reproduction-run'):
        cells['closure-'+name].source=cells['closure-'+name].source.replace(",core_views=RANGE_CORE['views_dir']",'').replace(",analog_views=RANGE_CORE['views_dir']",'')
    cells['closure-gating-run-method'].source=cells['closure-gating-run-method'].source.replace('The current-readout row additionally includes the adopted pulse construction.','The current-readout row is the adopted isolated calibration-gated implementation. The pulse measurement is an independent electrical check.')
    cells['closure-results-method'].source=cells['closure-results-method'].source.replace('They connect the delivered pulse and calibration policy to the output contract,','They show the measured routed-pulse discrepancy alongside the timing-aligned ideal-stimulus calibration/output contract,')
    cells['closure-results'].source+="\ndisplay(Markdown('**Sensor-duty accounting: measured disjoint terms**'))\ndisplay(pd.DataFrame(json.loads((CLOSURE_WORK/'sensor_duty_budget.json').read_text())))\n"
    for c in book.cells:
        if c.cell_type=='code':c.source=c.source.replace('reg [1023:0] folder','string folder')
        if c.id=='explain-standalone-runtime':
            c.source=c.source.split('\n\n`build_pulse_readout')[0]
        if c.id=='priority-power-run':
            c.source=c.source.replace("PRIORITY_WORK/'activity_power')","PRIORITY_WORK/'activity_power',clock_aware=True)")
        if c.id=='priority-summary-source':
            c.source='%%priority_module summary\n'+(Path(__file__).resolve().parent/'summarize_priority_implementation.py').read_text()
    return book

def append_candidate_evaluation(book,root):
    """Keep the qualified partition while measuring an independently rejected candidate."""
    root=Path(root);view=root/'inputs/electrical_candidate/readout'
    assert (view/'hardening.json').is_file() and (view/'source.sv').is_file()
    cells=[nb.v4.new_markdown_cell('''### Retest an electrical repair before adopting it

**Implementation:** Compare an explicit pulse-path repair with the qualified controller. The candidate uses matched reference/selected-delay mux paths and identical output-driver types, with row-local tap isolation/drive when present in its visible source. Its declared parent policy replaces only wordline buffer cones with stronger drivers before fresh routing; the source-matched physical views below are declared reusable hard IP. A new 160-MIM-per-bitline bank is generated with real geometry, Magic DRC, transistor LVS and extracted receiver loading. Route a fresh five-block candidate parent and measure all 64 loaded wordline/code combinations. Then drive 28 fixed signed single-row native cases with those exact PWL waveforms. A passing pulse gate additionally triggers 312 fresh calibration anchors and 96 matched-sum cases. A failed pulse, raw-code alias, invalid calibration ordering or held-out error rejects adoption; it cannot be repaired by a synthetic ADC answer.

**Inputs → outputs and downstream use:** The visible candidate RTL and frozen source-matched child views, original compute source and PDK generate a fresh enlarged macro, parent GDS/RC, delivered waveforms and live-SAR raw codes. Candidate results have their own `evaluated_candidate/` tree. They do not supply the separate ideal-50-ps calibration campaign or replace the selected ICG implementation. TT means typical transistor process; PDK means process design kit; RC means resistance and capacitance; LVS means layout-versus-schematic; DRC means design-rule check.''',id='closure-evaluated-candidate-method'),
        nb.v4.new_code_cell('CANDIDATE_READOUT_RTL = '+repr((view/'source.sv').read_text())+'''
assert (CLOSURE_ROOT/'inputs/electrical_candidate/readout/source.sv').read_text()==CANDIDATE_READOUT_RTL
print('Candidate source-bound physical views:',CLOSURE_ROOT/'inputs/electrical_candidate/readout')
''',id='closure-evaluated-candidate-source'),
        nb.v4.new_markdown_cell('''**Implementation:** Execute fresh macro generation, routing and electrical acquisition for the candidate. Native tool output reports actual checks; the tables retain both pass and rejection results. Render candidate overview/detail using the same fixed KLayout palette and independent repeated-image pixel check. The selected release remains determined by the independent full notebook audit.''',id='closure-evaluated-candidate-run-method'),
        nb.v4.new_code_cell('''EVALUATED_WORK=CLOSURE_WORK/'evaluated_candidate'
EVALUATED_WORK.mkdir(parents=True,exist_ok=False)
EVALUATED_CORE=CLOSURE_MODULES['range_core'].build(CLOSURE_ROOT,EVALUATED_WORK/'physical_range_core')
_candidate_view=CLOSURE_ROOT/'inputs/electrical_candidate/readout'
_candidate_report=json.loads((_candidate_view/'hardening.json').read_text())
for _key in ('source','gds','lef','odb','lib','mapped_netlist','spef'):_candidate_report[_key]=str(_candidate_view/_candidate_report[_key])
(EVALUATED_WORK/'hardening.json').write_text(json.dumps(_candidate_report,indent=2)+'\\n')
EVALUATED_PARENT=CLOSURE_MODULES['parent'].run(CLOSURE_ROOT,EVALUATED_WORK/'hardening.json',EVALUATED_WORK/'physical_parent',core_views=EVALUATED_CORE['views_dir'],upsize_wordline_buffers=_candidate_report.get('parent_wordline_drive_required',False))
EVALUATED_PWM=CLOSURE_MODULES['physical'].run(CLOSURE_ROOT,CLOSURE_ROOT/'inputs/electrical_candidate/readout',EVALUATED_WORK/'physical_parent/timing/automx_cim_mixed_signal_proto.spef',EVALUATED_WORK/'pwm',jobs=8,core_views=EVALUATED_CORE['views_dir'])
EVALUATED_NATIVE=CLOSURE_MODULES['candidate_eval'].run(CLOSURE_ROOT,EVALUATED_WORK/'pwm/verification.json',EVALUATED_CORE['views_dir'],EVALUATED_WORK/'native',jobs=8)
assert EVALUATED_NATIVE['native_unresolved']==0,EVALUATED_NATIVE['status']
EVALUATED_RENDER=CLOSURE_MODULES['final_render'].render(CLOSURE_ROOT,EVALUATED_PARENT['outputs']['gds']['path'],EVALUATED_WORK/'render')
display(pd.DataFrame([{k:r[k] for k in ('row','negative','magnitude','width_ps','peak_v','rising_edges','bitline_differential_change_v')} for r in EVALUATED_PWM['measurements']]))
display(pd.DataFrame(EVALUATED_NATIVE['single_row_codes']))
if EVALUATED_NATIVE['calibration']:
    display(pd.DataFrame([{'bank':i,'strict_calibration':EVALUATED_NATIVE['calibration']['strictly_increasing'][i],'minimum_adjacent_code_step':EVALUATED_NATIVE['calibration']['minimum_adjacent_code_step'][i],'matched_cases':sum(r['bank']==i for r in EVALUATED_NATIVE['matched_sum']),'decoded_cases':sum(r['bank']==i and 'decoded' in r for r in EVALUATED_NATIVE['matched_sum']),'decoded_wrong':(sum(r.get('decoded')!=r['expected'] for r in EVALUATED_NATIVE['matched_sum'] if r['bank']==i and r['bank_has_valid_ordered_calibration']) if EVALUATED_NATIVE['calibration']['strictly_increasing'][i] else None)} for i in range(8)]))
print('Candidate adoption:',EVALUATED_NATIVE['status'])
for _label in ('overview','detail'):display(Image(filename=EVALUATED_RENDER['images'][_label]))
''',id='closure-evaluated-candidate-run')]
    cells[-1].source+='''
_wire_rows=[]
for _variant,_directory in [('previous placement',CLOSURE_ROOT/'inputs/earlier_pulse_placement'),('adjacent placement',CLOSURE_ROOT/'inputs/electrical_candidate/readout')]:
    _logic,_=CLOSURE_MODULES['physical'].structural(next(_directory.glob('*.nl.v')))
    _rc=CLOSURE_MODULES['physical'].spef(next(_directory.glob('*.spef')))
    for _row in range(4):
        for _polarity in ('positive','negative'):
            _driver=_logic[f'pulse_generator[{_row}].{_polarity}_i']
            _net=_rc[_driver['pins']['X']]
            _wire_rows.append({'placement':_variant,'row':_row,'polarity':_polarity,'wire_capacitance_terms_fF':sum(c for a,b,c in _net['caps'])*1e15,'wire_resistance_terms_ohm':sum(v for a,b,v in _net['res'])})
(EVALUATED_WORK/'pulse_wire_loading.json').write_text(json.dumps(_wire_rows,indent=2)+'\\n')
display(pd.DataFrame(_wire_rows))
'''
    cells[0].source+='\n\nThe evaluated candidate places the pulse-forming gates next to their strong output drivers. Its earlier unclustered placement is retained as source-matched views under `inputs/earlier_pulse_placement`. This run retests the physical repair and then tests whether its calibration transfers across decompositions. A passed waveform is insufficient if raw-code intervals still overlap.'
    index=next(i for i,c in enumerate(book.cells) if c.id=='closure-native-method')
    book.cells[index:index]=cells
    return book

def build(root,output,profile='evaluated'):
    root=Path(root).resolve();book=nb.read(root/'AutoMX_CIM_Code_a_Chip.ipynb',4)
    original={c.id for c in book.cells};book.cells=[c for c in book.cells if not c.id.startswith('closure-')]
    def md(name,text):return nb.v4.new_markdown_cell(text,id='closure-'+name)
    def code(name,text):return nb.v4.new_code_cell(text,id='closure-'+name)
    chapter=[md('introduction','''<a id="electrical-closure"></a>
## Closing the electrical and application contracts

The design argument now tests the assumptions between its layers. A usable activation code must produce a delivered pulse; calibration must transfer between patterns and operating conditions; controller savings must survive actual clock activity; and a sensor decision must include programming, idle and host work. The following experiments retain the complete preceding laboratory and acquire new reports in this run's empty output directory.

Weights reside in controller registers. The eight-NMOS leaf implements product-dependent discharge; the SAR converts the acquired differential signal; the calibrated readout returns integer projections; the MHA IP computes attention/context and requests O. Feature extraction, embedding and the final class head execute in software.'''),
    md('sources-method','''**Implementation:** Register each visible source body as its actual module and write the same body to the native worker path. Definitions have their own namespace and the following run cells invoke those exact definitions. Full native transcripts stay beside the generated measurements; cell outputs show principal results and figures.

**Inputs → outputs and downstream use:** This notebook's source cells and the current fresh-run directory become executable workers and a new `electrical_closure/` report tree. Reusable hard-macro netlist/RC inputs are declared source-matched IP; circuit responses and candidate-top routing are newly acquired.'''),
    code('loader', '''from pathlib import Path
from IPython.core.magic import register_cell_magic
from IPython.display import display,Markdown,Image
import importlib,json,sys,types
import pandas as pd
CLOSURE_ROOT=PRIORITY_ROOT
CLOSURE_WORK=PRIORITY_WORK.parent/'electrical_closure'
CLOSURE_WORK.mkdir(parents=True,exist_ok=False)
CLOSURE_MODULES={}
CLOSURE_SOURCES='''+repr({name:path for name,(path,description) in DESCRIPTIONS.items()})+'''
@register_cell_magic
def closure_source(line,cell):
    name=line.strip();relative=CLOSURE_SOURCES[name];path=CLOSURE_ROOT/relative;path.write_text(cell)
    package=importlib.import_module('scripts');module=types.ModuleType('scripts.'+path.stem);module.__file__=str(path)
    sys.modules[module.__name__]=module;setattr(package,path.stem,module)
    exec(compile(cell,str(path),'exec'),module.__dict__);CLOSURE_MODULES[name]=module
    print('Source ready:',relative)
(CLOSURE_WORK/'flow_timer_start.json').write_text(json.dumps({'monotonic_start':FULL_LAB_START_MONOTONIC,'scope':'First code cell to final figure generation'},indent=2)+'\\n')
print('Electrical/service output directory:',CLOSURE_WORK)
''')]
    for name,(path,description) in DESCRIPTIONS.items():
        source=(root/path).read_text()
        chapter.extend([md(name+'-method','**Implementation:** '+description+function_table(source,description)),code(name+'-source','%%closure_source '+name+'\n'+source)])
    chapter.extend([
    md('timing-method','''<a id="closure-timing"></a>
### Establish the actual request schedule

The timer in a functional ADC fixture starts after START is detected; its parameter alone is not the elapsed conversion time. Measure the pin-to-pin interval. The last column also observes an older held sample than the first column, so each phase/column profile retains its own timestamps.'''),
    code('timing-run', '''CLOSURE_TIMING=CLOSURE_MODULES['capture'].capture(CLOSURE_ROOT,PRIORITY_WORK/'application',PRIORITY_WORK/'application_rtl/tb_application_binary.sv',CLOSURE_WORK/'control_timing_qualified')
display(pd.DataFrame(CLOSURE_TIMING['banks']))
'''),
    md('pulse-method','''<a id="closure-pulse"></a>
### Measure delivered activation pulses

The reference experiment and current candidate both use mapped SKY130 transistor drivers, distributed readout/parent RC and real core-PEX pin loading. The reference netlist/SPEF is a declared comparison fixture. The final parent is routed in this cell with the newly built MIM load bank. The smaller-capacitance prototype remains available in the preceding device-to-system laboratory. Calibration is regenerated for the adopted physical pulse and core. Compare zero-code quietness, nonzero swing, width ordering and the waveform actually delivered to the analog input.'''),
    code('pulse-run', '''RANGE_CORE=CLOSURE_MODULES['range_core'].build(CLOSURE_ROOT,CLOSURE_WORK/'physical_range_core')
_child_files=list(PRIORITY_WORK.parent.glob('**/digital_blocks/readout/hardening.json'))
assert len(_child_files)==1,_child_files
FINAL_PARENT=CLOSURE_MODULES['parent'].run(CLOSURE_ROOT,_child_files[0],CLOSURE_WORK/'physical_parent',core_views=RANGE_CORE['views_dir'])
_reference=CLOSURE_ROOT/'inputs/digital_benchmarks'
PWM_REFERENCE=CLOSURE_MODULES['physical'].run(CLOSURE_ROOT,_reference/'binary_reference',_reference/'reference_parent/timing/automx_cim_mixed_signal_proto.spef',CLOSURE_WORK/'pwm_reference',jobs=6,pilot=True,core_views=RANGE_CORE['views_dir'])
_parent_spefs=[CLOSURE_WORK/'physical_parent/timing/automx_cim_mixed_signal_proto.spef']
PWM_FINAL=CLOSURE_MODULES['physical'].run(CLOSURE_ROOT,CLOSURE_ROOT/'inputs/digital_blocks/readout',_parent_spefs[0],CLOSURE_WORK/'pwm_final',jobs=8,core_views=RANGE_CORE['views_dir'])
assert all(PWM_FINAL[k] for k in ('zero_code_ok','nonzero_full_swing','single_pulse_ok','unselected_lines_quiet','strict_width_order','strict_bitline_order','bitline_polarity_ok'))
PWM_NUMERICS=CLOSURE_MODULES['pwm_numerics'].run(CLOSURE_ROOT,CLOSURE_WORK/'pwm_final',CLOSURE_WORK/'pwm_numerics',jobs=4)
assert PWM_NUMERICS['status']=='PASS'
FINAL_RENDER=CLOSURE_MODULES['final_render'].render(CLOSURE_ROOT,FINAL_PARENT['outputs']['gds']['path'],CLOSURE_WORK/'final_top_render')
display(pd.DataFrame([{k:r[k] for k in ('row','negative','magnitude','width_ps','peak_v','rising_edges','bitline_differential_change_v')} for r in PWM_FINAL['measurements']]))
for _label in ('overview','detail'):display(Image(filename=FINAL_RENDER['images'][_label]))
'''),
    md('native-method','''<a id="closure-calibration"></a>
### Freeze calibration, challenge transfer, then replay six activities

Measure nominal calibration before the 88 held-out decompositions and eight explicit anchor rechecks. The seven PVT points use five measured anchors and seven held-out patterns in four banks; interpolation is evaluated as a model, separately from 39 directly measured nominal levels. PVT varies the transistor partition and scales the nominal delivered waveform voltage; the routed pulse-delay measurement is TT. The settling experiment keeps its scope explicit. Six first-occurring test frames, one per class, are fixed before circuit outcomes.'''),
    code('electrical-run', '''ELECTRICAL=CLOSURE_MODULES['campaign'].run(CLOSURE_ROOT,PRIORITY_WORK/'application',CLOSURE_WORK/'control_timing_qualified/control_timing.csv',CLOSURE_WORK/'electrical',CLOSURE_WORK/'pwm_final/verification.json',jobs=8,core_pex=True,core_views=RANGE_CORE['views_dir'])
assert ELECTRICAL['status']=='PASS',ELECTRICAL['status']
QUALIFIED_REPLAY=CLOSURE_MODULES['replay'].replay(CLOSURE_ROOT,PRIORITY_WORK/'application',CLOSURE_WORK/'electrical',PRIORITY_WORK/'application_rtl',CLOSURE_WORK/'native_replay')
_pvt=json.loads((CLOSURE_WORK/'electrical/pvt.json').read_text())
display(pd.DataFrame(_pvt['groups']))
display(pd.DataFrame(json.loads((CLOSURE_WORK/'electrical/settling.json').read_text())))
display(pd.DataFrame(ELECTRICAL['frames']))
'''),
    md('margin-budget-method','''**Implementation:** Turn calibration transfer and settling measurements into a raw-code guard budget. A decision guard is the number of ADC codes remaining before the neighboring programmed threshold. The minimum already includes the measured same-sum pattern spread. Subtract a conservative extra settling displacement and report the residual per bank; do not assume unmeasured stochastic noise or comparator offset. Keep the 16-clock policy in the matched power comparison even when a shorter wait passes the bounded electrical sweep.

**Inputs → outputs and downstream use:** Newly acquired `electrical/matched_sum.json`, `settling.json`, `pvt.json` and the campaign contract become `margin_budget.json`. The eight bank rows explain the supported calibration/settling policy beside the energy and application results.'''),
    code('margin-budget-run', '''MARGIN_BUDGET=CLOSURE_MODULES['margin_budget'].run(CLOSURE_WORK)
display(pd.DataFrame(MARGIN_BUDGET['banks']))
print('Sampled correct settling policies:',MARGIN_BUDGET['sampled_correct_settle_clocks'])
print('Retained matched-power policy:',MARGIN_BUDGET['retained_comparison_settle_clocks'],'clocks')
'''),
    md('convergence-run-method','''**Implementation:** Independently repeat the early/late core-PEX points using finer numerical settings, then integrate the newly measured conversion windows. A token projection contains eight conversions; the table labels the sum of those windows rather than treating repeated acquisition intervals as a continuous-frame energy measurement.'''),
    code('convergence-run', '''CONVERGENCE=CLOSURE_MODULES['convergence'].run(CLOSURE_ROOT,CLOSURE_WORK/'numerical_convergence',jobs=8,pwm=CLOSURE_WORK/'pwm_final/verification.json',core_views=RANGE_CORE['views_dir'])
assert CONVERGENCE['status']=='PASS'
CONVERSION_ENERGY=CLOSURE_MODULES['energy'].run(CLOSURE_WORK/'electrical',CLOSURE_WORK/'conversion_energy')
display(pd.DataFrame([CONVERSION_ENERGY['mean_conversion_nj'],CONVERSION_ENERGY['mean_projection_conversion_nj']],index=['one conversion window','eight-window token projection']))
'''),
    md('gating-run-method','''<a id="closure-cost"></a>
### Attribute cost and test calibration clock gating

Use a characterized integrated clock-gating cell for the threshold data bank. Compare its actual routed clock activity and output-equivalent native-backed workload with the programmable binary reference. A matched tool version is essential: clock activity must remain visible to the power estimator. The current-readout row additionally includes the adopted pulse construction.'''),
    code('gating-run', '''MATCHED_ACTIVITY=PRIORITY_MODULES['power'].measure(CLOSURE_ROOT,CLOSURE_WORK,CLOSURE_WORK/'matched_activity_power',clock_aware=True)
GATING=CLOSURE_MODULES['gatepower'].measure(CLOSURE_ROOT,CLOSURE_WORK,CLOSURE_WORK/'gating_power',CLOSURE_ROOT/'inputs/digital_benchmarks/calibration_gated/hardening.json',CLOSURE_ROOT/'inputs/digital_benchmarks/binary_reference/hardening.json')
CLOCK_ACTIVITY=CLOSURE_MODULES['clock'].run(CLOSURE_WORK/'gating_power',CLOSURE_WORK/'clock_activity')
ATTRIBUTION=CLOSURE_MODULES['attribution'].run(CLOSURE_ROOT,CLOSURE_WORK/'gating_power',CLOSURE_WORK/'power_attribution_sta3')
COST_COMPARISON=CLOSURE_MODULES['comparison'].run(CLOSURE_ROOT,CLOSURE_WORK/'matched_activity_power',CLOSURE_WORK/'gating_power',CLOSURE_WORK/'clock_aware_power')
AREA=CLOSURE_MODULES['area'].run(CLOSURE_ROOT,CLOSURE_WORK/'controller_adc_area',core_views=RANGE_CORE['views_dir'])
display(pd.DataFrame([{'variant':r['variant'],'latency_us':r['activity_window_s']/r['frames']*1e6,'child_digital_nJ/frame':r['child_digital_energy_per_frame_j']*1e9,'mismatches':r['gate_output_mismatches']} for r in COST_COMPARISON['results']]))
display(pd.DataFrame(AREA['designs']))
display(pd.DataFrame(AREA['routed_standard_cells']))
display(pd.DataFrame(AREA['physical_macros']))
'''),
    md('service-run-method','''<a id="closure-service"></a>
### Operate at a sensor cadence and change the resident configuration

Measure unforced boot, accepted programming traffic and retained-state idle wake. A separate mapped-readout VCD window measures 304 threshold writes and the four resident O-stage masks; its energy belongs to readout storage/control, while the MHA configuration interface is timed independently. The analog bias remains active. Validation corruption controls are fixed before evaluation; no test-subject retuning is performed. The second deployment uses equal attention probabilities through Q=0 on the same IP. Host feature/embedding/head latency, RTL latency and reference/analog ownership remain separate terms.'''),
    code('service-run', '''IDLE=CLOSURE_MODULES['idle'].run(CLOSURE_ROOT,PRIORITY_WORK/'application',CLOSURE_WORK/'idle_boot',core_views=RANGE_CORE['views_dir'],native=CLOSURE_WORK/'native_replay')
WAKE=CLOSURE_MODULES['wake'].run(CLOSURE_ROOT,PRIORITY_WORK/'application',PRIORITY_WORK/'application_rtl/tb_application_binary.sv',CLOSURE_WORK/'idle_wake_service')
SERVICE=CLOSURE_MODULES['service'].run(CLOSURE_ROOT,PRIORITY_WORK/'application',PRIORITY_WORK/'application_rtl',CLOSURE_WORK/'application_service')
SECOND_CONFIG=CLOSURE_MODULES['second'].run(CLOSURE_ROOT,PRIORITY_WORK/'application',CLOSURE_WORK/'second_configuration')
display(pd.DataFrame(SERVICE['validation_challenges'])[['challenge','model','windows','accuracy','macro_f1']])
display(pd.DataFrame(IDLE['digital']))
display(pd.DataFrame([{'boot_us':WAKE['cold_boot_ns']/1000,'calibration_us':WAKE['calibration_ns']/1000,'configuration_us':WAKE['configuration_ns']/1000,'analog_idle_mW':IDLE['analog_idle_dc']['monitored_w']*1000}]))
'''),
    md('reproduction-run-method','''<a id="closure-reproduction"></a>
### Execute the declared short check and the extracted IP

The short command recomputes frozen predictions, checks six class-selected RTL frames per path and inspects GDS hierarchy. A separate extraction uses an isolated Python environment and the declared host Icarus dependency. Full Run All performs the fresh circuit and physical acquisitions; these smaller checks expose their actual coverage and runtime.'''),
    code('reproduction-run', '''QUICK_REVIEW=CLOSURE_MODULES['quick'].run(CLOSURE_ROOT,CLOSURE_WORK/'quick_review',gds=_parent_spefs[0].parent.parent/'streamout/automx_cim_mixed_signal_proto.gds')
CLEAN_IP=CLOSURE_MODULES['clean'].run(CLOSURE_ROOT,CLOSURE_WORK/'clean_environment',analog_views=RANGE_CORE['views_dir'])
display(pd.DataFrame([{'check':'short review','elapsed_s':QUICK_REVIEW['elapsed_s'],'software_windows':QUICK_REVIEW['software_windows'],'rtl_frames_per_path':6},{'check':'isolated IP','elapsed_s':CLEAN_IP['elapsed_s'],'software_windows':None,'rtl_frames_per_path':None}]))
'''),
    md('results-method','''<a id="closure-evidence"></a>
### Read the measured design argument

The figures and four tables are regenerated from this execution's reports. They connect the delivered pulse and calibration policy to the output contract, then show the controller cost, application outcome and operating cadence. The complete device-to-layout laboratory remains above.'''),
    code('results', '''CLOSURE_PRESENTATION=CLOSURE_MODULES['presentation'].run(CLOSURE_ROOT,PRIORITY_WORK,CLOSURE_WORK)
for _picture in CLOSURE_PRESENTATION['figures']:display(Image(filename=_picture))
for _table in CLOSURE_PRESENTATION['tables']:
    display(Markdown('**'+_table.replace('_',' ').capitalize()+'**'))
    display(pd.DataFrame(json.loads((CLOSURE_WORK/(_table+'.json')).read_text())))
''')])
    i=next(i for i,c in enumerate(book.cells) if c.id=='references');book.cells[i:i]=chapter
    argument=md('design-argument','''## Design decisions and application value

The implemented coprocessor handles two tokens, four channels and two attention heads. Four programmable ternary projections, Q/K/V/O, reuse the same four-row/four-column compute macro and SAR path. The MHA controller keeps scores, probability approximation and context arithmetic in RTL. A software host extracts features from the 128-sample wearable window, creates the token embedding and classifies the returned attention output.

| Decision | Engineering question | Measurement that determines the choice |
|---|---|---|
| Differential, register-programmed compute | Can signed products be acquired and interpreted as the required integer partial sums? | MOS branch/sign checks, calibration ordering, held-out same-sum patterns, actual SAR words and request-tagged replay. |
| Shared calibrated converter/readout | Can one analog path serve all four projections with a consistent interface? | Phase/column hold age, START/EOC timing, six fixed native-backed frames and programmed-threshold decoding. |
| Calibration clock gating | Does a reusable programmable controller spend unnecessary energy retaining thresholds? | Actual threshold-clock edges, output-equivalent routed VCDs, disjoint instance power and mapped area. |
| Wearable attention deployment | Does the numerical contract survive a useful task and another resident configuration? | Subject-disjoint HAR predictions, quantization/control baselines, validation-only sensor challenges, boot/programming/idle/wake and host timing. |

The value demonstrated here is a measured, reusable CIM–SAR–MHA interface and a verified controller improvement. The same-workload serial ternary digital baseline is retained in every cost comparison. At this small array size its speed and child-digital energy are strong; the notebook measures that tradeoff rather than presuming an analog advantage. A correct hardware output may still produce an application classification error, so output equivalence and task accuracy are counted separately.''')
    if profile in ('routed','qualified'):
        argument.source+='''\n\nThe analog sizing follows $\\Delta V_{BL}\\approx\\int I_{cell}(t)dt/C_{BL}$: delivered pulse duration, cell current and bitline capacitance jointly determine range. The routed pulse unit is targeted near 0.42 ns, rather than the earlier ideal 50 ps diagnostic. Increasing the physical bitline bank from 20 to 160 identical MIM units per node keeps charge-induced swing in range while the measured tap table restores proportional pulse duration. The eight hold capacitors remain separate. The flow rebuilds this geometry and measures its area, then freezes 39-level calibration before held-out patterns. This range repair and its area cost are evaluated separately from calibration-data clock gating.'''
    book.cells.insert(4,argument)
    intro=md('review-route','''## Review in five minutes

Read the [electrical contract and delivered pulse](#closure-pulse), [calibration failure/recovery](#closure-calibration), [matched controller cost](#closure-cost), [sensor service and second configuration](#closure-service), then [the six evidence figures and four tables](#closure-evidence). The complete preceding laboratory and visible source implementations supply the detailed derivation. [Short and extracted-IP checks](#closure-reproduction) report their own coverage.''')
    book.cells.insert(4,intro)
    first_code=next(i for i,c in enumerate(book.cells) if c.cell_type=='code')
    book.cells[first_code:first_code]=[md('execution-clock-method','**Implementation:** Record the actual Python interpreter and the execution start clock. The final runtime table measures the full laboratory through figure generation; the headless runner independently audits cell coverage and completion.'),code('execution-clock',"import time,sys\nFULL_LAB_START_MONOTONIC=time.monotonic()\nprint('Python:',sys.executable)\n")]
    # Synchronize the visible early source binding only after the qualified RTL is adopted.
    for c in book.cells:
        if c.id=='priority-power-source':c.source='%%priority_module power\n'+(root/'scripts/measure_activity_power.py').read_text()
        if c.id=='priority-decoder-source':c.source='%%priority_module decoder\n'+(root/'scripts/verify_binary_decoder.py').read_text()
        if c.id=='standalone-runtime':
            c.source='%%standalone_runtime\n'+(root/'scripts/standalone_runtime.py').read_text()+"\nprint('Native flow runtime and hard-macro construction ready',flush=True)\n"
        if c.id=='explain-standalone-runtime':
            c.source+='\n\n`build_pulse_readout(root, source, work)` constructs the local-launch pulse implementation when that source is selected: protect its physical delay cells, place the delay line at legal row sites around well taps, synthesize the clock trees, size high-fanout data buffers, route and check the extracted block. Inputs are the visible readout RTL and pinned process/tool inputs; outputs are its netlist, GDS/LEF/ODB, RC and power/timing reports. The frozen source-matched views are reusable inputs; an RTL change invokes construction again.'
        if c.id=='priority-costs-source':c.source='%%priority_module costs\n'+(root/'scripts/measure_priority_costs.py').read_text()
        if c.id=='priority-readout-source':
            a=c.source.index('READOUT_RTL = ');b=c.source.index('\nfrom pathlib',a)
            c.source=c.source[:a]+'READOUT_RTL = '+repr((root/'rtl/automx_cim_readout_seq.sv').read_text())+c.source[b:]
        if c.id=='priority-readout-contract' and 'wire [72:0] tap;' in (root/'rtl/automx_cim_readout_seq.sv').read_text():
            if 'reference_low_i' in (root/'rtl/automx_cim_readout_seq.sv').read_text():
                c.source+='\n\nThe adopted pulse construction uses a regular 72-buffer line with isolated tap drivers. Matched reference and selected-delay mux paths form the two pulse edges, followed by identical static-enable gates and output-driver types for all eight signed wordlines. Magnitude selection is stable before launch. Each row’s isolated tap inputs are placed near their physical delay stages; local strong buffers carry the mux wiring. The parent’s eight wordline buffer cones use the declared stronger-driver policy. Actual propagated clock boundaries, route and receiver loading determine delivered duration and charge. Threshold data clocks use the characterized ICG only for accepted writes; reset, validity and request control retain their regular clocks.'
            else:
                c.source+='\n\nThe adopted pulse construction gives the common launch FF one delay-line load. Twelve local launch-reference FFs feed stronger pulse gates; a regular 72-buffer line uses a fixed, physically motivated tap-selection table for the supported magnitudes. Actual propagated clock boundaries and routed loading determine delivered widths. Threshold data clocks use a characterized integrated clock-gating cell only on accepted calibration writes; validity/reset and protocol state keep their regular clocks.'
        if c.id=='references':
            c.source=c.source.replace('including the hierarchical gate-netlist checks used here.','including the hierarchical gate-netlist checks used here. The activity comparison uses the pinned OpenSTA 3.1.0 build recorded in `tools/opensta_current/tool.json` and `read_vcd`; clock-activity checks independently verify the gated threshold bank.')
            if 'archive.ics.uci.edu/dataset/240' not in c.source:
                c.source=c.source.replace('The CIM transistor topology,','**[16]** <a id="ref-16"></a>J. Reyes-Ortiz et al., [*Human Activity Recognition Using Smartphones*, UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones), 2013, DOI 10.24432/C54S4K, CC BY 4.0. Sensor windows, official subject-disjoint test split and retained dataset attribution are supplied under `data/`.\n\nThe CIM transistor topology,')
    if profile in ('prototype','evaluated'):
        book=prototype_profile(book,preserve_physical_sources=profile=='evaluated')
        if profile=='evaluated':
            book=append_candidate_evaluation(book,root)
    else:
        cells={c.id:c for c in book.cells}
        cells['closure-electrical-run'].source=cells['closure-electrical-run'].source.replace('jobs=8,core_pex=True','jobs=8,core_pex=False')
        cells['closure-convergence-run'].source=cells['closure-convergence-run'].source.replace("core_views=RANGE_CORE['views_dir'])","core_views=RANGE_CORE['views_dir'],core_pex=False)")
        cells['closure-convergence-run-method'].source='''**Implementation:** Pair the declared compact transistor reference under finer numerical shunts/timesteps, then integrate the new measured conversion windows. Intrinsic MIM R-C is retained; routed driver/parent RC and receiver loading are measured separately. This is a transistor/SAR partition with actual delivered PWL input, rather than a complete internal-wire PEX co-simulation. A token projection contains eight conversions; its table sums those START–EOC windows.'''
        cells['closure-pulse-method'].source+='\n\nThe added bitline bank preserves full-scale range for the delivered pulse. Its original hierarchy and exact compact intrinsic MIM R-C representation are checked through the live SAR loop before use. The controller tap table is a characterized design parameter; this cell retests the implemented result over all rows, signs and supported magnitudes. Parent supply cleanup removes only redundant parent PG shapes inside the hard core, preserves the core rails, and requires actual power checks.'
        cells['closure-gating-run-method'].source=cells['closure-gating-run-method'].source.replace('The current-readout row additionally includes the adopted pulse construction.','The current-readout row includes the physically characterized pulse construction; the isolated gating row remains the controlled intervention.')
    if profile=='qualified':
        book=append_candidate_evaluation(book,root)
        _prior_ids={'closure-evaluated-candidate-method','closure-evaluated-candidate-source','closure-evaluated-candidate-run-method','closure-evaluated-candidate-run'}
        _prior=[c for c in book.cells if c.id in _prior_ids]
        book.cells=[c for c in book.cells if c.id not in _prior_ids]
        _position=next(i for i,c in enumerate(book.cells) if c.id=='closure-pulse-method')
        book.cells[_position:_position]=_prior
        _by_id={c.id:c for c in book.cells}
        _by_id['closure-evaluated-candidate-method'].source+='\n\nThis retained reference uses the same RTL as the selected readout and the previous physical placement. Both variants share this one newly generated bitline macro. The following selected-parent experiment tests the gate/driver placement repair with all 64 waveforms, live SAR calibration, held-out patterns and six complete native-backed frames.'
        _pulse=_by_id['closure-pulse-run']
        _pulse.source=_pulse.source.replace("RANGE_CORE=CLOSURE_MODULES['range_core'].build(CLOSURE_ROOT,CLOSURE_WORK/'physical_range_core')","RANGE_CORE=EVALUATED_CORE\n(CLOSURE_WORK/'physical_range_core').symlink_to(Path(EVALUATED_CORE['views_dir']).parent,target_is_directory=True)")
        _pulse.source+='''\n_wire_rows=[]
for _variant,_directory in [('previous placement',CLOSURE_ROOT/'inputs/electrical_candidate/readout'),('selected placement',CLOSURE_ROOT/'inputs/digital_blocks/readout')]:
    _logic,_=CLOSURE_MODULES['physical'].structural(next(_directory.glob('*.nl.v')))
    _parasitics=CLOSURE_MODULES['physical'].spef(next(_directory.glob('*.spef')))
    for _row in range(4):
        for _polarity in ('positive','negative'):
            _driver=_logic[f'pulse_generator[{_row}].{_polarity}_i']
            _net=_parasitics[_driver['pins']['X']]
            _wire_rows.append({'variant':_variant,'row':_row,'polarity':_polarity,'wire_capacitance_terms_fF':sum(c for a,b,c in _net['caps'])*1e15,'wire_resistance_terms_ohm':sum(r for a,b,r in _net['res'])})
(CLOSURE_WORK/'pulse_wire_loading.json').write_text(json.dumps(_wire_rows,indent=2)+'\\n')
display(pd.DataFrame(_wire_rows))
'''
        _by_id['closure-pulse-method'].source+='\n\nThe pulse-forming gate and its strong output driver are placed together. The output-net table is derived from actual child SPEF terms before and after the physical repair; receiver waveform measurement determines acceptance. Capacitance terms exclude cell-input capacitance, and use the declared quiet-neighbor policy. The reused negative placement is a measured reference, not the selected final top.'
    if profile in ('qualified','evaluated'):
        _parallel={c.id:c for c in book.cells}
        _parallel['priority-module-loader'].source+='\nimport os\nPRIORITY_JOBS=min(16,os.cpu_count() or 1)\nprint("Application acquisition workers:",PRIORITY_JOBS)\n'
        _parallel['priority-native-run'].source=_parallel['priority-native-run'].source.replace('jobs=8','jobs=PRIORITY_JOBS')
        _parallel['closure-loader'].source=_parallel['closure-loader'].source.replace('import importlib,json,sys,types','import importlib,json,sys,types,os')
        _parallel['closure-loader'].source+='\nCLOSURE_JOBS=min(16,os.cpu_count() or 1)\nprint("Electrical measurement workers:",CLOSURE_JOBS)\n'
        for _cell in book.cells:
            if _cell.cell_type=='code' and _cell.id.startswith('closure-') and _cell.id.endswith('-run'):
                _cell.source=_cell.source.replace('jobs=8','jobs=CLOSURE_JOBS')
    cells={c.id:c for c in book.cells}
    cells['closure-results-method'].source+='\n\nThe final cell exports the selected current-run GDS and renderings to `exports/`, with its actual stimulus and measurement counts in `LATEST_RUN.json`. A rejected candidate has separate filenames and does not replace the selected top. Independent whole-notebook coverage/audits are recorded after execution.'
    cells['closure-results'].source+="\nCURRENT_EXPORT=CLOSURE_MODULES['export'].run(CLOSURE_ROOT,CLOSURE_WORK,FINAL_PARENT,FINAL_RENDER,ELECTRICAL,evaluated=globals().get('EVALUATED_WORK'))\n"
    for c in book.cells:
        if c.cell_type=='code':c.source=c.source.replace('reg [1023:0] folder','string folder')
        if c.id=='explain-standalone-runtime':
            c.source+='\n\n`normalize_single_connected_power_label` renames a sole occupied supply node when the canonical label is unused. It merges no electrical nodes; multiple occupied aliases remain rejected. This handles extraction label selection while preserving the independently checked rail and signal connectivity.'
    import importlib.util
    spec=importlib.util.spec_from_file_location('automx_icg_audit_cells',root/'scripts/append_icg_timing_audit.py')
    audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    index=next(i for i,c in enumerate(book.cells) if c.id=='closure-results-method')
    book.cells[index:index]=audit.make_cells(root)
    assert original<={c.id for c in book.cells}
    nb.validate(book);nb.write(book,output)
    print(json.dumps({'output':str(output),'cells':len(book.cells),'code_cells':sum(c.cell_type=='code' for c in book.cells),'preceding_cell_ids_retained':len(original)},indent=2))
    return output

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path);p.add_argument('--profile',choices=['prototype','routed','evaluated','qualified'],default='evaluated');a=p.parse_args();build(a.root,a.output or a.root/'AutoMX_CIM_Code_a_Chip.closure.ipynb',a.profile)
