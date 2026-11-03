#!/usr/bin/env python3
"""Bounded PG connectivity and fresh nominal routed RC/STA for a GDS prototype.

Checks the ODB bound by the streamout receipt. Analog macros are uncharacterized
timing boundaries. A slower clock never waives hold or missing timing data.
"""
import argparse
import json
import math
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import flow2_integration_common as common
from scripts import run_flow2_wrapper_postroute as post

NATIVE = 'mixed_wrapper_srv_20261022_04_impl_gds'


def timing_metrics(text):
    """Require complete finite measured setup and hold, in native nanoseconds."""
    if 'AUTOMX_CHIP_STA_DONE' not in text or re.search(r'(?im)^\s*(?:Error:|\[ERROR)', text):
        raise ValueError('incomplete or erroneous STA')
    values = {}
    for kind in ('SETUP', 'HOLD'):
        block = re.search('AUTOMX_'+kind+r'_BEGIN\n(.*?)AUTOMX_'+kind+'_END', text, re.S)
        matches = re.findall(r'worst slack\s+([-+\deE.]+)', block[1] if block else '')
        if len(matches) != 1 or not math.isfinite(float(matches[0])):
            raise ValueError('one finite '+kind+' slack required')
        values[kind.lower()+'_slack_ns'] = float(matches[0])
    return values


def prototype_sdc(text, period):
    if not math.isfinite(period) or not 20 <= period <= 1000:
        raise ValueError('prototype period must be finite and 20..1000 ns')
    pattern = r'(?m)^(create_clock\b[^\n]*?-period\s+)\d+(?:\.\d+)?'
    result, count = re.subn(pattern, lambda m: m[1]+str(period), text)
    if count != 1:
        raise ValueError('one original clock required')
    return result


