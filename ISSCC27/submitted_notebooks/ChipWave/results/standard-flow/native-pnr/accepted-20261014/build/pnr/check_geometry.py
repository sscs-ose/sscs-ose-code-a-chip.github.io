import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

root=Path(__file__).resolve().parents[2]
c=json.loads((root/'physical/chip-nebula/implementation.constraints.json').read_text())
audit=json.loads((root/'reports/pnr/input_audit.json').read_text())
parser=argparse.ArgumentParser()
parser.add_argument('--database',default='build/pnr/results/6_final.odb')
parser.add_argument('--stage',choices=['placement','final'],default='final')
args=parser.parse_args()
report=root/'reports/pnr'
if args.stage=='placement':report=report/'placement_geometry';report.mkdir(exist_ok=True)
script=root/'build/pnr/geometry_check.tcl'
script.write_text(f'''if {{[catch {{
read_db {root/args.database}
set nebula_geometry_report {report}
source {root}/build/pnr/geometry_measure.tcl
}} message options]}} {{puts stderr $message; puts stderr [dict get $options -errorinfo]; exit 1}}
exit
''')
with (report/'geometry_check.log').open('w') as log:
    rc=subprocess.run([c['physical_execution']['openroad_executable'],'-no_init','-exit','-threads','2',str(script)],cwd=root,stdout=log,stderr=subprocess.STDOUT).returncode
