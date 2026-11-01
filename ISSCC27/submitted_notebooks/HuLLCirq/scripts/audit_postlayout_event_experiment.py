"""Original-job functional/provenance audit; never qualifies all S14 timing."""
from pathlib import Path
import argparse,hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from hullcirq.physical_tools import load,sha,require
from hullcirq.postlayout_execution_audit import validate_completed_execution
from hullcirq.postlayout_execution import fixed_worker_definition
from hullcirq.verification import object_hash

SOURCE=ROOT/'.work/m2k/dynamic/original-job-yfyg25m7'
EVIDENCE=ROOT/'results/npu_postlayout_diagnostic_v2/evidence.json'
EVIDENCE_SHA='93bfa502b27afec1e56f6e676d9e475b94ac57759431e94b46c071aa62d35850'

def validate_original_binding(binding,evidence):
    definition=fixed_worker_definition('v3')
    expected=set(definition['COMPILE_INPUTS'])|{'verification-plan.json','testbench-adapter.json',
        'hullcirq_readback.c','hullcirq_readback.vpi','sdf-readback-manifest.tsv'}
    require(type(binding) is dict and binding.get('kind')=='hullcirq-unchanged-original-job-event-experiment-v1'
        and binding.get('original_folder')==str(SOURCE) and binding.get('adoption_permitted') is False
        and binding.get('original_evidence_sha256')==EVIDENCE_SHA
        and binding.get('original_source_binding')==evidence['original_source_binding']
        and all(binding.get(key) is False for key in ('original_job_changed','rtl_changed','sdf_changed','cell_models_changed')),
        'event_original_binding','Do not replace the original source inputs or GUI data.')
    require(type(binding.get('unchanged_inputs')) is dict and set(binding['unchanged_inputs'])==expected,
        'event_original_inputs','Require the complete exact original input set, including the original plan and observer inputs.')
    require(binding.get('event_plugin_inputs')==definition['PLUGIN_SHA256'],
        'event_original_binding','Retain every fixed observer input and its exact byte identity.')

def output_values(log,plan):
    observed=[(int(i),int(value),int(cycle)) for i,value,cycle in
        re.findall(r'^HULLCIRQ_OUTPUT index=(\d+) value=(-?\d+) cycle=(\d+)$',log,re.M)]
    words=re.findall(r"expected\[(\d+)\] = 32'h([0-9a-f]{8});",plan['testbench'])
    require([int(i) for i,_ in words]==list(range(16)),'event_original_plan','Keep all sixteen inherited original expectations.')
    expected=[int(word,16)-(1<<32) if int(word,16)>=(1<<31) else int(word,16) for _,word in words]
    marker=f'HULLCIRQ_GLOBAL_PASS outputs=16 vector_hash={plan["vector_hash"]}'
    passed=([i for i,_,_ in observed]==list(range(16)) and [v for _,v,_ in observed]==expected
            and log.count(marker)==1 and 'HULLCIRQ_FAIL' not in log)
    return dict(status='Passed' if passed else 'Failed',expected=expected,observed=observed,
                expected_outputs=16,observed_outputs=len(observed),vector_hash=plan['vector_hash'])

def audit(folder,destination):
    folder=Path(folder).resolve();destination=Path(destination).resolve()
    require(folder.parent==(ROOT/'.work/m2l/dynamic').resolve(),'event_experiment_path','Use the new isolated original-job run.')
    require(sha(EVIDENCE)==EVIDENCE_SHA,'event_original_evidence','Retain the unchanged earlier original-job evidence.')
    evidence=load(EVIDENCE);binding=load(folder/'source-binding.json')
    validate_original_binding(binding,evidence)
    for name,expected in binding['unchanged_inputs'].items():
        require(sha(folder/name)==sha(SOURCE/name)==expected,'event_original_inputs','An original input changed: '+name)
    original_audits={op:validate_completed_execution(SOURCE,op,worker_version='v2') for op in ('compile','simulate')}
    require(object_hash(original_audits)==object_hash(evidence['execution_audits'])==object_hash(binding['original_execution_audits']),
        'event_original_execution','The inherited actual source execution is no longer bound.')
    audits={op:validate_completed_execution(folder,op,worker_version='v3') for op in ('compile','simulate')}
    for name,op in (('compile-execution.json','compile'),('simulate-execution.json','simulate')):
        result=load(folder/name)
        require(result.get('executed') is True and result.get('status')=='Completed' and result.get('exit_code')==0
            and result.get('cleanup_unresolved') is False,'event_execution','Require completed unchanged-input operations and verified cleanup.')
    plan=load(folder/'verification-plan.json')
    require(object_hash(plan)==evidence['original_source_binding']['verification_plan_sha256'],
            'event_original_plan','Preserve the original GUI verification plan.')
    functional=output_values((folder/'simulate/stdout.log').read_text(encoding='utf-8'),plan)
    original=output_values((SOURCE/'simulate/stdout.log').read_text(encoding='utf-8'),plan)
    functional.update(original_cycle_trace_equal=functional['observed']==original['observed'],
        original_verification_plan_sha256=object_hash(plan),scope='same original GUI job values, receiving cycles and sixteen finite assertions only',
        original_job_values_changed=False,adoption_permitted=False)
    if not functional['original_cycle_trace_equal']:functional['status']='Failed'
    summary=load(folder/'hullcirq-events-summary.json')
    report=dict(schema='hullcirq-original-job-event-experiment-audit-v1',functional=functional,
        execution_audits=audits,event_capture_summary=summary,
        original_input_hashes=binding['unchanged_inputs'],event_transcript_sha256=sha(folder/'hullcirq-events.tsv'),
        S14_status='Unsupported',adoption_permitted=False,
        reason='Conditional delay binding, full event timing and pulse/X qualification require their separate original-source audits.')
    destination.mkdir(exist_ok=False)
    with (destination/'functional-and-provenance.json').open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(dict(functional_status=functional['status'],observed_outputs=functional['observed_outputs'],
                         original_cycle_trace_equal=functional['original_cycle_trace_equal'],S14_status='Unsupported')))
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('experiment');parser.add_argument('new_audit_directory')
    args=parser.parse_args();audit(args.experiment,args.new_audit_directory)
