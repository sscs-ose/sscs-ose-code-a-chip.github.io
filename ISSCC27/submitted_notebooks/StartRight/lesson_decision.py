"""Reader-facing views of audited reset evidence. No new circuit model.
SPDX-License-Identifier: Apache-2.0
"""
from pathlib import Path
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from reference_evidence import load_vectors, policy_evidence
from guard_policy import choose

HERE = Path(__file__).resolve().parent
VARIANTS = ('original', 'digital_guard', 'reference_supervisor')
NAMES = dict(original='Published POR', digital_guard='POR + guard',
             reference_supervisor='Reference controller')
COLORS = dict(original='#626d7b', digital_guard='#b35d0c', reference_supervisor='#086d94')
CASES = ('cold_storage', 'cold_shallow', 'nominal_storage', 'nominal_shallow',
         'hot_storage', 'hot_shallow', 'nominal_analog')
CASE_NAMES = ('-40 C, store Q=1', '-40 C, reset after 1.35 V dip',
              '27 C, store Q=1', '27 C, reset after 1.35 V dip',
              '125 C, store Q=1', '125 C, reset after 1.35 V dip',
              '27 C, analog interruption')
PRESETS = {
    'limited': ['nominal_storage'],
    'nominal_reset': ['nominal_storage', 'nominal_shallow'],
    'expanded': ['nominal_storage', 'cold_shallow', 'hot_shallow',
                 'trough_cold_storage', 'trough_hot_storage'],
    'unmeasured': ['nominal_storage', 'unmeasured_short_zero'],
}
OPTIONS = {
    'retention_only': 'Restoration not exercised: desired state was already present',
    'setup_missing': 'The other state was not written',
    'reset_missed': 'The other state was written, but reset missed',
    'restoration_observed': 'Reset changed the written state to the target within the test limits',
    'storage_preserved': 'The stored data was kept in the no-event test',
    'unresolved': 'Simulation incomplete; no verdict',
}


def primary(record, case, variant):
    if record.get('status') != 'passed':
        raise ValueError('Audit the reference evidence before using this view')
    return next(r for r in record['cases'] if r['id'].startswith('primary/')
                and r['case'] == case and r['variant'] == variant)


def decision(record, required):
    """Explain the unchanged qualification-before-cost selector."""
    evidence = policy_evidence(record)
    required = list(required)
    selected = choose(evidence, required=required, anchor='nominal_storage')
    index = {(r['condition'], r['variant']): r for r in evidence['rows']}
    explanations = []
    for variant in VARIANTS:
        reasons = []
        for name in required:
            r = index.get((name, variant))
            if r is None:
                reasons.append(name + ': no measured evidence')
            elif r['status'] != 'completed':
                reasons.append(name + ': simulation incomplete')
            elif not r['cold_pass']:
                reasons.append(name + ': startup did not pass')
            elif not r['prior_verified']:
                reasons.append(name + ': Q=1 was not written')
            elif not r['functional_requirement_met']:
                reasons.append(name + ': requirement not met')
        anchor = index[('nominal_storage', variant)]
        explanations.append(dict(variant=variant, eligible=not reasons, reasons=reasons,
                                 anchor_uJ=anchor['source_work_delivered_J'] * 1e6))
    return dict(selected=selected, required=required, candidates=explanations,
                cost_anchor='nominal_storage', scope='Finite measured requirements; no lifetime energy ranking')


def summary_markdown(record):
    labels = dict(requirement_met='Met', not_exercised_cold_start='Setup missing',
                  not_exercised_prior_state='Write missing', functional_requirement_missed='Missed')
    text = ['| Sampled TT requirement | Published POR | POR + guard | Reference |',
            '|---|---|---|---|']
    for case, label in zip(CASES, CASE_NAMES):
        text.append('| ' + label + ' | ' + ' | '.join(
            labels[primary(record, case, v)['result']['diagnosis']] for v in VARIANTS) + ' |')
    text += ['', '**Met** means the declared requirement, including setup. A storage row requires Q=1 to remain stored.',
             '**Setup missing** is not an exercised reset miss. Seven development conditions do not qualify a temperature range.', '',
             '| Working matched history | Published POR, uJ | Guard, uJ | Reference, uJ |', '|---|---:|---:|---:|']
    for case, label in [('nominal_storage', '27 C storage'), ('nominal_analog', '27 C analog interruption')]:
        rows = [next(r for r in record['cases'] if r.get('group') == 'step'
                     and r['case'] == case and r['variant'] == v) for v in VARIANTS]
        if not all(r['result']['qualified'] for r in rows):
            raise ValueError('Only working matched circuits may be priced')
        if not all(r['source_functions'] == rows[0]['source_functions'] for r in rows):
            raise ValueError('Cost histories differ')
        costs = [r['result']['reference']['source_work']['delivered_J'] * 1e6 for r in rows]
        text.append('| ' + label + ' | ' + ' | '.join(f'{x:.6f}' for x in costs) + ' |')
    text += ['', 'All four independent sources and startup are counted. The two histories are separate comparisons, not a usage distribution.']
    return '\n'.join(text)