def run(root, *, tag, source_tag='antenna_streamout_srv_20261022_03',
        period_ns=40.0, timeout_s=180, execute=False):
    root = Path(root).resolve(); common.tag_ok(tag); common.tag_ok(source_tag)
    if not 1 <= timeout_s <= 300: raise ValueError('bounded tool budget required')
    if (root/common.BASE/tag/'inputs.json').exists(): raise FileExistsError('fresh chip STA tag required')
    receipt = root/common.BASE/source_tag/'summary.json'
    data = json.loads(receipt.read_text())
    if data.get('status') != 'GDS_PROTOTYPE_KLAYOUT_CLEAN_SIGNAL_LVS_ONLY':
        raise ValueError('audited streamout required')
    odb = common._verified(root, data['views']['odb'])
    gds = common._verified(root, data['views']['gds'])
    native = root/common.BUILD/NATIVE/'design/runs'/NATIVE
    config = native/'config.tcl'
    settings = dict(re.findall(r'^set ::env\(([^)]+)\) "([^\n]*)"$', config.read_text(), re.M))
    sdc_source = Path(settings['CURRENT_SDC'])
    sdc_text = prototype_sdc(sdc_source.read_text(), period_ns)
    lib = Path(settings['LIB_TYPICAL']); rules = Path(settings['RCX_RULES'])
    pg_worker = root/'scripts/flow2_chip_pg_check.py'
    sources = [common._item(root, p) for p in (receipt, odb, gds, config, sdc_source, Path(__file__), pg_worker)]
    external = [{'path':str(p),'sha256':common._sha(p)} for p in (lib,rules)]
    report = dict(format='automx-cim-chip-rc-sta-v1', tag=tag, source_tag=source_tag,
        status='PREPARED', qualification='NOT_QUALIFIED', period_ns=period_ns,
        frequency_mhz=1000/period_ns, corner='TT 1.80 V 25 C; nominal OpenRCX',
        sources=sources, external_sources=external, checks={},
        scope='Exact streamout ODB; fresh routed interconnect extraction and digital STA. '
              'Original IO delays/clock uncertainty retained. Analog macros have no Liberty '
              'timing arcs; no full transistor PEX, ADC completion, PVT, IR/EM qualification.')
    if not execute: return report
    store = common.Store(root, tag, dict(sources=sources, external_sources=external, period_ns=period_ns,
        timeout_s=timeout_s, image=post.native.notebook.DEFAULT_IMAGE))
    frozen = store.build/'executed_host_sources'; frozen.mkdir()
    for path in (Path(__file__),pg_worker):
        (frozen/path.name).write_bytes(path.read_bytes())
    sdc = store.build/'prototype.sdc'; sdc.write_text(sdc_text)
    report['sdc'] = common._item(root, sdc)

    def step(name, text, python_args=None):
        tcl = store.build/(name+'.tcl')
        if text is not None:tcl.write_text(text)
        args = ['-exit','-python',*python_args] if python_args else ['-exit',tcl]
        cmd = post.container_command(root, 'openroad', args, 'automx-'+tag+'-'+name)
        cmd[cmd.index('-w')+1] = str(store.build)
        def invoke(work):
            try: return subprocess.run(cmd,cwd=store.build,text=True,capture_output=True,timeout=timeout_s)
            except subprocess.TimeoutExpired as error:
                subprocess.run(['docker','rm','-f','automx-'+tag+'-'+name],capture_output=True,timeout=15)
                out = error.stdout or b''
                if isinstance(out,bytes): out=out.decode(errors='replace')
                return subprocess.CompletedProcess(cmd,124,out,'\nBOUNDED_TIMEOUT\n')
        result, _ = store.step(name,cmd,tcl=text,executor=invoke)
        item = dict(returncode=result.returncode,status='INCOMPLETE',
                    log=common._item(root,store.folder/(name+'.log')))
        report['checks'][name]=item
        common.save_summary(store.folder/'summary.json',report)
        return result.stdout+result.stderr,item

    try:
        # The pinned PSM uses SBox direction metadata. Set the two bridge
        # directions explicitly in disposable memory, verifying identical metal.
        pg_json=store.build/'power.json'
        text,item=step('power',None,[pg_worker,'--odb',odb,'--lib',lib,'--output',pg_json])
        if item['returncode']==0 and 'AUTOMX_CHIP_PG_METADATA_DONE' in text and pg_json.is_file():
            pg=json.loads(pg_json.read_text())
            item.update(rails=pg['rails'],geometry_proof=common._item(root,pg_json),
                status='PASS_EQUIVALENT_GEOMETRY' if pg['status']=='PG_CONNECTED_EQUIVALENT_GEOMETRY' and
                pg['geometry_changed'] is False and pg['published_views_changed'] is False else 'FAIL')
        spef = store.build/(post.TOP+'.spef')
        text,item=step('rcx', f'read_liberty {{{lib}}}\nread_db {{{odb}}}\nset_thread_count 8\n'
            'define_process_corner -ext_model_index 0 X\n'
            f'extract_parasitics -ext_model_file {{{rules}}} -lef_res\n'
            f'write_spef {{{spef}}}\nputs AUTOMX_CHIP_RCX_DONE\nexit\n')
        if item['returncode'] or 'AUTOMX_CHIP_RCX_DONE' not in text or not spef.is_file():
            raise ValueError('fresh routed extraction incomplete')
        if '*D_NET' not in spef.read_text(): raise ValueError('SPEF contains no net parasitics')
        item.update(status='PASS',spef=common._item(root,spef))
        text,item=step('sta', f'read_liberty {{{lib}}}\nread_db {{{odb}}}\nread_sdc {{{sdc}}}\n'
            f'read_spef {{{spef}}}\nset_propagated_clock [all_clocks]\n'
            'check_setup -verbose\nreport_parasitic_annotation\n'
            'puts AUTOMX_SETUP_BEGIN\nreport_worst_slack -max\nputs AUTOMX_SETUP_END\n'
            'puts AUTOMX_HOLD_BEGIN\nreport_worst_slack -min\nputs AUTOMX_HOLD_END\n'
            'report_checks -path_delay min_max -format full_clock_expanded -group_count 5\n'
            'report_check_types -max_slew -max_capacitance -max_fanout -violators\n'
            'puts AUTOMX_CHIP_STA_DONE\nexit\n')
        if item['returncode']: raise ValueError('STA did not complete')
        metrics=timing_metrics(text)
        item.update(metrics,status='PASS_NOMINAL_DIGITAL_SETUP_HOLD' if min(metrics.values())>=0 else 'FAIL_TIMING')
        item['unconstrained_endpoints'] = int(re.search(r'There are (\d+) unconstrained endpoints',text)[1]) if 'unconstrained endpoints' in text else 0
        item['unannotated_drivers'] = int(re.search(r'Found (\d+) unannotated drivers',text)[1])
        item['partially_unannotated_drivers'] = int(re.search(r'Found (\d+) partially unannotated drivers',text)[1])
        item['electrical_violations_retained_in_log']=True
        report['status']='CHIP_NOMINAL_RC_STA_MEASURED'
        for source in sources: common._verified(root,source)
        for source in external:
            if common._sha(Path(source['path'])) != source['sha256']:
                raise ValueError('PDK input changed during execution')
    except Exception as error:
        report.update(status='BLOCKED_CHIP_RC_STA',error=type(error).__name__+': '+str(error))
    finally: common.save_summary(store.folder/'summary.json',report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--tag',required=True)
    p.add_argument('--source-tag',default='antenna_streamout_srv_20261022_03')
    p.add_argument('--period-ns',type=float,default=40);p.add_argument('--timeout-s',type=int,default=180)
    p.add_argument('--run',action='store_true');a=p.parse_args()
    result=run(a.root,tag=a.tag,source_tag=a.source_tag,period_ns=a.period_ns,timeout_s=a.timeout_s,execute=a.run)
    print(json.dumps(result,indent=2))
    if a.run and result['status']!='CHIP_NOMINAL_RC_STA_MEASURED': raise SystemExit(1)
