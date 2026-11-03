"""One compact-placement 4 ms/25 ns transient after physical gates; --audit-only never simulates."""
import argparse
from collections import Counter
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys

DEST = Path(__file__).resolve().parent
REPO = DEST.parents[3]
sys.path.insert(0, str(REPO))
from examples.microrobot import clock_layout as layout


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


previous = load('local_routes', DEST.parent/'clock_local_routes/run_variant.py')
diagnostic = previous.diagnostic
sha, dump, counts = diagnostic.sha, diagnostic.dump, diagnostic.counts
LOCAL = REPO/'examples/microrobot/local_runs/clock_layout'
BASE = LOCAL/'stage_local_v1'
PHYSICAL = LOCAL/'compact_x_v1'
RUN = PHYSICAL/'extracted_25ns'
REVIEW = previous.REVIEW


def canonical_audit(path):
    """Verify device connectivity/dimensions and resolve changed extracted aliases."""
    source, devices = layout.physical_source()
    aliases = {node: node for _, nodes, _, _ in devices for node in nodes}
    for name, nodes, model, _ in devices:
        pins = ['C1','C2'] if '__cap_' in model else ['D','G','S','B']
        for pin, node in zip(pins, nodes):
            aliases[f'{name}.{pin}'] = node
            if name in layout.BIAS:
                aliases[f'Xbias.{name}.{pin}'] = node
    def signature(nodes, model, params):
        values = dict(value.split('=') for value in params)
        terminal = tuple(sorted(nodes)) if '__cap_' in model else (tuple(sorted([nodes[0], nodes[2]])), nodes[1], nodes[3])
        return model, terminal, float(values['w']), float(values['l'])
    expected = Counter(signature(nodes, model, params) for _, nodes, model, params in devices)
    captext = (path/'clock_capacitance.spice').read_text()
    extracted = Counter()
    capnodes = {}
    for line in captext.splitlines():
        if not line.startswith('X'): continue
        f = line.split(); n = 2 if '__cap_' in f[3] else 4
        for node in f[1:n+1]:
            capnodes[node] = aliases[node]
        extracted[signature([aliases[node] for node in f[1:n+1]], f[n+1], f[n+2:])] += 1
    assert extracted == expected, 'Cap-only devices differ from canonical source'
    text = (path/'clock_rc.spice').read_text()
    parent = {}
    def find(node):
        parent.setdefault(node,node)
        if parent[node] != node: parent[node] = find(parent[node])
        return parent[node]
    for line in text.splitlines():
        f=line.split()
        if f and f[0].startswith('R'): parent[find(f[1])] = find(f[2])
    roots = {}
    for node, logical in capnodes.items():
        root=find(node)
        assert root not in roots or roots[root] == logical
        roots[root]=logical
    extracted_rc = Counter()
    for line in text.splitlines():
        if not line.startswith('X'): continue
        f=line.split(); n=2 if '__cap_' in f[3] else 4
        extracted_rc[signature([roots[find(node)] for node in f[1:n+1]], f[n+1], f[n+2:])] += 1
    assert extracted_rc == expected, 'RC devices differ from canonical source'
    caps=[]
    for line in text.splitlines():
        f=line.split()
        if not f or not f[0].startswith('C'): continue
        value=re.fullmatch(r'([0-9.eE+\-]+)([fpnu]?)', f[3]); assert value
        scale={'':1.,'f':1e-15,'p':1e-12,'n':1e-9,'u':1e-6}[value[2]]
        caps.append((f[0],*(roots[find(node)] for node in f[1:3]),float(value[1])*scale))
    result={'method':'Sum explicit extracted C incident on resistor-connected canonical logical net; aliases verified against cap-only and RC canonical device signatures',
            'cap_only_and_RC_devices_match_canonical_29FET_7MIM':True,
            'extracted_alias_to_canonical_net':capnodes,
            'limitations':['Not ground-equivalent load; ignores coupling correlation', 'Excludes intentional MIM and model capacitances; no additive causal attribution'],
            'resistor_count':counts(text)['R'],'capacitor_count':len(caps),'logical_nets':{}}
    for logical in ['a','b','c','d','raw','buffered','clk','bias_n','bias_p','vdd','vss']:
        by_other={}
        for _, a, b, value in caps:
            if logical not in (a,b):continue
            other=b if a==logical else a
            by_other[other]=by_other.get(other,0)+value/1e-15
        result['logical_nets'][logical]={'total_incident_parasitic_fF':sum(by_other.values()),'by_other_logical_net_fF':by_other}
    return result