assert rc==0,'Native geometry/placement measurement failed'
g=json.loads((report/'database_geometry.json').read_text());f=c['floorplan'];dbu=g['dbu_per_micron'];area=audit['mapped_area_um2']
side=math.sqrt(area/(f['initial_core_utilization_percent']/100))
width=math.ceil(side/f['site_width_um'])*f['site_width_um']
height=math.ceil(side/f['row_height_um'])*f['row_height_um']
lx=f['margins_um']['left'];ly=f['margins_um']['bottom']
planned=[round(x*dbu) for x in [lx,ly,lx+width,ly+height]]
die=[round(x*dbu) for x in [0,0,width+lx+f['margins_um']['right'],height+ly+f['margins_um']['top']]]
sw=round(f['site_width_um']*dbu);sh=round(f['row_height_um']*dbu)
def inward(box):return [(box[0]+sw-1)//sw*sw,(box[1]+sh-1)//sh*sh,box[2]//sw*sw,box[3]//sh*sh]
assert inward([10000,10000,575800,575760])==[10120,10880,575460,573920]
expected=inward(planned)
def read(name):
    with (report/name).open() as stream:return list(csv.DictReader(stream,delimiter='\t'))
rows=read('database_rows.tsv');errors=[]
expected_rows={(expected[0],y,expected[2],y+sh) for y in range(expected[1],expected[3],sh)}
actual_rows={tuple(int(row[k]) for k in ['xmin','ymin','xmax','ymax']) for row in rows}
if g['die_dbu']!=die:errors.append('Actual ODB die differs from planned die')
if actual_rows!=expected_rows or len(rows)!=len(expected_rows):errors.append('Native row outlines differ from inward site-grid derivation')
if g['core_dbu']!=expected:errors.append('ODB core metadata differs from native row bbox')
if not rows or expected[0]>=expected[2] or expected[1]>=expected[3]:errors.append('Empty legal site region')
if any(expected[i]<planned[i] for i in [0,1]) or any(expected[i]>planned[i] for i in [2,3]):errors.append('Legal rows exceed planning box')
margins=[expected[0]-die[0],expected[1]-die[1],die[2]-expected[2],die[3]-expected[3]]
if any(x<10*dbu for x in margins):errors.append('Legal row margin below frozen minimum')
for row in rows:
    y=int(row['ymin']);orientation='MX' if ((y-expected[1])//sh)%2 else 'R0'
    if (row['site']!=f['site'] or int(row['site_width'])!=sw or int(row['site_height'])!=sh
        or int(row['count'])!=(expected[2]-expected[0])//sw or int(row['spacing'])!=sw or row['orientation']!=orientation):
        errors.append('Native row site/orientation mismatch: '+row['row'])
ports={p['port'] for p in read('database_ports.tsv') if p['signal_type'] not in ['POWER','GROUND']}
pins=read('database_pin_locations.tsv');located=set();pin_checks=[];side_boxes={}
spacing={r['layer']:int(r['spacing']) for r in read('database_pin_rules.tsv')}
tracks=Path(c['view_binding']['views']['make_tracks.tcl']['installed_path']).read_text()
track_rules={m[0]:[round(float(x)*dbu) for x in m[1:]] for m in re.findall(r'make_tracks (\w+) -x_offset ([\d.]+) -x_pitch ([\d.]+) -y_offset ([\d.]+) -y_pitch ([\d.]+)',tracks)}
for pin in pins:
    if pin['signal_type'] in ['POWER','GROUND']:continue
    located.add(pin['port']);layer=pin['layer'];box=[int(pin[k]) for k in ['xmin','ymin','xmax','ymax']];bad=[]
    if pin['status'] not in ['PLACED','FIRM','LOCKED'] or layer not in [c['pin_placement']['horizontal_layer'],c['pin_placement']['vertical_layer']]:bad.append('status/layer')
    if layer==c['pin_placement']['horizontal_layer']:
        axis=1;offset,pitch=track_rules[layer][2:];side='left' if box[0]==die[0] else 'right' if box[2]==die[2] else 'interior'
    elif layer==c['pin_placement']['vertical_layer']:
        axis=0;offset,pitch=track_rules[layer][:2];side='bottom' if box[1]==die[1] else 'top' if box[3]==die[3] else 'interior'
    else:errors.append('Pin layer differs: '+pin['port']);continue
    if (box[axis]+box[axis+2]-2*offset)%(2*pitch):bad.append('track phase')
    if side=='interior':bad.append('not on die edge')
    if box[axis]-die[axis]<spacing[layer] or die[axis+2]-box[axis+2]<spacing[layer]:bad.append('corner spacing')
    side_boxes.setdefault((side,layer),[]).append((box[axis],box[axis+2],pin['port']))
    pin_checks.append(dict(port=pin['port'],layer=layer,side=side,box_dbu=box,track_offset_dbu=offset,track_pitch_dbu=pitch,errors=bad))
    errors.extend('Pin '+pin['port']+': '+e for e in bad)
for (side,layer),boxes in side_boxes.items():
    boxes.sort()
    for first,second in zip(boxes,boxes[1:]):
        if second[0]-first[1]<spacing[layer]:errors.append('Pin spacing: '+first[2]+' / '+second[2])
if located!=ports:errors.append('Signal top bits missing pin boxes')
power=read('database_power_connections.tsv');unconnected_pg=[]
for term in power:
    expected_net='VDD' if term['signal_type']=='POWER' else 'VSS'
    if not term['net']:unconnected_pg.append(term['instance']+'/'+term['pin'])
    if term['net']!=expected_net and (term['net'] or args.stage=='final'):errors.append('Power connection mismatch: '+term['instance']+'/'+term['pin'])
placed=read('database_placed_instances.tsv');groups={}
for inst in placed:
    group=groups.setdefault(inst['type'],dict(count=0,footprint_um2=0.0));group['count']+=1;group['footprint_um2']+=int(inst['footprint_dbu2'])/dbu**2
bbox=[min(int(x['xmin']) for x in placed),min(int(x['ymin']) for x in placed),max(int(x['xmax']) for x in placed),max(int(x['ymax']) for x in placed)]
legal_area=sum(int(r['count'])*sw*sh for r in rows)/dbu**2
receipt=dict(schema_version=1,status='passed' if not errors else 'failed',errors=errors,stage=args.stage,
    planned_core_dbu=planned,expected_native_core_dbu=expected,actual_core_dbu=g['core_dbu'],actual_die_dbu=g['die_dbu'],dbu_per_micron=dbu,
    required_core_um=[x/dbu for x in planned],actual_core_um=[x/dbu for x in g['core_dbu']],required_die_um=[x/dbu for x in die],actual_die_um=[x/dbu for x in g['die_dbu']],
    requested_core_area_um2=width*height,actual_core_area_um2=legal_area,mapped_area_um2=area,planned_utilization_percent=100*area/(width*height),legal_row_utilization_percent=100*area/legal_area,
    planned_aspect_ratio=width/height,legal_row_aspect_ratio=(expected[2]-expected[0])/(expected[3]-expected[1]),actual_margins_um=dict(zip(['left','bottom','right','top'],[x/dbu for x in margins])),
    unconnected_pg_terminal_count=len(unconnected_pg),power_connection_scope='Final checks require all PG terms; native ORFS final_connect runs after filler, so new placement PG terms are recorded before connection.',mapped_whitespace_um2=legal_area-area,placed_area_groups=groups,total_placed_footprint_um2=sum(x['footprint_um2'] for x in groups.values()),occupied_instance_bbox_dbu=bbox,
    row_count=len(rows),legal_site_count=sum(int(r['count']) for r in rows),site=f['site'],signal_top_bits=len(ports),located_signal_top_bits=len(located),pin_checks=pin_checks,
    database_odb=args.database,database_sha256=hashlib.sha256((root/args.database).read_bytes()).hexdigest(),tool_identity=audit['tool_identity'],inputs=audit['inputs'],
    mapped_netlist_sha256=hashlib.sha256((root/'build/synth/nebula_cpu_npu_top.v').read_bytes()).hexdigest(),
    evidence=[str((report/n).relative_to(root)) for n in ['database_geometry.json','database_rows.tsv','database_pin_locations.tsv','database_placed_instances.tsv','database_pin_rules.tsv','database_power_connections.tsv','geometry_check.log']],
    historical_failure_evidence=['reports/pnr/history/v1-resume/geometry_acceptance.json','reports/pnr/history/v1-resume/row_phase_failure/5_2_route.log','reports/pnr/history/v1-resume/core_boundary_failure/place.log'])
(report/'geometry_acceptance.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:receipt[k] for k in ['status','stage','actual_core_um','actual_margins_um','row_count','legal_site_count','legal_row_utilization_percent','unconnected_pg_terminal_count']} | dict(error_count=len(errors),first_errors=errors[:10]),indent=2))
raise SystemExit(0 if not errors else 1)
