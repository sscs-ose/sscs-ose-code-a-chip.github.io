"""Retained RTL batch inspection must never resume generation or rewrite history."""
import json
from pathlib import Path
import tempfile
import unittest

from hullcirq.domain import DomainError
from hullcirq.readonly_view import build_readonly_context
from hullcirq.store import ProjectStore


class SavedGenerationBatchTests(unittest.TestCase):
    def test_missing_batch_store_is_empty_without_creation(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / '.work') as directory:
            root = Path(directory)
            ProjectStore(root)
            before = {p.name: p.read_bytes() for p in root.glob('*.json')}
            context = build_readonly_context(root)
            self.assertEqual(context.generation_batches.envelope()['generation_batches']['batches'], [])
            self.assertFalse(context.generation_batches.is_active())
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.glob('*.json')})

    def test_active_saved_batch_is_inspected_as_interrupted_and_plan_cannot_start(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / '.work') as directory:
            root = Path(directory)
            ProjectStore(root)
            path = root / 'generation_batches.json'
            path.write_text(json.dumps({'batches': [{'id': 'batch', 'execution_status': 'Running', 'items': []}],
                                        'plans': [{'plan_id': 'plan', 'ready_to_start': True}]}), encoding='utf-8')
            before = path.read_bytes()
            context = build_readonly_context(root)
            batch = context.generation_batches.batch('batch')
            self.assertEqual(batch['execution_status'], 'Interrupted')
            self.assertEqual(batch['recorded_execution_status'], 'Running')
            self.assertFalse(context.generation_batches.plan('plan')['ready_to_start'])
            self.assertIsNone(context.generation_batches.envelope()['generation_batches']['active_batch_id'])
            with self.assertRaises(DomainError):
                context.generation_batches.batch('missing')
            context.generation_batches.close()
            self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
