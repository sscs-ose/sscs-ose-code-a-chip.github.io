"""Independent integer/floating references and native Icarus verification of MHA IP."""
from pathlib import Path
import argparse,json,math,re,subprocess,time
import numpy as np

MAGNITUDES=(0,1,2,3,4,6,8,12)

def pack(values,bits):
    return sum((int(v)&((1<<bits)-1))<<(bits*i) for i,v in enumerate(np.asarray(values).reshape(-1)))

def probability_fixed(difference):
    negative=difference<0; magnitude=abs(int(difference)); scaled=magnitude*181
    if magnitude>=46: value=32768
    else:
        index,fraction=divmod(scaled,128)
        lo=round(32768/(1+math.exp(-index/8)))
        hi=round(32768/(1+math.exp(-(index+1)/8)))
        value=lo+((hi-lo)*fraction+64)//128
    return 32768-value if negative else value

def quantize_x2(values):
    return np.array([(-1 if x<0 else 1)*min(MAGNITUDES,key=lambda m:abs(abs(int(x))-32768*m))
                     for x in np.asarray(values).reshape(-1)],dtype=int).reshape(np.asarray(values).shape)

def reference(activation,weights):
    q,k,v=[np.asarray(activation,dtype=np.int64)@weights[n] for n in ('Q','K','V')]
    context=np.zeros((2,4),dtype=np.int64);probabilities=np.zeros((2,2,2),dtype=np.int64)
    float_context=np.zeros((2,4),dtype=float)
    for head in range(2):
        hs=slice(2*head,2*head+2)
        scores=q[:,hs]@k[:,hs].T
        for row in range(2):
            difference=int(scores[row,0]-scores[row,1]);p=probability_fixed(difference)
            probabilities[head,row]=[p,32768-p]
            context[row,hs]=probabilities[head,row]@v[:,hs]
            true_p=1/(1+math.exp(-max(-700,min(700,difference/(4*math.sqrt(2))))))
            float_context[row,hs]=np.array([true_p,1-true_p])@v[:,hs]
    context_x2=quantize_x2(context)
    float_quantized=np.array([(-1 if x<0 else 1)*min(MAGNITUDES,key=lambda m:abs(abs(float(x))-m))
                            for x in float_context.reshape(-1)]).reshape(2,4)
    output=context_x2@weights['O']
    return dict(q=q,k=k,v=v,context_x2=context_x2,probabilities=probabilities,
                output_x2=output,float_quantized_output_x2=float_quantized@weights['O'],
                floating_output_x2=float_context@weights['O'])

def vectors(root,count):
    spec=json.loads((root/'inputs/experiment_spec.json').read_text())['mha']
    rng=np.random.default_rng(2027)
    result=[(np.array(spec['activation_x2'],dtype=int),{k:np.array(v,dtype=int) for k,v in spec['weights'].items()})]
    result.append((np.zeros((2,4),dtype=int),{k:np.zeros((4,4),dtype=int) for k in ('Q','K','V','O')}))
    alphabet=np.array(sorted(set(MAGNITUDES)|{-v for v in MAGNITUDES}))
    for _ in range(count-len(result)):
        result.append((rng.choice(alphabet,size=(2,4)),{k:rng.integers(-1,2,(4,4)) for k in ('Q','K','V','O')}))
    return result

