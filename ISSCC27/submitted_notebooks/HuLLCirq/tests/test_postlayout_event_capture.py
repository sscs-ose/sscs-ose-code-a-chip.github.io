"""Focused checks of isolated native-recorder probes, never NPU validation."""
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / '.work/m2l/events'
QA = BASE / 'qualification01'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class NativeEventRecorderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (QA / 'report.json').is_file():
            raise unittest.SkipTest('Run the independent pinned recorder capability probes first; no qualification result is fabricated.')
        cls.report = load(QA / 'report.json')
        cls.baseline = QA / 'same_tick_glitch_x_z_nba'
        cls.summary = load(cls.baseline / 'hullcirq-events-summary.json')
        cls.rows = [row.split('\t') for row in (cls.baseline / 'hullcirq-events.tsv').read_text().splitlines()]
        cls.events = [row for row in cls.rows if row[0] == 'EVENT']

    def test_probe_scope_and_frozen_default_build_are_explicit(self):
        self.assertFalse(self.report['original_npu_executed'])
        self.assertEqual(self.report['new_original_job_runs'], 0)
        build = self.report['build_manifest']
        for name in ('postlayout_event_capture.c', 'hullcirq_event_capture.vpi', 'event-signal-manifest.tsv'):
            path = BASE / 'build' / name
            self.assertEqual(sha(path), build['files'][name]['sha256'])
            self.assertEqual(path.stat().st_size, build['files'][name]['bytes'])
        self.assertEqual(sha(ROOT / 'scripts/postlayout_event_capture.c'), build['files']['postlayout_event_capture.c']['sha256'])

    def test_all_observed_callbacks_keep_contiguous_order_and_four_state_values(self):
        self.assertEqual([int(row[1]) for row in self.events], list(range(1, 40)))
        times = [int(row[2]) for row in self.events]
        self.assertEqual(times, sorted(times))
        for row in self.events:
            self.assertRegex(row[5], r'^[01xz]+$')
        self.assertEqual(self.summary['ordering'], 'callback_invocation_order')
        self.assertEqual(self.summary['delta_identity'], 'unavailable')

    def test_same_tick_blocking_inactive_nba_x_and_z_are_not_coalesced(self):
        values = [row[5] for row in self.events if row[2:5] == ['1000', '1', 'change']]
        self.assertEqual(values, ['1', '0', 'x', 'z', '0', '1', '0', '1'])
        vcd_tick = (self.baseline / 'normal.vcd').read_text().split('#1000\n')[1].split('#1500')[0]
        self.assertEqual(vcd_tick.count('$\n'), 1)
        self.assertIn('1$\n', vcd_tick)

    def test_vector_glitches_and_unknown_bits_are_retained(self):
        values = [row[5] for row in self.events if row[2:5] == ['1000', '4', 'change']]
        self.assertEqual(values, ['01xz', '10zx', '0000'])

    def test_initial_unknowns_and_time_zero_settlement_are_separate(self):
        initial = [row for row in self.events if row[4] == 'initial']
        settled = [row for row in self.events if row[4] == 'settled']
        self.assertEqual(len(initial), 4)
        self.assertEqual(len(settled), 4)
        self.assertTrue(all(row[2] == '0' and set(row[5]) == {'x'} for row in initial))
        self.assertGreater(int(settled[0][1]), int(initial[-1][1]))
        self.assertEqual({row[3]: row[5] for row in settled}, {'1': '0', '2': '0', '3': '0', '4': '0000'})

    def test_recorder_does_not_change_control_waveform(self):
        strip_date = lambda value: re.sub(r'\$date.*?\$end', '', value, flags=re.S)
        recorded = strip_date((self.baseline / 'normal.vcd').read_text())
        control = strip_date((QA / 'without_recorder_control/normal.vcd').read_text())
        self.assertEqual(recorded, control)
        source = (ROOT / 'scripts/postlayout_event_capture.c').read_text()
        self.assertIsNone(re.search(r'\b(?:vpi_put_value|vpi_put_delays|vpi_control)\s*\(', source))

    def test_original_manifest_has_all_sequential_pins_and_top_signals(self):
        rows = [row.split('\t') for row in (BASE / 'build/event-signal-manifest.tsv').read_text().splitlines()[1:]]
        self.assertEqual(len(rows), 9969)
        self.assertEqual([int(row[0]) for row in rows], list(range(1, 9970)))
        self.assertEqual(len({row[1] for row in rows}), 9969)
        by_role = {}
        for row in rows:
            by_role.setdefault(row[3], []).append(row)
        for role in ('CLK', 'D', 'CLK_delayed', 'D_delayed', 'Q'):
            self.assertEqual(len(by_role[role]), 1991)
            self.assertTrue(all(row[2] == '1' for row in by_role[role]))
        self.assertEqual(len(by_role['SOURCE_CLK']), 1)
        self.assertEqual(len(by_role['TOP_INPUT']) + len(by_role['TOP_OUTPUT']), 13)
        config = next(row for row in rows if row[1] == 'hullcirq_global_tb.dut.config_data')
        self.assertEqual(config[2], '134')

    def test_incomplete_mapping_limits_and_output_conflicts_fail_closed(self):
        expected = {'missing_signal': 'signal_missing_or_width_conflict', 'wrong_width': 'signal_missing_or_width_conflict',
            'duplicate_path': 'duplicate_signal_path', 'unsupported_precision': 'precision_not_picoseconds',
            'existing_output_refused': 'output_exists_or_unwritable', 'event_limit_incomplete': 'event_limit',
            'byte_limit_incomplete': 'byte_limit'}
        for name, code in expected.items():
            with self.subTest(name=name):
                summary = load(QA / name / 'hullcirq-events-summary.json')
                self.assertFalse(summary['capture_complete'])
                self.assertGreater(summary['error_count'], 0)
                self.assertEqual(summary['last_error'], code)
        self.assertEqual((QA / 'existing_output_refused/hullcirq-events.tsv').read_bytes(), b'EXISTING_OUTPUT_MUST_NOT_CHANGE\n')
        self.assertLessEqual((QA / 'byte_limit_incomplete/hullcirq-events.tsv').stat().st_size, 128)
        quota = load(QA / 'event_limit_incomplete/hullcirq-events-summary.json')
        self.assertEqual(quota['events_written'], 10)
        self.assertGreater(quota['dropped_events'], 0)

    def test_footer_counts_flush_and_complete_manifest_agree(self):
        footer = self.rows[-1]
        self.assertEqual(footer, ['END', '39', '3000', '4', '39', '0', '1'])
        self.assertEqual(self.summary['events_written'], len(self.events))
        self.assertEqual(self.summary['initial_events'] + self.summary['change_callbacks'] + self.summary['settled_events'], len(self.events))
        self.assertTrue(self.summary['capture_complete'])
        self.assertTrue(self.summary['flush_complete'])
        self.assertTrue(self.summary['end_callback_seen'])
        self.assertEqual(self.summary['output_bytes'], (self.baseline / 'hullcirq-events.tsv').stat().st_size)
        counts = {row[1]: [int(value) for value in row[2:]] for row in self.rows if row[0] == 'COUNTS'}
        for signal in self.summary['signals']:
            self.assertEqual(counts[str(signal['id'])], [signal['initial_count'], signal['change_count'], signal['settled_count']])
            self.assertEqual(signal['path'], signal['resolved_path'])


if __name__ == '__main__': unittest.main()
