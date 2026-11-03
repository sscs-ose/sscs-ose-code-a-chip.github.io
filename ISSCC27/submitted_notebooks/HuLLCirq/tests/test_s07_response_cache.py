"""S07 final-response cache QA on isolated copied proof; no model or EDA."""
from __future__ import annotations

from collections import Counter
from contextlib import ExitStack
from types import MethodType
import unittest
from unittest.mock import patch

import test_implementation_specs as fixtures
from hullcirq.domain import DomainError
from hullcirq.envelope_cache import _READ_CACHE, memoized_envelope


class S07ResponseCacheTests(unittest.TestCase):
    setUp = fixtures.SpecSoftwareQATests.setUp
    tearDown = fixtures.SpecSoftwareQATests.tearDown

    def instrument(self):
        """Count actual cold view construction, not calls served by the cache."""
        counts, events, stack = Counter(), [], ExitStack()
        self.addCleanup(stack.close)
        for label, manager in (("generation", self.generation), ("workflow", self.workflow)):
            original = manager.envelope
            raw = original.__func__.__wrapped__

            def counted(instance, _raw=raw, _label=label):
                counts[(_label, _READ_CACHE.get() is not None)] += 1
                return _raw(instance)

            stack.enter_context(patch.object(manager, "envelope", MethodType(memoized_envelope(counted), manager)))
        for name in ("_eligible", "_derive", "_source_reviews", "_record_review", "_persist"):
            original = getattr(self.manager, name)

            def observed(*args, _name=name, _original=original, **kwargs):
                events.append((_name, _READ_CACHE.get() is not None))
                return _original(*args, **kwargs)

            stack.enter_context(patch.object(self.manager, name, observed))
        return counts, events

    def start(self):
        return self.manager.start("node-pe", self.store.envelope()["revision"]["id"])

    def test_start_caches_only_final_reads_and_keeps_mutation_checks_uncached(self):
        counts, events = self.instrument()
        response = self.start()
        self.assertEqual(response["implementation_specs"][-1]["review_status"], "Accepted")
        # The two separate mutation guards really rebuild their read views.
        for label in ("generation", "workflow"):
            self.assertEqual(counts[(label, False)], 2)
            self.assertEqual(counts[(label, True)], 1)
        persist = next(index for index, event in enumerate(events) if event[0] == "_persist")
        self.assertTrue(any(name == "_eligible" for name, cached in events[:persist]))
        self.assertTrue(all(not cached for name, cached in events[:persist + 1]))
        self.assertTrue(all(not cached for name, cached in events if name in ("_derive", "_record_review", "_persist")))
        self.assertTrue(any(cached for name, cached in events[persist + 1:] if name == "_eligible"))
        self.assertIsNone(_READ_CACHE.get())

    def test_explicit_acceptance_checks_remain_uncached_before_cached_response(self):
        policy = self.store.review_policy()
        self.store.set_review_policy("manual", False, "Isolated cache QA manual policy.", policy["id"])
        spec = self.start()["implementation_specs"][-1]
        self.assertEqual(spec["review_status"], "Awaiting Review")
        counts, events = self.instrument()
        response = self.manager.review(spec["id"], "accepted", "Isolated explicit adoption.")
        self.assertEqual(response["implementation_specs"][-1]["review_status"], "Accepted")
        for label in ("generation", "workflow"):
            self.assertGreaterEqual(counts[(label, False)], 2)
            self.assertEqual(counts[(label, True)], 1)
        persist = next(index for index, event in enumerate(events) if event[0] == "_persist")
        self.assertTrue(all(not cached for name, cached in events[:persist + 1]))
        self.assertIsNone(_READ_CACHE.get())

    def test_independent_response_observes_changed_review_without_mutating_previous_view(self):
        first = self.start()
        spec = first["implementation_specs"][-1]
        changed = self.manager.review(spec["id"], "changes_requested", "Inspect the finite scope.")
        self.assertEqual(spec["review_status"], "Accepted")
        self.assertEqual(changed["implementation_specs"][-1]["review_status"], "Changes Requested")
        node = next(node for node in changed["implementation_spec_nodes"] if node["node_id"] == "node-pe")
        self.assertIsNone(node["accepted_spec_id"])
        again = self.manager._result_envelope()
        self.assertEqual(again, changed)
        self.assertIsNot(again, changed)
        self.assertIsNone(_READ_CACHE.get())

    def test_previous_response_cannot_hide_source_withdrawal_from_next_mutation(self):
        first = self.start()
        count = len(self.manager._state["specs"])
        candidate = first["implementation_specs"][-1]["candidate_id"]
        self.generation.review(candidate, "changes_requested", "Isolated source withdrawal.")
        with self.assertRaises(DomainError):
            self.start()
        self.assertEqual(len(self.manager._state["specs"]), count)
        self.assertIsNone(_READ_CACHE.get())

    def test_response_exception_discards_cache_after_durable_mutation(self):
        with patch.object(self.manager, "envelope", side_effect=RuntimeError("Isolated response failure")):
            with self.assertRaisesRegex(RuntimeError, "response failure"):
                self.start()
        self.assertIsNone(_READ_CACHE.get())
        self.assertTrue(self.manager.path.is_file())
        recovered = self.manager._result_envelope()
        self.assertEqual(len(recovered["implementation_specs"]), 1)
        self.assertEqual(recovered["implementation_specs"][-1]["review_status"], "Accepted")
        self.assertIsNone(_READ_CACHE.get())


if __name__ == "__main__":
    unittest.main()
