"""Authoring templates: every implementation below is emitted into notebook cells."""
from textwrap import dedent

SETUP = r'''
from pathlib import Path
import os, json, re, copy, tempfile, time, subprocess, shutil, gzip, sys
import numpy as np
import matplotlib.pyplot as plt
from IPython.display import display, Markdown, Image

BASE = Path(os.environ.get('AUTOMX_REVIEW_DIR', '.')).resolve()
if not (BASE/'data/evidence.json').is_file():
    raise FileNotFoundError('Open this notebook from the extracted automx_cim folder.')
OUT = Path(tempfile.mkdtemp(prefix='automx_review_'))
E = json.loads((BASE/'data/evidence.json').read_text())
NATIVE = os.environ.get('AUTOMX_REVIEW_NATIVE', 'auto').lower()
if NATIVE not in ('auto', 'on', 'off'): raise ValueError('AUTOMX_REVIEW_NATIVE: auto/on/off')
plt.rcParams.update({'figure.dpi':120, 'axes.spines.top':False,
                     'axes.spines.right':False, 'font.size':10})
def table(headers, rows):
    display(Markdown('| '+' | '.join(map(str,headers))+' |\n| '+
        ' | '.join(['---']*len(headers))+' |\n'+'\n'.join(
        '| '+' | '.join(map(str,row))+' |' for row in rows)))
def record(path): return json.loads((BASE/path).read_text())
def savefig(name):
    plt.tight_layout(); plt.savefig(OUT/name, bbox_inches='tight'); plt.show(); plt.close()
print('Analysis of supplied native measurements; no analog simulation is replayed as fresh.')
print('New analysis output folder:', OUT.name)
print('Python', sys.version.split()[0], '| NumPy', np.__version__, '| native mode:', NATIVE)
'''

VALIDATOR = r'''
RTL_FIELDS = ('sample','sample_n','result','eoc','eoc_osr','pr','pro','pc','pb','p0',
              'nr','nro','nc','nb','n0')
def payload(d):
    return (tuple(d['activation_x2']), tuple(tuple(row) for row in d['weights']), d['column'])
def truth(d):
    a=np.asarray(d['activation_x2']); w=np.asarray(d['weights'])
    if a.shape!=(4,) or w.shape!=(4,4): raise ValueError('invalid physical pattern shape')
    if not np.isin(a,[-12,-8,-6,-4,-3,-2,-1,0,1,2,3,4,6,8,12]).all():
        raise ValueError('activation outside signed E2M1 x2 set')
    if not np.isin(w,[-1,0,1]).all(): raise ValueError('nonternary weight')
    if d['column']!=0: raise ValueError('this study uses physical column zero')
    return int(a @ w[:,d['column']])
def parse_states(text):
    states=[]
    for line in text.splitlines():
        if not line.startswith('STATE '): continue
        tokens=line.split()[1:]
        if len(tokens)!=len(RTL_FIELDS) or any(re.search('[xz]',t,re.I) for t in tokens):
            raise ValueError('unknown or incomplete RTL state')
        states.append(dict(zip(RTL_FIELDS,[int(t,16) for t in tokens])))
    return states
def validate_case(d, rtl_text):
    expected=truth(d)
    if expected!=d['expected_integer_sum']: raise ValueError('stimulus/reference mismatch')
    code=d['result_code_12bit']; word=d['result_word_16bit']; trace=d['trace']
    if not isinstance(code,int) or not 0<=code<4096 or word!=(code<<4):
        raise ValueError('word bridge: result_word must equal code << 4')
    if d['cycles']!=16 or len(trace)!=16: raise ValueError('incomplete SAR trace')
    if not 0<d['start_s']<d['eoc_s']: raise ValueError('start/EOC timing')
    if not np.isclose(d['eoc_s']-d['start_s'],d['start_to_eoc_s'],rtol=1e-9,atol=1e-18):
        raise ValueError('latency receipt mismatch')
    if not np.all(np.diff([t['time_s'] for t in trace])>0): raise ValueError('nonmonotonic trace')
    states=parse_states(rtl_text)
    if len(states)!=18: raise ValueError('reset + priming + 16 SAR states required')
    for i,t in enumerate(trace):
        decision=t['decision']; voltage=t['comparator_v']
        if t['cycle']!=i or decision not in (0,1): raise ValueError('cycle/decision')
        if not np.isfinite(voltage) or not (voltage<=.18 if decision==0 else voltage>=1.62):
            raise ValueError('comparator rail disagrees with decision')
        if t['rtl']!=states[i+2]: raise ValueError('summary/native RTL trace mismatch')
        if i<15 and t['rtl']['eoc_osr']: raise ValueError('premature EOC')
    if not trace[-1]['rtl']['eoc_osr'] or not trace[-1]['rtl']['eoc']:
        raise ValueError('missing final EOC')
    if trace[-1]['rtl']['result']!=word: raise ValueError('trace/result mismatch')
    return expected
def assert_disjoint(calibration, holdout):
    c={payload(d) for d in calibration}; h=[payload(d) for d in holdout]
    if len(c)!=len(calibration) or c.intersection(h): raise ValueError('calibration leakage')
    if len(h)!=len(set(h)): raise ValueError('duplicate holdout patterns')

CASES={row['id']: record(row['summary']) for row in E['cases']}
META={row['id']: row for row in E['cases']}
for key,d in CASES.items():
    requested=record(META[key]['stimulus'])
    if payload(d)!=payload(requested): raise ValueError('requested stimulus/native summary mismatch')
    validate_case(d,(BASE/META[key]['rtl_log']).read_text())
CAL_IDS=E['calibration_ids']
HOLD_IDS=[r['id'] for r in E['cases'] if r['cohort']!='calibration']
assert_disjoint([CASES[k] for k in CAL_IDS],[CASES[k] for k in HOLD_IDS])
table(['Recorded cohort','Unique native conversions','Purpose'],[
    ['Calibration',len(CAL_IDS),'fit once'],
    ['MHA projections',sum(r['cohort']=='projection' for r in E['cases']),'Q/K/V/O'],
    ['New challenge',sum(r['cohort']=='challenge' for r in E['cases']),'frozen-fit diagnostic']])
print('All',len(CASES),'records agree with stimulus, word bridge, comparator rails and RTL logs.')
'''

