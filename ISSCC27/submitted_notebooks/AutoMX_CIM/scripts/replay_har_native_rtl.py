"""Replay native ADC words through the real MHA/readout with transaction checks."""
from pathlib import Path
import argparse,csv,json,math,re,subprocess,shutil,time
import numpy as np
from ip.automx_mha.verify import pack

def replay(root,application,native,rtl_work,work):
    root=Path(root).resolve();application=Path(application).resolve();native=Path(native).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    measured=json.loads((native/'verification.json').read_text());assert measured['status']=='PASS'
    binding=(root/'inputs/automx_cim_mixed_signal_proto.sv').read_text()
    assert '.inn_analog(AINP), .inp_analog(AINN)' in binding,'Physical top ADC polarity differs from measured path'
    indices=[f['index'] for f in measured['frames']];n=len(indices)
    for name in ('activations','weights','outputs'):
        lines=(application/f'{name}.memh').read_text().splitlines()
        (work/f'{name}.memh').write_text('\n'.join(lines[i] for i in indices)+'\n')
    for name in ('thresholds.memh','adc_words.memh'):shutil.copy2(native/name,work/name)
    traces=list(csv.DictReader((native/'native_frame_trace.csv').open()))
    assert len(traces)==n*64
    tags={'native_pos':[],'native_neg':[],'native_acts':[],'native_phase':[],'native_column':[],'native_delay':[]}
    for row in traces:
        case=json.loads((Path(row['case'])/'case.json').read_text());w=np.array(case['weights'])
        deck=(Path(row['case'])/'coupled.spice').read_text()
        assert 'XSP SAMPLE_N AINN SAMPLE CTOPP' in deck and 'XSN SAMPLE_N AINP SAMPLE CTOPN' in deck
        tags['native_pos'].append(sum(int(w[r,c]>0)<<(4*r+c) for r in range(4) for c in range(4)))
        tags['native_neg'].append(sum(int(w[r,c]<0)<<(4*r+c) for r in range(4) for c in range(4)))
        tags['native_acts'].append(pack(case['activation_x2'],5));tags['native_phase'].append(int(row['phase']));tags['native_column'].append(int(row['column']))
        tags['native_delay'].append(math.ceil(float(row['start_to_eoc_s'])/40e-9))
    for key,values in tags.items():(work/f'{key}.memh').write_text('\n'.join(f'{v:05x}' for v in values)+'\n')
    source=(Path(rtl_work)/'tb_application_binary.sv').read_text()
    extra='''reg [11:0] native_thresholds[0:303];reg [15:0] native_words[0:4095];
reg [19:0] native_pos[0:4095],native_neg[0:4095],native_acts[0:4095];
reg [19:0] native_phase[0:4095],native_column[0:4095],native_delay[0:4095];
reg [19:0] requested_acts;'''
    source=source.replace('integer r,sum,bin,col,phase,j;',extra+'\n    integer r,sum,bin,col,phase,j;')
    marker='if(!$value$plusargs("CASES=%d",cases))$fatal(1,"CASES required");'
    reads='\n        $readmemh({folder,"/thresholds.memh"},native_thresholds,0,303);\n        $readmemh({folder,"/adc_words.memh"},native_words,0,64*cases-1);'
    reads+=''.join(f'\n        $readmemh({{folder,"/{key}.memh"}},{key},0,64*cases-1);' for key in tags)
    source=source.replace(marker,marker+reads)
    source=source.replace("cal_threshold_i=12'(100+80*(i%38))",'cal_threshold_i=native_thresholds[i]')
    pattern=r'sum=0;col=dut\.seq_i\.column;phase=dut\.seq_i\.phase_b;.*?adc_word<=16\x27\(\(50\+80\*bin\)<<4\);adc_timer<=3;conversions<=conversions\+1;'
    replacement='''col=dut.seq_i.column;phase=dut.seq_i.phase_b;requested_acts=0;
            for(r=2*phase;r<2*phase+2;r=r+1)requested_acts[5*r+:5]=dut.seq_i.acts[5*r+:5];
            if(conversions>=64*cases)$fatal(1,"unexpected extra ADC request");
            if(col!=native_column[conversions] || phase!=native_phase[conversions] ||
               dut.wp!==native_pos[conversions][15:0] || dut.wn!==native_neg[conversions][15:0] ||
               requested_acts!==native_acts[conversions])$fatal(1,"native response transaction identity mismatch %0d",conversions);
            adc_word<=native_words[conversions];adc_timer<=native_delay[conversions];conversions<=conversions+1;'''
    source,count=re.subn(pattern,replacement,source,flags=re.S);assert count==1,count
    source=source.replace('observed_binary.memh','observed_native.memh').replace('latency_binary.csv','latency_native.csv')
    tb=work/'tb_native_replay.sv';tb.write_text(source)
    command=['iverilog','-g2012','-s','tb_mha_mixed_top','-o',work/'replay.vvp',root/'ip/automx_mha/rtl/automx_mha_ip.sv',root/'rtl/automx_cim_readout_seq.sv',root/'inputs/automx_cim_mixed_signal_proto.sv',root/'inputs/wrapper_blackboxes.sv',tb]
    start=time.monotonic()
    for label,args in [('compile',command),('replay',['vvp',work/'replay.vvp','+DATA='+str(work),f'+CASES={n}'])]:
        result=subprocess.run(list(map(str,args)),cwd=work,capture_output=True,text=True,timeout=120)
        (work/f'{label}.log').write_text(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError((result.stdout+result.stderr)[-3500:])
    observed=(work/'observed_native.memh').read_text().splitlines();expected=(work/'outputs.memh').read_text().splitlines()
    assert [int(x,16) for x in observed]==[int(x,16) for x in expected]
    deployment=json.loads((application/'deployment.json').read_text());head=np.array(deployment['head_weight']);bias=np.array(deployment['head_bias'])
    frames=[]
    for f in measured['frames']:
        logits=head@(np.array(f['output_x2']).reshape(-1)/2)+bias
        frames.append({'test_index':f['index'],'label':f['label'],'predicted_class':int(logits.argmax()),'output_mismatches':f['output_mismatches']})
    report={'status':'PASS','frames':n,'output_values':n*8,'native_adc_transactions':len(traces),'calibration_thresholds':304,
       'native_transaction_identity_checked':True,'mismatches':0,'frames_and_predictions':frames,'elapsed_s':time.monotonic()-start,
       'adc_input_polarity':'conditioner AINN -> ADC inp; conditioner AINP -> ADC inn',
       'scope':'Actual MHA and two-phase readout RTL replaying native SAR/transistor ADC words and measured EOC duration. Stimuli are checked against every measured transaction. Measurement-driven replay, not concurrent full-chip transistor simulation.'}
    (work/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('NATIVE_CODE_MHA_REPLAY_PASS',json.dumps(report),flush=True);return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--application',type=Path,required=True);p.add_argument('--native',type=Path,required=True);p.add_argument('--rtl-work',type=Path,required=True);p.add_argument('--work',type=Path,required=True)
    a=p.parse_args();replay(a.root,a.application,a.native,a.rtl_work,a.work)
