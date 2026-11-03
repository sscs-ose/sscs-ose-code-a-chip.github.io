"""Route and check an isolated five-block parent using a candidate readout view."""
from pathlib import Path
import argparse,json,os,subprocess,sys,time,types
from scripts import standalone_runtime as runtime

WORDLINE_BUFFER_REPAIR_TCL=r'''source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
read
set block [ord::get_db_block]
set strong [[ord::get_db] findMaster sky130_fd_sc_hd__buf_16]
set core [$block findInst core_i]
set queue {}
foreach polarity {P N} {
    for {set row 0} {$row<4} {incr row} {
        lappend queue [[$core findITerm WL$polarity$row] getNet]
    }
}
set visited {};set changed {};set boundaries 0
while {[llength $queue]} {
    set net [lindex $queue 0];set queue [lrange $queue 1 end]
    set name [$net getName]
    if {[dict exists $visited $name]} {continue}
    dict set visited $name 1
    foreach pin [$net getITerms] {
        if {[[$pin getMTerm] getIoType] ne "OUTPUT"} {continue}
        set inst [$pin getInst];set instname [$inst getName]
        if {$instname eq "seq_i"} {incr boundaries;continue}
        set model [[$inst getMaster] getName]
        if {![regexp {^sky130_fd_sc_hd__(buf|clkbuf|dlymetal)[_0-9a-z]*$} $model]} {
            error "Refuse to replace non-buffer on delivered-wordline cone: $instname $model"
        }
        if {![dict exists $changed $instname]} {
            if {![$inst swapMaster $strong]} {error "Wordline buffer resize failed: $instname"}
            dict set changed $instname $model
            set_dont_touch [get_cells $instname]
        }
        lappend queue [[$inst findITerm A] getNet]
    }
}
if {$boundaries!=8 || [dict size $changed]<8} {error "Expected eight complete wordline buffer cones"}
detailed_placement
check_placement -verbose
puts "WORDLINE_BUFFER_DRIVE_REPAIR boundaries=$boundaries buffers=[dict size $changed] master=sky130_fd_sc_hd__buf_16"
write
'''

CORE_PARENT_PDN_CLEANUP_TCL = '# Remove only redundant parent PG shapes strictly inside the hard core.\n# The core\'s physical rails remain untouched; native macro LVS proves them.\nproc automx_core_parent_pdn_cleanup {} {\n    set block [ord::get_db_block]\n    set tech [ord::get_db_tech]\n    set u [$block getDbUnitsPerMicron]\n    set core [$block findInst core_i]\n    set b [$core getBBox]\n    set bounds [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]\n    foreach inst [$block getInsts] {\n        if {[[$inst getMaster] isBlock] || [$inst getPlacementStatus] == "NONE"} {continue}\n        set ib [$inst getBBox]\n        if {[automx_overlaps $bounds [list [$ib xMin] [$ib yMin] [$ib xMax] [$ib yMax]]]} {\n            error "Refuse PDN cleanup over a placed standard cell: [$inst getName]"\n        }\n    }\n    set remove {}\n    foreach name {VPWR VGND} {\n        foreach wire [[ $block findNet $name] getSWires] {\n            foreach shape [$wire getWires] {\n                if {[automx_covers $bounds [list [$shape xMin] [$shape yMin] [$shape xMax] [$shape yMax]]]} {\n                    lappend remove $shape\n                }\n            }\n        }\n    }\n    foreach shape $remove {odb::dbSBox_destroy $shape}\n    # This M5 landing lies on the additive core\'s actual VGND spine, checked\n    # against its GDS. The other end lands on the continuous external M4 rail.\n    set ground [$block findNet VGND]\n    set wire [lindex [$ground getSWires] 0]\n    set m5 [$tech findLayer met5]\n    set via [$tech findVia M4M5_PR]\n    set plate {24.34 203.92 51.9 205.52}\n    foreach shape [automx_special_shapes $block met5] {\n        if {[lindex $shape 0] ne "VGND" && [automx_overlaps [lrange $shape 1 4] [automx_dbu $u $plate 1.6]]} {\n            error "New core ground plate conflicts with [lindex $shape 0]"\n        }\n    }\n    odb::dbSBox_create $wire $m5 {*}[automx_dbu $u $plate] STRIPE 1\n    odb::dbSBox_create $wire $via [expr {round(25.14*$u)}] [expr {round(204.72*$u)}] STRIPE\n    puts "CORE_PARENT_PDN_CLEANUP removed=[llength $remove] independent_macro_rails_retained=1 external_ground_M5=$plate"\n}\nrename automx_ground_bridges automx_ground_bridges_before_core_cleanup\nproc automx_ground_bridges {} {\n    automx_ground_bridges_before_core_cleanup\n    automx_core_parent_pdn_cleanup\n}\n'

def item(path):
    path=Path(path);return {'path':str(path),'bytes':path.stat().st_size if path.is_file() else None}

class Flow:
    def __init__(self,root,work):self.root=Path(root).resolve();self.work=Path(work).resolve();self.outputs={};self.receipts={}
    def run(self,name,args,inputs=(),outputs=(),cwd=None,timeout_s=180):
        cwd=Path(cwd or self.work);log=cwd/(name+'.native.log');started=time.monotonic()
        try:
            with log.open('w') as stream:q=subprocess.run(list(map(str,args)),cwd=cwd,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout_s)
            code=q.returncode
        except subprocess.TimeoutExpired:code=124
        report={'returncode':code,'elapsed_s':time.monotonic()-started,'log':item(log),'command':list(map(str,args))}
        (cwd/(name+'.step.json')).write_text(json.dumps(report,indent=2)+'\n')
        if code:raise RuntimeError(f'{name}: exit {code}; {log}')
        assert all(Path(p).is_file() for p in outputs),(name,outputs)
        print('PARENT_CHECK',name,'PASS',round(report['elapsed_s'],2),flush=True);return report

