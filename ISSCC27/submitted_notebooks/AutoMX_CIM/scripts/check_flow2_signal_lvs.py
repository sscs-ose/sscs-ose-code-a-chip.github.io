#!/usr/bin/env python3
"""Signal-only macro LVS from completed bounded DEF/LEF or GDS extraction.

PG/body terminals are removed from SKY130 HD opaque cell interfaces on BOTH
sides, not by net names. Analog macro PG ports and signal ties to rails stay.
Raw extraction/reference remain immutable. No PG/body/transistor qualification.
"""
from pathlib import Path
import argparse
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import flow2_integration_common as common
from scripts import run_flow2_wrapper_postroute as post
from scripts.run_flow2_wrapper_transistor_lvs import validate_netgen

PG = {'VPWR', 'VGND', 'VPB', 'VNB'}


def standard(name):
    return name.startswith(('sky130_fd_sc_hd__', 'sky130_ef_sc_hd__'))


def signal_spice(text):
    lines = []
    for line in text.splitlines():
        if line.startswith('+'):
            if not lines: raise ValueError('orphan SPICE continuation')
            lines[-1] += ' '+line[1:].strip()
        else: lines.append(line)
    masks, removed = {}, {}
    for line in lines:
        fields = line.split()
        if len(fields) > 2 and fields[0].lower() == '.subckt' and standard(fields[1]):
            masks[fields[1]] = [port.upper() not in PG for port in fields[2:]]
            removed[fields[1]] = [port for port in fields[2:] if port.upper() in PG]
    result, count = [], 0
    for line in lines:
        fields = line.split()
        if fields and fields[0].lower() == '.subckt' and fields[1] in masks:
            line = ' '.join(fields[:2]+[p for p, keep in zip(fields[2:], masks[fields[1]]) if keep])
        elif fields and fields[0][0].upper() == 'X':
            end = next((i for i, token in enumerate(fields) if '=' in token), len(fields))
            model = fields[end-1]
            if model in masks:
                nodes, mask = fields[1:end-1], masks[model]
                if len(nodes) != len(mask): raise ValueError('stdcell node/port cardinality differs: '+model)
                line = ' '.join([fields[0]]+[n for n, keep in zip(nodes, mask) if keep]+fields[end-1:])
                count += 1
            elif standard(model): raise ValueError('stdcell has no interface definition: '+model)
        result.append(line)
    return '\n'.join(result)+'\n', {'removed_ports_by_master': removed, 'standard_instances': count}


def signal_verilog(text, removed):
    count = 0
    pattern = r'(?ms)^(\s*(sky130_(?:fd|ef)_sc_hd__\w+)\s+\S+\s*\()(.*?)(\)\s*;)'
    def rewrite(match):
        nonlocal count
        prefix, model, body, ending = match.groups()
        if model not in removed: raise ValueError('reference stdcell interface missing: '+model)
        pins = re.findall(r'\.([A-Za-z_][\w$]*)\s*\(([^()]*)\)', body)
        residue = re.sub(r'\.([A-Za-z_][\w$]*)\s*\(([^()]*)\)', '', body)
        if residue.replace(',', '').strip(): raise ValueError('unsupported named stdcell pin expression')
        count += 1
        keep = [(p, n) for p, n in pins if p not in removed[model]]
        return prefix+'\n'+',\n'.join('    .'+p+'('+n+')' for p, n in keep)+'\n'+ending
    result = re.sub(pattern, rewrite, text)
    return result, count


