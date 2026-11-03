"""Re-evaluate matched routed-gate VCDs with clock-aware OpenSTA 3.1."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse,json,re,subprocess,time

def run(root,reference,gated,work):
    root=Path(root).resolve();reference=Path(reference).resolve();gated=Path(gated).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    sta=root/'tools/opensta_current/build/sta';assert sta.is_file()
    ref=json.loads((reference/'verification.json').read_text());gate=json.loads((gated/'verification.json').read_text())
    variants=[('linear',reference/'linear',next(r for r in ref['results'] if r['variant']=='linear')),
       ('binary',gated/'binary_reference',next(r for r in gate['results'] if r['variant']=='binary_reference')),
       ('binary_gated',gated/'binary',next(r for r in gate['results'] if r['variant']=='binary')),
       ('digital',gated/'digital',next(r for r in gate['results'] if r['variant']=='digital')),
       ('current_readout',reference/'binary',next(r for r in ref['results'] if r['variant']=='binary'))]
    def measure(entry):
        label,source,old=entry;folder=work/label;folder.mkdir(exist_ok=True);powers=[]
        for original in sorted(source.glob('power_*.tcl')):
            # Ignore experimental power scripts; use the original measured block scripts.
            if original.name not in ('power_readout.tcl','power_mha.tcl','power_digital_attention.tcl'):continue
            text=re.sub(r'read_power_activities -scope (\S+) -vcd (.*)',r'read_vcd -scope \1 \2',original.read_text())
            script=folder/original.name;script.write_text(text)
            q=subprocess.run([sta,'-exit',script],capture_output=True,text=True,timeout=600);log=script.with_suffix('.log');log.write_text(q.stdout+q.stderr)
            assert q.returncode==0 and not re.search(r'(?im)^Error:',q.stdout+q.stderr),(q.stdout+q.stderr)[-2000:]
            values=re.search(r'(?m)^Total\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)',q.stdout);assert values
            powers.append({'block':original.stem.removeprefix('power_'),'internal_w':float(values[1]),'switching_w':float(values[2]),'leakage_w':float(values[3]),'total_w':float(values[4]),'log':str(log)})
        assert len(powers)==len(old['power_blocks'])
        total=sum(p['total_w'] for p in powers);row={'variant':label,'frames':old['frames'],'activity_window_s':old['activity_window_s'],
           'power_blocks':powers,'child_digital_power_w':total,'child_digital_energy_per_frame_j':total*old['activity_window_s']/old['frames'],
           'gate_output_mismatches':old['gate_output_mismatches'],'scope':old['scope']}
        print('CLOCK_AWARE_POWER',label,f"{total*1e3:.6f}mW",f"{row['child_digital_energy_per_frame_j']*1e9:.6f}nJ/frame",flush=True);return row
    with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(measure,variants))
    binary=next(r for r in rows if r['variant']=='binary');g=next(r for r in rows if r['variant']=='binary_gated')
    result={'status':'PASS','tool_version':subprocess.check_output([sta,'-version'],text=True).strip(),'results':rows,
       'gating_child_energy_reduction_percent':100*(1-g['child_digital_energy_per_frame_j']/binary['child_digital_energy_per_frame_j']),
       'condition':f"TT 1.8 V 25 C, same {rows[0]['frames']} native-backed frames, same declared profile; extracted child RC, zero-delay GLS",
       'scope':'Clock-aware VCD/Liberty estimate. The original OpenSTA 2.4 estimates remain versioned measurements; do not mix versions within a comparison.'}
    (work/'verification.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--reference',type=Path,required=True);p.add_argument('--gated',type=Path,required=True);p.add_argument('--work',type=Path,required=True);a=p.parse_args();run(a.root,a.reference,a.gated,a.work)
