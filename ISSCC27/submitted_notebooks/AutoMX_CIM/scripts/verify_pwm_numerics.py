"""Compare the practical pulse-cone integration with independent finer transients."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse,json,shutil,subprocess,sys
import numpy as np
from scripts.flow2_waveforms import read_raw

def characterize(raw,node):
    t=raw['time'];v=raw['v('+node.lower()+')'];high=(t>4e-9)&(v>.9)
    edges=[]
    for i in np.flatnonzero(np.diff(high.astype(int))):
        if t[i]>=4e-9:edges.append(t[i]+(.9-v[i])*(t[i+1]-t[i])/(v[i+1]-v[i]))
    width=(edges[1]-edges[0])*1e12 if len(edges)>=2 else 0.
    keep=t>4e-9
    area=float(np.trapezoid(v[keep],t[keep]) if hasattr(np,'trapezoid') else np.trapz(v[keep],t[keep]))
    return {'width_ps':width,'area_v_s':area,'peak_v':float(v[keep].max())}

def run(root,pwm,work,jobs=4):
    root=Path(root).resolve();pwm=Path(pwm).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=False)
    original=json.loads((pwm/'verification.json').read_text());nodes=original['cone']['output_nodes']
    selected=[r for r in original['measurements'] if (r['row'],r['negative'],r['magnitude']) in [(0,False,1),(0,False,12),(3,True,1),(3,True,12)]]
    assert len(selected)==4
    def one(row):
        folder=work/f"row{row['row']}_{'n' if row['negative'] else 'p'}_{row['magnitude']}";folder.mkdir()
        shutil.copy2(Path(row['folder'])/'pulse.spice',folder/'pulse.spice')
        args=[sys.executable,str(root/'scripts/measure_physical_pwm.py'),'--worker',str(folder),'--library',str(root/'tools/ngspice/libngspice.so'),'--max-step-ps','25','--reltol','0.0001']
        with (folder/'console.log').open('w') as log:result=subprocess.run(args,cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=900)
        assert result.returncode==0,(folder,(folder/'console.log').read_text()[-1000:])
        node=nodes['WL'+('N' if row['negative'] else 'P')+str(row['row'])]
        coarse=characterize(read_raw(Path(row['folder'])/'pulse.raw'),node);fine=characterize(read_raw(folder/'pulse.raw'),node)
        width=abs(coarse['width_ps']-fine['width_ps']);area=abs(coarse['area_v_s']/fine['area_v_s']-1)
        return {'row':row['row'],'negative':row['negative'],'magnitude':row['magnitude'],'practical':coarse,'fine':fine,
            'width_difference_ps':width,'relative_area_difference':area,'pass':bool(width<=max(10.,.02*fine['width_ps']) and area<=.01)}
    with ThreadPoolExecutor(max_workers=jobs) as pool:rows=list(pool.map(one,selected))
    result={'status':'PASS' if all(r['pass'] for r in rows) else 'NUMERICAL_SENSITIVITY','rows':rows,
        'scope':'Four actual routed-cone early/late-sign samples: practical max step 100 ps/reltol 1e-3 versus 25 ps/1e-4. Acceptance: <=1% pulse voltage-area change and <=max(10 ps,2%) width change. A sampled numerical check, not noise/yield qualification.'}
    (work/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print('PWM_NUMERICAL_SENSITIVITY',result['status'],flush=True);return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);parser.add_argument('--pwm',type=Path,required=True);parser.add_argument('--work',type=Path,required=True);parser.add_argument('--jobs',type=int,default=4);args=parser.parse_args();run(args.root,args.pwm,args.work,args.jobs)
