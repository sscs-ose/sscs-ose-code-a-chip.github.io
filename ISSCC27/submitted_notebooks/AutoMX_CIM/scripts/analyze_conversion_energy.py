"""Integrate measured supply currents in explicit acquisition/conversion windows."""
from pathlib import Path
import argparse,csv,gzip,json,tempfile
import numpy as np
from scripts.flow2_waveforms import read_raw

def integrate(time,values,begin,end):
    keep=(time>begin)&(time<end);x=np.r_[begin,time[keep],end];y=np.r_[np.interp(begin,time,values),values[keep],np.interp(end,time,values)]
    return float(np.trapezoid(y,x) if hasattr(np,'trapezoid') else np.trapz(y,x))

def measure_case(folder):
    folder=Path(folder);report=json.loads((folder/'summary.json').read_text())
    if (folder/'waveforms.npz').exists():
        with np.load(folder/'waveforms.npz') as data:raw={k:data[k] for k in data.files}
    else:
        with tempfile.TemporaryDirectory(prefix='automx_energy_') as tmp:
            dest=Path(tmp)/'wave.raw'
            with gzip.open(folder/'coupled.raw.gz','rb') as source,dest.open('wb') as target:__import__('shutil').copyfileobj(source,target)
            raw=read_raw(dest)
    # Legacy ASCII writer normalizes vector names to lower case.
    raw={k.lower():v for k,v in raw.items()};t=raw['time'];v=raw['v(vpwr)'];base=report.get('base_time_s',0.)
    powers={name:v*raw['i('+probe.lower()+')'] for name,probe in [('core','VCORE_METER'),('conditioner','VCOND_METER'),('adc','VADC_METER')]}
    powers['reference_bridge']=-sum(raw['v('+node.lower()+')']*raw['i('+source.lower()+')'] for node,source in [('BOTTOMP','VBOTTOMP'),('BOTTOMN','VBOTTOMN'),('SAMPLE','VSAMPLE'),('SAMPLE_N','VSAMPLEN'),('ADC_CLK_COMP','VCLKCOMP'),('VCM','VVCM')])
    windows={'conversion':(report['start_s'],report['eoc_s']),
       'acquisition':(max(t[0],base),base+report['profile'].get('timing',{}).get('track_end_ns',160)*1e-9),
       'whole_case':(float(t[0]),float(t[-1]))}
    energies={name:{key:integrate(t,p,a,b) for key,p in powers.items()} for name,(a,b) in windows.items()}
    for name,e in energies.items():e['monitored_total']=sum(e.values())
    assert np.isclose(energies['whole_case']['monitored_total'],report['energy']['monitored_total_j'],rtol=1e-7,atol=1e-17)
    return energies

def run(native,work):
    native=Path(native).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    traces=list(csv.DictReader((native/'native_frame_trace.csv').open()));cache={};rows=[];projections={}
    for t in traces:
        folder=t['case']
        if folder not in cache:cache[folder]=measure_case(folder)
        e=cache[folder]['conversion'];row={k:t[k] for k in ('frame_index','stage','token','phase','column')}
        row.update({k+'_nj':v*1e9 for k,v in e.items()});rows.append(row)
        key=(t['frame_index'],t['stage'],t['token']);g=projections.setdefault(key,{'conversions':0,'energies_j':{k:0. for k in e}});g['conversions']+=1
        for k,v in e.items():g['energies_j'][k]+=v
    out=[]
    for (frame,stage,token),g in projections.items():
        assert g['conversions']==8;out.append({'frame_index':int(frame),'stage':stage,'token':int(token),'conversions':8,**{k+'_nj':v*1e9 for k,v in g['energies_j'].items()}})
    for name,data in [('conversion_energy',rows),('projection_conversion_energy',out)]:
        with (work/(name+'.csv')).open('w') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    result={'status':'PASS','logical_conversions':len(rows),'unique_measured_cases':len(cache),'token_projections':len(out),
       'mean_conversion_nj':{k:float(np.mean([r[k] for r in rows])) for k in rows[0] if k.endswith('_nj')},
       'mean_projection_conversion_nj':{k:float(np.mean([r[k] for r in out])) for k in out[0] if k.endswith('_nj')},
       'scope':'Actual sampled V/I integrals over SAR START-to-EOC. Projection is eight such conversion windows for one four-output token. Acquisition/hold, controller/MHA and idle are separate ownership windows; these are not complete projection or whole-chip energies.'}
    (work/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print('CONVERSION_WINDOW_ENERGY_PASS',json.dumps(result),flush=True);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--work',type=Path,required=True);a=p.parse_args();run(a.native,a.work)
