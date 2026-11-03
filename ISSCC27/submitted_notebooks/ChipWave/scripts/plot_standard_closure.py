"""Plot measured electrical repair from the selected native PnR delivery."""
from pathlib import Path
import hashlib
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'results/standard-flow/native-pnr/accepted-20261014'
receipt = SOURCE / 'reports/pnr/rc_eco.json'
data = json.loads(receipt.read_text())
gates = json.loads((SOURCE / 'reports/pnr/exit_gates.json').read_text())
assert data['status'] == 'passed' and gates['passed']
assert data['final_liberty_thresholds_unchanged']
assert all(v == 0 for v in data['final_violations'].values())
assert data['post_route_setup_slack_ns'] >= 0 and data['post_route_hold_slack_ns'] >= 0

fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={'width_ratios': [1, 1.4]})
ax = axes[0]
for positions, values, color, label in [
    ([-.18, .82], [data['baseline_violations'][k] for k in ('max_slew', 'max_capacitance')], '#c76b25', 'Before repair'),
    ([.18, 1.18], [data['final_violations'][k] for k in ('max_slew', 'max_capacitance')], '#087f8c', 'After repair'),
]:
    ax.bar(positions, values, width=.34, color=color, label=label)
    for x, value in zip(positions, values):
        ax.text(x, value + .1, str(value), ha='center', fontsize=12)
ax.set_xticks([0, 1], ['Slew', 'Capacitance'])
ax.set_ylabel('Final extracted violations (count)')
ax.set_ylim(0, 4.3)
ax.set_yticks(range(5))
ax.legend(frameon=False, loc='upper right')
ax.spines[['top', 'right']].set_visible(False)

axes[1].axis('off')
guard = data['guardband']; repair = data['grt_repairs']
lines = [
    'Measured extraction mismatch → bounded repair → recheck',
    f"Slew target margin: {guard['slew_margin_percent']:.3f}%",
    f"Capacitance target margin: {guard['cap_margin_percent']:.3f}%",
    f"{repair['resized_instances']} resized cells · {repair['inserted_buffers']} buffers · {repair['new_antenna_diodes']} new diode",
    f"Final setup: +{data['post_route_setup_slack_ns']:.3f} ns",
    f"Final hold: +{data['post_route_hold_slack_ns']:.3f} ns",
    'Router / fixed-deck DRC, antenna, connectivity: pass',
    'Final Liberty limits unchanged; RTL and netlist inputs frozen',
]
for i, line in enumerate(lines):
    axes[1].text(0, .93 - i * .105, line, fontsize=11 if i else 12,
                 color='#163447' if i else '#087f8c', transform=axes[1].transAxes)
fig.suptitle('Observed physical feedback repair in the standard CSIR flow', fontsize=15)
fig.text(.5, .015, 'Sky130HD TT · 25 °C / 1.8 V · 100 ns clock · 2 threads · single-corner engineering closure',
         ha='center', fontsize=10, color='#536574')
fig.tight_layout(rect=(0, .05, 1, .94))
for suffix in ('png', 'svg'):
    fig.savefig(ROOT / f'figures/standard_closure.{suffix}', dpi=180, bbox_inches='tight')
plt.close(fig)
(ROOT / 'figures/standard_closure.source.json').write_text(json.dumps({
    'source_receipt': str(receipt.relative_to(ROOT)),
    'source_sha256': hashlib.sha256(receipt.read_bytes()).hexdigest(),
    'snapshot_id': data['final_snapshot_id'],
    'scope': 'Observed same-case native PnR repair; no held-out RSI or whole-project acceptance claim',
}, indent=2) + '\n')
print('STANDARD_CLOSURE_FIGURE_PASS')
