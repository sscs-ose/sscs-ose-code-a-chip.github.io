#!/usr/bin/env python3
"""Whole-chip prototype physical signoff with explicit bounded evidence/waivers.

This profile accepts a layout/digital integration prototype, not fabrication
qualification or a demonstrated end-to-end analog inference engine.
"""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import flow2_integration_common as common
from scripts import run_flow2_chip_sta as sta
from scripts import run_flow2_chip_gds_lvs as gds_lvs
from scripts import run_flow2_chip_etm as etm
from scripts import run_flow2_wrapper_full_magic as magic
from scripts import run_flow2_wrapper_rtl as rtl
from scripts.flow2_klayout_checks import full_groups_clean
from scripts.run_flow2_wrapper_transistor_lvs import validate_netgen


def decision(gates):
    required=('gds_inventory','gds_placements','gds_klayout_drc','independent_route_drc',
              'signal_lvs','gds_signal_macro_lvs','power_connectivity','nominal_digital_timing','fresh_digital_etm','rtl_transactions')
    return 'PROTOTYPE_PHYSICAL_SIGNOFF_WITH_WAIVERS' if all(gates.get(k) is True for k in required) else 'PROTOTYPE_SIGNOFF_REVIEW_REQUIRED'


def electrical_counts(text):
    counts={};section=None
    for line in text.splitlines():
        if line in ('max slew','max capacitance','max fanout'):
            section=line.replace(' ','_');counts[section]=0
        elif section and '(VIOLATED)' in line:counts[section]+=1
    return counts