ARCHITECTURE = r'''
from matplotlib.patches import FancyBboxPatch
fig,ax=plt.subplots(figsize=(12,4.1));ax.set(xlim=(0,12),ylim=(0,4));ax.axis('off')
def block(x,y,w,text,color):
    ax.add_patch(FancyBboxPatch((x,y),w,.82,boxstyle='round,pad=.05',fc=color,ec='#334155',lw=1))
    ax.text(x+w/2,y+.41,text,ha='center',va='center',fontsize=9)
def arrow(start,end,label=''):
    ax.annotate('',xy=end,xytext=start,arrowprops={'arrowstyle':'->','color':'#334155'})
    if label:ax.text((start[0]+end[0])/2,(start[1]+end[1])/2+.12,label,ha='center',fontsize=8)
block(.15,2.5,1.65,'Activation / weight\nPWM stimulus','#e2e8f0')
block(2.35,2.5,1.6,'Ternary CIM\n4 rows × 4 cols','#ffedd5')
block(4.5,2.5,2.0,'Acquisition\nS/H + conditioner','#ffedd5')
block(7.1,2.5,2.3,'ADC input switches\n+ comparator','#ffedd5')
block(7.1,.65,2.3,'SAR / decoder / OSR\nIcarus RTL','#dbeafe')
block(4.5,.65,2.0,'Charge-equivalent CDAC\nideal bottom drivers','#fef9c3')
block(9.95,.65,1.8,'Decoded Q/K/V/O\nCPU attention','#dbeafe')
for a,b,label in [((1.8,2.91),(2.35,2.91),'PWM'),((3.95,2.91),(4.5,2.91),'ΔV'),
                  ((6.5,2.91),(7.1,2.91),'held V'),((8.25,2.5),(8.25,1.47),'decision'),
                  ((7.1,1.06),(6.5,1.06),'controls'),((5.5,1.47),(7.1,2.5),'feedback'),
                  ((9.4,1.06),(9.95,1.06),'code')]:arrow(a,b,label)
ax.text(.15,.35,'Orange: transistor SPICE  |  Blue: digital  |  Yellow: partition model',fontsize=10)
ax.set_title('Inspectable mixed-signal boundary: one physical column reused for projection transactions',pad=8)
savefig('architecture.png')
'''

