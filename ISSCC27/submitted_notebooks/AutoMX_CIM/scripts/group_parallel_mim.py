"""Verify and apply the simulator's exact parallel multiplicity for identical MIMs."""
from pathlib import Path
from collections import defaultdict
import argparse,json,re
import numpy as np

def verify(root,work,copies=140):
    from scripts.portable_cim_sar import SharedSpice
    root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=False);rows=[]
    for name,corner,supply,temp in [('tt','tt',1.8,25),('ss','ss',1.62,70),('ff','ff',1.95,0)]:
        folder=work/name;folder.mkdir();deck=folder/'compare.spice'
        text=['Explicit versus parallel-multiplied PDK MIM',f'.lib "{root}/pdks/analog/sky130A/libs.tech/ngspice/sky130.lib.spice" {corner}',
            '.param MC_MM_SWITCH=0',f'.temp {temp}', '.option klu method=gear reltol=1e-6 abstol=1e-15',
            f'VA A 0 PWL(0 0 1n 0 2n {supply} 5n {supply})',f'VB B 0 PWL(0 0 1n 0 2n {supply} 5n {supply})']
        text.extend(f'X{i} A 0 sky130_fd_pr__cap_mim_m3_1 w=4.2 l=4.2' for i in range(copies))
        text.extend([f'XPAR B 0 sky130_fd_pr__cap_mim_m3_1 w=4.2 l=4.2 m={copies}','.save i(VA) i(VB)','.end']);deck.write_text('\n'.join(text)+'\n')
        with (folder/'ngspice.log').open('w') as log:
            spice=SharedSpice(root/'tools/ngspice/libngspice.so',log)
            for command in ('set ngbehavior=hsa','set skywaterpdk','set num_threads=1','set noinit','source '+str(deck),'option klu','tran 10p 5n 0 20p'):spice.command(command)
            t=spice.vector('time').copy();a=spice.vector('i(VA)').copy();b=spice.vector('i(VB)').copy();assert t[-1]>=4.99e-9
            integral=np.trapezoid if hasattr(np,'trapezoid') else np.trapz
            relative=float(np.max(np.abs(a-b))/(np.max(np.abs(a))+1e-30));area=float(abs(integral(a,t)/integral(b,t)-1))
            rows.append({'condition':name,'max_current_difference_fraction':relative,'charge_difference_fraction':area,'pass':relative<1e-4 and area<1e-5})
            spice.command('destroy all')
    result={'status':'PASS' if all(r['pass'] for r in rows) else 'MIM_MULTIPLICITY_MISMATCH','rows':rows,
        'copies':copies,'scope':f'{copies} explicit PDK MIM R-C subcircuits versus one identical subcircuit with m={copies}; three process/supply/temperature points, MC_MM_SWITCH=0. Both intrinsic series resistors and the capacitor are retained.'}
    (work/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print('PARALLEL_MIM_EQUIVALENCE',result['status'],rows,flush=True);return result

def group(source,target,proof):
    source=Path(source).resolve();target=Path(target).resolve();check=json.loads(Path(proof).read_text());assert check['status']=='PASS'
    lines=source.read_text().splitlines();groups=defaultdict(list);scope=''
    for i,line in enumerate(lines):
        f=line.split()
        if f and f[0].lower()=='.subckt':scope=f[1]
        if f and f[0].lower()=='.ends':scope=''
        if f and f[0].startswith('X') and 'sky130_fd_pr__cap_mim_m3_1' in f:
            assert not any(v.startswith('m=') for v in f[1:]),line
            groups[(scope,tuple(f[1:]))].append(i)
    replacements={};removed=set();mapping=[]
    for n,((scope,pins),indices) in enumerate(groups.items()):
        if len(indices)==1:continue
        replacements[indices[0]]='XPARALLEL_'+str(n)+' '+' '.join(pins)+' m='+str(len(indices));removed.update(indices[1:])
        mapping.append({'subcircuit':scope,'equivalent':f'XPARALLEL_{n}','multiplicity':len(indices),'original_instances':[lines[i].split()[0] for i in indices]})
    target.write_text('\n'.join(replacements.get(i,line) for i,line in enumerate(lines) if i not in removed)+'\n')
    report={'status':'PASS','source':str(source),'target':str(target),'original_mim_instances':sum(map(len,groups.values())),
        'equivalent_mim_subcircuits':len(groups),'mapping':mapping,'equivalence_proof':str(Path(proof).resolve()),'required_mc_mm_switch':0,
        'scope':'Only identical MIM instances on the same two nodes are grouped. The validated simulator multiplicity retains the parallel intrinsic R-C network; physical GDS and the full extracted netlist remain unchanged.'}
    target.with_suffix('.groups.json').write_text(json.dumps(report,indent=2)+'\n');print('MIM_PARALLEL_GROUPING',report['original_mim_instances'],'->',len(groups),flush=True);return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);parser.add_argument('--work',type=Path,required=True);args=parser.parse_args();verify(args.root,args.work)
