"""Draw observed specification repair and the separate measured fault replay."""
from pathlib import Path
from html import escape
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
receipt = ROOT / 'results/fault-replay/summary.json'
data = json.loads(receipt.read_text())
assert data['complete'] and len(data['rows']) == 7
assert not data['ai_repair_comparison_measured'] and not data['held_out_transfer_measured']
control = next(r for r in data['rows'] if r['treatment'] == 'accepted')
assert control['checker_passed']
for name in ('signedness', 'reduction-width', 'kill-priority'):
    fault = next(r for r in data['rows'] if r['fault'] == name and r['treatment'] == 'faulty')
    repair = next(r for r in data['rows'] if r['fault'] == name and r['treatment'] == 'preset-repair')
    assert fault['declared_fault_detected'] and repair['checker_passed']
    assert repair['rtl_sha256'] == control['rtl_sha256']
spec = ROOT / 'results/standard-flow/design/spec/draft.specir'
assert 'let id_serial_wait: bit = if_v && (id_csr || id_mret)' in spec.read_text()
parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 870" role="img" aria-labelledby="title desc"><title id="title">From failure to checked repair</title><desc id="desc">An observed valid-token specification repair is separate from three deliberate NPU mutations. Preset inverse edits restore accepted source; AI repair efficiency and cross-task learning are unmeasured.</desc><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8" fill="#5eead4"/></marker></defs><rect width="1440" height="870" fill="#0f172a"/><g font-family="Arial,sans-serif">']


def text(x, y, lines, size=18, color='#cbd5e1'):
    for n, line in enumerate(lines):
        parts.append(f'<text x="{x}" y="{y+n*27}" font-size="{size}" fill="{color}">{escape(line)}</text>')


text(30, 42, ['FROM FAILURE TO CHECKED REPAIR'], 28, '#f8fafc')
text(30, 76, ['A. Observed in the native CPU/NPU design run'], 21, '#5eead4')
cards = [
    ('1 · Expose the failure', ['RTL designer experiment', 'Unowned instruction data', 'incorrectly blocks progress.']),
    ('2 · Correct the specification', ['Authorized CSIR correction', 'Add the valid-token guard.', 'Original requirements retained.']),
    ('3 · Recheck the handoff', ['Independent closure review', 'Compiler and fresh spec freeze', 'before RTL generation resumes.']),
    ('4 · Test the new RTL', ['Independent common checker', 'Base functional score: 50/50', 'Physical closure is separate.']),
]
for i, (title, lines) in enumerate(cards):
    x = 30 + i*350
    parts.append(f'<rect x="{x}" y="102" width="320" height="167" rx="12" fill="#172b46" stroke="#38bdf8"/>')
    text(x+14, 135, [title], 19, '#f8fafc')
    text(x+14, 176, lines, 17)
    if i < 3:
        parts.append(f'<path d="M{x+321} 186 L{x+342} 186" stroke="#5eead4" stroke-width="2" marker-end="url(#arrow)"/>')
parts.append('<rect x="30" y="291" width="1370" height="111" rx="10" fill="#102a2e"/>')
text(48, 320, ['Concrete rule: control decisions require ownership by a valid instruction.'], 20, '#ccfbf1')
text(48, 351, ['Before:  (id_csr || id_mret) && (ex_v || mem_v || wb_v)',
               'After:   if_v && (id_csr || id_mret) && (ex_v || mem_v || wb_v)'], 18)
guard_path = ROOT / 'results/csir-guard-audit/summary.json'
guard = json.loads(guard_path.read_text())
assert guard['accepted_expression']['violations'] == 0 and guard['reconstructed_missing_guard_mutant']['violations'] == 21
text(30, 426, ['Supplemental Boolean audit (not a native Gate): accepted 0; reconstructed missing-guard variant 21 / 64 assignments.'], 16, '#ccfbf1')
text(30, 456, ['B. Deliberately injected NPU faults — a reproducible checker lesson'], 21, '#fbbf24')
text(30, 485, ['Accepted control: 264,202 arithmetic/protocol cases and 8 cancellation scenarios pass.'], 18)
parts.append('<rect x="30" y="505" width="1370" height="222" rx="10" fill="#172b46"/>')
text(48, 538, ['Changed rule'], 18, '#f8fafc')
text(490, 538, ['Observed faulty behavior'], 18, '#f8fafc')
text(1060, 538, ['Fixed checker / preset repair'], 18, '#f8fafc')
rows = [
    ('Treat one INT8 lane as unsigned', '1 × (-128): +128 instead of -128', 'Detected / full replay passes'),
    ('Truncate one product-pair sum', 'Four (-128 × -128): 0 instead of 65,536', 'Detected / full replay passes'),
    ('Remove response kill suppression', 'Cancelled response remains visible', 'Detected / full replay passes'),
]
for i, row in enumerate(rows):
    y = 586 + i*51
    for x, value in zip((48, 490, 1060), row):
        text(x, y, [value], 17, '#e2e8f0')
text(30, 751, ['Preset repairs restore the exact accepted RTL. These are operator-defined edits, not autonomous AI repair trials.'], 18, '#fbbf24')
text(30, 786, ['NEXT EXPERIMENT · Same-model, equal-budget repair comparison; then held-out rule transfer.'], 18, '#94a3b8')
text(30, 822, ['Neither repair-efficiency improvement nor recursive self-improvement has been measured here.'], 18, '#94a3b8')
parts.append('</g></svg>')
(ROOT / 'figures/repair_evidence.svg').write_text(''.join(parts))
(ROOT / 'figures/repair_evidence.source.json').write_text(json.dumps({
    'fault_receipt': str(receipt.relative_to(ROOT)), 'fault_receipt_sha256': hashlib.sha256(receipt.read_bytes()).hexdigest(),
    'specification': str(spec.relative_to(ROOT)), 'specification_sha256': hashlib.sha256(spec.read_bytes()).hexdigest(),
    'observed_correction_record': 'results/standard-flow/valid-token-repair-confirmation.json',
    'guard_audit': str(guard_path.relative_to(ROOT)), 'guard_audit_sha256': hashlib.sha256(guard_path.read_bytes()).hexdigest(),
    'ai_repair_comparison_measured': False, 'held_out_transfer_measured': False,
}, indent=2) + '\n')
print('REPAIR_EVIDENCE_FIGURE_PASS: measured faults, source-identical preset repairs, explicit scope')