NEGATIVE = r'''
# Deliberately corrupt COPIES of evidence. These are checker tests, not silicon faults.
key=HOLD_IDS[0]; original=CASES[key]; text=(BASE/META[key]['rtl_log']).read_text()
mutations=[]
bad=copy.deepcopy(original); bad['result_word_16bit'] >>= 4
mutations.append(('Word alignment',lambda:validate_case(bad_word,text)))
bad_word=bad
bad_rail=copy.deepcopy(original); bad_rail['trace'][0]['decision']^=1
mutations.append(('Comparator polarity',lambda:validate_case(bad_rail,text)))
bad_eoc=copy.deepcopy(original); bad_eoc['trace'][-1]['rtl']['eoc_osr']=0
mutations.append(('Missing EOC',lambda:validate_case(bad_eoc,text)))
mutations.append(('Calibration leakage',lambda:assert_disjoint([original],[original])))
rejected=[]
for name,check in mutations:
    try: check()
    except ValueError as error:
        print('EXPECTED REJECTION |',name,'|',error); rejected.append(name)
    else: raise AssertionError('Checker accepted injected error: '+name)
assert len(rejected)==4
print('Checker detects all four deliberately injected errors; original evidence remains intact.')
'''

FACTORIAL = r'''
def parse_measurements(text):
    matches=re.findall(r'^\s*((?:diff|blp|bln)_c\d_t(?:09|19|21))\s*=\s*([-+\deE.]+)',text,re.M)
    if len(matches)!=28 or len(dict(matches))!=28: raise ValueError('incomplete/duplicate PEX measures')
    values={k:float(v) for k,v in matches}
    if not all(np.isfinite(list(values.values()))): raise ValueError('nonfinite PEX measures')
    return values
gaps={}; rows=[]
for condition in E['factorial']:
    c,p=condition['load_ff'],condition['pwm_unit_ps']; voltages=[]
    for job in condition['jobs']:
        measures=parse_measurements((BASE/job['log']).read_text())
        if any(not np.isclose(measures[k],v,rtol=0,atol=1e-12)
               for k,v in job['measurements_v'].items()): raise ValueError('PEX log/receipt mismatch')
        if int(np.asarray(job['activation_x2']) @ np.asarray(job['ternary_weights'])[:,0])!=job['integer_sums'][0]:
            raise ValueError('PEX stimulus/reference mismatch')
        voltages.append(measures['diff_c0_t19'])
    gap=voltages[1]-voltages[0]; gaps[c,p]=gap
    rows.append([c,p,*[f'{v*1000:.4f}' for v in voltages],f'{gap*1000:+.4f}',condition['acquisition']])
table(['C / fF','PWM / ps','s11 / mV','s12 / mV','gap / mV','Acquisition'],rows)
effects={
    'Load effect at 50 ps':gaps[800,50]-gaps[200,50],
    'Load effect at 100 ps':gaps[800,100]-gaps[200,100],
    'PWM shortening at 200 fF':gaps[200,50]-gaps[200,100],
    'PWM shortening at 800 fF':gaps[800,50]-gaps[800,100]}
interaction=effects['Load effect at 50 ps']-effects['Load effect at 100 ps']
table(['Controlled effect','Change in signed gap / mV'],[[k,f'{v*1000:+.4f}'] for k,v in effects.items()]+
      [['Load × PWM interaction',f'{interaction*1000:+.4f}']])
fig,axes=plt.subplots(1,2,figsize=(10,3.5))
for c,color in [(200,'#b24a43'),(800,'#245c8a')]:
    axes[0].plot([50,100],[gaps[c,50]*1000,gaps[c,100]*1000],'o-',label=f'{c} fF',color=color)
axes[0].axhline(0,color='black',lw=.7); axes[0].set(xlabel='PWM unit / ps',ylabel='s12 − s11 gap / mV',title='Matched-pattern 2×2 ablation')
axes[0].legend()
for i,condition in enumerate(E['factorial']):
    v=[j['measurements_v']['diff_c0_t19']*1000 for j in condition['jobs']]
    axes[1].plot([i,i],v,color='#718096'); axes[1].scatter(i,v[0],marker='s',color='#b24a43')
    axes[1].scatter(i,v[1],marker='o',color='#245c8a')
axes[1].set_xticks(range(4),[f"{r['load_ff']} fF\n{r['pwm_unit_ps']} ps" for r in E['factorial']])
axes[1].set(ylabel='Differential voltage / mV',title='Squares: s11; circles: s12')
savefig('factorial.png')
print('Recorded ngspice measurement block (unaltered numerical rows):')
example=E['factorial'][0]['jobs'][0]
for line in (BASE/example['log']).read_text().splitlines():
    if re.match(r'^\s*(?:diff|blp|bln)_c\d_t',line): print(line)
'''

