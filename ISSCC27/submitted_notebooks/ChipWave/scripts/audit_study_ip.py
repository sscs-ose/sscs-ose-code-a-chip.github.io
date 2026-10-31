"""Verify the original PE is instantiated and contributes to the delivered result."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from study_protocol import digest, write_json

CASE = Path(__file__).resolve().parents[1]
ORIGINAL_PE = 'f841e0a3676c4d367e7ce966e3fb11f27880076a2361e440d1319d39771db664'


def data_contributions(design):
    modules = design['modules']; top = modules['nebula_npu_dot4']
    pe = []; edges = []; aliases = {}

    def node(path, bit):
        return (path, bit) if isinstance(bit, int) else ((), str(bit))

    def find(item):
        aliases.setdefault(item, item)
        if aliases[item] != item: aliases[item] = find(aliases[item])
        return aliases[item]

    def walk(module, path=(), stack=()):
        if module in stack: raise ValueError('Recursive design hierarchy')
        for name, cell in modules[module].get('cells', {}).items():
            kind = cell['type']; child = modules.get(kind)
            source = child.get('attributes', {}).get('src', '') if child else ''
            connections = cell.get('connections', {})
            if child and (kind == 'gemm_pe' or kind.startswith('gemm_pe$')) and '/ip/gemm_pe.sv:' in source:
                pe.append(('/'.join((*path, name)), [node(path, bit) for bit in connections.get('accumulator', [])]))
            elif child:
                child_path = (*path, name)
                for port, declaration in child.get('ports', {}).items():
                    parent_bits = connections.get(port, [])
                    if len(parent_bits) != len(declaration['bits']):
                        raise ValueError('Hierarchy port width mismatch')
                    for parent, local in zip(parent_bits, declaration['bits']):
                        aliases[find(node(child_path, local))] = find(node(path, parent))
                walk(kind, child_path, (*stack, module))
            else:
                inputs = {node(path, bit) for port, bits in connections.items()
                          if cell.get('port_directions', {}).get(port) == 'input'
                          and port not in {'CLK', 'C', 'ARST', 'SRST', 'CLR', 'SET'}
                          for bit in bits if isinstance(bit, int)}
                for port, bits in connections.items():
                    if cell.get('port_directions', {}).get(port) == 'output':
                        edges.extend((node(path, bit), inputs) for bit in bits if isinstance(bit, int))
    walk('nebula_npu_dot4')
    reverse = {}
    for output, inputs in edges: reverse.setdefault(find(output), set()).update(find(bit) for bit in inputs)
    cone = {find(node((), bit)) for bit in top['ports']['rsp_data']['bits'] if isinstance(bit, int)}
    todo = list(cone)
    while todo:
        bit = todo.pop()
        for parent in reverse.get(bit, ()):
            if parent not in cone:
                cone.add(parent); todo.append(parent)
    contributions = [{'instance': name, 'accumulator_bits_in_result_cone': len({find(bit) for bit in bits} & cone)} for name, bits in pe]
    return {'reachable_pe_instances': len(pe), 'contributions': contributions,
            'passed': len(pe) == 4 and all(row['accumulator_bits_in_result_cone'] > 0 for row in contributions),
            'scope': 'Four unchanged PE instances with accumulator outputs in the structural result-data cone after synthesis optimization; this is not formal arithmetic equivalence'}


def audit(selected, output):
    selected, output = Path(selected).resolve(), Path(output).resolve()
    if output.exists(): raise ValueError('Existing IP audit preserved')
    output.mkdir(parents=True)
    record = json.loads((selected/'selected-delivery.json').read_text())
    for relative, expected in record['exported_source_sha256'].items():
        path = selected/relative
        if path.is_symlink() or not path.resolve().is_relative_to(selected) or digest(path) != expected:
            raise ValueError('Selected source identity changed')
    original = selected/'ip/gemm_pe.sv'
    if not original.is_file() or digest(original) != ORIGINAL_PE:
        result = {'passed': False, 'reason': 'Supplied original PE missing or modified'}
    else:
        sources = sorted(selected.glob('rtl/**/*.sv')) + sorted(selected.glob('rtl/**/*.v'))
        sources += sorted(selected.glob('ip/**/*.sv')) + sorted(selected.glob('ip/**/*.v'))
        command = ['yosys','-Q','-T','-p','read_slang --keep-hierarchy --top nebula_npu_dot4 '+
                   ' '.join(map(str,sources))+'; hierarchy -check -top nebula_npu_dot4; proc; opt; check -assert; write_json '+str(output/'hierarchy.json')]
        process = subprocess.run(command,text=True,capture_output=True,timeout=120)
        (output/'synthesis.log').write_text(process.stdout+process.stderr)
        result = {'passed': False, 'synthesis_exit_code': process.returncode}
        if process.returncode == 0:
            result.update(data_contributions(json.loads((output/'hierarchy.json').read_text())))
        result['source_sha256'] = record['exported_source_sha256']
    result['evaluator_sha256'] = digest(Path(__file__))
    write_json(output/'audit.json',result)
    return result


def rescore_trial(folder):
    folder = Path(folder).resolve()
    result_path = folder/'results/result.json'
    raw = json.loads(result_path.read_text())
    revised_path = folder/'results/final-evaluator-v3.json'
    if revised_path.exists(): raise ValueError('Existing corrected evaluation preserved')
    final = raw['final_checker']
    functional_synthesis_passed = (final.get('command_exit_codes') == [0,0,0] and
        'NPU_ACCEPTANCE_PASS cases=264202 cancellations=8' in (folder/'results/acceptance.log').read_text())
    if raw['job']['input'] == 'ip':
        proof = audit(folder/'results/selected',folder/'results/ip-hierarchy-audit-v3') if functional_synthesis_passed else {'passed':False,'reason':'Independent functional/synthesis checks failed'}
        passed = functional_synthesis_passed and proof['passed']
    else:
        proof = None; passed = raw['passed']
    record = {'passed':bool(passed),'original_result_sha256':digest(result_path),
              'original_verdict':raw['passed'],'ip_proof':proof,'evaluator_sha256':digest(Path(__file__)),
              'criteria_unchanged': 'Original criterion requires four unchanged supplied PEs. Original flat synthesis erased instance names; corrected measurement preserves hierarchy and checks result-data contribution.',
              'no_model_rerun':True,'no_agent_feedback':True,'final_checker_sha256':final.get('checker_sha256')}
    write_json(revised_path,record)
    return record


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--trial',type=Path,required=True)
    args=p.parse_args();print(json.dumps(rescore_trial(args.trial)))