def collect(root, *, tag, source_tag, sta_tag, lvs_tag, magic_tag, rtl_tag,etm_tag=None):
    root=Path(root).resolve()
    for t in (tag,source_tag,sta_tag,lvs_tag,magic_tag,rtl_tag):common.tag_ok(t)
    receipts={}
    def read(name,t):
        path=root/common.BASE/t/'summary.json'
        receipts[name]=common._item(root,path)
        return json.loads(path.read_text())
    source=read('streamout',source_tag);timing=read('sta',sta_tag)
    physical=read('gds_lvs',lvs_tag);mdrc=read('magic',magic_tag);digital=read('rtl',rtl_tag)
    model=read('etm',etm_tag) if etm_tag else {}
    if model and (model.get('source_tag')!=source_tag or model.get('sta_tag')!=sta_tag):
        raise ValueError('ETM belongs to another GDS/RC/STA point')
    if source['status']!='GDS_PROTOTYPE_KLAYOUT_CLEAN_SIGNAL_LVS_ONLY':raise ValueError('audited streamout required')
    views={k:common._item(root,common._verified(root,v)) for k,v in source['views'].items()}
    for child in (timing,mdrc):
        if child.get('source_tag')!=source_tag:raise ValueError('cross-GDS signoff evidence rejected')
        child_sources=child.get('sources',child.get('inputs',{}).get('sources',[]))
        if views['gds'] not in child_sources:raise ValueError('child lacks exact GDS hash binding')
    if physical.get('gds_tag',physical.get('source_tag'))!=source_tag or views['gds'] not in physical.get('sources',[]):
        raise ValueError('GDS LVS lacks exact source hash binding')
    gds_status=physical.get('status')
    accepted_gds_lvs=gds_status in ('GDS_POWERED_MACRO_LVS_MATCH',
        'SIGNAL_ONLY_GDS_MACRO_LVS_MATCH_NO_PG_BODY_QUALIFICATION',
        'GDS_SIGNAL_MACRO_LVS_MATCH_NO_STANDARD_PG_BODY_QUALIFICATION')
    extraction=read('gds_extraction',physical['source_tag']) if physical.get('gds_tag') else physical
    candidate=read('candidate',source['candidate_tag']);signal=read('signal_lvs',source['signal_lvs_tag'])
    if candidate.get('candidate_odb')!=views['odb']:raise ValueError('route evidence ODB differs')
    if signal.get('candidate_tag')!=source['candidate_tag']:raise ValueError('signal LVS belongs to another ODB')
    # Parse independent raw reports, not just a successful process exit.
    xml=root/common.BUILD/source_tag/'klayout.xml'
    tree=ET.parse(xml).getroot()
    if tree.tag!='report-database':raise ValueError('invalid KLayout report')
    receipts['klayout_xml']=common._item(root,xml)
    place_path=common._verified(root,source['placement_audit']['report'])
    place=json.loads(place_path.read_text());receipts['placements']=common._item(root,place_path)
    drc=root/common.BUILD/source['candidate_tag']/'independent.drc'
    receipts['independent_drc']=common._item(root,drc)
    validate_netgen(common._verified(root,signal['lvs_log']).read_text())
    if signal.get('status')!='SIGNAL_ONLY_DEF_LEF_LVS_MATCH_NO_PG_BODY_QUALIFICATION':raise ValueError('signal LVS not complete')
    if accepted_gds_lvs:
        validate_netgen(common._verified(root,physical['lvs_log']).read_text())
    tc=timing.get('checks',{});pg=tc.get('power',{});st=tc.get('sta',{});rc=tc.get('rcx',{})
    for check in tc.values():
        if 'log' in check:common._verified(root,check['log'])
    pg_proof=json.loads(common._verified(root,pg['geometry_proof']).read_text()) if 'geometry_proof' in pg else {}
    if 'spef' in rc:views['spef']=common._item(root,common._verified(root,rc['spef']))
    if 'sdc' in timing:views['sdc']=common._item(root,common._verified(root,timing['sdc']))
    if 'view' in model:views['lib']=common._item(root,common._verified(root,model['view']))
    for item in digital.get('inputs',{}).get('sources',[]):common._verified(root,item)
    gates=dict(gds_inventory=source['instance_audit']['status']=='ALL_DEF_COMPONENTS_PRESENT',
        gds_placements=place.get('status')=='PRESERVED_GDS_PLACEMENTS' and place.get('missing_or_moved_instances')==0,
        gds_klayout_drc=full_groups_clean(xml,source.get('klayout_rule_groups',{})),
        independent_route_drc=drc.stat().st_size==0 and candidate.get('independent_drc_bytes')==0,
        signal_lvs=True,gds_signal_macro_lvs=accepted_gds_lvs,
        power_connectivity=pg.get('status')=='PASS_EQUIVALENT_GEOMETRY' and
            pg_proof.get('rails')=={'VPWR':'PASS','VGND':'PASS'} and pg_proof.get('geometry_changed') is False,
        nominal_digital_timing=st.get('status')=='PASS_NOMINAL_DIGITAL_SETUP_HOLD' and rc.get('status')=='PASS' and
            st.get('setup_slack_ns',-1)>=0 and st.get('hold_slack_ns',-1)>=0,
        fresh_digital_etm=model.get('status')=='FRESH_NOMINAL_DIGITAL_ETM_PARSE_PASS',
        rtl_transactions=digital.get('status')=='PASS_WRAPPER_RTL_TRANSACTIONS')
    sl=common._verified(root,st['log']).read_text() if 'log' in st else ''
    waivers=[
        dict(id='ANTENNA',observed=source['antenna'],reason='Accepted for prototype layout review; manufacturing gate remains open.'),
        dict(id='ELECTRICAL_TIMING_COVERAGE',observed=electrical_counts(sl),
            unconstrained_endpoints=st.get('unconstrained_endpoints'),unannotated_drivers=st.get('unannotated_drivers'),
            reason='Only constrained nominal digital paths pass; analog macro arcs, slew/fanout and other corners remain open.'),
        dict(id='FULL_MAGIC',observed=mdrc['status'],reason='Bounded full-hierarchy check; timeout is incomplete, never zero violations.'),
        dict(id='TRANSISTOR_BODY_PEX',observed=gds_status,reason='GDS signal macro LVS omits standard-cell formal PG/body ports on both sides; analog macro PG and rail-tied signal inputs retained. No full PG/body/transistor LVS or transistor RC PEX.'),
        dict(id='PG_ONLY_INTERIORS',observed=extraction.get('physical_pg_only_instances_omitted'),raw_powered_comparison=extraction.get('status'),reason='PG-only cell interiors omitted on both physical/logical sides; full powered comparison did not complete. PG rails checked independently in the exact ODB with equivalent geometry.'),
        dict(id='ANALOG_ADC',observed='NO_FRESH_ADC_CONVERSION',reason='Three coupled frontend TT pilots use a 2pF ADC load; original 0.8mV capture requirement still fails. End-to-end ADC/MHA, noise and PVT remain unproven.'),
        dict(id='POWER_PACKAGE',observed='CONNECTIVITY_ONLY',reason='Virtual power sources; no padframe/package, IR drop or EM qualification.'),
        dict(id='READER_GRID',observed=extraction.get('reader_technology'),reason='Local LVS reader permits 1nm import precision; native DRC deck is unchanged.'),
    ]
    canonical=root/'results/receipts/wrapper_signoff.json'
    return dict(format='automx-cim-chip-prototype-signoff-v1',tag=tag,timestamp_utc=datetime.now(timezone.utc).isoformat(),
        status=decision(gates),profile='mixed_signal_layout_and_digital_prototype_v1',qualification='NOT_QUALIFIED',
        fabrication_ready=False,end_to_end_analog_demonstrated=False,source_tag=source_tag,
        views=views,evidence=receipts,gates=gates,waivers=waivers,
        operating_point=dict(period_ns=timing['period_ns'],frequency_mhz=timing['frequency_mhz'],corner=timing['corner'],
            setup_slack_ns=st.get('setup_slack_ns'),hold_slack_ns=st.get('hold_slack_ns')),
        canonical_strict_signoff=common._item(root,canonical),canonical_strict_status=json.loads(canonical.read_text())['status'],
        scope='Prototype physical/digital integration only. Waivers are profile selections requested for this experiment; '
              'they are not evidence that the waived checks passed.')