CALIBRATION = r'''
x=np.array([truth(CASES[k]) for k in CAL_IDS],float)
y=np.array([CASES[k]['result_code_12bit'] for k in CAL_IDS],float)
if sorted(x.tolist())!=[-8.,0.,8.]: raise ValueError('unexpected calibration stimulus')
slope,offset=np.polyfit(x,y,1)
if abs(slope)<1: raise ValueError('unusable calibration span')
FROZEN=(float(slope),float(offset))
residual=y-(slope*x+offset)
table(['Calibration sum','Native ADC code','Fit residual / codes'],
      [[int(a),int(b),f'{r:+.6f}'] for a,b,r in zip(x,y,residual)])
print(f'Frozen calibration: code = {slope:.8f} × sum + {offset:.8f}')
print(f'Maximum calibration residual: {np.max(abs(residual)):.6f} codes')
def estimate(d): return (d['result_code_12bit']-FROZEN[1])/FROZEN[0]
def decode(d): return int(np.rint(estimate(d)))
observations=[]
for key in HOLD_IDS:
    d=CASES[key]; s=truth(d)
    observations.append({'id':key,'cohort':META[key]['cohort'],'truth':s,'code':d['result_code_12bit'],
        'estimate':float(estimate(d)),'decoded':decode(d),'residual':float(estimate(d)-s),
        'activity':int(np.sum(abs(np.asarray(d['activation_x2'])*np.asarray(d['weights'])[:,0]))),
        'latency_ns':d['start_to_eoc_s']*1e9})
table(['Holdout cohort','Patterns','Integer mismatches','Max |sum residual|'],[
    [cohort,len(group),sum(r['decoded']!=r['truth'] for r in group),f"{max(abs(r['residual']) for r in group):.6f}"]
    for cohort in ('projection','challenge')
    for group in [[r for r in observations if r['cohort']==cohort]]])
assert all(r['decoded']==r['truth'] for r in observations)
fig,axes=plt.subplots(1,2,figsize=(10,3.3))
for cohort,marker in [('projection','o'),('challenge','s')]:
    g=[r for r in observations if r['cohort']==cohort]
    axes[0].scatter([r['truth'] for r in g],[r['code'] for r in g],label=cohort,marker=marker,alpha=.75)
    axes[1].scatter([r['activity'] for r in g],[r['residual'] for r in g],label=cohort,marker=marker,alpha=.75)
xx=np.linspace(-8,8,100); axes[0].plot(xx,slope*xx+offset,color='black',lw=.8,label='3-point frozen fit')
axes[0].set(xlabel='Stimulus integer sum',ylabel='Measured ADC code',title='Calibration → independent decoding');axes[0].legend(fontsize=8)
axes[1].axhline(0,color='black',lw=.7);axes[1].set(xlabel='Activity Σ|aᵣwᵣ|',ylabel='Unrounded sum − truth',title='Variation remains visible before rounding')
savefig('calibration_holdout.png')
'''

CHALLENGE = r'''
challenge=[r for r in observations if r['cohort']=='challenge']
table(['New pattern','Sum','Activity','Code','Unrounded sum','Decoded'],[
    [r['id'],r['truth'],r['activity'],r['code'],f"{r['estimate']:+.6f}",r['decoded']] for r in challenge])
for sign in ('p3','n3'):
    lo=next(r for r in challenge if r['id']==f'sum_{sign}_low')
    hi=next(r for r in challenge if r['id']==f'sum_{sign}_high')
    print(f"Same sum {lo['truth']:+d}, activity {lo['activity']} → {hi['activity']}: "
          f"ADC code {lo['code']} → {hi['code']}; Δcode = {hi['code']-lo['code']:+d}")
latencies=np.array([r['latency_ns'] for r in observations])
print(f'Measured start→EOC across {len(observations)} holdouts: '
      f'{latencies.min():.3f}…{latencies.max():.3f} ns; median {np.median(latencies):.3f} ns')
'''

