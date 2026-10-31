"""Add a physically connected MIM load bank for the measured routed PWM range."""
from pathlib import Path
import argparse,json,os,re,subprocess,time

LAYOUT_SOURCE=r'''import pya,json,re
l=pya.Layout();l.read(src);top=l.top_cell();old_dbu=l.dbu
pins={}
for layer in l.layer_indexes():
 for shape in top.shapes(layer).each():
  if shape.is_text():
   name=shape.text.string;point=[shape.text.x*l.dbu,shape.text.y*l.dbu]
   if name not in pins or point[1]>pins[name][1]:pins[name]=point
text=open(lefsrc).read()
for name,body in re.findall(r'(?ms)^\s*PIN\s+(BL[PN][0-3])\s*\n(.*?)^\s*END\s+\1\s*$',text):
 rects=[tuple(map(float,x)) for x in re.findall(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)',body)]
 rect=max(rects,key=lambda x:(x[1]+x[3])/2)
 pins[name]=[(rect[0]+rect[2])/2,(rect[1]+rect[3])/2]
l.read(leaf);assert l.dbu==old_dbu
unit=l.cell('automx_range_mim_unit');assert unit is not None
for layer in l.layer_indexes():
 for shape in list(unit.shapes(layer).each()):
  if shape.is_text():shape.delete()
def box(layer,x1,y1,x2,y2):
 top.shapes(l.layer(*layer)).insert(pya.DBox(x1,y1,x2,y2).to_itype(l.dbu))
def via4(x,y):
 box((71,44),x-.4,y-.4,x+.4,y+.4)
 for layer in ((71,20),(72,20)):box(layer,x-.8,y-.8,x+.8,y+.8)
def via3(x,y):
 box((70,44),x-.1,y-.1,x+.1,y+.1)
 for layer in ((70,20),(71,20)):box(layer,x-.3,y-.3,x+.3,y+.3)
count=0;connections=[]
for column in range(4):
 for polarity in range(2):
  name='BL'+('P' if polarity==0 else 'N')+str(column);ordinal=2*column+polarity
  x0=28+200*column+100*polarity;bus=x0-4;y0=280
  for row in range(14):
   y=y0+7*row
   for col in range(10):
    x=x0+8*col
    top.insert(pya.CellInstArray(unit.cell_index(),pya.Trans(round(x/l.dbu),round(y/l.dbu))))
    via4(x,y);box((71,20),x+2.37,y0-2.3,x+3.17,379)
    count+=1
   box((72,20),bus-.8,y-.8,x0+72+.8,y+.8);via4(bus,y)
  px,py=pins[name];channel=276-2*ordinal
  # Narrow M3 breakouts keep neighboring 1 um-spaced access points isolated.
  box((70,20),px-.2,py-.3,px+.2,channel+.3);via3(px,py);via3(px,channel)
  box((71,20),min(px,bus)-.8,channel-.8,max(px,bus)+.8,channel+.8)
  box((71,20),bus-.8,channel-.8,bus+.8,y0+91+.8)
  connections.append({'net':name,'original_pin_um':[px,py],'new_capacitors':140,'bus_x_um':bus,'channel_y_um':channel})
box((71,20),4,378,807,380)
box((72,20),4.1,158,5.9,379.8);via4(5,379)
top.flatten(True)
assert len(list(l.top_cells()))==1
l.write(out)
report={'added_mim_devices':count,'expected_total_mim_devices':1288,'pins':pins,'connections':connections,'bbox_um':[top.bbox().left*l.dbu,top.bbox().bottom*l.dbu,top.bbox().right*l.dbu,top.bbox().top*l.dbu]}
open(receipt,'w').write(json.dumps(report,indent=2))
'''

def native(args,work,name,env=None,timeout=180):
    start=time.monotonic();result=subprocess.run(list(map(str,args)),cwd=work,env=env,capture_output=True,text=True,timeout=timeout)
    log=Path(work)/(name+'.log');log.write_text(result.stdout+result.stderr)
    assert result.returncode==0,(name,(result.stdout+result.stderr)[-1800:])
    return result.stdout+result.stderr,time.monotonic()-start