def overview(record):
    """One figure joins ordinary operation, coverage and the design consequence."""
    fig = plt.figure(figsize=(13.2, 9.2), layout='constrained')
    gs = fig.add_gridspec(4, 2, height_ratios=(.60, 1, 1, 1), width_ratios=(1, 1.25))
    flow = fig.add_subplot(gs[0, :]); flow.set(xlim=(0, 4), ylim=(0, 1)); flow.axis('off')
    steps = ['1  Write Q=1\nordinary clock/data', '2  Verify Q=1\nbefore the disturbance',
             '3  Apply the history\nsame consumer and load', '4  Check the requirement\nthen compare working cost']
    for i, text in enumerate(steps):
        flow.add_patch(FancyBboxPatch((i + .025, .20), .88, .62, boxstyle='round,pad=.025',
                                     facecolor='#edf5f8', edgecolor='#87a4b2'))
        flow.text(i + .465, .51, text, ha='center', va='center', fontsize=10)
        if i < 3:
            flow.annotate('', xy=(i + 1.01, .51), xytext=(i + .94, .51),
                          arrowprops=dict(arrowstyle='->', color='#4c6472'))
    axes = [fig.add_subplot(gs[i, 0]) for i in (1, 2, 3)]
    for variant in VARIANTS:
        d = load_vectors(primary(record, 'hot_shallow', variant))
        t = d[:, 0] * 1000; m = (t >= 20.8) & (t <= 29.5)
        if variant == 'original':
            axes[0].plot(t[m], d[m, 3], color='#203847', label='DVDD')
            axes[0].plot(t[m], d[m, 6], color='#9c4188', lw=1, label='Ordinary D input')
        for ax, col in zip(axes[1:], (2, 1)):
            ax.plot(t[m], d[m, col], color=COLORS[variant],
                    ls='--' if variant == 'digital_guard' else '-', lw=1.55, label=NAMES[variant])
    for ax in axes:
        ax.set(xlim=(20.8, 29.5), ylim=(-.10, 2.03))
        ax.grid(alpha=.2)
        ax.axvspan(25, 26.001, color='#c5dbe5', alpha=.25)
    for ax, text in zip(axes, ('DVDD (V)', 'Consumer reset-bar (V)', 'DFF output Q (V)')):
        ax.set_ylabel(text)
    axes[0].set_title('A real reset test after a normal write\nSaved TT / 125 C / 1.35 V dip / 2 us maximum step', fontsize=10)
    axes[0].annotate('Ordinary D pulse', xy=(21.01, 1.8), xytext=(21.4, .65),
                     arrowprops=dict(arrowstyle='->', color='#203847'), fontsize=9)
    axes[2].axhline(.36, color='#5b777f', ls=':', lw=.8)
    axes[2].annotate('Q=1 verified\nbefore the dip', xy=(24.9998, 1.8), xytext=(22.7, .80),
                     arrowprops=dict(arrowstyle='->', color='#203847'), fontsize=9)
    axes[2].text(27.0, .53, 'Required Q <= 0.36 V', fontsize=8)
    axes[0].legend(fontsize=8, loc='upper right')
    axes[2].set_xlabel('Time (ms)'); axes[1].legend(fontsize=8, loc='lower left')
    matrix = fig.add_subplot(gs[1:3, 1]); matrix.axis('off')
    short = dict(requirement_met='Met', not_exercised_cold_start='Setup',
                 not_exercised_prior_state='Write', functional_requirement_missed='Miss')
    values = [[short[primary(record, c, v)['result']['diagnosis']] for v in VARIANTS] for c in CASES]
    table = matrix.table(cellText=values, rowLabels=CASE_NAMES, colLabels=['POR', '+ guard', 'Reference'],
                         cellLoc='center', loc='center', bbox=(.49, .13, .51, .78))
    table.auto_set_font_size(False); table.set_fontsize(8.5)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor('#d8e1e7')
        if row == 0:
            cell.set_facecolor('#e8f0f4'); cell.set_text_props(weight='bold')
        elif col >= 0:
            cell.set_facecolor({'Met': '#dceee8', 'Setup': '#eceef1', 'Write': '#eceef1', 'Miss': '#f9e1d8'}[values[row-1][col]])
    matrix.set_title('Which sampled requirement is met?', fontsize=11)
    matrix.text(0, .015, 'Setup: cold readiness or prior operation missing.\nStorage controls require Q=1, not erasure. TT samples only.',
                fontsize=9, transform=matrix.transAxes)
    cost = fig.add_subplot(gs[3, 1]); positions = np.arange(2)
    for i, variant in enumerate(VARIANTS):
        work = []
        for case in ('nominal_storage', 'nominal_analog'):
            r = next(r for r in record['cases'] if r.get('group') == 'step' and r['case'] == case and r['variant'] == variant)
            if not r['result']['qualified']:
                raise ValueError('Ineligible circuit in cost figure')
            work.append(r['result']['reference']['source_work']['delivered_J'] * 1e6)
        cost.bar(positions + (i-1)*.22, work, width=.21, color=COLORS[variant], label=NAMES[variant])
    cost.set_xticks(positions, ['27 C storage', '27 C analog interruption'])
    cost.set_ylabel('Delivered source work (uJ)'); cost.set_ylim(0, 1.8); cost.grid(axis='y', alpha=.2)
    cost.set_title('Price only working matched alternatives\nAll sources and startup; separate histories', fontsize=10)
    fig.suptitle('StartRight: a cold-start pass leaves a different question open', fontsize=15, weight='bold')
    return fig