MHA = r'''
def attention(q,k,v,heads=2):
    q,k,v=[np.asarray(t,float) for t in (q,k,v)]
    if q.shape!=k.shape or q.shape!=v.shape or q.ndim!=2: raise ValueError('Q/K/V shape')
    n,d=q.shape
    if d%heads: raise ValueError('head dimension')
    qh,kh,vh=[t.reshape(n,heads,d//heads).transpose(1,0,2) for t in (q,k,v)]
    scores=qh@kh.transpose(0,2,1)/np.sqrt(d//heads)
    exp=np.exp(scores-scores.max(axis=-1,keepdims=True)); probabilities=exp/exp.sum(axis=-1,keepdims=True)
    return (probabilities@vh).transpose(1,0,2).reshape(n,d),probabilities
def quantize_context(values):
    magnitudes=np.array([0,.5,1,1.5,2,3,4,6]); values=np.asarray(values,float)
    nearest=magnitudes[np.argmin(abs(abs(values)[...,None]-magnitudes),axis=-1)]
    return (np.sign(values)*nearest*2).astype(int)
def relative_l2(reference,candidate):
    return float(np.linalg.norm(candidate-reference)/max(np.linalg.norm(reference),1e-12))
spec=E['mha']; a=np.asarray(spec['activation_x2']); weights={k:np.asarray(v) for k,v in spec['weights'].items()}
projections={stage:np.zeros((2,4)) for stage in ('Q','K','V','O')}
jobs=spec['jobs']
if len(jobs)!=32 or len({(j['stage'],j['row'],j['column']) for j in jobs})!=32:
    raise ValueError('missing or duplicate projection transactions')
def measured_projection(stage,activation):
    for job in [j for j in jobs if j['stage']==stage]:
        row,col,key=job['row'],job['column'],job['case']; d=CASES[key]
        if META[key]['cohort']!='projection': raise ValueError('MHA must use projection holdout')
        if d['activation_x2']!=activation[row].tolist(): raise ValueError('projection activation mismatch')
        if np.asarray(d['weights'])[:,0].tolist()!=weights[stage][:,col].tolist():
            raise ValueError('projection weight mismatch')
        projections[stage][row,col]=decode(d)/2
    return projections[stage]
q,k,v=[measured_projection(stage,a) for stage in ('Q','K','V')]
context,probabilities=attention(q,k,v)
output=measured_projection('O',quantize_context(context))
gold_context,gold_probabilities=attention(a@weights['Q']/2,a@weights['K']/2,a@weights['V']/2)
ref_quantized=quantize_context(gold_context)@weights['O']/2
ref_float=gold_context@weights['O']
assert np.allclose(probabilities.sum(axis=-1),1)
assert np.array_equal(output,ref_quantized)
assert np.allclose(output,spec['recorded_output'])
MHA_QUANT=relative_l2(ref_quantized,output); MHA_FLOAT=relative_l2(ref_float,output)
table(['Reference','Relative L2 error'],[['Same context quantization',f'{MHA_QUANT:.9f}'],
                                        ['Floating context',f'{MHA_FLOAT:.9f}']])
print('Measured MHA output (32 transactions; 30 unique projection patterns):\n',output)
fig,axes=plt.subplots(1,3,figsize=(10.5,3))
for ax,values,title in zip(axes,[ref_float,output,output-ref_float],['Floating reference','Measured projection output','Measured − floating']):
    m=ax.imshow(values,cmap='RdBu_r',vmin=-3.1 if '−' not in title else -.4,vmax=3.1 if '−' not in title else .4)
    ax.set(title=title,xlabel='Dimension',ylabel='Token');ax.set_xticks(range(4));ax.set_yticks([0,1])
    for (i,j),value in np.ndenumerate(values): ax.text(j,i,f'{value:.2f}',ha='center',va='center',fontsize=9)
    fig.colorbar(m,ax=ax,shrink=.7)
savefig('mha.png')
'''