def placement_audit():
    old=layout.specs(layout.physical_source()[1]); new=layout.specs(layout.physical_source()[1],placement='compact_x')
    normalize=lambda path: re.sub(r'^timestamp \d+$','timestamp 0',path.read_text(),flags=re.M)
    def instances(path):
        return {name:(cell,int(x),int(y)) for cell,name,x,y in re.findall(r'use (\S+)\s+(\S+)\n.*?transform 1 0 (\S+) 0 1 (\S+)',path.read_text(),re.S)}
    before,after=[instances(path/'clock_cells.mag') for path in (BASE,PHYSICAL)]
    oldpins,newpins=[json.loads((path/'instance_pins.json').read_text()) for path in (BASE,PHYSICAL)]
    assert set(before)==set(after)==set(oldpins)==set(newpins)
    shifts={}
    for a,b in zip(old,new):
        assert {k:v for k,v in a.items() if k not in ['x','y']}=={k:v for k,v in b.items() if k not in ['x','y']}
        shifts[a['name']]=(b['x']-a['x'],b['y']-a['y'])
    shifts['Xbias']=(0,0)
    for name,(dx,dy) in shifts.items():
        cell,x,y=before[name]; cell2,xx,yy=after[name]
        assert cell==cell2 and abs((xx-x)*.005-dx)<1e-10 and abs((yy-y)*.005-dy)<1e-10
        assert normalize(BASE/(cell+'.mag'))==normalize(PHYSICAL/(cell+'.mag'))
        assert set(oldpins[name])==set(newpins[name])
        for pin,(x,y,layer) in oldpins[name].items():
            xx,yy,ll=newpins[name][pin]
            assert abs(xx-x-dx)<1e-10 and abs(yy-y-dy)<1e-10 and layer==ll
    envelopes=[]
    for e in new:
        if 'fet_' not in e['model']:continue
        center=newpins[e['name']]['G'][0]; half=e['l']/2
        lo,hi=center-half-3-.2,center+half+3+.2
        assert abs(lo-e['x']+2.485)<1e-10 and abs(hi-e['x']-e['l']-3.915)<1e-10
        envelopes.append((e['name'],lo,hi))
    gaps=[b[1]-a[2] for a,b in zip(envelopes[:-1],envelopes[1:])]
    assert all(abs(gap-2.6)<1e-10 for gap in gaps)
    return {'instances_are_pure_translations':True,'all_cell_paint_unchanged_after_timestamp_normalization':True,'all_pin_centers_translate_exactly':True,
            'bias_unchanged':True,'minimum_adjacent_FET_escape_paint_gap_um':min(gaps),'FET_escape_envelopes_um':envelopes,
            'entries':new,'translation_um':shifts}


def inputs():
    report=json.loads((PHYSICAL/'report.json').read_text())
    assert report['placement_drc'].startswith('DRC_ERRORS 0')
    assert all(report[k] for k in ['native_drc_pass','native_lvs_pass','negative_control_rejected','roundtrip_drc_pass','roundtrip_lvs_pass'])
    for folder in [PHYSICAL,PHYSICAL/'gds_roundtrip']:
        assert 'Circuits match uniquely.' in (folder/'lvs.txt').read_text()
        assert 'Circuits match uniquely.' not in (folder/'negative_control_lvs.txt').read_text()
    assert not (PHYSICAL/'streamout_feedback.tcl').read_text().strip()
    assert report['routing_variant']=='stage_local' and report['placement_variant']=='compact_x'
    for name in ['physical_clock.spice','microrobot_bias.mag','tracks.json']:
        assert sha(BASE/name)==sha(PHYSICAL/name)
    place=placement_audit()
    caps={name:canonical_audit(path) for name,path in [('stage_local',BASE),('compact_x',PHYSICAL)]}
    for name in ['stage_local','compact_x']:
        assert caps[name]['cap_only_and_RC_devices_match_canonical_29FET_7MIM']
    original=(BASE/'clock_rc.spice').read_text(); variant=(PHYSICAL/'clock_rc.spice').read_text()
    assert counts(variant)=={'R':851,'C':376,'FET':29,'MIM':7}
    deck=(BASE/'extracted_25ns/clock.spice').read_text()
    assert deck.count(original)==1
    changed=deck.replace(original,variant,1)
    assert changed.replace(variant,original,1)==deck
    assert [line for line in changed.splitlines() if line.startswith('tran ')]==['tran 2.5e-08 0.004 0 2.5e-08']
    library=Path(re.search(r'^\.lib "([^"]+)" tt$',deck,re.M)[1])
    assert sha(library)==json.loads((DEST.parent/'clock_local_routes/metrics.json').read_text())['proof']['pdk_top_level_library_sha256']
    return report,place,caps,original,variant,deck,changed,library


def execute():
    # Reuse the accepted one-shot execution function with this module's paths
    # and input checks. It creates RUN with exist_ok=False before ngspice.
    previous.PHYSICAL,previous.RUN=PHYSICAL,RUN
    previous.inputs=lambda: (None,None,None,None,inputs()[6],None)
    previous.execute()


