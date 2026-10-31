"""Pair native core-PEX results across numerical shunt and timestep choices."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse,json,subprocess,sys,time
from scripts.run_electrical_qualification import case,profile

def run(root,work,jobs=4,pwm=None,core_views=None,core_pex=True):
    root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True);requests=[]
    for bank in (0,3):
        for pair in ((12,0),(6,6)):
            for rshunt,step in [(1e12,10),(1e14,.2)]:
                p=profile(bank,pwm,core_views=core_views);p.update(core_pex=core_pex,rshunt_ohm=rshunt,quiet_step_ns=step);requests.append(case(bank,pair,p))
    def one(item):
        i,c=item;folder=work/f'case_{i}';folder.mkdir(exist_ok=False);(folder/'case.json').write_text(json.dumps(c,indent=2)+'\n');start=time.monotonic()
        with (folder/'console.log').open('w') as log:
            q=subprocess.run([sys.executable,'-u',str(root/'scripts/qualified_cim_sar.py'),'--root',str(root),'--library',str(root/'tools/ngspice/libngspice.so'),'--work',str(folder),'--case',str(folder/'case.json')],cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=480)
        assert q.returncode==0,(folder,(folder/'console.log').read_text()[-800:])
        d=json.loads((folder/'summary.json').read_text());return {'case':c,'code':d['result_code_12bit'],'start_to_eoc_ns':d['start_to_eoc_s']*1e9,'elapsed_s':time.monotonic()-start}
    with ThreadPoolExecutor(max_workers=jobs) as pool:rows=list(pool.map(one,enumerate(requests)))
    deltas=[abs(rows[i]['code']-rows[i+1]['code']) for i in range(0,8,2)]
    report={'status':'PASS' if max(deltas)<=2 else 'NUMERICAL_SENSITIVITY','rows':rows,'max_code_change':max(deltas),'stimulus':'routed measured PWM' if pwm else 'ideal 50 ps unit',
       'core_model':'extracted-wire PEX' if core_pex else 'transistor reference; compact intrinsic MIM R-C',
       'scope':('Paired core-PEX points' if core_pex else 'Paired compact transistor-reference points')+': numerical shunt 1e12 to 1e14 ohm and quiet max step 10 ns to 0.2 ns; 0.2 ns cap around conversion boundaries. This checks numerical sensitivity at the sampled points.'}
    (work/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('NATIVE_CONVERGENCE',report['status'],'max_code_change',max(deltas),flush=True);return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--work',type=Path,required=True);p.add_argument('--jobs',type=int,default=4);p.add_argument('--pwm',type=Path);p.add_argument('--core-views',type=Path);a=p.parse_args();run(a.root,a.work,a.jobs,a.pwm,a.core_views)
