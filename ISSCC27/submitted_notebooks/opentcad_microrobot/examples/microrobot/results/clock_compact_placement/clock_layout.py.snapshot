"""Prototype canonical clock layout: exact-source physical gates before SPICE.

The existing flat bias macro is reused unchanged. No controller/POR, footprint
closure or fabrication signoff is implied. Original clock source is read only.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from .layout import magic_run

HERE = Path(__file__).resolve().parent
BIAS = {'Xb1','Xb2','Xb3','Xmirror','Xpdiode','Xcbiasp','Xcbiasn'}
PORTS = ['clk','vdd','vss','bias_n','bias_p']
CANONICAL_SHA = 'dc606bcaa35616e6412c2b8d8c63e17175f6b53d6baad820a222b66b74dc29de'


def physical_source():
    """Flatten five four-FET stages; explicitly alias the zero-V bias probe."""
    source = HERE/'circuits/starved_clock.spice'
    original = source.read_text()
    if hashlib.sha256(source.read_bytes()).hexdigest() != CANONICAL_SHA:
        raise ValueError('Canonical source changed; review before regenerating layout')
    main, inv = original.split('.subckt micro_starved_inv ',1)
    inv = inv.split('\n',1)[1].split('.ends')[0]
    devices=[]
    for line in main.splitlines():
        if not line.startswith('X'):continue
        tok=line.replace('ref_vdd','vdd').split()
        if tok[-1]=='micro_starved_inv':
            name,*pins,_=tok
            mapping=dict(zip(['a','y','vdd','vss','bp','bn'],pins))
            for sub in inv.splitlines():
                if not sub.startswith('X'):continue
                st=sub.split();nodes=[mapping.get(n,name+'_'+n) for n in st[1:5]]
                devices.append((name+'_'+st[0],nodes,st[5],st[6:]))
        else:
            count=2 if '__cap_' in tok[3] else 4
            devices.append((tok[0],tok[1:1+count],tok[1+count],tok[2+count:]))
    if len(devices)!=36 or sum('__cap_' in q[2] for q in devices)!=7:
        raise ValueError('Canonical physical inventory is not29FET+7MIM')
    lines=['* Derived from unchanged canonical clock; Vbias0V removed, ref_vdd aliased to vdd.',
           '.subckt microrobot_clock '+' '.join(PORTS)]
    lines += [' '.join([name,*nodes,model,*params]) for name,nodes,model,params in devices]
    return '\n'.join(lines+['.ends microrobot_clock','']), devices


def specs(devices, *, placement='baseline'):
    if placement not in {'baseline', 'compact_x'}:
        raise ValueError(f'Unknown clock placement variant: {placement}')
    result=[];index=0;next_x=120
    for name,nodes,model,params in devices:
        if name in BIAS:continue
        values=dict(p.split('=') for p in params)
        if '__cap_' in model:
            stage=int(name[-1])-1
            x,y=(145.75+53*stage if placement=='compact_x' else 154+80*stage),35
        else:
            x,y=(next_x if placement=='compact_x' else 120+20*index),10
            # Actual PDK pins plus unchanged escape paint span x-2.485
            # through x+L+3.915 um. This pitch leaves 2.6 um between them.
            next_x=x+float(values['l'])+9
            index+=1
        result.append(dict(name=name,nodes=nodes,model=model,w=float(values['w']),
                           l=float(values['l']),x=x,y=y))
    assert index==24 and len(result)==29
    return result


def generate_script(pdk, entries):
    generator=pdk/'libs.tech/magic/sky130A.tcl'
    lines=[f'set fd [open {{{generator}}} r]','set text [read $fd]','close $fd',
           'uplevel #0 [string map [list {$sky130::ruleset} {$::sky130::ruleset}] $text]',
           'random seed 1729','load clock_cells']
    for e in entries:
        short=e['model'].removeprefix('sky130_fd_pr__')
        lines += [f"box values {e['x']}um {e['y']}um {e['x']}um {e['y']}um",
                  f"magic::gencell sky130::{e['model']} {e['name']} w {e['w']} l {e['l']}"+(' viagb 100' if 'fet_' in short else '')]
    lines += ['select top cell','expand','save clock_cells',
              'foreach cell [cellname list children clock_cells] { if {$cell ne "microrobot_bias"} { load $cell; save $cell } }',
              'load clock_cells','select top cell','box values -40um 0um 650um 120um',
              'drc check','drc catchup','set f [open placement_drc.txt w]',
              'puts $f "DRC_ERRORS [drc list count total]"','puts $f [drc listall why]','close $f']
    return '\n'.join(lines)


def read_pins(dest, entries):
    text=(dest/'clock_cells.mag').read_text();instances={}
    if 'magscale 1 2' not in text:raise ValueError('Expected5nm Magic grid')
    for m in re.finditer(r'use (\S+)\s+(\S+)\n.*?transform 1 0 (\S+) 0 1 (\S+)',text,re.S):
        cell,name,tx,ty=m.groups();labels={}
        for q in re.finditer(r'rlabel (\S+) (\S+) (\S+) (\S+) (\S+) \S+ (\S+)',(dest/(cell+'.mag')).read_text()):
            layer,x1,y1,x2,y2,pin=q.groups()
            labels[pin]=((float(tx)+(float(x1)+float(x2))/2)*.005,
                         (float(ty)+(float(y1)+float(y2))/2)*.005,layer)
        instances[name]=labels
    if set(instances)!={e['name'] for e in entries}|{'Xbias'}:
        raise ValueError('Unexpected placement instance inventory')
    return instances


def routing_script(entries, pins, *, routing='baseline'):
    if routing not in {'baseline', 'stage_local'}:
        raise ValueError(f'Unknown clock routing variant: {routing}')
    local_tracks = dict(zip(['a', 'b', 'c', 'd', 'raw'], [20., 22., 24., 26., 28.])) if routing == 'stage_local' else {}
    lines=['load microrobot_clock','select top cell'];endpoints={};used=[]
    def rect(layer,x1,y1,x2,y2):
        lines.extend([f'box values {min(x1,x2):.3f}um {min(y1,y2):.3f}um {max(x1,x2):.3f}um {max(y1,y2):.3f}um',f'paint {layer}'])
    def patch(layer,x,y,w):rect(layer,x-w/2,y-w/2,x+w/2,y+w/2)
    def wire(layer,x,y,xx,yy,w=.4):rect(layer,min(x,xx)-w/2,min(y,yy)-w/2,max(x,xx)+w/2,max(y,yy)+w/2)
    def via1(x,y):
        patch('metal1',x,y,.4);patch('metal2',x,y,.4);patch('via1',x,y,.28)
    def via2(x,y):
        patch('metal2',x,y,.4);patch('metal3',x,y,.4);patch('via2',x,y,.30)
    def via3(x,y):
        patch('metal3',x,y,.6);patch('metal4',x,y,.4);patch('via3',x,y,.34)
    def endpoint(net,x,y):
        endpoints.setdefault(net,[]).append((x,y));used.append(x)
    for e in entries:
        if '__cap_' in e['model']:continue
        pp=pins[e['name']];center=pp['G'][0];half=e['l']/2
        escape={'D':center-half-2,'G':center-half-3,'S':center+half+2,'B':center+half+3}
        for pin,net in zip(['D','G','S','B'],e['nodes']):
            x,y,_=pp[pin]
            if pin=='G':
                # Both gate contacts are electrically joined by the PDK gate.
                # Bottom contact plus55nm offset fits between drain metal and
                # existing bottom guard without widening their narrow gap.
                y=2*pp['D'][1]-y-.055
            elif pin=='B':
                # Contact the existing broad bottom guard metal off-center;
                # no new M1 wire across the gate/guard separation.
                x+=1
            via1(x,y);xx=escape[pin];wire('metal2',x,y,xx,y);endpoint(net,xx,y)
    # Bias is unchanged: extend its rectangular M3 ports outside the existing macro.
    for i,net in enumerate(['vdd','vss','bias_n','bias_p']):
        x,y,_=pins['Xbias'][net];xx=-5-2*i
        wire('metal3',x,y,xx,y);via2(xx,y);endpoint(net,xx,y)
    def free_x(wanted):
        x=wanted
        while any(abs(x-q)<.8 for q in used):x+=.8
        used.append(x);return x
    for e in entries:
        if '__cap_' not in e['model']:continue
        pp=pins[e['name']]
        # C1 top escapes in M4 before vias descend outside the plate.
        x,y,_=pp['C1'];xx=free_x(max(pp['C1'][0],pp['C2'][0])+4)
        # Local timing routes escape below the MIM row before descending;
        # retain the original endpoint x and every non-timing connection.
        escape_y=30 if e['nodes'][0] in local_tracks else 55
        wire('metal4',x,y,x,escape_y);wire('metal4',x,escape_y,xx,escape_y);via3(xx,escape_y);via2(xx,escape_y);endpoint(e['nodes'][0],xx,escape_y)
        x,y,_=pp['C2'];xx=free_x(max(pp['C1'][0],pp['C2'][0])+6)
        wire('metal3',x,y,xx,y);via2(xx,y);endpoint(e['nodes'][1],xx,y)
    nets=list(dict.fromkeys(['vss','vdd','bias_n','bias_p',*[n for e in entries for n in e['nodes']]]))
    tracks={net:70+1.2*i for i,net in enumerate(nets)}
    tracks.update(local_tracks)
    for net,points in endpoints.items():
        yy=tracks[net];xs=[q[0] for q in points]
        for x,y in points:wire('metal2',x,y,x,yy);via2(x,yy)
        lo,hi=min(xs)-.5,max(xs)+.5
        if net in ['vss','vdd','bias_n','bias_p']:lo=-30
        wire('metal3',lo,yy,hi,yy)
        # Internal nets use labels; only the five interface labels become ports.
        rect('metal3',lo,yy-.2,lo+.4,yy+.2)
        lines += [f'box values {lo:.3f}um {yy-.2:.3f}um {lo+.4:.3f}um {yy+.2:.3f}um',f'label {net} center metal3']
        if net in PORTS:lines.append(f'port make {PORTS.index(net)+1}')
    lines += ['save microrobot_clock','box values -40um 0um 650um 120um','drc check','drc catchup',
              'set f [open drc.txt w]','puts $f "DRC_ERRORS [drc list count total]"','puts $f [drc listall why]','close $f',
              'extract all','ext2spice lvs','ext2spice -o clock_lvs.spice','ext2spice cthresh 0','ext2spice -o clock_capacitance.spice',
              'gds write microrobot_clock.gds','feedback save streamout_feedback.tcl']
    return '\n'.join(lines),tracks


def lvs(dest, schematic, pdk, name):
    executable=os.environ.get('NETGEN') or shutil.which('netgen')
    if not executable and Path('/tmp/opentcad-netgen/bin/netgen').is_file():executable='/tmp/opentcad-netgen/bin/netgen'
    if not executable:raise FileNotFoundError('Set NETGEN to installed Netgen')
    result=subprocess.run([executable,'-batch','lvs','clock_lvs.spice microrobot_clock',
                           f'{schematic} microrobot_clock',str(pdk/'libs.tech/netgen/sky130A_setup.tcl'),f'{name}.txt','-json'],
                          cwd=dest,capture_output=True,text=True,timeout=120)
    (dest/(name+'.log')).write_text(result.stdout+result.stderr)
    report=(dest/(name+'.txt')).read_text()
    return result.returncode==0 and 'Circuits match uniquely.' in report and 'Property errors' not in report


def run(destination, *, physical_only=True, routing='baseline', placement='baseline'):
    dest=Path(destination).resolve()
    if dest.exists():raise FileExistsError('Choose a fresh clock-layout destination')
    dest.mkdir(parents=True)
    pdk=Path(os.environ.get('PDK_ROOT','/usr/local/share/pdk'))/'sky130A'
    source,devices=physical_source();entries=specs(devices,placement=placement)
    (dest/'physical_clock.spice').write_text(source)
    bias=HERE/'results/layout/bias_reference_final/microrobot_bias.mag'
    shutil.copy2(bias,dest/bias.name)
    (dest/'clock_cells.mag').write_text('magic\ntech sky130A\nmagscale 1 2\ntimestamp 0\nuse microrobot_bias Xbias\ntimestamp 0\ntransform 1 0 0 0 1 0\nbox -40 1947 18440 10000\n<< end >>\n')
    report={'scope':__doc__,'canonical_source_sha256':CANONICAL_SHA,'physical_source_sha256':hashlib.sha256(source.encode()).hexdigest(),
            'bias_mag_sha256':hashlib.sha256(bias.read_bytes()).hexdigest(),'physical_source_transform':'Remove ideal Vbias0V measurement source and alias ref_vdd to vdd; flatten five four-FET stages; no sizing changes',
            'inventory':{'FET':29,'MIM':7,'total':36},'electrical_executed':False,'status':'Physical gates pending'}
    if placement!='baseline':report['placement_variant']=placement
    def save(): (dest/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    save();magic_run(dest,generate_script(pdk,entries),'generate_cells',pdk)
    report['placement_drc']=(dest/'placement_drc.txt').read_text();save()
    if placement!='baseline' and not report['placement_drc'].startswith('DRC_ERRORS 0'):
        report['status']='Placement DRC failed; no routing/electrical promotion';save();return report
    pins=read_pins(dest,entries)
    (dest/'instance_pins.json').write_text(json.dumps(pins,indent=2)+'\n')
    magic_run(dest,'load clock_cells\nselect top cell\nflatten microrobot_clock\nload microrobot_clock\nsave microrobot_clock','flatten',pdk)
    mag=dest/'microrobot_clock.mag';mag.write_text('\n'.join(s for s in mag.read_text().splitlines() if not s.startswith('port '))+'\n')
    script,tracks=routing_script(entries,pins,routing=routing);(dest/'tracks.json').write_text(json.dumps(tracks,indent=2)+'\n')
    report['routing_variant']=routing;save()
    magic_run(dest,script,'route_extract',pdk)
    report['native_drc']=(dest/'drc.txt').read_text();report['native_drc_pass']=report['native_drc'].startswith('DRC_ERRORS 0');save()
    if not report['native_drc_pass']:
        report['status']='Native DRC failed; no LVS/electrical promotion';save();return report
    report['native_lvs_pass']=lvs(dest,dest/'physical_clock.spice',pdk,'lvs');save()
    if not report['native_lvs_pass']:
        report['status']='Native LVS failed; no electrical promotion';save();return report
    bad=dest/'negative_control.spice';bad.write_text(source.replace('X1_Xpi a raw','X1_Xpi a vdd'))
    report['negative_control_rejected']=not lvs(dest,bad,pdk,'negative_control_lvs');save()
    if not report['negative_control_rejected']:raise RuntimeError('LVS failed negative control')
    target=dest/'gds_roundtrip';target.mkdir()
    magic_run(target,'gds read ../microrobot_clock.gds\nload microrobot_clock\nselect top cell\nexpand\nbox values -40um 0um 650um 120um\ndrc check\ndrc catchup\nset f [open drc.txt w]\nputs $f "DRC_ERRORS [drc list count total]"\nputs $f [drc listall why]\nclose $f\nextract all\next2spice lvs\next2spice -o clock_lvs.spice','roundtrip',pdk)
    report['roundtrip_drc_pass']=(target/'drc.txt').read_text().startswith('DRC_ERRORS 0');report['roundtrip_lvs_pass']=lvs(target,dest/'physical_clock.spice',pdk,'lvs');save()
    if not (report['roundtrip_drc_pass'] and report['roundtrip_lvs_pass']):raise RuntimeError('GDS roundtrip failed')
    if (dest/'streamout_feedback.tcl').read_text().strip():raise RuntimeError('GDS streamout feedback')
    magic_run(dest,'load microrobot_clock\nselect top cell\nexpand\nextract all\next2sim labels on\next2sim\nextresist tolerance 10\nextresist\next2spice lvs\next2spice cthresh 0\next2spice extresist on\next2spice -o clock_rc.spice','extract_rc',pdk)
    rc=(dest/'clock_rc.spice').read_text();report['rc_resistors']=len(re.findall(r'^R\d+ ',rc,re.M));report['rc_capacitors']=len(re.findall(r'^C\d+ ',rc,re.M));report['status']='Physical gates passed; extracted electrical validation pending';save()
    return report


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--routing',choices=['baseline','stage_local'],default='baseline')
    parser.add_argument('--placement',choices=['baseline','compact_x'],default='baseline')
    args=parser.parse_args();print(json.dumps(run(args.output,routing=args.routing,placement=args.placement),indent=2))
