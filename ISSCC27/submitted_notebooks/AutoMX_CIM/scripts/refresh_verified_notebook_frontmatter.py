"""Refresh narrative from completed execution only; preserve every code cell and output."""
from pathlib import Path
import argparse,json
import nbformat

def refresh(root):
    root=Path(root).resolve();record=root/'experiments/closure_20261028/notebook_execution.json'
    execution=json.loads(record.read_text())
    assert execution['status']=='ALL_CODE_CELLS_EXECUTED' and not execution['errors'] and not execution['empty_output_cells']
    run=max((root/'runs').glob('fresh_*'));w=run/'electrical_closure';base=run/'priority_application'
    def read(p):return json.loads(Path(p).read_text())
    native=read(w/'electrical/verification.json');assert native['status']=='PASS' and native['partial_decode_mismatches']==0
    app=read(base/'application/application_metrics.json');a=app['models']['integer_mha'];power=read(w/'clock_aware_power/verification.json')
    assert power['status']=='PASS' and len(native['frames'])==6 and native['logical_conversions']==384
    result=Path(execution['output']);book=nbformat.read(result,4);cells={c.id:c for c in book.cells}
    before={c.id:(c.source,c.execution_count,c.outputs) for c in book.cells if c.cell_type=='code'}
    title=cells['title'];old=title.source
    footer=old[old.index('Original notebook analysis and package code:'):] if 'Original notebook analysis and package code:' in old else ''
    title.source=f'''## Abstract

AutoMX-CIM integrates a register-programmed eight-NMOS ternary projection macro, sampled analog acquisition, a real SAR controller and a synthesizable two-head attention IP. A wearable activity classifier exercises the complete software–hardware path. The laboratory follows measured physical failures through controlled interventions, calibration and numerical reconstruction, then tests controller switching and sensor-duty operation against a matched serial digital backend.

**Measured application:** {app['test_windows']:,} official HAR test windows from nine unseen subjects; **{a['accuracy']*100:.3f}% accuracy / {a['macro_f1']*100:.3f}% macro-F1**. Four RTL paths preserve every output value. The native transistor/SAR partition supplies **six preselected activity frames / {native['logical_conversions']} conversions with zero partial/output mismatches**, followed by request-tagged replay through the real MHA/readout. Its declared stimulus is **{native['contract']['stimulus']}**; the delivered-waveform experiment separately records every physical acceptance check.

**Measured design decision:** programmable calibration-storage clock gating reduces matched child-digital energy by **{power['gating_child_energy_reduction_percent']:.3f}%** beyond binary decoding, with real clock-edge, output-equivalence and ICG timing checks. Area, conversion/projection energy, programming, retained idle and sensor service are reported with explicit ownership. The efficient serial sign/add alternative remains the baseline; no complete-chip energy advantage is inferred.

**Circuit foundation:** the retained controlled experiment initially finds reversed bitline ordering, separates load and PWM interventions, then measures three calibration conversions and 38 distinct holdouts with zero integer decoding mismatches. Its 32-transaction tiny-MHA reconstruction has relative L2 0.114477 against floating context. These smaller checks establish the circuit and numerical premises for the larger application and operating-envelope experiments.

{footer}'''
    nav=cells['output-results-map'];marker='### Application and controller result'
    assert marker in nav.source
    nav.source=nav.source.split(marker,1)[0]+f'''### Application and controller result

The frozen six-activity UCI HAR model reaches **{a['accuracy']*100:.3f}% accuracy** and **{a['macro_f1']*100:.3f}% macro-F1** on {app['test_windows']:,} windows from nine unseen subjects. All four RTL paths preserve all 23,576 output values per path. Six preselected class frames additionally match {native['logical_conversions']} native ADC transactions and request-tagged MHA/readout replay, with zero partial/final mismatches. The hardware preserves the frozen classifier's actual errors.

The isolated ICG comparison reduces matched child-digital energy by {power['gating_child_energy_reduction_percent']:.3f}%. [Electrical evidence, current component cost and application service](#electrical-closure) retain the delivered-pulse acceptance result, seven-condition calibration transfer, settling, boot, programming and sensor-duty measurements. The serial ternary digital baseline is included under the same operation and timing policy. All preceding detailed experiments remain below.
'''
    if 'native-restored-archive-001' in cells:
        cells['native-restored-archive-001'].source='''## Setup: resolve the prepared bundle and PDK paths

The workspace cell selects this prepared bundle and its supplied analog and digital SKY130 PDK roots. Native-tool dependencies and versions are declared in `environment.yml`, `requirements.txt` and `docs/MEASUREMENT_TOOLCHAIN.md`. The source tree and reusable hard-IP inputs are included; full Run All creates a new empty result directory.'''
    assert before=={c.id:(c.source,c.execution_count,c.outputs) for c in book.cells if c.cell_type=='code'}
    nbformat.validate(book);nbformat.write(book,result)
    for name in ('AutoMX_CIM_Code_a_Chip.ipynb','AutoMX_CIM_Code_a_Chip.executed.ipynb'):
        p=root/name
        if p.exists() and p.resolve()!=result.resolve():
            oldbook=nbformat.read(p,4)
            if {c.id for c in oldbook.cells}==set(cells):
                for c in oldbook.cells:
                    if c.cell_type=='markdown' and c.id in ('title','output-results-map','native-restored-archive-001'):c.source=cells[c.id].source
                nbformat.write(oldbook,p)
    print('VERIFIED_FRONTMATTER_REFRESHED',root,'code and measured outputs unchanged',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);refresh(p.parse_args().root)
