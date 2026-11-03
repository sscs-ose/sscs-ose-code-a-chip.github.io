"""Presentation revision regression on isolated software fixtures, never live EDA."""
import copy
import unittest
from unittest.mock import patch

import test_postlayout_workflow as fixtures
import test_global_workflow as global_fixtures
from hullcirq.domain import DomainError
from hullcirq.presentation_revision import same_revision_design


class PresentationChainTests(unittest.TestCase):
    def setUp(self):
        self.base = fixtures.PostLayoutWorkflowTests("runTest")
        self.base.setUp()
        self.addCleanup(self.base.doCleanups)

    def test_all_s08_to_s14_sources_and_store_bytes_survive_display_save_and_reopen(self):
        final = self.base.run_postlayout()
        lvs_base = self.base.base
        drc_base = lvs_base.base
        physical_base = drc_base.base
        global_base = physical_base.base
        managers = [global_base.global_manager, global_base.manager,
                    self.base.physical, self.base.drc, self.base.lvs, self.base.manager]
        old_bytes = {manager.path: manager.path.read_bytes() for manager in managers}
        old_states = [(manager._state["source_key"], manager._state["source_epoch"]) for manager in managers]
        current = self.base.store.envelope()
        changed = copy.deepcopy(current["design"])
        changed["layout"]["viewport"]["zoom"] *= 1.125
        changed["layout"]["viewport"]["x"] += 12
        changed["project"]["name"] += " display only"
        saved = self.base.store.save(changed, current["revision"]["id"])
        self.assertTrue(same_revision_design(self.base.store, current["revision"]["id"], saved["revision"]["id"]))
        for manager in managers:
            data = next(iter(manager.envelope().values()))
            self.assertTrue(data["ready"], data.get("blocked_reason"))
            self.assertIsNone(data.get("storage_error"))
            records = data.get("runs", data.get("jobs"))
            self.assertEqual(records[-1]["review_status"], "Accepted")
            self.assertEqual(records[-1]["freshness"], "Current")
        self.assertEqual([(manager._state["source_key"], manager._state["source_epoch"]) for manager in managers], old_states)
        self.assertEqual({manager.path: manager.path.read_bytes() for manager in managers}, old_bytes)
        reopened_lvs = lvs_base.new_manager(); self.addCleanup(reopened_lvs.close)
        reopened = self.base.new_manager(); self.addCleanup(reopened.close)
        self.assertEqual(reopened_lvs.envelope()["lvs_workflow"]["accepted_run_id"], self.base.lvs_run["id"])
        self.assertEqual(reopened.envelope()["postlayout_workflow"]["accepted_run_id"], final["id"])
        self.assertEqual({manager.path: manager.path.read_bytes() for manager in managers}, old_bytes)

    def test_stale_request_revisions_cannot_start_any_downstream_stage(self):
        self.base.run_postlayout()
        global_base = self.base.base.base.base.base
        old = self.base.store.envelope()
        changed = copy.deepcopy(old["design"])
        changed["layout"]["viewport"]["x"] += 5
        self.base.store.save(changed, old["revision"]["id"])
        calls = [
            (global_base.manager, ("global_synthesis", global_base.job["id"], None, old["revision"]["id"])),
            (global_base.manager, ("global_netlist_simulation", global_base.job["id"], self.base.base.base.base.synthesis["id"], old["revision"]["id"])),
            (self.base.physical, ("layout", global_base.job["id"], self.base.base.base.base.synthesis["id"], self.base.base.base.base.simulation["id"], old["revision"]["id"])),
            (self.base.drc, ("drc", self.base.layout["id"], old["revision"]["id"])),
            (self.base.lvs, ("lvs", self.base.layout["id"], self.base.drc_run["id"], old["revision"]["id"])),
            (self.base.manager, ("post_layout_verification", self.base.layout["id"], self.base.drc_run["id"], self.base.lvs_run["id"], old["revision"]["id"])),
        ]
        for manager, args in calls:
            count = len(manager._state["runs"])
            with self.subTest(stage=args[0]), patch.object(manager, "_execute") as execute:
                with self.assertRaises(DomainError):
                    manager.start(*args)
                execute.assert_not_called()
                self.assertEqual(len(manager._state["runs"]), count)

    def test_new_downstream_requests_use_current_revision_but_freeze_original_chain(self):
        global_base = self.base.base.base.base.base
        original = self.base.store.envelope()
        changed = copy.deepcopy(original["design"])
        changed["layout"]["viewport"]["x"] += 5
        current = self.base.store.save(changed, original["revision"]["id"])["revision"]["id"]
        def finish(manager):
            manager._worker.join(20)
            self.assertFalse(manager._worker.is_alive())
            record = manager._state["runs"][-1]
            self.assertEqual(record["revision_id"], original["revision"]["id"])
            self.assertEqual(record["review_status"], "Accepted")
            self.assertEqual(manager._state["reviews"][-1]["reviewed_revision_id"], current)
            return record
        with patch("hullcirq.global_workflow.synthesize_global_generic", side_effect=global_fixtures.synthesis_fixture), \
                patch("hullcirq.global_workflow.check_global_netlist", side_effect=global_fixtures.simulation_fixture):
            global_base.manager.start("global_synthesis", global_base.job["id"], revision_id=current)
            synthesis = finish(global_base.manager)
            global_base.manager.start("global_netlist_simulation", global_base.job["id"], synthesis["id"], current)
            simulation = finish(global_base.manager)
        self.base.physical.start("layout", global_base.job["id"], synthesis["id"], simulation["id"], current)
        layout = finish(self.base.physical)
        self.base.drc.start("drc", layout["id"], current)
        drc = finish(self.base.drc)
        self.base.lvs.start("lvs", layout["id"], drc["id"], current)
        lvs = finish(self.base.lvs)
        self.base.manager.start("post_layout_verification", layout["id"], drc["id"], lvs["id"], current)
        finish(self.base.manager)
        for fixture in (global_base, self.base.base.base.base, self.base.base.base, self.base.base, self.base):
            reopened = fixture.new_manager(); self.addCleanup(reopened.close)
            self.assertIsNone(reopened._storage_error)


if __name__ == "__main__":
    unittest.main()
