"""Flatten the exact hierarchical core reference, then group parallel MIMs."""
from pathlib import Path
import argparse,json,re
from scripts.group_parallel_mim import verify,group

def compact(root,source,work):
    root=Path(root).resolve();source=Path(source).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=False)
    text=source.read_text();blocks={}
    for m in re.finditer(r'(?ims)^\.subckt\s+(\S+)\s+([^\n]+)\n(.*?)^\.ends[^\n]*',text):
        blocks[m[1]]=(m[2].split(),m[3].splitlines())
    top='automx_cim_core_acquisition_proto';ports=blocks[top][0];rows=[]
    def emit(name,mapping,prefix):
        def node(value):return '0' if value=='0' else mapping.get(value,prefix+'__'+value)
        for line in blocks[name][1]:
            f=line.split()
            if not f or f[0].startswith('*'):continue
            assert f[0].startswith('X'),('Unsupported non-instance reference statement',line)
            if f[-1] in blocks:
                child=f[-1];pins=blocks[child][0];assert len(pins)==len(f)-2
                emit(child,dict(zip(pins,map(node,f[1:-1]))),prefix+'__'+f[0])
            else:
                index=next(i for i,x in enumerate(f) if x.startswith('sky130_fd_pr__'))
                rows.append('X'+prefix+'__'+f[0][1:]+' '+' '.join([*map(node,f[1:index]),*f[index:]]))
    emit(top,dict(zip(ports,ports)),'FLAT')
    full=work/'core_acquisition.flat.spice'
    full.write_text('* Exact hierarchical elaboration; original PDK leaf devices retained.\n.subckt '+top+' '+' '.join(ports)+'\n'+'\n'.join(rows)+'\n.ends '+top+'\n')
    proof=verify(root,work/'parallel_mim_160',copies=160);assert proof['status']=='PASS'
    grouped=work/'core_acquisition.spice';result=group(full,grouped,work/'parallel_mim_160/verification.json')
    assert result['original_mim_instances']==1288 and result['equivalent_mim_subcircuits']==16,result
    report={'status':'EXACT_SCHEMATIC_COMPACTION_READY','source':str(source),'full_elaborated_reference':str(full),'schematic':str(grouped),
        'leaf_devices':len(rows),'parallel_mim':result,'scope':'Exact elaboration and parallel intrinsic MIM R-C grouping with mismatch sampling disabled. Reference schematic, not extracted-wire PEX; actual physical GDS and complete PEX remain separate.'}
    (work/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('CORE_REFERENCE_COMPACTION_READY',len(rows),'leaves, 1288 -> 16 MIM subcircuits',flush=True);return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--source',type=Path,required=True);p.add_argument('--work',type=Path,required=True)
    a=p.parse_args();compact(a.root,a.source,a.work)