def questions(record, retained=None):
    specs = [('cold_original', 'cold_shallow', 'original'), ('hot_original', 'hot_shallow', 'original'),
             ('hot_reference', 'hot_shallow', 'reference_supervisor'), ('storage_control', 'nominal_storage', 'original')]
    result = []
    for key, case, variant in specs:
        row = primary(record, case, variant); q = row['result']; r = q['reference']
        cold = bool(r['events'][0]['pass_contract']); prior = bool(r['declared_precondition_verified'])
        if not cold or not prior:
            expected = 'setup_missing'
            reason = 'The trace does not establish cold readiness and a verified ordinary Q=1 write. Q ending near zero cannot demonstrate reset of Q=1.'
        elif q['storage_requirement'] and q['qualified']:
            expected = 'storage_preserved'
            reason = 'This is a no-dip storage control. The ordinary write established Q=1 and the storage/reset-inactive checks pass. Restoring Q=0 would violate this requirement.'
        elif q['qualified']:
            expected = 'restoration_observed'
            reason = 'Cold readiness and the ordinary Q=1 write are verified. Recovery reaches the declared Q=0 band and reset-release contract. This is finite schematic evidence.'
        else:
            expected = 'reset_missed'
            reason = 'Cold readiness and the ordinary Q=1 write are verified, but recovery fails the declared contract. A completed simulation and released reset do not establish Q=0.'
        witnesses = dict(cold_ready=cold, prior_Q1_verified=prior, requirement_met=bool(q['qualified']),
                         final_Q_V=r['final_q_V'], recovery_state_met=bool(r['events'][1]['state']['pass_contract']))
        result.append(dict(id=key, title=NAMES[variant] + ': ' + CASE_NAMES[CASES.index(case)],
                           source=row['id'], expected=expected, reason=reason, witnesses=witnesses))
    if retained is not None:
        row = next(r for r in retained['cases'] if r['configuration']['id'] == 'frozen_rc_sr')
        expected = ('unresolved' if row['status'] != 'measured' else
                    ('setup_missing' if not row.get('declared_precondition_verified') else 'retention_only'))
        result.insert(0, dict(id='retained_rc', title='Fresh RC latch: no ordinary SET_A command',
                             source='Current retained-state acquisition', expected=expected,
                             reason='Inspect the printed functional verdict separately. Without a verified different prior state, this trial does not exercise restoration from that state.',
                             witnesses=dict(observed_pass=row.get('observed_pass'), different_prior_exercised=row.get('alternate_state_exercised'))))
    return result


def feedback(record, answers, retained=None):
    bank = questions(record, retained); ids = {q['id'] for q in bank}
    if set(answers) - ids:
        raise ValueError('Unknown exercise identifier')
    lines = []; attempted = correct = 0
    for q in bank:
        answer = answers.get(q['id'])
        lines.append('**' + q['title'] + '**')
        if answer is None or answer == '':
            lines.append('Choose an answer code and rerun this cell. No answer has been scored.')
        else:
            if answer not in OPTIONS:
                raise ValueError('Unknown answer code: ' + str(answer))
            attempted += 1; good = answer == q['expected']; correct += int(good)
            lines += [('Correct. ' if good else 'Recheck. ') + q['reason'],
                      'Recorded witnesses: `' + json.dumps(q['witnesses'], sort_keys=True) + '`.',
                      'Evidence: `' + q['source'] + '`.']
        lines.append('')
    lines.append(f'{correct}/{attempted} attempted answers agree with the recorded evidence. This is exercise feedback, not a human learning study.')
    return '\n\n'.join(lines)


def browser_payload(record):
    evidence = policy_evidence(record)
    return dict(version='0.21', variants=list(VARIANTS), names=NAMES, options=OPTIONS,
                questions=questions(record), presets=PRESETS, rows=evidence['rows'],
                expected_choices={k: decision(record, v)['selected'] for k, v in PRESETS.items()},
                scope='Saved audited schematic data. Controls select and explain existing evidence; no fresh simulation, new temperature, physical qualification or lifetime ranking.')


def export_browser(record, destination=None):
    destination = Path(destination or HERE)
    payload = browser_payload(record)
    template = (HERE / 'lesson_template.html').read_text(encoding='utf-8')
    # Keep JSON inert inside its script element, including future source descriptions.
    encoded = json.dumps(payload, ensure_ascii=True).replace('<', '\\u003c')
    page = template.replace('<!--LESSON_DATA-->', encoded)
    (destination / 'Explore_reset.html').write_text(page, encoding='utf-8')
    (destination / 'lesson_view.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
    return payload
