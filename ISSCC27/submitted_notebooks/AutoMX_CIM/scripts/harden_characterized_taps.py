"""Implement the measured tap-choice repair and require actual routed retest."""
from pathlib import Path
import argparse,json,re,time
from scripts.harden_pulse_readout import build

def harden(root,source,diagnostic,work):
    root=Path(root).resolve();source=Path(source).resolve();diagnostic=Path(diagnostic).resolve();work=Path(work).resolve()
    measurement=json.loads(diagnostic.read_text());assert measurement['status']=='COUNTERFACTUAL_TAP_CHOICE_DIAGNOSTIC'
    selected={int(k):int(v['tap']) for k,v in measurement['selected'].items()}
    body=source.read_text();changed=[]
    def update(match):
        mag=int(match[2]);old=int(match[3]);new=selected.get(mag,old)
        if new!=old:changed.append({'magnitude':mag,'old_tap':old,'new_tap':new})
        return match[1]+str(new)
    body=re.sub(r'((?:pulse_index==(\d+)\s*\?\s*))(\d+)',update,body)
    assert changed
    work.mkdir(parents=True,exist_ok=False);candidate=work/'readout_characterized.sv';candidate.write_text(body)
    (work/'tap_selection.json').write_text(json.dumps({'changes':changed,'diagnostic':str(diagnostic),
        'qualification':'Diagnostic selects taps only; the newly implemented routed pulse must be measured again.'},indent=2)+'\n')
    start=time.monotonic();result=build(root,candidate,work/'physical')
    report={'status':'ROUTED_TAP_REPAIR_READY','hardening':result,'tap_changes':changed,'elapsed_s':time.monotonic()-start,
        'scope':'Fresh source-based child hardening. Actual delivered pulse, calibration transfer and native application qualification remain separate acceptance steps.'}
    (work/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('ROUTED_TAP_REPAIR_READY',changed,flush=True);return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--source',type=Path,required=True);p.add_argument('--diagnostic',type=Path,required=True);p.add_argument('--work',type=Path,required=True)
    a=p.parse_args();harden(a.root,a.source,a.diagnostic,a.work)
