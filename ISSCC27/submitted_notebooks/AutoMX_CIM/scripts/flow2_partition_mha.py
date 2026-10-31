"""Tiny MHA fed by measured, directly coupled CIM/ADC partition conversions.

Q/K/V/O projections reuse one physical column. Attention/softmax are the
architectural digital CPU runtime. No fitted analog lookup supplies an ADC
word; every requested physical pattern has a native conversion receipt.
"""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import numpy as np

from automx_cim.attention import mha_from_projections,error_metrics
from scripts.flow2_runall_support import digest,item,save,verified


def quantize_context(values):
    magnitudes=np.array([0,.5,1,1.5,2,3,4,6])
    v=np.asarray(values,dtype=float)
    if not np.all(np.isfinite(v)):raise ValueError('nonfinite context')
    closest=magnitudes[np.argmin(abs(abs(v)[...,None]-magnitudes),axis=-1)]
    return (np.sign(v)*closest*2).astype(int)


class Experiment:
    def __init__(self,flow):
        self.flow=flow;self.root=flow.root;self.references={};self.calibration_keys=set();self.required=[]
        self.lib=flow.base/'tools/ngspice_shared44/install/lib/libngspice.so'
        if not self.lib.is_file():raise FileNotFoundError('prepare the pinned shared ngspice runtime first')
        self.sources=[self.lib,*[self.root/'scripts'/f for f in ('flow2_rtl_spice_cosim.py','flow2_adc_partition.py')]]
        ip=self.root/'third_party/SKY130_SAR_ADC1/mixed_signal_partition'
        manifest=json.loads((ip/'provenance.json').read_text())
        for source in manifest['files']:
            path=ip/source['path']
            if digest(path)!=source['sha256']:raise ValueError('pinned SAR source changed')
            self.sources.append(path)
        from scripts.run_flow2_core_tap_transient import source
        from scripts import flow2_integration_common as common
        receipt,data,views=source(self.root,'core_tap_pex_srv_20261022_01')
        condition=self.root/common.BASE/'mixed_wrapper_20261020_01_cond/summary.json'
        c=json.loads(condition.read_text());c=c.get('block',c)
        self.sources += [receipt,views['schematic'],condition,common._verified(self.root,c['views']['schematic']),
            Path(data['pdk'])/'libs.tech/ngspice/sky130.lib.spice']

    @staticmethod
    def payload(activation,weights):
        a=np.asarray(activation,dtype=int);w=np.zeros((4,4),dtype=int);w[:,0]=weights
        data={'activation_x2':a.tolist(),'weights':w.tolist(),'column':0}
        import hashlib
        key=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()[:16]
        return key,data

    def measure(self,payload):
        key,data=payload;name='conversion_'+key;work=self.flow.work/name;work.mkdir(exist_ok=True)
        case=work/'case.json';save(case,data)
        command=[__import__('sys').executable,'-u',self.root/'scripts/flow2_rtl_spice_cosim.py',
            '--root',self.root,'--work',work,'--library',self.lib,'--case',case]
        self.flow.run(name,command,inputs=[case,*self.sources],outputs=['summary.json','coupled.raw','ngspice.log','rtl.log'],
                      timeout_s=self.flow.settings.timeout_s)
        result=json.loads((work/'summary.json').read_text())
        if result['status']!='COUPLED_ANALOG_RTL_ADC_PARTITION_CONVERSION_PASS':raise ValueError('conversion did not pass')
        if any(result[k]!=data[k] for k in ('activation_x2','weights','column')):
            raise ValueError('native result does not belong to requested physical pattern')
        if not 0<=result['result_code_12bit']<4096 or result['result_word_16bit']!=result['result_code_12bit']<<4 or result['cycles']<16:
            raise ValueError('native result word or SAR trace incomplete')
        self.references[key]=item(work/'summary.json')
        return result

    def many(self,payloads):
        unique=dict(payloads)
        with ThreadPoolExecutor(max_workers=self.flow.settings.jobs) as pool:
            results=list(pool.map(self.measure,unique.items()))
        return dict(zip(unique,results))

    def calibrate(self):
        rows=([0,0,0,0],[-4,-4,0,0],[4,4,0,0])
        payloads=[self.payload(a,[1,1,1,1]) for a in rows]
        self.calibration_keys={p[0] for p in payloads};cases=self.many(payloads)
        x=np.array([sum(a) for a in rows],float)
        y=np.array([cases[k]['result_code_12bit'] for k,_ in payloads],float)
        order=np.argsort(x);steps=np.diff(y[order])
        if not(np.all(steps>0) or np.all(steps<0)):raise ValueError('three fresh calibration codes must be distinct and monotonic')
        slope,offset=np.polyfit(x,y,1)
        if abs(slope)<1:raise ValueError('ADC calibration has no usable signal span')
        self.slope=float(slope);self.offset=float(offset)
        self.calibration={'expected_integer_sums':x.tolist(),'measured_ADC_codes':y.tolist(),
            'slope_codes_per_integer_sum':self.slope,'offset_code':self.offset,
            'maximum_residual_codes':float(np.max(abs(y-(slope*x+offset)))),
            'frozen_before_holdout':True,'source_cases':{k:self.references[k] for k,_ in payloads}}
        save(self.flow.work/'calibration.json',self.calibration)
        print('Measured ADC calibration:',json.dumps(self.calibration,indent=2))
        return self.calibration

    def project(self,activation,weights,label):
        a=np.asarray(activation,dtype=int);w=np.asarray(weights,dtype=int)
        requests=[(row,col,self.payload(a[row],w[:,col])) for row in range(a.shape[0]) for col in range(4)]
        result=self.many([p for _,_,p in requests]);out=np.zeros((len(a),4));jobs=[]
        for row,col,(key,payload) in requests:
            if key in self.calibration_keys:raise ValueError('calibration pattern reused as holdout')
            measured=result[key];estimate=(measured['result_code_12bit']-self.offset)/self.slope
            decoded=int(np.rint(estimate));out[row,col]=decoded/2
            truth=int(a[row]@w[:,col]);self.required.append(key)
            jobs.append({'stage':label,'row':row,'column':col,'physical_column':0,'case':self.references[key],
                'raw_ADC_code':measured['result_code_12bit'],'decoded_integer_sum':decoded,
                'unrounded_calibrated_sum':float(estimate),'reference_integer_sum':truth})
        return out,jobs

    def mha(self):
        if not hasattr(self,'slope'):raise ValueError('freeze independent calibration first')
        a=np.array([[2,-1,1,0],[-1,2,0,1]],int)
        q=np.array([[1,0,1,-1],[0,1,-1,1],[1,1,0,0],[-1,1,1,0]],int)
        k=np.roll(q,1,axis=0)
        v=np.array([[1,0,-1,1],[0,1,1,0],[-1,1,0,1],[1,-1,1,0]],int)
        o=np.array([[1,0,-1,1],[-1,1,0,1],[0,-1,1,1],[1,1,-1,0]],int)
        projections=[];jobs=[]
        for label,weight in (('Q',q),('K',k),('V',v)):
            projection,rows=self.project(a,weight,label);projections.append(projection);jobs+=rows
        measured=mha_from_projections(*projections,np.eye(4),2)
        context_x2=quantize_context(measured.context)
        output,rows=self.project(context_x2,o,'O');jobs+=rows
        gold=mha_from_projections(a@q/2,a@k/2,a@v/2,np.eye(4),2)
        reference=quantize_context(gold.context)@o/2
        metrics=error_metrics(reference,output)
        relative=float(np.linalg.norm(output-reference)/max(np.linalg.norm(reference),1e-12))
        if not np.allclose(measured.probabilities.sum(axis=-1),1):raise ValueError('attention rows do not sum to one')
        report={'status':'MEASURED_PARTITION_ANALOG_ADC_MHA_END_TO_END_PASS' if relative<=.25 else 'MHA_PARTITION_ACCURACY_FAIL',
            'shape':{'sequence':2,'d_model':4,'heads':2,'physical_rows':4,'physical_columns_used':1},
            'activation_x2':a.tolist(),'weights':{n:w.tolist() for n,w in (('Q',q),('K',k),('V',v),('O',o))},
            'calibration':self.calibration,'output':output.tolist(),'reference_quantized_output':reference.tolist(),
            'probabilities':measured.probabilities.tolist(),'measured_projections':{n:p.tolist() for n,p in zip(('Q','K','V'),projections)},
            'measured_context':measured.context.tolist(),'context_activation_x2':context_x2.tolist(),
            'floating_reference_output':(gold.context@o).tolist(),
            'floating_reference_metrics':error_metrics(gold.context@o,output),
            'floating_reference_relative_l2':float(np.linalg.norm(output-gold.context@o)/max(np.linalg.norm(gold.context@o),1e-12)),
            'metrics':metrics,'relative_l2':relative,'prototype_relative_l2_budget':.25,
            'projection_transactions':len(jobs),'unique_holdout_patterns':len(set(self.required)),
            'unmeasured_analog_lookup_estimates':0,'calibration_holdout_pattern_overlap':0,'jobs':jobs,
            'evidence':self.references,'fabrication_ready':False,'whole_chip_transistor_verified':False,
            'scope':'End-to-end simulation of tiny MHA using measured native CIM/ADC partition for every Q/K/V/O projection. '
              'One physical column time-multiplexed. CPU attention/softmax and a frozen 3-point digital calibration. '
              'Schematic analog core/conditioner, real transistor comparator/input sampler; aggregated CDAC with ideal bottom drivers, '
              'external clock/VCM, comparator noise-decoupling varactors omitted. Not full-top RC/PEX/noise/PVT or trained-model accuracy.'}
        save(self.flow.work/'mha_end_to_end.json',report)
        self.flow.outputs['analog_adc_mha']=item(self.flow.work/'mha_end_to_end.json')
        print(json.dumps({k:v for k,v in report.items() if k not in ('jobs','evidence')},indent=2))
        if report['status'].endswith('FAIL'):raise ValueError('measured MHA error exceeds the frozen prototype budget')
        return report
