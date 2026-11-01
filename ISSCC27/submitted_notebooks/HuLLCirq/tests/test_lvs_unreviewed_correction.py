"""An unresolved extraction warning must not need adoption to be corrected."""
import copy
import json
from unittest.mock import patch
from test_lvs_repair_direct_v7_session import DirectV7SessionTests
from test_lvs_repair_session import checksum
from hullcirq import lvs_repair_session as session
from hullcirq.domain import DomainError


class UnreviewedCorrectionTests(DirectV7SessionTests):
    def pending(self):
        record = self.qa.records['lvs']
        record['review_status'] = 'Awaiting Review'
        checksum(record)
        self.qa.histories['lvs']['reviews'] = []
        self.qa.server.lvs_workflow._state['runs'] = [copy.deepcopy(record)]
        self.qa.write_histories()

    def test_pending_source_prepares_and_restores_without_any_review_or_source_write(self):
        self.pending()
        before = {p: p.read_bytes() for p in self.qa.system.iterdir()}
        self.assertTrue(session.eligibility(self.qa.server)['eligible'])
        self.prepare()
        bundle = json.loads(self.path.read_bytes())
        self.assertEqual(bundle['schema'], session.DIRECT_PENDING_SCHEMA)
        self.assertTrue(self.qa.restore()[1]['configured'])
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        self.assertEqual(self.qa.histories['lvs']['reviews'], [])

    def test_pending_with_previous_review_is_not_silently_overridden(self):
        self.pending()
        self.qa.histories['lvs']['reviews'] = [{'run_id': 'lvs-software', 'decision': 'changes_requested'}]
        self.qa.write_histories()
        with self.assertRaises(DomainError): self.prepare()
        self.assertFalse(self.path.exists())

    def test_unadopted_upstream_or_failed_source_cannot_use_pending_path(self):
        self.pending()
        for name, field, value in [('physical', 'review_status', 'Awaiting Review'),
                                   ('drc', 'review_status', 'Awaiting Review'),
                                   ('lvs', 'validation_status', 'Failed')]:
            record = self.qa.records[name]
            previous = copy.deepcopy(record)
            record[field] = value
            checksum(record); self.qa.write_histories()
            with self.assertRaises(DomainError): self.prepare()
            record.clear(); record.update(previous); self.qa.write_histories()
        self.assertFalse(self.path.exists())

    def test_historical_schema_still_requires_accepted_source(self):
        self.pending(); self.prepare()
        bundle = json.loads(self.path.read_bytes())
        bundle['schema'] = session.DIRECT_SCHEMA
        checksum(bundle); self.path.write_text(json.dumps(bundle), encoding='utf-8')
        self.assertFalse(self.qa.restore()[1]['configured'])

    def test_modified_unreviewed_source_invalidates_prepared_binding(self):
        self.pending(); self.prepare()
        self.qa.records['lvs']['checks']['summary']['extraction']['feedback'][0]['geometry'] = ['changed']
        checksum(self.qa.records['lvs']); self.qa.write_histories()
        self.assertFalse(self.qa.restore()[1]['configured'])