def audit():
    report,place,caps,original,variant,deck,changed,library=inputs()
    assert (RUN/'clock.spice').read_text()==changed
    for name in ['.spiceinit','receiver_cells.spice']:
        assert sha(RUN/name)==sha(BASE/'extracted_25ns'/name)
    reviewed=json.loads((DEST.parent/'clock_local_routes/metrics.json').read_text())
    cases={name:diagnostic.audit_case(LOCAL/'contact_escape_v2'/name) for name in ['schematic_25ns','extracted_25ns']}
    cases['stage_local_25ns']=diagnostic.audit_case(BASE/'extracted_25ns')
    for name,case in cases.items():
        assert case['sha256']['clock.dat']==reviewed['cases'][name]['sha256']['clock.dat']
        assert case['sha256']['clock.spice']==reviewed['cases'][name]['sha256']['clock.spice']
    cases['compact_x_25ns']=diagnostic.audit_case(RUN)
    execution=json.loads((RUN/'execution.json').read_text())
    assert execution['simulator_invocations']==1 and execution['returncode']==0
    assert all(case['full_completion'] for case in cases.values())
    for name in ['clock.spice','.spiceinit','receiver_cells.spice','ngspice.log','execution.json']:
        shutil.copy2(RUN/name,DEST/name)
    for source in sorted(PHYSICAL.rglob('*')):
        relative=source.relative_to(PHYSICAL)
        if source.is_file() and 'extracted_25ns' not in relative.parts and source.suffix in {'.spice','.json','.txt','.tcl','.log','.mag','.gds'}:
            target=DEST/'physical'/relative;target.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(source,target)
    shutil.copy2(REPO/'examples/microrobot/clock_layout.py',DEST/'clock_layout.py.snapshot')
    shutil.copy2(REVIEW/'provenance/pv_fit.json',DEST/'pv_fit.json')
    (DEST/'generator.diff').write_text(''.join(difflib.unified_diff((DEST.parent/'clock_local_routes/clock_layout.py.snapshot').read_text().splitlines(keepends=True),
        (DEST/'clock_layout.py.snapshot').read_text().splitlines(keepends=True),fromfile='accepted_stage_local/clock_layout.py',tofile='compact_x/clock_layout.py')))
    for name,before,after in [('netlist',original,variant),('deck',deck,changed),('routing',(BASE/'route_extract.tcl').read_text(),(PHYSICAL/'route_extract.tcl').read_text()),('placement',(BASE/'generate_cells.tcl').read_text(),(PHYSICAL/'generate_cells.tcl').read_text())]:
        (DEST/f'{name}.diff').write_text(''.join(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='stage_local/'+name,tofile='compact_x/'+name)))
    area={name:previous.extent(path/'microrobot_clock.mag') for name,path in [('stage_local',BASE),('compact_x',PHYSICAL)]}
    freq={name:case['edges']['steady_clock_frequency_Hz'] for name,case in cases.items()}
    result={'status':'Reviewed and accepted as compact-placement improvement evidence; no electrical design acceptance',
            'physical_gates':report,'roundtrip_negative_control_rejected':True,'execution':execution,'placement':place,
            'proof':{'canonical_source_sha256':layout.CANONICAL_SHA,'physical_source_and_bias_identical':True,
                     'cap_only_and_RC_canonical_signatures_match':True,'deck_unchanged_outside_replaced_RC':True,
                     'stage_local_RC_sha256':sha(BASE/'clock_rc.spice'),'compact_RC_sha256':sha(PHYSICAL/'clock_rc.spice'),
                     'pdk_top_level_library_sha256':sha(library),'stage_local_review_metrics_sha256':sha(DEST.parent/'clock_local_routes/metrics.json')},
            'helper_sha256':{str(path.relative_to(REPO)):sha(path) for path in [DEST.parent/'clock_local_routes/run_variant.py',DEST.parent/'clock_cap_ablation/run_diagnostic.py',DEST.parent/'clock_layout_review/plot_layout.py']},
            'routing':{'variant':'stage_local','tracks_unchanged':True,'timing_MIM_escape_y_um':30,'free_x_algorithm_unchanged':True},
            'area':area,'capacitance':caps,'cases':cases,
            'comparison':{'frequency_Hz':freq,'compact_over_stage_local_frequency_ratio':freq['compact_x_25ns']/freq['stage_local_25ns'],
                          'compact_over_schematic_frequency_ratio':freq['compact_x_25ns']/freq['schematic_25ns'],
                          'compact_over_stage_local_whole_power_ratio':cases['compact_x_25ns']['power_W']['whole_clock_and_first_ff']/cases['stage_local_25ns']['power_W']['whole_clock_and_first_ff'],
                          'paint_bounding_box_area_reduction_fraction':1-area['compact_x']['bounding_box_area_um2']/area['stage_local']['bounding_box_area_um2']},
            'assumptions':reviewed['assumptions'],
            'limitations':reviewed['limitations']+['Only one bounded compact placement and one matched transient; no repair sweep', 'Physical source identical; extracted device numbering, aliases, D/S orientation and RC values can change with placement; canonical signatures verify connectivity and dimensions']}
    dump(DEST/'metrics.json',result)
    dump(DEST/'sha256.json',{str(p.relative_to(DEST)):sha(p) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='sha256.json' and '__pycache__' not in p.parts})
    print(json.dumps({'comparison':result['comparison'],'compact':cases['compact_x_25ns'],'area':area}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-only',action='store_true')
    args=parser.parse_args()
    if not args.audit_only:execute()
    audit()
