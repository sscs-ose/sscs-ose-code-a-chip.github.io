"""Classify conclusive physical reports without treating missing data as a pass."""
import math
import json
from pathlib import Path


def read_reports(evidence):
    evidence=Path(evidence);errors=[]
    def nonfinite(token):
        raise ValueError('Nonfinite JSON literal: '+token)
    def read(path):
        try:
            value=json.loads(path.read_text(),parse_constant=nonfinite)
            if not isinstance(value,dict):raise ValueError('Report must be an object')
            return value
        except (OSError,ValueError):
            errors.append('invalid_physical_report');return {}
    paths=list(evidence.glob('orfs-work/logs/**/6_report.json'))
    raw=read(paths[0]) if len(paths)==1 else {}
    if len(paths)>1:errors.append('ambiguous_physical_report')
    if (evidence/'summary.json').exists():native=read(evidence/'summary.json')
    elif (evidence/'physical-report.json').exists():
        native=read(evidence/'physical-report.json').get('raw_flow_summary',{})
        if not isinstance(native,dict):native={};errors.append('invalid_physical_report')
    else:native={}
    return raw,native,sorted(set(errors))


def number(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def classify(physical,raw,native):
    failures=set(physical.get('failure_classes',[]))
    if not physical['physical_qualified'] and not failures:failures.add('physical_execution')
    if physical['physical_qualified'] and physical.get('task_state')!='satisfied':failures.add('physical_execution')
    for field,label in (('detailed_routing_violations','routing'),('drc_violations','drc')):
        value=native.get(field)
        if number(value) and value>0:failures.add(label)
        elif physical['physical_qualified'] and (not number(value) or value!=0):failures.add('incomplete_physical_metrics')
    if native.get('lvs') in ('failed','mismatched','unmatched'):failures.add('lvs')
    elif physical['physical_qualified'] and native.get('lvs')!='matched':failures.add('incomplete_physical_metrics')
    if native.get('functional_simulation')=='failed':failures.add('functional')
    for kind in ('setup','hold'):
        value=raw.get('finish__timing__'+kind+'__ws')
        count=raw.get('finish__timing__drv__'+kind+'_violation_count')
        if number(value) and value<0 or number(count) and count>0:failures.add('timing')
        if physical['physical_qualified'] and not number(value):failures.add('incomplete_physical_metrics')
    for kind in ('max_slew','max_cap','max_fanout'):
        value=raw.get('finish__timing__drv__'+kind)
        if number(value) and value>0:failures.add('electrical')
        elif physical['physical_qualified'] and (not number(value) or value!=0):failures.add('incomplete_physical_metrics')
    for key in ('finish__design__instance__area__stdcell','finish__design__die__area'):
        if physical['physical_qualified'] and (not number(raw.get(key)) or raw[key]<=0):
            failures.add('incomplete_physical_metrics')
    if physical.get('frozen_inputs_unchanged') is False:failures.add('source_or_constraint_changed')
    return sorted(failures)