def run(root,readout,work,core_views=None,upsize_wordline_buffers=None):
    root=Path(root).resolve();readout=Path(readout).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    while not readout.is_file():
        if time.monotonic()-started>5400:raise TimeoutError('Candidate hardening not complete')
        time.sleep(5)
    ro=json.loads(readout.read_text());assert ro['status']=='PASS'
    assert ro['setup_slack_ns']>=0 and ro['hold_slack_ns']>=0,('Child timing must pass before parent qualification',ro)
    library=root/'inputs/digital_blocks';frozen=json.loads((library/'source_library.json').read_text())
    mha=next(dict(v) for v in frozen['blocks'] if v['name']=='mha')
    for key in ('source','gds','lef','odb','lib','mapped_netlist','spef'):mha[key]=str(library/mha[key])
    blocks=[ro,mha];(work/'digital_blocks').mkdir(exist_ok=True)
    (work/'digital_blocks/hardening.json').write_text(json.dumps({'status':'PASS','blocks':blocks},indent=2)+'\n')
    design,config=runtime.prepare_pnr(root,work,blocks)
    if core_views:
        core_views=Path(core_views).resolve()
        core=json.loads((core_views/'verification.json').read_text());assert core['status']=='PHYSICAL_CORE_DRC_LVS_PEX_READY'
        config['EXTRA_LEFS'][0]=str(core_views/'core.lef');config['EXTRA_GDS_FILES'][0]=str(core_views/'core.gds')
        (design/'config.json').write_text(json.dumps(config,indent=2)+'\n')
        if core.get('parent_pg_cleanup_required'):
            policy=Path(config['FP_PDN_CFG']);policy.write_text(policy.read_text()+CORE_PARENT_PDN_CLEANUP_TCL)
    name='automx-closure-parent-'+str(os.getpid())
    policy=root/'inputs/wordline_routing_policy.json'
    if upsize_wordline_buffers is None:
        upsize_wordline_buffers=policy.is_file() and json.loads(policy.read_text()).get('upsize_wordline_buffers',False)
    if upsize_wordline_buffers:
        repair=work/'wordline_buffer_repair.tcl';repair.write_text(WORDLINE_BUFFER_REPAIR_TCL)
        script=work/'route_wordline_repair.tcl'
        script.write_text('lappend ::auto_path /openlane/scripts\npackage require openlane\nprep -design {'+str(design)+'} -config_file {'+str(design/'config.json')+'} -tag cold\n'+
            'set ::env(AUTOMX_WORDLINE_REPAIR) {'+str(repair)+'}\n'+r'''
rename run_resizer_timing_routing run_resizer_timing_routing_before_wordline
proc run_resizer_timing_routing {args} {
    run_resizer_timing_routing_before_wordline {*}$args
    run_openroad_script $::env(AUTOMX_WORDLINE_REPAIR) -indexed_log $::env(routing_logs)/wordline_drive.log -save "dir=$::env(routing_tmpfiles),def,sdc,odb,netlist,powered_netlist"
}
run_synthesis
run_floorplan
run_placement
run_cts
run_resizer_timing
run_routing
run_magic
run_klayout
save_final_views
save_state
puts WORDLINE_DRIVE_PARENT_ROUTED
''')
        arguments=['-interactive','-file',script]
    else:arguments=['-design',design,'-config_file',design/'config.json','-tag','cold']
    args=runtime.container(root,'/openlane/flow.tcl',arguments,name,'/openlane')
    log=design.parent/'native.log';stream=log.open('w');process=subprocess.Popen(args,stdout=stream,stderr=subprocess.STDOUT)
    runtime.PNR={'process':process,'stream':stream,'command':args,'log':log,'started':time.monotonic(),'design':design,'run':design/'runs/cold','config':config,'name':name,'root':root}
    support=types.ModuleType('automx_nb_inline_v1.support');support.item=item
    sys.modules['automx_nb_inline_v1.support']=support
    flow=Flow(root,work)
    runtime.wait_pnr(flow);runtime.streamout(flow);runtime.power(flow);runtime.lvs(flow);runtime.hierarchical_timing(flow)
    timing=flow.outputs['nominal_timing'];assert timing['setup_slack_ns']>=0 and timing['hold_slack_ns']>=0,timing
    if upsize_wordline_buffers:
        import re
        drive_log=design/'runs/cold/logs/routing/wordline_drive.log'
        found=re.search(r'WORDLINE_BUFFER_DRIVE_REPAIR boundaries=8 buffers=(\d+) master=sky130_fd_sc_hd__buf_16',drive_log.read_text())
        assert found and int(found[1])>=8,'Missing executed wordline drive repair'
        print(found[0],flush=True)
    runtime.audit_gds(flow)
    report={'status':'PASS','elapsed_s':time.monotonic()-started,'outputs':flow.outputs,'readout_source':ro['source'],'core_views':str(core_views) if core_views else None,'wordline_buffer_drive_repair':bool(upsize_wordline_buffers),'scope':'Fresh isolated five-block parent; actual RC hierarchical TT STA, rails and signal macro-boundary LVS. Bounded foundry DRC status is reported separately.'}
    (work/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('CANDIDATE_PARENT_PASS',json.dumps(timing),flush=True);return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--readout',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--core-views',type=Path);a=p.parse_args();run(a.root,a.readout,a.work,a.core_views)
