"""Verify a published mirror against its explicitly declared execution root."""
from pathlib import Path
import argparse,json,subprocess,sys

def verify(root):
    root=Path(root).resolve();manifest=json.loads((root/'CURRENT_RELEASE.json').read_text())
    verified=Path(manifest['execution_root']).resolve()
    report=json.loads(Path(manifest['execution_receipt']).read_text())
    assert report['status'] in ('VERIFIED_MEASURED_PROTOTYPE_RELEASE','VERIFIED_ROUTED_PARTITION_RELEASE')
    assert all((root/n).read_bytes()==(verified/n).read_bytes() for n in manifest['mirrored_files'])
    checks=[]
    for name in ('verify_standalone_run.py','verify_measured_costs.py','verify_mha_ip_run.py'):
        command=[sys.executable,str(verified/'scripts'/name)]
        if name=='verify_standalone_run.py':command.append(str(verified))
        q=subprocess.run(command,cwd=verified,capture_output=True,text=True,timeout=600)
        log=root/'experiments/closure_20261028'/('mirror_'+Path(name).stem+'.log');log.write_text(q.stdout+q.stderr)
        assert q.returncode==0,(name,str(log));checks.append(name)
    (verified/'LATEST_RUN.json').write_text(json.dumps({'run':report['fresh_run'],'execution_root':str(verified),'top_gds':str(verified/'exports/AutoMX_CIM_five_block_top.gds'),'manifest':str(Path(report['fresh_run'])/'full_native/full_native/runall_manifest.json'),'release_validation':manifest['execution_receipt']},indent=2)+'\n')
    result={'status':'VERIFIED_DECLARED_EXECUTION_AND_IDENTICAL_MIRROR','entry_root':str(root),'execution_root':str(verified),
        'compared_files':len(manifest['mirrored_files']),'independent_checks':checks,
        'scope':'Execution is attributed to its actual independent folder; all mirrored source and export bytes match. No new execution in the entry folder is implied.'}
    print(json.dumps(result,indent=2));return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args();verify(a.root)
