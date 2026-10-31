import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

root=Path(__file__).resolve().parents[2]
out=root/'build/gds'
os.chdir(root)
(out/'negative').mkdir(exist_ok=True)
def read(path): return json.loads(Path(path).read_text())
def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()
def write(name,data): (out/name).write_text(json.dumps(data,indent=2)+'\n')

snapshot=read('reports/pnr/delivery_snapshot.json')
assert all(digest(p)==h for p,h in snapshot['files'].items())
upstream={str(p):digest(p) for base in ['build/pnr','reports/pnr'] for p in Path(base).rglob('*') if p.is_file()}
write('input_snapshot.json',dict(snapshot_id=snapshot['snapshot_id'],files=upstream))
records=[]
for name in ['artifact-8bfa326445194758816c2d0d07307a6f','artifact-d2ef1f1f7d194cf0b4a0c9e746873b2c','artifact-971f6c7042664af69515024a25a72bc2','artifact-7295759bd83c446780157c3cdc2d72ae']:
    path=Path('.nebula_inputs')/name/'artifact.json'
    record=read(path)
    records.append(dict(artifact_id=name,record_sha256=digest(path),commit=record['content']['commit'],digest=record['digest']))
write('input_records.json',records)
audit=read('reports/pnr/input_audit.json')
views={v['name']:v for v in audit['views']}
selected=['gds/sky130_fd_sc_hd.gds','lef/sky130_fd_sc_hd.tlef','lef/sky130_fd_sc_hd_merged.lef','drc/sky130hd.lydrc','lvs/sky130hd.lylvs','cdl/sky130hd.cdl','sky130hd.lyt']
for name in selected: assert digest(views[name]['path'])==views[name]['sha256'],name
flow=Path(views['sky130hd.lyt']['path']).parents[2]
tech=ET.fromstring(Path('build/pnr/objects/klayout.lyt').read_text())
lefs=tech.findall('reader-options/lefdef/lef-files')
assert len(lefs)==2
lefs[0].text=views['lef/sky130_fd_sc_hd.tlef']['path']
lefs[1].text=views['lef/sky130_fd_sc_hd_merged.lef']['path']
ET.ElementTree(tech).write(out/'streamout.lyt',encoding='utf-8',xml_declaration=True)
(out/'layer_map.txt').write_text(tech.find('reader-options/lefdef/layer-map').text+'\n')
write('resources.json',dict(views=[views[n] for n in selected],flow=str(flow),
                          def2stream_sha256=digest(flow/'util/def2stream.py'),
                          source_technology_sha256=digest('build/pnr/objects/klayout.lyt'),
                          technology_note='Only LEF file paths are resolved to frozen installed bytes; layer map and all reader options preserved.'))
commands=[]
klayout='/tmp/chipnebula-pinned-tools/bin/klayout'
def run(name,argv):
    with (out/(name+'.log')).open('w') as log:
        rc=subprocess.run(argv,cwd=root,stdout=log,stderr=subprocess.STDOUT).returncode
    commands.append(dict(name=name,argv=argv,exit_code=rc,log='build/gds/'+name+'.log'))
    write('commands.json',commands)
    print(name,rc,flush=True)
    assert rc==0,name

run('klayout_version',[klayout,'-v'])
assert (out/'klayout_version.log').read_text().strip()=='KLayout 0.30.12'
assert digest(klayout)==read('reports/pnr/klayout_identity.json')['wrapper_sha256']
run('identity_probe',[klayout,'-b','-r',str(out/'identity_probe.py')])
openroad=Path('/tmp/chipnebula-pinned-tools/bin/openroad')
assert digest(openroad.resolve())=='99517bea0776886f56750e54f87e8e91df94aecee6189cb9c0a3be2d62cabedf'
run('openroad_export',[str(openroad),'-no_init','-exit','-threads','2','build/gds/export.tcl'])
assert digest(out/'final.def')==snapshot['files']['build/pnr/results/6_final.def'], 'Regenerated final DEF differs'
run('stream_out',[klayout,'-b','-rd','design_name=nebula_cpu_npu_top','-rd','in_def='+str(out/'final.def'),
                  '-rd','in_files='+views['gds/sky130_fd_sc_hd.gds']['path'],'-rd','seal_file=',
                  '-rd','out_file='+str(out/'nebula_cpu_npu_top.gds'),'-rd','tech_file='+str(out/'streamout.lyt'),
                  '-rd','layer_map=','-r',str(flow/'util/def2stream.py')])
run('inspect_gds',[klayout,'-b','-r',str(out/'inspect_gds.py')])
run('compare_geometry',[klayout,'-b','-r',str(out/'compare_geometry.py')])
# The delivered CDL is already concatenated with the frozen device library.
combined=Path('build/pnr/objects/6_final_concat.cdl')
assert combined.read_bytes()==Path('build/pnr/results/6_final.cdl').read_bytes()+b'\n'+Path(views['cdl/sky130hd.cdl']['path']).read_bytes()
for prefix,gds,report in [('drc',out/'nebula_cpu_npu_top.gds',out/'drc.lyrdb'),
                           ('negative_drc',out/'negative/drc_width.gds',out/'negative/drc_width.lyrdb')]:
    run(prefix,[klayout,'-b','-rd','in_gds='+str(gds),'-rd','report_file='+str(report),'-r',views['drc/sky130hd.lydrc']['path']])
for prefix,gds,report,netlist in [('lvs',out/'nebula_cpu_npu_top.gds',out/'lvs.lvsdb',out/'extracted.cir'),
                                 ('negative_lvs',out/'negative/lvs_missing_gate.gds',out/'negative/lvs_missing_gate.lvsdb',out/'negative/extracted.cir')]:
    run(prefix,[klayout,'-b','-rd','in_gds='+str(gds),'-rd','cdl_file='+str(root/combined),
                '-rd','top_cell=nebula_cpu_npu_top','-rd','target_netlist='+str(netlist),
                '-rd','report_file='+str(report),'-r',views['lvs/sky130hd.lylvs']['path']])
run('read_checks',[klayout,'-b','-r',str(out/'read_checks.py')])
assert all(digest(p)==h for p,h in upstream.items()), 'Supplied physical snapshot modified'
write('preservation.json',dict(status='passed',snapshot_id=snapshot['snapshot_id'],files_checked=len(upstream),
                               input_database_netlist_parasitics_unchanged=True,evidence='build/gds/input_snapshot.json'))
write('tool_identity.json',dict(klayout_requested=klayout,klayout_resolved=str(Path(klayout).resolve()),
                               klayout_wrapper_sha256=digest(klayout),version='0.30.12',
                               runtime_module=read('reports/pnr/klayout_identity.json')['pya_module'],
                               runtime_identity='build/gds/klayout_runtime_identity.json',
                               openroad_requested=str(openroad),openroad_resolved=str(openroad.resolve()),
                               openroad_sha256=digest(openroad.resolve()),threads=2,NUM_CORES=os.environ.get('NUM_CORES'),
                               environment_sources=['/tmp/chipnebula-pinned-tools/env.sh','/opt/rh/gcc-toolset-13/enable']))
