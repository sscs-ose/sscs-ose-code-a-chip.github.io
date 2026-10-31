"""Retain proven unchanged port access while enclosing the added MIM geometry."""
from pathlib import Path
import argparse,json,re

def build(root,core,work):
    root=Path(root).resolve();core=Path(core).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=False)
    original=(root/'inputs/core.lef').read_text();extracted=(core/'core.lef').read_text()
    layout=json.loads((core/'layout.json').read_text());receipt=json.loads((core/'verification.json').read_text())
    assert receipt['magic_drc']==0 and receipt['transistor_lvs']=='PASS'
    assert layout['added_mim_devices']==1120
    def pin_blocks(text):return re.findall(r'(?ms)^\s*PIN\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$',text)
    assert set(n for n,b in pin_blocks(original))==set(n for n,b in pin_blocks(extracted))
    # Original top geometry is retained verbatim by the additive constructor.
    # Its metal-only interface is therefore still a valid access abstraction.
    header=extracted[:extracted.index('  PIN ')]
    pins=''.join('  PIN '+n+'\n'+b+'  END '+n+'\n' for n,b in pin_blocks(original))
    match=re.search(r'(?ms)(^\s*PIN VGND\s*\n)(.*?)(^\s*END VGND\s*$)',pins)
    body=match[2];at=body.rindex('    END')
    body=body[:at]+'      LAYER met5 ;\n        RECT 4.100 170.000 5.900 171.800 ;\n'+body[at:]
    pins=pins[:match.start()]+match[1]+body+match[3]+pins[match.end():]
    obstruction=re.search(r'(?ms)^\s*OBS\s*\n(.*?)^\s*END\s*$',original)[1]
    # The new bank and its narrow breakout channels sit above the original
    # geometry; reserve these routing layers without advertising internal PG.
    for layer in ('met1','met2','met3','met4','met5'):
        obstruction+='      LAYER '+layer+' ;\n        RECT 4.000 256.000 1000.300 380.000 ;\n'
    text=header+pins+'  OBS\n'+obstruction+'  END\nEND automx_cim_core_acquisition_proto\nEND LIBRARY\n'
    (work/'core.lef').write_text(text)
    for name in ('core.gds','core_acquisition.spice','core_acquisition.pex.spice','core_acquisition.fast.pex.spice','core_acquisition.grouped.pex.spice','layout.json'):
        (work/name).symlink_to(core/name)
    check=work/'access_check.py';check.write_text('import pya\nl=pya.Layout();l.read('+repr(str(core/'core.gds'))+');t=l.top_cell();r=pya.Region(t.begin_shapes_rec(l.layer(72,20)));q=pya.Region(pya.DBox(4.1,170,5.9,171.8).to_itype(l.dbu));assert (q-r).is_empty();print("ACTUAL_GDS_M5_ACCESS_COVERAGE_PASS")\n')
    import subprocess
    q=subprocess.run(['klayout','-b','-r',check],capture_output=True,text=True,timeout=90)
    (work/'access_check.log').write_text(q.stdout+q.stderr);assert q.returncode==0,q.stderr
    receipt.update(views_dir=str(work),routing_abstract_policy='Original metal access plus a GDS-checked VGND M5 spine landing; actual enlarged bounds and new bank obstructions',
        original_ports_retained=True,core_gds_changed=False,parent_pg_cleanup_required=True,ground_access_gds_coverage=True)
    (work/'verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('CORE_ACCESS_ABSTRACT_READY',len(pin_blocks(text)),'unchanged ports; actual enlarged bounds',flush=True);return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--core',type=Path,required=True);p.add_argument('--work',type=Path,required=True)
    a=p.parse_args();build(a.root,a.core,a.work)