def run_command(command,work,logname,timeout=90):
    start=time.monotonic();result=subprocess.run(list(map(str,command)),cwd=work,capture_output=True,text=True,timeout=timeout)
    (work/logname).write_text(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError(f'{logname}: '+(result.stdout+result.stderr)[-4000:])
    return result.stdout,time.monotonic()-start

def verify(root,work,count=98):
    root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    cases=vectors(root,count);gold=[reference(a,w) for a,w in cases]
    data={name:[] for name in ('activations','weights','outputs','probabilities','context')}
    for (a,w),g in zip(cases,gold):
        masks=[]
        for stage in ('Q','K','V','O'):
            for row in range(4):
                pos=sum(int(w[stage][row,c]>0)<<c for c in range(4))
                neg=sum(int(w[stage][row,c]<0)<<c for c in range(4))
                masks.append(pos|(neg<<4))
        for name,value,width in [('activations',pack(a,5),10),('weights',pack(masks,8),32),
             ('outputs',pack(g['output_x2'],12),24),('probabilities',pack(g['probabilities'],16),32),
             ('context',pack(g['context_x2'],5),10)]:data[name].append(f'{value:0{width}x}')
    for name,rows in data.items():
        (work/(name+'.memh')).write_text('\n'.join(rows)+'\n')
        (work/('canonical_'+name+'.memh')).write_text(rows[0]+'\n')
    src=root/'ip/automx_mha'
    compile_log,_=run_command(['iverilog','-g2012','-s','tb_mha_ip','-o',work/'mha.vvp',
                  src/'rtl/automx_mha_ip.sv',src/'sim/tb_mha_ip.sv'],work,'iverilog.log')
    stdout,elapsed=run_command(['vvp',work/'mha.vvp','+DATA='+str(work),'+CASES='+str(count)],work,'vvp.log')
    assert f'MHA_IP_BIT_EXACT_PASS cases={count}' in stdout
    trace=re.search(r'MHA_RTL_CANONICAL q=(\w+) k=(\w+) v=(\w+) context=(\w+) output=(\w+)',stdout)
    assert trace,stdout
    def decode_hex(text,bits,rows=2,columns=4):
        value=int(text,16);mask=(1<<bits)-1
        data=[(value>>(i*bits))&mask for i in range(rows*columns)]
        return np.array([x-(1<<bits) if x&(1<<(bits-1)) else x for x in data]).reshape(rows,columns)
    observed={name:decode_hex(value,5 if name=='context_x2' else 12).tolist()
        for name,value in zip(['q','k','v','context_x2','output_x2'],trace.groups())}
    for name,values in observed.items():assert np.array_equal(values,gold[0][name]),name
    (work/'canonical_rtl.json').write_text(json.dumps(observed,indent=2)+'\n')
    required=['RANDOM_STALLS_AND_OUTPUT_BACKPRESSURE','RESET_ABORT','INVALID_ACTIVATION','BACKEND_TIMEOUT','UNCALIBRATED_RESULT','BACKEND_FAULT']
    assert all(x+'_PASS' in stdout for x in required),stdout
    run_command(['iverilog','-g2012','-s','tb_mha_mixed_top','-o',work/'integrated.vvp',
        src/'rtl/automx_mha_ip.sv',root/'rtl/automx_cim_readout_seq.sv',
        root/'inputs/automx_cim_mixed_signal_proto.sv',root/'inputs/wrapper_blackboxes.sv',
        src/'sim/tb_mha_mixed_top.sv'],work,'integration_compile.log')
    integration_log,_=run_command(['vvp',work/'integrated.vvp','+DATA='+str(work)],work,'integration.log')
    assert 'MHA_CIM_SAR_RTL_TOP_PASS vectors=8 adc_conversions=64' in integration_log
    assert 'MHA_TOP_DIRECT_CIM_SAR_MODE_PASS' in integration_log
    errors=[]
    for d in range(-9216,9217):
        p=1/(1+math.exp(-max(-700,min(700,d/(4*math.sqrt(2))))))
        errors.append(abs(probability_fixed(d)/32768-p))
    assert max(errors)<.0005
    canonical={k:v.tolist() for k,v in gold[0].items()}
    (work/'canonical_reference.json').write_text(json.dumps(canonical,indent=2)+'\n')
    mismatches=sum(np.any(g['output_x2']!=g['float_quantized_output_x2']) for g in gold)
    report={'status':'PASS','configuration':{'tokens':2,'channels':4,'heads':2},
      'test_cases':count,'checked_output_values':count*8,'projection_vector_transactions':count*8,
      'bit_exact_errors':0,'softmax_absolute_probability_error_max':max(errors),
      'softmax_score_differences_checked':len(errors),'probability_row_sum':32768,
      'output_cases_different_from_float_softmax':int(mismatches),
      'canonical_output':(gold[0]['output_x2']/2).tolist(),
      'canonical_quantized_reference_l2':float(np.linalg.norm(gold[0]['output_x2']-gold[0]['float_quantized_output_x2'])/max(np.linalg.norm(gold[0]['float_quantized_output_x2']),1e-12)),
      'canonical_floating_reference_l2':float(np.linalg.norm(gold[0]['output_x2']-gold[0]['floating_output_x2'])/max(np.linalg.norm(gold[0]['floating_output_x2']),1e-12)),
      'protocol_tests':required,'simulation_elapsed_s':elapsed,'simulator':'Icarus Verilog',
      'integrated_top':'PASS: MHA IP plus actual readout RTL, 64 modeled ADC conversions, calibrated decoder and host mode arbitration',
      'backend':'Unit dot-product transaction model and top-level functional ADC response fixture; transistor analog measurements are separate'}
    (work/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(stdout.strip());print(integration_log.strip());print('MHA_IP_VERIFIED',json.dumps({k:report[k] for k in ['status','test_cases','bit_exact_errors','softmax_absolute_probability_error_max','canonical_quantized_reference_l2','canonical_floating_reference_l2']}),flush=True)
    return report

def synthesize(root,work,full_top=False):
    root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    image=json.loads((root/'standalone.json').read_text())['openlane_image']
    liberty=root/'pdks/digital/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib'
    summaries=[]
    targets=['automx_mha_ip']+(['automx_cim_mixed_signal_proto'] if full_top else [])
    for top in targets:
        script=work/(top+'.ys');stat=work/(top+'.stat.json');mapped=work/(top+'.mapped.v')
        sources=[root/'ip/automx_mha/rtl/automx_mha_ip.sv']
        if top!='automx_mha_ip': sources += [root/'rtl/automx_cim_readout_seq.sv',root/'inputs/automx_cim_mixed_signal_proto.sv']
        text=f'read_liberty -lib "{liberty}"\n'
        if top!='automx_mha_ip':text+=f'read_verilog -lib "{root/"inputs/wrapper_blackboxes.sv"}"\n'
        text+=''.join(f'read_verilog -sv "{p}"\n' for p in sources)
        text+=f'hierarchy -check -top {top}\nsynth -top {top} -flatten\n'
        text+=f'dfflibmap -liberty "{liberty}"\nabc -liberty "{liberty}"\nclean\ncheck -assert\n'
        text+=f'write_verilog -noattr -noexpr "{mapped}"\ntee -o {stat} stat -json -liberty "{liberty}"\n'
        script.write_text(text)
        command=['docker','run','--rm','--network','none','--user',f'{__import__("os").getuid()}:{__import__("os").getgid()}',
                 '-v',f'{root}:{root}','-w',str(work),'--entrypoint','yosys',image,'-s',str(script)]
        stdout,elapsed=run_command(command,work,top+'.yosys.log',timeout=240)
        result=json.loads(stat.read_text());module=result['modules']['\\'+top]
        assert module['num_cells']>0 and mapped.stat().st_size>0
        macros={name:module['num_cells_by_type'].get(name,0) for name in
                ['automx_cim_core_acquisition_proto','automx_cim_condition_mux_proto','adc_top']}
        if top!='automx_mha_ip':assert all(v==1 for v in macros.values()),macros
        row={'top':top,'mapped_cells':module['num_cells'],'mapped_area_um2':module.get('area'),
             'elapsed_s':elapsed,'hard_macros':macros,'log':str(work/(top+'.yosys.log'))}
        summaries.append(row)
        print('YOSYS_MHA_SYNTHESIS_PASS',json.dumps(row),flush=True)
    (work/'synthesis.json').write_text(json.dumps({'status':'PASS','targets':summaries},indent=2)+'\n')
    return summaries

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--work',type=Path,required=True);p.add_argument('--cases',type=int,default=98)
    a=p.parse_args();verify(a.root,a.work,a.cases)