WAVEFORM_PLOT = r'''
wave=read_raw(BASE/E['waveform']['path']); case=CASES[E['waveform']['case']]
t=wave['time']*1e9
fig,axes=plt.subplots(4,1,figsize=(10,7),sharex=True)
axes[0].plot(t,wave['v(ainp)']-wave['v(ainn)'],label='ADC input difference')
axes[0].plot(t,wave['v(ctopp)']-wave['v(ctopn)'],label='CDAC top difference',alpha=.8)
axes[0].set_ylabel('V');axes[0].legend(loc='upper right')
for key in ('adc_clk_comp','latch_q','sample'):
    axes[1].plot(t,wave[f'v({key})'],label=key)
axes[1].set_ylabel('V'); axes[1].legend(loc='upper right',ncol=3)
for key in ('start','eoc'): axes[2].plot(t,wave[f'v({key})'],label=key)
axes[2].set_ylabel('V');axes[2].legend(loc='upper right')
word=sum((wave[f'v(result_{i})']>.9).astype(int)*(1<<i) for i in range(16))
axes[3].step(t,word>>4,where='post',label='result >> 4'); axes[3].legend(loc='upper left')
axes[3].set(xlabel='Time / ns',ylabel='ADC code')
assert int(word[-1]>>4)==case['result_code_12bit']
fig.suptitle('Recorded coupled transistor / RTL transient — '+E['waveform']['case'])
savefig('coupled_waveform.png')
print('Recorded Icarus state transcript for this waveform:')
print((BASE/META[E['waveform']['case']]['rtl_log']).read_text())
'''

NATIVE_RTL = r'''
def run_tool(args, *, input_text=None, env=None, timeout=90):
    print('RUN:', ' '.join(map(str,args)),flush=True)
    started=time.monotonic()
    result=subprocess.run(list(map(str,args)),input=input_text,text=True,
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env,timeout=timeout,cwd=OUT)
    print(result.stdout,end='' if result.stdout.endswith('\n') else '\n',flush=True)
    print('EXIT:',result.returncode,'| elapsed_s:',round(time.monotonic()-started,3),flush=True)
    if result.returncode: raise RuntimeError('Native tool failed')
    return result.stdout
rtl_results=[]
available=shutil.which('iverilog') and shutil.which('vvp')
if NATIVE=='on' and not available: raise FileNotFoundError('Install Icarus Verilog (iverilog + vvp)')
if NATIVE!='off' and available:
    bench=OUT/'cosim.sv';bench.write_text(TESTBENCH)
    exe=OUT/'sar.vvp'
    files=sorted((BASE/'rtl').glob('*.v'))
    run_tool(['iverilog','-V'])
    run_tool(['iverilog','-g2012','-s','cosim','-o',exe,bench,*files])
    for key,d in CASES.items():
        decisions=[str(t['decision']) for t in d['trace']]
        print('LIVE RTL REPLAY:',key,'| recorded analog decisions; fresh digital simulation')
        text=run_tool(['vvp',exe],input_text='0\n'+'\n'.join(decisions)+'\n')
        states=parse_states(text)
        if len(states)!=18 or states[2:]!=[t['rtl'] for t in d['trace']]:
            raise AssertionError('Native RTL state replay mismatch: '+key)
        (OUT/(key+'.rtl.log')).write_text(text)
        rtl_results.append(key)
    print('Native RTL:',len(rtl_results),'cases × 16 states ×',len(RTL_FIELDS),'signals matched.')
else:
    print('Native RTL not executed. Recorded-state validation above completed.')
'''

PHYSICAL = r'''
physical=E['physical']; geometry=record(physical['geometry']); power=record(physical['power']); drc=record(physical['drc'])
timing=(BASE/physical['timing_log']).read_text()
def slack(kind):
    matches=re.findall(r'AUTOMX_'+kind+r'_BEGIN\s+worst slack\s+([-+\d.]+)\s+AUTOMX_'+kind+r'_END',timing)
    if len(matches)!=1: raise ValueError('missing/ambiguous STA slack')
    return float(matches[0])
setup,hold=slack('SETUP'),slack('HOLD')
table(['Artifact / check','Recorded result'],[
    ['GDS geometry equivalence',geometry['status']],
    ['Cells / geometry instances / masters',f"{geometry['cells']} / {geometry['instances']} / {geometry['masters']}"],
    ['Supply connectivity',', '.join(f'{k}: {v}' for k,v in power['rails'].items())],
    ['Digital TT 25 MHz setup / hold slack',f'{setup:+.2f} ns / {hold:+.2f} ns'],
    ['Enabled-rule DRC attempt',drc['status']]])
print('Recorded OpenROAD STA header and summary:')
print('\n'.join(timing.splitlines()[:16]))
print('Recorded Netgen signal check — final verdict; complete transcript supplied in data/physical/:')
lvs=(BASE/physical['lvs_log']).read_text()
if 'Final result: Circuits match uniquely.' not in lvs: raise ValueError('Netgen unique match missing')
for line in lvs.splitlines():
    if line.startswith(('Final result:','Cell pin lists are equivalent.','Device classes automx_')): print(line)
print('DRC status is incomplete; no zero-violation claim is inferred from this report.')
display(Image(filename=str(BASE/'figures/top.png'),width=1000))
for name in ('core_acquisition','conditioner_mux','adc_reference'):
    display(Markdown('**Recorded KLayout render: '+name.replace('_',' ')+'**'))
    display(Image(filename=str(BASE/'figures'/f'{name}.png'),width=850))
'''

