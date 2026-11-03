"""Check current-run MHA simulation, analog correspondence and retained physical logic."""
from pathlib import Path
from datetime import datetime,timezone
import json,re,subprocess,sys
import nbformat


def verify(root):
    root=Path(root).resolve();run=max((root/'runs').glob('fresh_*'),key=lambda p:p.name)
    work=run/'full_native/full_native'
    execution=json.loads((root/'standalone_execution.json').read_text())
    assert execution['status']=='ALL_CODE_CELLS_EXECUTED' and not execution['errors']
    ip=json.loads((work/'mha_ip/verification.json').read_text())
    bridge=json.loads((work/'mha_ip_measured_comparison.json').read_text())
    syn=json.loads((work/'mha_ip/synthesis/synthesis.json').read_text())
    manifest=json.loads((work/'runall_manifest.json').read_text())
    assert ip['status']==bridge['status']==syn['status']=='PASS'
    assert ip['test_cases']==98 and ip['checked_output_values']==784 and ip['bit_exact_errors']==0
    assert ip['softmax_score_differences_checked']==18433 and ip['softmax_absolute_probability_error_max']<.0005
    assert bridge['rtl_matches_measured_qkv'] and bridge['rtl_matches_measured_context'] and bridge['rtl_matches_measured_output']
    assert bridge['relative_l2_quantized']==0
    assert all(key in manifest['views'] for key in ('mha_rtl_verification','mha_rtl_synthesis','mha_rtl_measured_comparison'))
    log=(work/'mha_ip/integration.log').read_text()
    for marker in ('MHA_CIM_SAR_RTL_TOP_PASS vectors=8 adc_conversions=64','MHA_OWNER_LOCK_CALIBRATION_AND_BACKPRESSURE_PASS','MHA_TOP_DIRECT_CIM_SAR_MODE_PASS'):
        assert marker in log,marker
    book=nbformat.read(root/'AutoMX_CIM_Code_a_Chip.executed.ipynb',4)
    for name in ('rtl-source','binding-source','fixtures','verify','comparison'):
        cell=next(c for c in book.cells if c.id=='mha-ip-'+name)
        assert cell.execution_count is not None and cell.outputs
    config=json.loads((work/'cold_pnr/design/config.json').read_text())
    hardening_path=work/'digital_blocks/hardening.json'
    hardening=json.loads(hardening_path.read_text()) if hardening_path.is_file() else None
    if hardening is None:assert str(root/'ip/automx_mha/rtl/automx_mha_ip.sv') in config['VERILOG_FILES']
    else:
        assert hardening['status']=='PASS' and len(hardening['blocks'])==2
        for block in hardening['blocks']:
            assert block['routed_drc_violations']==0 and all(v=='PASS' for v in block['power_rails'].values())
            source=root/('ip/automx_mha/rtl/automx_mha_ip.sv' if block['name']=='mha' else 'rtl/automx_cim_readout_seq.sv')
            assert source.read_bytes()==Path(block['source']).read_bytes()
    physical=work/'mha_ip/physical';physical.mkdir(exist_ok=True)
    script=physical/'inventory.py';out=physical/'inventory.json'
    script.write_text('''import odb,json,sys
from pathlib import Path
p=Path(sys.argv[1]);db=odb.dbDatabase.create();odb.read_db(db,str(p));block=db.getChip().getBlock()
nets=[n for n in block.getNets() if 'mha_i.' in n.getName()]
connected={it.getInst().getName() for n in nets for it in n.getITerms()}
ports=[bt.getName() for bt in block.getBTerms() if bt.getName().startswith('mha_')]
macros={i.getName():{'master':i.getMaster().getName(),'location_dbu':i.getLocation(),'orientation':i.getOrient()} for i in block.getInsts() if i.getMaster().isBlock()}
children={}
for name,path in json.loads(sys.argv[3]).items():
    child=odb.dbDatabase.create();odb.read_db(child,path);cb=child.getChip().getBlock();rect=cb.getDieArea();du=cb.getDbUnitsPerMicron()
    children[name]={'instances':len(list(cb.getInsts())),'nets':len(list(cb.getNets())),'size_um':[rect.dx()/du,rect.dy()/du]}
value={'digital_blocks':children,'mha_internal_nets':len(nets),'digital_cells_on_mha_nets':len(connected),'mha_ports':ports,'hard_macros':macros,'dbu_per_um':block.getDbUnitsPerMicron()}
Path(sys.argv[2]).write_text(json.dumps(value,indent=2)+'\\n');print(json.dumps(value))
''')
    if str(root) not in sys.path:sys.path.insert(0,str(root))
    from scripts.standalone_runtime import container
    odb=work/'cold_pnr/design/runs/cold/results/routing/automx_cim_mixed_signal_proto.odb'
    command=container(root,'openroad',['-exit','-python',script,odb,out,json.dumps({v['name']:v['odb'] for v in hardening['blocks']} if hardening else {})],
                      'automx-mha-inventory-'+str(__import__('os').getpid()),physical)
    result=subprocess.run(command,capture_output=True,text=True,timeout=90)
    (physical/'native.log').write_text(result.stdout+result.stderr)
    assert result.returncode==0,(result.stdout+result.stderr)[-2000:]
    inventory=json.loads(out.read_text())
    assert hardening is not None or (inventory['mha_internal_nets']>100 and inventory['digital_cells_on_mha_nets']>100),inventory
    assert {'mha_mode_i','mha_req_valid_i','mha_rsp_valid_o','mha_rsp_ready_i','mha_busy_o','mha_fault_o'}.issubset(inventory['mha_ports'])
    if hardening:
        for v in hardening['blocks']:
            child=inventory['digital_blocks'][v['name']]
            assert child['instances']>100 and child['nets']>100
            assert child['size_um']==[v['width_um'],v['height_um']]
        floorplan=json.loads((work/'block_floorplan.json').read_text())
        assert floorplan['status']=='PASS' and len(floorplan['blocks'])==5
    u=inventory['dbu_per_um'];expected={'core_i':(50,50),'condition_i':(1100,50),'adc_i':(3100,50)}
    if hardening is not None:expected.update(mha_i=(2250,800),seq_i=(800,450))
    assert set(inventory['hard_macros'])==set(expected)
    for name,(x,y) in expected.items():
        assert inventory['hard_macros'][name]['location_dbu']==[x*u,y*u]
        assert inventory['hard_macros'][name]['orientation']=='R0'
    drc=re.findall(r'Number of violations = (\d+)',max((work/'cold_pnr/design/runs/cold/logs/routing').glob('*-detailed.log')).read_text())
    assert drc and int(drc[-1])==0
    assert 'Final result: Circuits match uniquely.' in (work/'signal_lvs/netgen.log').read_text()
    assert json.loads((work/'power/power.json').read_text())['rails']=={'VPWR':'PASS','VGND':'PASS'}
    wirelength=re.findall(r'^Total wire length = ([\d.]+) um\.',max((work/'cold_pnr/design/runs/cold/logs/routing').glob('*-detailed.log')).read_text(),re.M)
    report={'status':'PASS','run':str(run),'checked_utc':datetime.now(timezone.utc).isoformat(),
       'unit':ip,'native_measurement_bridge':bridge,'synthesis':syn,'physical':inventory,'hardening':hardening,
       'routing_violations':0,'detailed_wirelength_um':float(wirelength[-1]),'signal_lvs_match':True,'power_rails_connected':True,
       'scope':'MHA/readout hard macros in routed mixed top; hierarchy checked from gate netlists and child/parent RC; native analog measurements compared with observed RTL tensors; full-readout functional simulation uses ADC response fixture.'}
    (root/'docs/mha_ip_validation_20261027.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('unit','synthesis','physical')},indent=2))
    print('DIGITAL_HARD_MACRO_CONTENTS',inventory['digital_blocks'])
    return report

if __name__=='__main__':verify(Path(__file__).resolve().parents[1])