def check_klayout(root,work):
    root=Path(root).resolve();work=Path(work).resolve();report=work/'klayout.xml'
    deck=root/'pdks/digital/sky130A/libs.tech/klayout/drc/sky130A_mr.drc'
    from scripts.standalone_runtime import container
    name='automx-core-drc-'+str(os.getpid())
    args=container(root,'klayout',['-b','-r',deck,'-rd','input='+str(work/'core.gds'),'-rd','report='+str(report),'-rd','beol=true','-rd','offgrid=true','-rd','feol=true','-rd','thr=4'],name,work)
    try:native(args,work,'klayout',timeout=45)
    except subprocess.TimeoutExpired as error:
        subprocess.run(['docker','stop','-t','1',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
        (work/'klayout.log').write_text('Bounded KLayout BEOL/off-grid run exceeded 45 seconds.\n')
        result={'status':'INCOMPLETE_TIMEOUT','violations':None}
    except AssertionError as error:
        result={'status':'INCOMPLETE_TOOL_ERROR','violations':None,'error':str(error)}
    else:
        from xml.etree import ElementTree as ET
        count=len(list(ET.parse(report).getroot().iter('item')))
        result={'status':'MEASURED_RULES_CLEAN' if count==0 else 'MEASURED_WITH_VIOLATIONS','violations':count}
    (work/'klayout_check.json').write_text(json.dumps(result,indent=2)+'\n');return result

def build(root,work):
    root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=False)
    pdk=root/'pdks/analog/sky130A';env=dict(os.environ,PDK_ROOT=str(root/'pdks/analog'))
    magic=['magic','-dnull','-noconsole','-rcfile',pdk/'libs.tech/magic/sky130A.magicrc']
    leaf=work/'leaf';leaf.mkdir();script=leaf/'generate.tcl'
    script.write_text('''crashbackups stop
load automx_range_mim_unit
box values 0 0 0 0
sky130::sky130_fd_pr__cap_mim_m3_1_draw [dict merge [sky130::sky130_fd_pr__cap_mim_m3_1_defaults] {w 4.2 l 4.2 nx 1 ny 1}]
box values -0.2um -0.2um 0.2um 0.2um
label BL center metal4
port make 1
box values 2.6um -0.2um 2.9um 0.2um
label VGND center metal4
port make 2
select top cell
drc on
drc check
drc catchup
puts "MIM_UNIT_DRC=[drc list count total]"
extract all
ext2spice lvs
ext2spice -o unit.spice
gds write unit.gds
quit -noprompt
''')
    log,_=native([*magic,script],leaf,'generation',env);assert 'MIM_UNIT_DRC=0' in log
    for line in log.splitlines():
        if line.startswith('Magic ') or line.startswith('MIM_UNIT_DRC='):print(line.split(' - Compiled')[0],flush=True)
    assert re.search(r'X0 BL VGND .*cap_mim_m3_1', (leaf/'unit.spice').read_text())
    script=work/'layout.py';script.write_text(LAYOUT_SOURCE)
    native(['klayout','-b','-r',script,'-rd','src='+str(root/'inputs/core.gds'),'-rd','lefsrc='+str(root/'inputs/core.lef'),'-rd','leaf='+str(leaf/'unit.gds'),'-rd','out='+str(work/'core.gds'),'-rd','receipt='+str(work/'layout.json')],work,'layout')
    layout=json.loads((work/'layout.json').read_text());assert layout['added_mim_devices']==1120
    reference=(root/'inputs/core_acquisition.spice').read_text();extra=[]
    for c in range(4):
        for pol in ('P','N'):
            extra.extend(f'XRANGE_{pol}{c}_{i} BL{pol}{c} VGND sky130_fd_pr__cap_mim_m3_1 W=4.2 L=4.2' for i in range(140))
    marker='.ends automx_cim_core_acquisition_proto';assert reference.count(marker)==1
    (work/'core_acquisition.spice').write_text(reference.replace(marker,'\n'.join(extra)+'\n'+marker))
    script=work/'extract.tcl';script.write_text(f'''crashbackups stop
gds read {{{work/'core.gds'}}}
load automx_cim_core_acquisition_proto
select top cell
drc on
drc check
drc catchup
puts "RANGE_CORE_DRC=[drc list count total]"
puts "RANGE_CORE_DRC_DETAILS=[drc listall why]"
extract do local
extract all
ext2spice lvs
ext2spice -o {{{work/'physical.spice'}}}
puts RANGE_CORE_EXTRACTION_DONE
quit -noprompt
''')
    log,elapsed=native([*magic,script],work,'extract',env,300)
    count=int(re.search(r'RANGE_CORE_DRC=(\d+)',log)[1])
    return finish_views(root,work,layout,count,elapsed)

def finish_views(root,work,layout=None,count=None,elapsed=0.):
    root=Path(root).resolve();work=Path(work).resolve();pdk=root/'pdks/analog/sky130A'
    env=dict(os.environ,PDK_ROOT=str(root/'pdks/analog'))
    layout=layout or json.loads((work/'layout.json').read_text())
    if count is None:count=int(re.search(r'RANGE_CORE_DRC=(\d+)',(work/'extract.log').read_text())[1])
    assert count==0,('Macro Magic DRC must pass',count)
    from scripts.flow2_adc_partition import ports
    cell='automx_cim_core_acquisition_proto'
    expected=ports((work/'core_acquisition.spice').read_text(),cell);actual=ports((work/'physical.spice').read_text(),cell)
    assert set(actual)==set(expected),('Extracted macro ports differ',actual,expected)
    native(['tclsh',root/'tools/netgen/lib/netgen/tcl/netgen.tcl','-batch','lvs',str(work/'physical.spice')+' '+cell,str(work/'core_acquisition.spice')+' '+cell,pdk/'libs.tech/netgen/sky130A_setup.tcl',work/'lvs.out'],work,'netgen',timeout=180)
    verdict=(work/'lvs.out').read_text();assert 'Circuits match uniquely.' in verdict,verdict[-1800:]
    for line in verdict.splitlines():
        if line.startswith('Final result:'):print(line,flush=True)
    extraction=work/'pex';extraction.mkdir(exist_ok=True);script=extraction/'extract.tcl'
    bbox=' '.join(f'{v:.9g}um' for v in layout['bbox_um'])
    script.write_text(f'''crashbackups stop
+drc off
+gds read {{{work/'core.gds'}}}
+load {cell}
+select top cell
+snap internal
+box values {bbox}
+property FIXED_BBOX [box values]
+lef write {{{work/'core.lef'}}}
+flatten {cell}_raw
+load {cell}_raw
+select top cell
+extract do local
+extract do unique
+extract do resistance
+extract all
+ext2sim labels on
+ext2sim
+extresist tolerance 10
+extresist all
+ext2spice lvs
+ext2spice scale off
+ext2spice cthresh 0.01
+ext2spice extresist on
+ext2spice short resistor
+ext2spice subcircuit on
+ext2spice subcircuit top on
+ext2spice -o {{{extraction/'raw.spice'}}}
+puts RANGE_CORE_RC_READY
+quit -noprompt
+'''.replace('\n+','\n'))
    log,pex_elapsed=native(['magic','-dnull','-noconsole','-rcfile',pdk/'libs.tech/magic/sky130A.magicrc',script],extraction,'extract',env,300)
    assert 'RANGE_CORE_RC_READY' in log
    text=(extraction/'raw.spice').read_text();actual=ports(text,cell+'_raw');assert set(actual)==set(expected),(actual,expected)
    text=re.sub(r'(?im)^\s*\.end\s*$','',text)
    ordered='\n.subckt '+cell+'_pex '+' '.join(expected)+'\nXRAW '+' '.join(actual)+' '+cell+'_raw\n.ends '+cell+'_pex\n'
    (work/'core_acquisition.pex.spice').write_text(text.rstrip()+ordered)
    from scripts.reduce_pex_resistors import reduce
    reduction=reduce(work/'core_acquisition.pex.spice',work/'core_acquisition.fast.pex.spice')
    from scripts.group_parallel_mim import verify,group
    parallel=verify(root,work/'parallel_mim_equivalence');assert parallel['status']=='PASS',parallel
    grouping=group(work/'core_acquisition.fast.pex.spice',work/'core_acquisition.grouped.pex.spice',work/'parallel_mim_equivalence/verification.json')
    rc={'resistors':len(re.findall(r'(?im)^R\S*\s',text)),'capacitors':len(re.findall(r'(?im)^C\S*\s',text))}
    assert rc['resistors']>0 and rc['capacitors']>0,rc
    lef=(work/'core.lef').read_text();lef_pins=re.findall(r'(?m)^\s*PIN\s+(\S+)\s*$',lef);assert set(lef_pins)==set(expected),(lef_pins,expected)
    size=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',lef);assert size
    dimensions=list(map(float,size.groups()));bbox=layout['bbox_um']
    assert all(abs(a-b)<.001 for a,b in zip(dimensions,[bbox[2]-bbox[0],bbox[3]-bbox[1]])),('LEF/GDS bounding boxes differ',dimensions,bbox)
    klayout=check_klayout(root,work)
    report={'status':'PHYSICAL_CORE_DRC_LVS_PEX_READY','views_dir':str(work),'added_bitline_mim_per_node':140,'total_bitline_mim_per_node':160,
        'macro_dimensions_um':dimensions,'magic_drc':count,'transistor_lvs':'PASS','layout':layout,'elapsed_extract_s':elapsed,'elapsed_pex_s':pex_elapsed,'distributed_rc_elements':rc,
        'klayout_beol_offgrid':klayout,
        'exact_resistor_reduction':reduction,'parallel_mim_equivalence':parallel,'parallel_mim_grouping':grouping,
        'scope':'Actual additional MIM geometry, named bitline/ground wiring, complete transistor LVS and distributed Magic RC. Electrical range/calibration and parent physical checks must pass before adoption.'}
    (work/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    from scripts.compact_core_reference import compact
    compacted=compact(root,work/'core_acquisition.spice',work/'compact_reference')
    from scripts.verify_compact_core_native import run as verify_compact
    native_equivalence=verify_compact(root,work/'core_acquisition.spice',compacted['schematic'],work/'compact_native_check')
    assert native_equivalence['status']=='PASS',native_equivalence
    from scripts.build_core_routing_abstract import build as routing_abstract
    routed=routing_abstract(root,work,work/'routing_views')
    (work/'routing_views/core_acquisition.compact.spice').symlink_to(compacted['schematic'])
    routed['native_reference_compaction']=compacted
    routed['native_compaction_verification']=native_equivalence
    (work/'routing_views/verification.json').write_text(json.dumps(routed,indent=2)+'\n')
    print('PHYSICAL_RANGE_CORE_PASS','Magic_DRC',count,'transistor_LVS=PASS','MIM_total=1288','RC',rc,flush=True);return routed

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);parser.add_argument('--work',type=Path,required=True);parser.add_argument('--finish',action='store_true');args=parser.parse_args();finish_views(args.root,args.work) if args.finish else build(args.root,args.work)
