#!/usr/bin/env python3
"""Fast native TT core-RC plus schematic-conditioner coupling experiment.

Both blocks share real held nodes (no ideal held-node voltage drivers).
ADC is explicitly a 2pF/input load stand-in; no conversion word is claimed.
"""
from pathlib import Path
import argparse
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import flow2_integration_common as common
from scripts import flow2_live_spice as live
from scripts import flow2_waveforms as waves
from scripts import run_flow2_core_tap_transient as pilot
from scripts import flow2_wrapper_design as design


def bench(model, core, condition, case='pair_a', selected=2):
    if selected not in range(4) or case not in ('zero', 'pair_a', 'pair_b'):
        raise ValueError('known stimulus and one-hot column required')
    text = pilot.nominal_deck(model, core, 'pex', case)
    # Preserve the circuit/stimulus. Widen only the integration ceiling and
    # run long enough to observe the follower/mux after physical S/H turnoff.
    text = text.split('.control\n', 1)[0]
    text = text.replace('.tran 5p 16n', '.tran 50p 80n 0 200p')
    text = text.replace('p 20n)', 'p 1000n)')
    text = text.replace('.save ', '* core save list: ')
    nodes = ['0' if p == 'VGND' else p for p in design.COND_PINS]
    extra = ['.include "'+str(condition)+'"', 'XCOND '+' '.join(nodes)+' '+design.COND]
    extra += ['VSEL'+str(c)+' SEL'+str(c)+' 0 '+('1.8' if c == selected else '0') for c in range(4)]
    extra += ['CLOADP AINP 0 2p', 'CLOADN AINN 0 2p']
    vectors = ['v('+p+')' for p in (*pilot.core.acq.PINS[:16], 'TRACK_B', 'TRACK_N',
                                      'AINP', 'AINN', 'BIAS_MON')]
    vectors += ['i(VVDD)']
    extra += ['.save '+' '.join(vectors), '.control', 'set filetype=ascii', 'set numdgt=17',
              'run', 'write coupled.raw '+' '.join(vectors), 'quit', '.endc', '.end', '']
    return text+'\n'.join(extra)


def analyze(raw, selected=2):
    values = waves.read_raw(raw)
    if float(values['time'][-1]) < 80e-9*(1-1e-9):
        raise ValueError('full coupled interval required')
    vp, vn = (waves.sample(values, 'v(AIN'+p+')',75e-9) for p in ('P','N'))
    early = waves.sample(values,'v(AINP)',65e-9)-waves.sample(values,'v(AINN)',65e-9)
    hp, hn = (waves.sample(values,'v(H'+p+str(selected)+')',75e-9) for p in ('P','N'))
    captured = [waves.sample(values,'v(HN'+str(c)+')',12e-9)-waves.sample(values,'v(HP'+str(c)+')',12e-9) for c in range(4)]
    before = [waves.sample(values,'v(BLN'+str(c)+')',7.95e-9)-waves.sample(values,'v(BLP'+str(c)+')',7.95e-9) for c in range(4)]
    capture_error = max(abs(a-b) for a,b in zip(captured,before))
    return {'output_diff_v':vp-vn, 'output_cm_v':(vp+vn)/2,
            'selected_input_diff_v':hp-hn, 'selected_column':selected,
            'output_diff_change_65_to_75ns_v':vp-vn-early,
            'within_supply_rails':.05 < min(vp,vn) and max(vp,vn) < 1.75,
            'maximum_capture_error_v':capture_error, 'capture_budget_met':capture_error <= .0008,
            'held_differentials_at_12ns_v':captured, 'before_turnoff_differentials_v':before}


def run(root, *, tag, case='pair_a', selected=2, timeout_s=120, execute=False):
    root=Path(root).resolve();common.tag_ok(tag)
    if not 1 <= timeout_s <= 180: raise ValueError('bounded coupled probe budget required')
    if (root/common.BASE/tag/'inputs.json').exists(): raise FileExistsError('fresh coupled tag required')
    receipt, data, views=pilot.source(root,'core_tap_pex_srv_20261022_01')
    condition_receipt=root/common.BASE/'mixed_wrapper_20261020_01_cond/summary.json'
    condition=json.loads(condition_receipt.read_text())
    # This is an independently validated layout/reference, not a fresh PEX load model.
    block=condition.get('block', condition)
    if block['status'] != 'BLOCK_DRC_TRANSISTOR_LVS_RC_PEX_PASS':
        raise ValueError('verified conditioner block required')
    net=common._verified(root,block['views']['schematic'])
    model=Path(data['pdk'])/'libs.tech/ngspice/sky130.lib.spice'
    tool=shutil.which('ngspice')
    if not tool: raise FileNotFoundError('ngspice required')
    deck=bench(model,views['pex'],net,case,selected)
    sources=[common._item(root,p) for p in (receipt,condition_receipt,views['gds'],views['pex'],net,
        Path(__file__),Path(pilot.__file__),Path(pilot.core.__file__),Path(design.__file__))]
    identity={'sources':sources,'model':{'path':str(model),'sha256':common._sha(model)},
        'tool':{'path':tool,'sha256':common._sha(Path(tool))},'timeout_s':timeout_s,
        'case':case,'selected':selected,'step_s':50e-12,'max_step_s':200e-12}
    report={'format':'automx-cim-coupled-frontend-pilot-v1','tag':tag,'status':'PREPARED',
        'qualification':'NOT_QUALIFIED','inputs':identity,'new_ADC_conversions':0,
        'scope':'Native TT tap-repaired core RC directly drives schematic conditioner; '
                '2pF/input ADC stand-in. Coarser time-step pilot; no ADC EOC/word, conditioner '
                'internal RC, routed top interconnect, noise/PVT or system qualification.'}
    if not execute:return report
    store=common.Store(root,tag,identity)
    snapshot=store.build/'executed_host_sources';snapshot.mkdir()
    for p in (Path(__file__),Path(pilot.__file__),Path(pilot.core.__file__)):
        (snapshot/p.name).write_bytes(p.read_bytes())
    command=[tool,'-b','bench.spice']
    def simulate(work):
        (work/'bench.spice').write_text(deck)
        return live.run(command,work,timeout_s)
    try:
        result,work=store.step('coupled',command,tcl=deck,executor=simulate)
        report['returncode']=result.returncode
        if result.returncode:raise ValueError('coupled simulation failed: '+str(result.returncode))
        raw=work/'coupled.raw';report['measurement']=analyze(raw,selected)
        report['waveform']=common._item(root,raw)
        report['status']='COUPLED_CORE_RC_SCHEMATIC_CONDITIONER_MEASURED'
        for item in sources:common._verified(root,item)
    except Exception as error:
        report.update(status='BLOCKED_COUPLED_FRONTEND',error=type(error).__name__+': '+str(error))
    finally:common.save_summary(store.folder/'summary.json',report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--tag',required=True)
    p.add_argument('--case',choices=('zero','pair_a','pair_b'),default='pair_a')
    p.add_argument('--selected',type=int,default=2);p.add_argument('--timeout-s',type=int,default=120)
    p.add_argument('--run',action='store_true');a=p.parse_args()
    r=run(a.root,tag=a.tag,case=a.case,selected=a.selected,timeout_s=a.timeout_s,execute=a.run)
    print(json.dumps(r,indent=2))
    if a.run and r['status']!='COUPLED_CORE_RC_SCHEMATIC_CONDITIONER_MEASURED':raise SystemExit(1)
