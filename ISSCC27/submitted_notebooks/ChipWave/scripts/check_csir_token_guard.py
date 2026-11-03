#!/usr/bin/env python3
"""Supplemental Boolean audit of one frozen CSIR ownership expression.

This checks a bounded expression property, not the CPU's sequential semantics.
"""
import argparse
import ast
import hashlib
import itertools
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / 'results/standard-flow/frozen-v2/specification/spec/draft.specir'
VARIABLES = ('if_v', 'id_csr', 'id_mret', 'ex_v', 'mem_v', 'wb_v')


def parse(expression):
    tree = ast.parse(expression.replace('&&', ' and ').replace('||', ' or ').replace('!', ' not ').strip(), mode='eval')
    allowed = (ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.Name, ast.Load, ast.UnaryOp, ast.Not)
    for node in ast.walk(tree):
        if not isinstance(node, allowed) or isinstance(node, ast.Name) and node.id not in VARIABLES:
            raise ValueError('Only declared Boolean variables and conjunction/disjunction/negation are supported.')
    return tree.body


def value(node, state):
    if isinstance(node, ast.Name):
        return state[node.id]
    if isinstance(node, ast.UnaryOp):
        return not value(node.operand, state)
    values = [value(n, state) for n in node.values]
    return all(values) if isinstance(node.op, ast.And) else any(values)


def audit(expression):
    tree = parse(expression)
    failures = []
    for bits in itertools.product((False, True), repeat=len(VARIABLES)):
        state = dict(zip(VARIABLES, bits))
        if not state['if_v'] and value(tree, state):
            failures.append(state)
    return {'expression': expression, 'abstract_assignments': 64,
            'invalid_token_assignments': 32, 'violations': len(failures),
            'counterexamples': failures}


def run(output):
    original = SPEC.read_bytes()
    matches = re.findall(r'^\s*let id_serial_wait: bit = (.+)$', original.decode(), re.M)
    assert len(matches) == 1
    expression = matches[0].strip()
    assert expression.startswith('if_v && ')
    accepted, mutant = audit(expression), audit(expression[len('if_v && '):])
    assert accepted['violations'] == 0 and mutant['violations'] == 21
    # At least one counterexample respects CSR/MRET mutual exclusion.
    assert any(s['id_csr'] and not s['id_mret'] for s in mutant['counterexamples'])
    for unsupported in ('if_v()', '__import__', 'if_v + ex_v', 'True', 'if_v == ex_v'):
        try:
            parse(unsupported)
        except (ValueError, SyntaxError):
            pass
        else:
            raise AssertionError('Unsupported expression accepted: ' + unsupported)
    output.mkdir(parents=True, exist_ok=False)
    result = {'complete': True, 'source': str(SPEC.relative_to(ROOT)),
              'source_sha256': hashlib.sha256(original).hexdigest(),
              'property': 'if_v == false implies id_serial_wait == false',
              'accepted_expression': accepted, 'reconstructed_missing_guard_mutant': mutant,
              'scope': 'All 64 assignments of six Boolean symbols; overapproximates reachable CPU states. Supplemental operator-authored audit, not an existing native compiler gate, whole-CPU proof, or held-out learning.',
              'mutant_origin': 'Remove the valid-token guard from the accepted expression for a controlled lesson; this is not a replay of the original failing RTL.'}
    assert SPEC.read_bytes() == original
    (output / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print('CSIR_GUARD_AUDIT_PASS: accepted 0 violations, reconstructed mutant 21 / 64 abstract assignments')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    run(parser.parse_args().output.resolve())
