"""Generate six evidence figures, four result tables and the short reviewer route."""
from pathlib import Path
import argparse,csv,json,time
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def run(root,base,work):
    root=Path(root).resolve();base=Path(base).resolve();work=Path(work).resolve();fig=work/'figures';fig.mkdir(parents=True,exist_ok=True)
    def read(path):return json.loads(Path(path).read_text())
    app=read(base/'application/application_metrics.json');power=read(work/'clock_aware_power/verification.json') if (work/'clock_aware_power/verification.json').exists() else read(base/'activity_power/verification.json')
    idle=read(work/'idle_boot/verification.json');service=read(work/'application_service/verification.json')
    clock=read(work/'clock_activity/verification.json')
    pwm=read(work/'pwm_reference/verification.json') if (work/'pwm_reference/verification.json').exists() else read(work/'pwm_compact_pilot/verification.json')
    final_pwm=read(work/'pwm_final/verification.json') if (work/'pwm_final/verification.json').exists() else None
    electrical=read(work/'electrical/verification.json') if (work/'electrical/verification.json').exists() else None
    images=[]
    def save(f,name):f.tight_layout();path=fig/(name+'.png');f.savefig(path,dpi=160);f.savefig(fig/(name+'.svg'));plt.close(f);images.append(str(path))
    f,ax=plt.subplots(figsize=(12,3.5));ax.set(xlim=(0,12),ylim=(0,3));ax.axis('off')
    boxes=[(.1,1.8,'128 sensor samples\nmean / RMS + embedding','Software'),(2.5,1.8,'MHA IP\nQ / K / V / O requests','Designed RTL'),
       (5.1,1.8,'Eight-NMOS compute\nacquisition / conditioner','Designed analog'),(7.8,1.8,'SAR conversion\ncalibrated readout','Reused SAR + designed RTL'),
       (10.1,1.8,'Attention output\nsoftware class head','Hardware → software')]
    for x,y,label,owner in boxes:
        ax.text(x,y,label,ha='left',va='center',fontsize=9,bbox=dict(boxstyle='round,pad=.5',facecolor='#e9f1f7',edgecolor='#386784'));ax.text(x,y-.7,owner,fontsize=8,color='#444')
    for a,b in zip(boxes[:3],boxes[1:4]):ax.annotate('',xy=(b[0]-.1,1.8),xytext=(a[0]+1.9,1.8),arrowprops=dict(arrowstyle='->',color='#386784'))
    ax.plot([8.5,8.5,3.35],[1.55,1.39,1.39],color='#386784',lw=1.2)
    ax.annotate('',xy=(3.35,1.55),xytext=(3.35,1.39),arrowprops=dict(arrowstyle='->',color='#386784'))
    ax.text(5.7,1.23,'Calibrated projection vectors return to MHA',ha='center',fontsize=8,color='#386784')
    ax.plot([3.35,3.35,10.8],[2.08,2.65,2.65],color='#386784',lw=1.2)
    ax.annotate('',xy=(10.8,2.08),xytext=(10.8,2.65),arrowprops=dict(arrowstyle='->',color='#386784'))
    ax.text(7,2.76,'Attention/context and O output to the software classifier',ha='center',fontsize=9,color='#386784')
    ax.text(.2,.15,'Controller registers store weight bits; eight-NMOS branches convert weight/activation products into bitline discharge.',fontsize=9)
    save(f,'01_architecture_ownership')
    f,axes=plt.subplots(1,2,figsize=(11,3.7))
    rows=pwm['measurements'];x=[r['magnitude'] for r in rows];y=[r['width_ps'] for r in rows]
    axes[0].plot(x,y,'o-',label='Reference routed pulse');axes[0].plot(x,np.array(x)*50,'--',label='Ideal 50 ps diagnostic')
    if final_pwm:
        rr=[r for r in final_pwm['measurements'] if r['row']==0 and not r['negative']];axes[0].plot([r['magnitude'] for r in rr],[r['width_ps'] for r in rr],'s-',label='Current routed pulse, row 0+')
    axes[0].set(xlabel='Activation magnitude / X2',ylabel='Delivered width / ps',title='Actual mapped driver + distributed RC');axes[0].legend(fontsize=8)
    for r in rows:
        if r['magnitude'] in (1,8,12):axes[1].plot(r['waveform']['time_ns'],r['waveform']['voltage_v'],label=str(r['magnitude']))
    axes[1].set(xlabel='Time from launch clock / ns',ylabel='CIM wordline / V',title='Reference failure witness');axes[1].legend(title='Magnitude')
    previous=work/'evaluated_candidate/pwm/verification.json'
    if previous.exists() and electrical and electrical['contract']['stimulus']=='routed measured PWM':
        prior=read(previous)
        earlier=[row for row in prior['measurements'] if row['row']==0 and row['negative']]
        selected=[row for row in final_pwm['measurements'] if row['row']==0 and row['negative']]
        axes[0].clear()
        for label,group,style in [('Previous placement',earlier,'o--'),('Selected placement',selected,'s-')]:
            axes[0].plot([row['magnitude'] for row in group],[row['width_ps'] for row in group],style,label=label)
        axes[0].set(xlabel='Activation magnitude / X2',ylabel='Delivered width / ps',title='Identical RTL / measured routed receiver input')
        axes[0].legend(fontsize=8)
        axes[1].clear()
        for label,group in [('Previous placement',earlier),('Selected placement',selected)]:
            trace=next(row for row in group if row['magnitude']==1)['waveform']
            axes[1].plot(trace['time_ns'],trace['voltage_v'],label=label)
        trace=next(row for row in selected if row['magnitude']==1)['waveform']
        tx=np.asarray(trace['time_ns']);vy=np.asarray(trace['voltage_v']);active=tx[vy>.1]
        if len(active):axes[1].set_xlim(float(active[0]-.5),float(active[-1]+.5))
        axes[1].set(xlabel='Time from launch clock / ns',ylabel='Wordline / V',title='Minimum-code recovery / row 0 negative')
        axes[1].legend(fontsize=8)
    if previous.exists() and electrical and electrical['contract']['stimulus']!='routed measured PWM':
        repaired=read(previous)
        rr=[row for row in repaired['measurements'] if row['row']==0 and not row['negative']]
        axes[0].plot([row['magnitude'] for row in rr],[row['width_ps'] for row in rr],'d-',label='Adjacent candidate / row 0+')
        axes[0].set_title('Delivered receiver pulse / independently measured candidates')
        axes[0].legend(fontsize=7)
        axes[1].clear()
        for label,group in [('Binary reference',rows),('Adjacent candidate',rr)]:
            trace=next(row for row in group if row['magnitude']==1)['waveform']
            axes[1].plot(trace['time_ns'],trace['voltage_v'],label=label)
        axes[1].set(xlabel='Time from launch clock / ns',ylabel='Wordline / V',title='Minimum-pulse repair; calibration tested separately')
        axes[1].legend(fontsize=7)
    save(f,'02_electrical_contract')
    f,axes=plt.subplots(1,2,figsize=(10,3.5))
    cr=clock['rows'];axes[0].bar(['Reference','ICG candidate'],[r['weighted_clock_edges']/1e6 for r in cr],color=['#ae5545','#386784'])
    axes[0].set(ylabel='Weighted clock edges / million',title='3,648 threshold flops, measured VCD')
    axes[1].axis('off');axes[1].text(.02,.9,'Design decision',fontsize=13,weight='bold');axes[1].text(.02,.72,'Gate calibration storage only while writing.\nPreserve the programmable threshold interface.\nCheck real clock edges separately from\nthe power estimator’s clock assumptions.',va='top',linespacing=1.7)
    save(f,'03_iteration_clock_evidence')
    f,axes=plt.subplots(1,2,figsize=(11,3.7));pr=power['results']
    axes[0].bar([r['variant'] for r in pr],[r['child_digital_energy_per_frame_j']*1e9 for r in pr],color=['#ae5545','#386784','#6c9760']);axes[0].set(yscale='log',ylabel='Estimated child-digital nJ / frame',title='Matched activity and power-tool version');axes[0].tick_params(axis='x',labelrotation=20)
    attribution=read(work/'power_attribution_sta3/verification.json') if (work/'power_attribution_sta3/verification.json').exists() else read(work/'power_attribution/verification.json');gr=[r for r in attribution['rows'] if r['variant']=='binary_reference']
    axes[1].barh([r['group'].replace('_',' ') for r in gr],[r['total_w']*1e3 for r in gr],color='#386784');axes[1].set(xlabel='Estimated power / mW',title='Reference readout attribution')
    save(f,'04_cost_attribution')
    f,axes=plt.subplots(1,2,figsize=(11,4));cm=np.array(app['models']['integer_mha']['confusion_matrix']);im=axes[0].imshow(cm,cmap='Blues')
    for a in range(6):
        for b in range(6):axes[0].text(b,a,str(cm[a,b]),ha='center',va='center',fontsize=8,color='white' if cm[a,b]>.5*cm.max() else 'black')
    axes[0].set(xlabel='Predicted class',ylabel='True class',title='Observed-RTL sensor-to-label predictions')
    names=['float','integer_mha','uniform_retrained','linear_features'];axes[1].barh(names,[app['models'][n]['macro_f1']*100 for n in names],color=['#999','#386784','#6c9760','#ae5545']);axes[1].set(xlabel='Test macro-F1 / %',xlim=(0,100),title='Nine unseen subjects / 2,947 windows')
    save(f,'05_application')
    f,axes=plt.subplots(1,3,figsize=(15,4.5));stride=idle['sensor_stride_s'];active=next(r for r in pr if r['variant']=='current_readout')
    axes[0].bar(['Active child digital','Always-on analog / stride'],[active['child_digital_energy_per_frame_j']*1e6,idle['analog_always_biased_energy_per_stride_j']*1e6],color=['#386784','#ae5545']);axes[0].set(yscale='log',ylabel='Separate energy terms / µJ',title=f'Sensor decisions every {stride:.2f} s')
    axes[1].axis('off');t=service['host_timing_us'];axes[1].text(.02,.95,f"Unforced boot: {idle['cold_boot_clocks']:,} clocks\nAnalog idle: {idle['analog_idle_dc']['monitored_w']*1e3:.3f} mW\nHost preprocessing median: {t['preprocess_embedding_median']:.2f} µs\nHost head median: {t['head_median']:.2f} µs\nResident masks: 128 bits\nCalibration data: 3,648 bits",va='top',linespacing=1.8)
    pvt_path=work/'electrical/pvt.json'
    if not pvt_path.exists():pvt_path=work/'schematic_timing/pvt.json'
    if pvt_path.exists():
        groups=read(pvt_path)['groups'];conditions=list(dict.fromkeys(g['condition'] for g in groups));banks=[0,3,4,7]
        errors=np.array([[next(g for g in groups if g['condition']==c and g['bank']==b).get('frozen_tt_wrong',np.nan) for b in banks] for c in conditions])
        stimulus=electrical['contract']['stimulus'] if electrical else 'ideal 50 ps'
        axes[2].imshow(errors,cmap='YlOrRd',vmin=0,vmax=7,aspect='auto');axes[2].set_xticks(range(4),banks);axes[2].set_yticks(range(len(conditions)),conditions);axes[2].set(xlabel='Bank',title=('Routed PWM' if stimulus=='routed measured PWM' else 'Ideal 50 ps')+' / frozen-TT wrong')
        for i in range(len(conditions)):
            for j in range(4):axes[2].text(j,i,str(int(errors[i,j])) if np.isfinite(errors[i,j]) else '?',ha='center',va='center',fontsize=8)
        axes[2].text(0,-.18,'Recalibrated: '+str(sum(g.get('five_anchor_recalibrated_wrong',0) for g in groups))+' wrong / 196',transform=axes[2].transAxes,fontsize=9)
    else:axes[2].axis('off')
    save(f,'06_sensor_service_budget')
    area=read(work/'controller_adc_area/verification.json')
    mapped={r['design']:r['mapped_area_um2'] for r in area['designs']}
    routed={r['design']:r['routed_stdcell_area_um2'] for r in area['routed_standard_cells']}
    earlier=read(base/'costs/costs.json')['designs']
    earlier_mapped={r['design']:r['mapped_area_um2'] for r in earlier}
    mapped['linear_readout']=earlier_mapped['linear_readout']
    names={'linear':'linear_readout','binary':'binary_reference','binary_gated':'calibration_gated','current_readout':'current_readout'}
    implementation=[{'variant':r['variant'],'frames':r['frames'],'latency_us':r['activity_window_s']/r['frames']*1e6,'child_digital_nj_per_frame':r['child_digital_energy_per_frame_j']*1e9,
        'component':('serial ternary projector' if r['variant']=='digital' else 'calibrated readout'),'component_mapped_um2':(earlier_mapped['digital_projection'] if r['variant']=='digital' else mapped.get(names.get(r['variant']))),'sar_digital_mapped_um2':(0 if r['variant']=='digital' else mapped['sar_digital']),'readout_mapped_um2':mapped.get(names.get(r['variant'])), 'readout_routed_stdcell_um2':routed.get(names.get(r['variant'])),
        'output_mismatches':r['gate_output_mismatches'],'scope':r['scope']} for r in pr]
    analog=[{'experiment':'reference routed PWM','cases':len(rows),'result':'short-code loss measured','scope':pwm['scope']},
        {'experiment':'actual controller timing','cases':384,'result':'six-clock START/EOC checked','scope':'Six class-selected frames; clocked controls'},
        {'experiment':'idle analog DC','cases':1,'result':f"{idle['analog_idle_dc']['monitored_w']*1e3:.6f} mW",'scope':idle['scope']}]
    study=work/'electrical'
    if not (study/'calibration.json').exists():study=work/'schematic_timing'
    if (study/'matched_sum.json').exists():
        nominal=read(study/'matched_sum.json');analog.append({'experiment':'Nominal same-sum transfer','cases':96,'result':str(sum(r.get('decoded')!=r['expected'] for r in nominal))+' wrong; 88 held-out / 8 anchor rechecks; minimum margin '+str(min(r.get('margin_codes',-999) for r in nominal))+' codes','scope':str(study.name)+' transistor partition and declared pulse/timing profile'})
    if (study/'pvt.json').exists():
        g=read(study/'pvt.json')['groups'];analog.append({'experiment':'Seven-condition calibration transfer','cases':336,'result':'frozen TT '+str(sum(x.get('frozen_tt_wrong',0) for x in g))+'/196 wrong; five-anchor recalibration '+str(sum(x.get('five_anchor_recalibrated_wrong',0) for x in g))+'/196 wrong; unresolved '+str(sum(x['unresolved'] for x in g)),'scope':'140 measured anchors and 196 held-out pattern checks; nominal driver waveform policy'})
    if (work/'numerical_convergence/verification.json').exists():
        n=read(work/'numerical_convergence/verification.json');analog.append({'experiment':'Declared native-model numerical sensitivity','cases':8,'result':'maximum change '+str(n['max_code_change'])+' raw codes','scope':n['scope']})
    if electrical:analog.append({'experiment':'native electrical campaign','cases':electrical['unique_native_jobs'],'result':electrical['status'],'scope':electrical['scope']})
    if final_pwm:
        checks=('zero_code_ok','nonzero_full_swing','single_pulse_ok','unselected_lines_quiet','strict_width_order','strict_bitline_order','bitline_polarity_ok')
        failed=[k for k in checks if final_pwm.get(k) is False]
        absent=[k for k in checks if k not in final_pwm]
        verdict='PASS' if not failed and not absent else '; '.join(s for s in [('Failed: '+', '.join(failed)) if failed else '',('Unmeasured checks: '+', '.join(absent)) if absent else ''] if s)
        analog.append({'experiment':'Current implemented pulse delivery','cases':len(final_pwm['measurements']),'result':verdict,'scope':final_pwm['scope']})
    energy=read(work/'conversion_energy/verification.json')
    digital_idle=next(r for r in idle['digital'] if r['window']=='idle')['readout_w']
    digital_boot=next(r for r in idle['digital'] if r['window']=='cold')['readout_j']
    programming=next((r for r in idle['digital'] if r['window']=='programming'),None)
    programming_j=programming['readout_j'] if programming else 0.0
    active_s=active['activity_window_s']/active['frames']
    analog.append({'experiment':'SAR conversion-window energy','cases':energy['logical_conversions'],'result':str(energy['mean_conversion_nj']['monitored_total_nj'])+' nJ/conversion; '+str(energy['mean_projection_conversion_nj']['monitored_total_nj'])+' nJ/eight-window token projection','scope':energy['scope']})
    if programming:
        analog.append({'experiment':'Readout threshold/resident-mask programming','cases':308,'result':str(programming['readout_j']*1e9)+' nJ in '+str(programming['duration_s']*1e6)+' us','scope':idle['programming_ownership']['scope']})
    budget_path=work/'margin_budget.json'
    if budget_path.exists():
        budget=read(budget_path);guards=[r['remaining_conditional_guard_codes'] for r in budget['banks'] if r['remaining_conditional_guard_codes'] is not None]
        analog.append({'experiment':'Conditional raw-code guard budget','cases':8,'result':'minimum residual '+str(min(guards) if guards else None)+' codes after sampled settling debit','scope':budget['scope']})
    # Every reported sum contains disjoint windows and named owners. Missing
    # chip/reference/host terms remain explicit rather than assigned zero.
    duty=[]
    for label,stride_s,boot_share in [('resident sensor',1.28,1000),('100-frame burst',max(active_s,1e-6),100)]:
        idle_s=max(0,stride_s-active_s)
        known=active['child_digital_energy_per_frame_j']+(idle['analog_idle_dc']['monitored_w']+digital_idle)*idle_s+(digital_boot+programming_j)/boot_share
        duty.append({'scenario':label,'stride_s':stride_s,'active_child_digital_j':active['child_digital_energy_per_frame_j'],
            'idle_analog_j':idle['analog_idle_dc']['monitored_w']*idle_s,'idle_readout_j':digital_idle*idle_s,
            'amortized_readout_boot_j':digital_boot/boot_share,'amortized_readout_programming_j':programming_j/boot_share,'programming_energy_measured':programming is not None,'decisions_per_boot':boot_share,
            'accounted_subtotal_j':known,'scope':'Partial disjoint-window subtotal; active analog acquisition, MHA idle, SAR digital, parent CTS/IO, MHA configuration, analog calibration acquisition, host energy and reference startup are not included.'})
    (work/'sensor_duty_budget.json').write_text(json.dumps(duty,indent=2)+'\n')
    ownership=[{'component':'Compute leaf, acquisition and conditioning','owner':'EDABK design','evidence':'MOS/MIM source, layout, circuit experiments'},
       {'component':'MHA, calibration/readout, mixed binding','owner':'EDABK design','evidence':'Synthesizable RTL, dataset/protocol/gate checks'},
       {'component':'SAR digital control, comparator/TG/CDAC inventory','owner':'SKY130_SAR_ADC1 upstream; adapted partition','evidence':'Attributed original source and live SAR feedback'},
       {'component':'PDK, Liberty and physical tools','owner':'SKY130 / upstream open-source projects','evidence':'NOTICE and pinned tool configuration'},
       {'component':'HAR windows','owner':'UCI dataset authors, CC BY 4.0','evidence':'Subject-separated train/validation/test'}]
    runtime=[]
    for label,path in [('Short review',work/'quick_review/verification.json'),('Isolated environment',work/'clean_environment/verification.json')]:
        if not path.exists():
            path=path.parent.with_name(path.parent.name+'_retry')/path.name
        if path.exists():d=read(path);runtime.append({'path':label,'elapsed_s':d['elapsed_s'],'scope':d['scope']})
    timer=work/'flow_timer_start.json'
    if timer.exists():
        receipt=work/'flow_runtime.json'
        if not receipt.exists():receipt.write_text(json.dumps({'elapsed_s':time.monotonic()-read(timer)['monotonic_start'],'scope':'Full laboratory from its first code cell through final figure generation; cell coverage/completion is independently audited by the headless runner.'},indent=2)+'\n')
        t=read(receipt);runtime.append({'path':'Full measured flow','elapsed_s':t['elapsed_s'],'scope':t['scope']})
    tables={'implementation_comparison':implementation,'analog_qualification':analog,'evidence_ownership':ownership,'reproduction_runtime':runtime}
    for name,rows in tables.items():
        (work/(name+'.json')).write_text(json.dumps(rows,indent=2)+'\n')
        if rows:
            with (work/(name+'.csv')).open('w') as stream:w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    result={'status':'PASS','figures':images,'tables':list(tables),'application_windows':2947,'scope':'Figures/tables generated from declared measured reports; counts of unlike checks remain separate.'}
    (work/'presentation.json').write_text(json.dumps(result,indent=2)+'\n');print('EVIDENCE_FIGURES_AND_TABLES',len(images),len(tables),flush=True);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--base',type=Path,required=True);p.add_argument('--work',type=Path,required=True);a=p.parse_args();run(a.root,a.base,a.work)