def run(root, *, source_tag, tag, execute=False, netgen_binary=None,gds_source=False):
    root = Path(root).resolve(); common.tag_ok(source_tag); common.tag_ok(tag)
    if (root/common.BASE/tag/'inputs.json').exists(): raise FileExistsError('fresh signal LVS tag required')
    source_path = root/common.BASE/source_tag/'summary.json'
    source = json.loads(source_path.read_text())
    if source['checks']['extract']['returncode'] != 0: raise ValueError('completed physical extraction required')
    work = root/common.BUILD/source_tag
    physical, reference = work/'signal_scope.lef.spice', work/'signal_scope.v'
    extra=[];gds_tag=None
    candidate_tag=source.get('candidate_tag')
    if gds_source:
        gds_tag=source['source_tag']
        proto_path=root/common.BASE/gds_tag/'summary.json';proto=json.loads(proto_path.read_text())
        gds=common._verified(root,proto['views']['gds'])
        if common._item(root,gds) not in source['sources']:raise ValueError('GDS extraction hash differs')
        log=common._verified(root,source['checks']['extract']['log'])
        if 'AUTOMX_GDS_MACRO_EXTRACT_DONE' not in log.read_text():raise ValueError('incomplete GDS extraction')
        physical=work/'gds_macro.spice'
        refs=[v for v in source['sources'] if v['path'].endswith('/signal_scope.v')]
        if len(refs)!=1:raise ValueError('one powered ODB reference required')
        reference=common._verified(root,refs[0]);candidate_tag=proto['candidate_tag']
        extra=[proto_path,gds,log]
    ptext, scope = signal_spice(physical.read_text())
    vtext, reference_count = signal_verilog(reference.read_text(), scope['removed_ports_by_master'])
    if not scope['standard_instances'] or reference_count != scope['standard_instances']:
        raise ValueError('all standard instances must be present on both sides')
    report = {'format': 'automx-cim-signal-only-lvs-v1', 'tag': tag, 'source_tag': source_tag,
              'candidate_tag': candidate_tag, 'status': 'PREPARED', 'qualification': 'NOT_QUALIFIED',
              'scope': 'Signal-only DEF/LEF macro connectivity. Standard-cell PG/body ports omitted on BOTH sides; '
                       'analog macro PG and signal pins tied to rails retained. No PG/body/tap/decap/GDS/transistor or analog qualification.',
              'transformation': scope, 'reference_standard_instances': reference_count}
    if gds_source:
        report.update(gds_tag=gds_tag,scope='Actual GDS parent routing, native maglef/analog LEF boundaries; '
            'standard-cell PG/body ports omitted on BOTH sides, analog macro PG and rail-tied signal pins retained. '
            'No standard-cell PG/body/tap/decap interior, transistor or analog qualification.')
    binary = Path(netgen_binary).resolve() if netgen_binary else None
    if binary:
        if not binary.is_file(): raise FileNotFoundError('diagnostic Netgen executable required')
        report['netgen'] = {'mode': 'isolated_host_diagnostic', 'path': str(binary),
            'launcher_sha256': common._sha(binary), 'shared_libraries': [
                {'path': str(p), 'sha256': common._sha(p)} for p in sorted(binary.parent.parent.rglob('*.so'))]}
    else:
        report['netgen'] = {'mode': 'pinned_native_image', 'image': post.native.notebook.DEFAULT_IMAGE}
    if not execute: return report
    sources = [common._item(root, p) for p in (source_path, physical, reference, Path(__file__),*extra)]
    report['sources'] = sources
    store = common.Store(root, tag, {'sources': sources, 'netgen': report['netgen']})
    frozen = store.build/'executed_host_sources'; frozen.mkdir()
    (frozen/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    ppath, vpath = store.build/'signal_only.spice', store.build/'signal_only.v'
    ppath.write_text(ptext); vpath.write_text(vtext)
    report['physical'] = common._item(root, ppath); report['reference'] = common._item(root, vpath)
    log = store.build/'netgen.log'
    pdk = post.native.notebook.DEFAULT_PDK/'sky130A'
    arguments = ['-batch', 'lvs', str(ppath)+' '+post.TOP,
        str(vpath)+' '+post.TOP, str(pdk/'libs.tech/netgen/sky130A_setup.tcl'), str(log)]
    if binary:
        command = [str(binary), *arguments]
    else:
        command = post.container_command(root, 'netgen', arguments, 'automx-'+tag)
        command[command.index('-w')+1] = str(store.build)
    def invoke(w):
        try: return subprocess.run(command, cwd=store.build, text=True, capture_output=True, timeout=120)
        except subprocess.TimeoutExpired as error:
            if not binary:
                subprocess.run(['docker', 'rm', '-f', 'automx-'+tag], capture_output=True, timeout=15)
            value = error.stdout or b''
            if isinstance(value, bytes): value = value.decode(errors='replace')
            return subprocess.CompletedProcess(command, 124, value, '\nBOUNDED_TIMEOUT\n')
    try:
        result, _ = store.step('lvs', command, executor=invoke)
        if result.returncode: raise ValueError('native signal LVS failed: '+str(result.returncode))
        validate_netgen(log.read_text()+'\n'+result.stdout+result.stderr)
        for item in sources: common._verified(root, item)
        report['status'] = ('SIGNAL_ONLY_GDS_MACRO_LVS_MATCH_NO_PG_BODY_QUALIFICATION' if gds_source else
                            'SIGNAL_ONLY_DEF_LEF_LVS_MATCH_NO_PG_BODY_QUALIFICATION')
    except Exception as error:
        report.update(status='BLOCKED_SIGNAL_LVS', error=type(error).__name__+': '+str(error))
    finally:
        if log.exists():report['lvs_log'] = common._item(root, log)
        common.save_summary(store.folder/'summary.json', report)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--source-tag', default='antenna_lvs_srv_20261022_01')
    p.add_argument('--tag', required=True)
    p.add_argument('--run', action='store_true')
    p.add_argument('--netgen-binary', type=Path, help='isolated diagnostic executable; keep the same input netlists/PDK setup')
    p.add_argument('--gds-source',action='store_true',help='consume completed actual GDS parent extraction')
    a = p.parse_args(); result = run(a.root, source_tag=a.source_tag, tag=a.tag, execute=a.run,
                                    netgen_binary=a.netgen_binary,gds_source=a.gds_source)
    print(json.dumps(result, indent=2))
    if a.run and result['status'].startswith('BLOCKED'): raise SystemExit(1)