def run(root, *, tag, source_tag='antenna_streamout_srv_20261022_03', sta_tag=None,lvs_tag=None,magic_tag=None,rtl_tag=None,etm_tag=None,
        period_ns=40,execute=False):
    root=Path(root).resolve();common.tag_ok(tag)
    if not execute:return dict(status='PREPARED',tag=tag,source_tag=source_tag,scope=__doc__)
    if (root/common.BASE/tag/'inputs.json').exists():raise FileExistsError('fresh signoff tag required')
    canonical=root/'results/receipts/wrapper_signoff.json';strict_hash=common._sha(canonical)
    source=root/common.BASE/source_tag/'summary.json'
    store=common.Store(root,tag,dict(source=common._item(root,source),runner=common._sha(Path(__file__)),
        reuse=dict(sta=sta_tag,lvs=lvs_tag,magic=magic_tag,rtl=rtl_tag,etm=etm_tag),period_ns=period_ns))
    (store.build/'executed_runner.py').write_bytes(Path(__file__).read_bytes())
    try:
        with common.export_mode('deferred'):
            if sta_tag is None:
                sta_tag=tag+'_sta';sta.run(root,tag=sta_tag,source_tag=source_tag,period_ns=period_ns,execute=True)
            if etm_tag is None:
                etm_tag=tag+'_etm';etm.run(root,tag=etm_tag,sta_tag=sta_tag,execute=True)
            if lvs_tag is None:
                lvs_tag=tag+'_lvs';gds_lvs.run(root,tag=lvs_tag,source_tag=source_tag,execute=True,signal_only=True,timeout_s=300)
            if magic_tag is None:
                magic_tag=tag+'_magic';magic.run(root,tag=magic_tag,source_tag=source_tag,timeout_s=180,execute=True)
            if rtl_tag is None:
                rtl_tag=tag+'_rtl';rtl.run(root,tag=rtl_tag,timeout_s=120,execute=True)
        report=collect(root,tag=tag,source_tag=source_tag,sta_tag=sta_tag,lvs_tag=lvs_tag,magic_tag=magic_tag,rtl_tag=rtl_tag,etm_tag=etm_tag)
        if common._sha(canonical)!=strict_hash:raise ValueError('strict receipt changed during prototype campaign')
    except Exception as error:
        report=dict(status='BLOCKED_CHIP_PROTOTYPE_SIGNOFF',tag=tag,qualification='NOT_QUALIFIED',
                    error=type(error).__name__+': '+str(error))
    common.save_summary(store.folder/'summary.json',report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--tag',required=True);p.add_argument('--source-tag',default='antenna_streamout_srv_20261022_03')
    for name in ('sta','lvs','magic','rtl','etm'):p.add_argument('--'+name+'-tag')
    p.add_argument('--period-ns',type=float,default=40);p.add_argument('--run',action='store_true');a=p.parse_args()
    r=run(a.root,tag=a.tag,source_tag=a.source_tag,sta_tag=a.sta_tag,lvs_tag=a.lvs_tag,magic_tag=a.magic_tag,
        rtl_tag=a.rtl_tag,etm_tag=a.etm_tag,period_ns=a.period_ns,execute=a.run)
    print(json.dumps(r,indent=2,ensure_ascii=False))
    if a.run and r['status']!='PROTOTYPE_PHYSICAL_SIGNOFF_WITH_WAIVERS':raise SystemExit(1)