KLAYOUT = r'''
fresh_native_klayout=False
available=shutil.which('klayout')
if NATIVE=='on' and not available: raise FileNotFoundError('Install KLayout to inspect the supplied GDS')
if NATIVE!='off' and available:
    gds=OUT/'top.gds'
    with gzip.open(BASE/'layout/top.gds.gz','rb') as source,gds.open('wb') as target:
        shutil.copyfileobj(source,target)
    script=OUT/'render.py';script.write_text(KLAYOUT_SCRIPT)
    env=os.environ.copy();env.update(QT_QPA_PLATFORM='offscreen',AUTOMX_GDS=str(gds),
        AUTOMX_PNG=str(OUT/'top_live.png'),AUTOMX_GEOMETRY=str(OUT/'gds_live.json'))
    log=run_tool(['klayout','-z','-r',script],env=env,timeout=120)
    (OUT/'klayout.log').write_text(log)
    native_geometry=json.loads((OUT/'gds_live.json').read_text())
    if native_geometry['cells']!=geometry['cells']: raise AssertionError('GDS cell count mismatch')
    fresh_native_klayout=True
    print('Fresh KLayout read and render completed from the supplied GDS.')
    display(Image(filename=str(OUT/'top_live.png'),width=1000))
else:
    print('KLayout not executed; recorded native renders are displayed above.')
'''

KLAYOUT_SCRIPT = r'''
import os,json
from pathlib import Path
import pya
print('KLayout',pya.Application.instance().version(),flush=True)
window=pya.Application.instance().main_window()
if window is None: raise RuntimeError('Run with klayout -z and offscreen Qt')
window.load_layout(os.environ['AUTOMX_GDS'],1)
view=window.current_view(); cv=view.active_cellview(); layout=cv.layout()
cell=layout.cell('automx_cim_mixed_signal_proto')
if cell is None: raise RuntimeError('Expected mixed-signal top missing')
cv.cell=cell; view.add_missing_layers();view.max_hier();view.show_all_cells()
box=cell.dbbox(); margin=.02*max(box.width(),box.height())
if box.empty(): raise RuntimeError('Empty top geometry')
view.zoom_box(pya.DBox(box.left-margin,box.bottom-margin,box.right+margin,box.top+margin))
view.save_image(os.environ['AUTOMX_PNG'],1600,max(500,min(1600,round(1600*box.height()/box.width()))))
result={'cells':layout.cells(),'top':cell.name,'width_um':box.width(),'height_um':box.height()}
Path(os.environ['AUTOMX_GEOMETRY']).write_text(json.dumps(result,indent=2))
print('GDS_READ_AND_RENDER',json.dumps(result),flush=True)
pya.Application.instance().exit(0)
'''

SUMMARY = r'''
summary={'measurement_mode':'recorded native analog; fresh Python analysis',
    'unique_calibration':len(CAL_IDS),'unique_holdout':len(HOLD_IDS),
    'integer_decode_mismatches':sum(r['decoded']!=r['truth'] for r in observations),
    'max_abs_holdout_sum_residual':max(abs(r['residual']) for r in observations),
    'factorial_gap_mv':{f'{c}fF_{p}ps':v*1000 for (c,p),v in gaps.items()},
    'mha_transactions':len(jobs),'mha_relative_l2_quantized':MHA_QUANT,
    'mha_relative_l2_float':MHA_FLOAT,'negative_controls_rejected':len(rejected),
    'fresh_native_rtl_cases':len(rtl_results),'fresh_klayout_render':fresh_native_klayout,
    'setup_slack_ns':setup,'hold_slack_ns':hold,
    'drc_status':drc['status']}
(OUT/'review_results.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
print('New figures, fresh digital logs and recomputed results saved in',OUT.name)
'''

def code(value):
    return dedent(value).strip()+'\n'
