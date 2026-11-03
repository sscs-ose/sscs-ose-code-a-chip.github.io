"""Fresh native PEX measurements; every invocation executes ngspice."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json,math,re,shutil,subprocess,time
from threading import Event,Timer
from IPython.display import Markdown,display

RESULTS={}
# Stimulus vectors from the diagnosed sum-11/sum-12 pair; no old voltages/logs.
PATTERNS=(('sum11',(-1,2,12,-8),((1,1,1,-1),(0,-1,1,0),(1,0,-1,1),(0,1,1,0))),
          ('sum12',(12,-12,12,0),((1,-1,1,0),(1,-1,-1,0),(1,-1,1,0),(0,0,0,0))))


def measure_pair(root,work,load_ff,pwm_unit_ps):
    root=Path(root);work=Path(work);folder=work/f'fresh_pex_c{load_ff}_pwm{pwm_unit_ps}';folder.mkdir(exist_ok=False)
    # Existing PEX is a circuit design input; measurement outputs start empty.
    pex=root/'physical/sky130/macro/automx_ternary_cim_4x4_core.pex.spice'
    manifest=json.loads((root/'generated/sky130/spice/stage4_manifest.json').read_text())
    model=Path(manifest['model_library'])
    executable=shutil.which('ngspice')
    if not executable or not pex.is_file():raise FileNotFoundError('ngspice / PEX input')
    def run(pattern):
        name,acts,weights=pattern;case=Case(name,acts,weights);deck=folder/(name+'.spice');log=folder/(name+'.log')
        deck.write_text(make_pex_deck(case,model,pex,load_ff,pwm_unit_ps))
        command=[executable,'-b',str(deck)];start=time.monotonic()
        print('RUN FRESH ngspice:',name,'load=',load_ff,'fF; PWM=',pwm_unit_ps,'ps; command:',' '.join(command),flush=True)
        print('NATIVE ngspice OUTPUT:',name,flush=True)
        actual=([shutil.which('stdbuf'),'-oL','-eL'] if shutil.which('stdbuf') else [])+command
        process=subprocess.Popen(actual,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace',bufsize=1)
        expired=Event()
        def terminate():
            if process.poll() is None:expired.set();process.kill()
        timer=Timer(180,terminate);timer.daemon=True;timer.start()
        try:
            with log.open('w') as stream:
                for line in process.stdout:
                    stream.write(line);stream.flush();print('[ngspice '+name+'] '+line,end='',flush=True)
            code=process.wait()
        finally:
            timer.cancel()
            if process.poll() is None:process.kill();process.wait()
            process.stdout.close()
        if expired.is_set():raise RuntimeError('Fresh PEX pilot timeout: '+str(log))
        text=log.read_text();values={m[0].lower():float(m[1]) for m in re.findall(r'^\s*((?:diff|blp|bln)_c\d_t(?:09|19|21))\s*=\s*([-+\deE.]+)',text,re.M)}
        if code or len(values)!=28 or not all(math.isfinite(v) for v in values.values()):raise RuntimeError('Fresh PEX measurement failed: '+str(log))
        print('EXIT ngspice',name,':',code,'| elapsed_s:',round(time.monotonic()-start,3),flush=True)
        return {'case':name,'activation_x2':list(acts),'ternary_weights':[list(r) for r in weights],'integer_sums':list(case.sums),'measurements_v':values,'returncode':code,'elapsed_s':time.monotonic()-start,'log':str(log),'deck':str(deck)}
    with ThreadPoolExecutor(max_workers=2) as pool:jobs=list(pool.map(run,PATTERNS))
    gap=jobs[1]['measurements_v']['diff_c0_t19']-jobs[0]['measurements_v']['diff_c0_t19']
    result={'mode':'FRESH_NATIVE','timestamp_utc':datetime.now(timezone.utc).isoformat(),'load_ff':load_ff,'pwm_unit_ps':pwm_unit_ps,'jobs':jobs,'gap_v':gap,'overlap_count':int(gap<=0),'samples':2}
    (folder/'measured.json').write_text(json.dumps(result,indent=2)+'\n');RESULTS[str(load_ff)]=result
    display(Markdown('| Case | Sum c0 | ΔV c0 @ 1.9 ns / V |\n|---|---|---|\n'+'\n'.join(f'| {r["case"]} | {r["integer_sums"][0]} | {r["measurements_v"]["diff_c0_t19"]:.8f} |' for r in jobs)))
    print('Measured signed-level gap:',gap*1000,'mV; overlap_count:',result['overlap_count'])
    return result


def plot_progress(work):
    import matplotlib.pyplot as plt
    before=RESULTS['200'];after=RESULTS['800']
    fig,ax=plt.subplots(figsize=(7,3.5),layout='constrained');ax.bar(['200 fF / 100 ps','800 fF / 50 ps'],[before['gap_v']*1000,after['gap_v']*1000],color=['#c44e52','#55a868']);ax.axhline(0,color='black',lw=.8);ax.set_ylabel('Fresh PEX sum12 − sum11 gap / mV')
    path=Path(work)/'fresh_pex_before_after.png';fig.savefig(path,dpi=140);plt.show();plt.close(fig)
    result={'before':before,'after':after,'plot':str(path),'mode':'FRESH_NATIVE'}
    (Path(work)/'fresh_pex_before_after.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def fresh_activity(flow):
    start=json.loads((flow.work/'fresh_start.json').read_text());rows=[]
    for name,reference in flow.receipts.items():
        record=json.loads(Path(reference['path']).read_text())
        log=Path(record['log']['path'])
        if not log.is_relative_to(flow.base) or log.stat().st_mtime<start['started_epoch_s']:raise ValueError('Native log was not created in this fresh session')
        rows.append({'step':name,'returncode':record['returncode'],'elapsed_s':record['elapsed_s'],'log':str(log)})
    print('FRESH SESSION:',flow.work,'; pre-existing result files:',start['pre_existing_results'],'; reuse:',flow.settings.reuse)
    if flow.settings.reuse or start['pre_existing_results']:raise ValueError('Fresh session reused prior results')
    display(Markdown('| Tool step | Return code | Runtime / s |\n|---|---|---|\n'+'\n'.join(f'| {r["step"]} | {r["returncode"]} | {r["elapsed_s"]:.2f} |' for r in rows)))
    result={'start':start,'native_steps':rows,'fresh_native_steps':len(rows),'reuse':False,'pex_pilot':RESULTS}
    path=flow.work/'fresh_activity.json';path.write_text(json.dumps(result,indent=2)+'\n')
    from automx_nb_inline_v1.support import item
    flow.outputs['fresh_activity']=item(path)
    return result
