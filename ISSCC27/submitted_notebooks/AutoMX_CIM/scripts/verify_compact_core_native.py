"""Compare reference and compact core models through the same live SAR loop."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json,subprocess,sys,time
from scripts.run_electrical_qualification import case,profile

def run(root,reference,compacted,work,jobs=4):
    root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=False)
    requests=[]
    for model,source in enumerate((reference,compacted)):
        for pair in ((0,0),(12,0)):
            p=profile(0);p.update(core_pex=False,core_schematic=str(Path(source).resolve()),rshunt_ohm=1e14)
            request=case(0,pair,p);request['pwm_unit_ps']=400;requests.append((model,pair,request))
    def measure(item):
        model,pair,request=item;folder=work/f'm{model}_a{pair[0]}';folder.mkdir()
        (folder/'case.json').write_text(json.dumps(request,indent=2)+'\n');start=time.monotonic()
        with (folder/'console.log').open('w') as stream:
            result=subprocess.run([sys.executable,str(root/'scripts/qualified_cim_sar.py'),'--root',str(root),'--library',str(root/'tools/ngspice/libngspice.so'),
                '--work',str(folder),'--case',str(folder/'case.json')],cwd=root,stdout=stream,stderr=subprocess.STDOUT,timeout=180)
        assert result.returncode==0,folder
        value=json.loads((folder/'summary.json').read_text())
        return {'model':model,'activation':pair[0],'code':value['result_code_12bit'],'input_diff_v':value['measured_input_diff_v'],'elapsed_s':time.monotonic()-start}
    with ThreadPoolExecutor(max_workers=jobs) as pool:rows=list(pool.map(measure,requests))
    changes=[abs(next(r['code'] for r in rows if r['model']==0 and r['activation']==a)-next(r['code'] for r in rows if r['model']==1 and r['activation']==a)) for a in (0,12)]
    report={'status':'PASS' if max(changes)<=1 else 'NUMERICAL_DIFFERENCE','rows':rows,'max_code_delta':max(changes),
        'scope':'Two zero/single-row core/SAR model-equivalence cases: full hierarchical reference versus exact elaboration/parallel-MIM compaction. Intrinsic MC0 R-C retained. Both use rshunt=1e14 and an ideal 400ps unit for this model comparison, independently of routed-pulse qualification.'}
    (work/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('COMPACT_CORE_NATIVE_EQUIVALENCE',report['status'],'max_code_delta',max(changes),flush=True);return report
