"""Isolated local-tool path and sanitized failure QA. No EDA is executed."""
import copy
import errno
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.domain import DomainError
from hullcirq.workflow import (WorkflowManager, allocate_synthesis_directory,
    node_artifact_parent, synthesize_generic, workflow_exception_diagnostic)


class LocalWorkflowArtifactPathTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / ".work" / "local_workflow_qa"
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = {"kind": "native", "executable": str(self.root / "yosys.exe"),
                       "working_directory": str(self.root / "tools")}

    def manager(self, stage="local_synthesis"):
        run = {"id": "software-only-run", "stage_id": stage, "execution_status": "Queued",
               "validation_status": "Not Checked", "module_name": "scalar", "verification_plan": {},
               "netlist": "module scalar; endmodule\n", "tool_configuration": copy.deepcopy(self.config),
               "checks": {}, "diagnostics": [], "error": None}
        manager = SimpleNamespace(lock=threading.RLock(), path=self.root / "arbitrarily_deep_project" / "workflow.json",
                                  _run=lambda identifier: run, _persist=Mock(), observe_design=Mock(),
                                  store=SimpleNamespace(review_policy=lambda: {"mode": "manual", "user_authorized": False}))
        return manager, run

    @staticmethod
    def failed_fixture(*args, **kwargs):
        return {"validation_status": "Failed", "executed": False, "exit_code": None,
                "commands": [], "diagnostics": [], "fixture_notice": "Software fixture; no tool executed"}

    def test_trusted_tool_parent_and_unique_short_synthesis_directories(self):
        parent = node_artifact_parent(self.config)
        self.assertEqual(parent, Path(self.config["working_directory"]).resolve())
        first, second = allocate_synthesis_directory(self.config), allocate_synthesis_directory(self.config)
        self.assertNotEqual(first, second)
        self.assertEqual(first.parent, parent)
        self.assertTrue(first.name.startswith("hullcirq-s05-"))
        self.assertLess(len(str(first / "candidate.v")), 248)
        with patch("hullcirq.workflow.execute_fixed", return_value={"status": "Completed", "exit_code": 1,
                    "executed": False, "stdout": "", "stderr": "SOFTWARE_QA_NO_TOOL"}) as tool:
            result = synthesize_generic("module scalar; endmodule\n", "scalar", self.config, first)
        self.assertEqual(result["artifacts_directory"], str(first))
        self.assertTrue((first / "candidate.v").is_file())
        self.assertEqual(tool.call_count, 2)

    def test_fallback_stays_inside_HuLLCirq_and_rejects_relative_configured_parent(self):
        self.assertEqual(node_artifact_parent({}), ROOT / ".work" / "node_runs")
        with self.assertRaises(DomainError) as caught:
            node_artifact_parent({"working_directory": "relative"})
        self.assertEqual(caught.exception.code, "workflow_environment_error")
        self.assertEqual(caught.exception.next_action, "retry_same_RTL")

    def test_worker_S05_passes_unique_trusted_directory_not_deep_project_run_path(self):
        manager, run = self.manager()
        retained = {"old_run": {"id": "old-run", "checks": {"artifacts_directory": "retained-original-path"}}}
        original = copy.deepcopy(retained)
        with patch("hullcirq.workflow.synthesize_generic", side_effect=self.failed_fixture) as runner:
            WorkflowManager._execute(manager, run["id"], "module scalar; endmodule", threading.Event())
        directory = runner.call_args.args[3]
        self.assertEqual(directory.parent, Path(self.config["working_directory"]))
        self.assertNotIn("workflow_runs", directory.parts)
        self.assertEqual(retained, original)
        self.assertEqual(run["execution_status"], "Completed")

    def test_worker_S06_passes_parent_directly_to_existing_unique_child_creator(self):
        manager, run = self.manager("local_netlist_simulation")
        with patch("hullcirq.workflow.verify_behavior", side_effect=self.failed_fixture) as runner:
            WorkflowManager._execute(manager, run["id"], "not_used", threading.Event())
        self.assertEqual(runner.call_args.args[3], Path(self.config["working_directory"]))
        self.assertNotIn(run["id"], str(runner.call_args.args[3]))

    def test_pretool_directory_failure_is_environment_retry_same_RTL_and_sanitized(self):
        manager, run = self.manager()
        failure = FileNotFoundError(errno.ENOENT, "SECRET_EXCEPTION_MESSAGE", "SECRET_PRIVATE_FILENAME")
        failure.winerror = 206
        with patch("hullcirq.workflow.tempfile.mkdtemp", side_effect=failure), \
                patch("hullcirq.workflow.synthesize_generic") as runner:
            WorkflowManager._execute(manager, run["id"], "module scalar; endmodule", threading.Event())
        runner.assert_not_called()
        error = run["error"]
        self.assertEqual(run["execution_status"], "Failed")
        self.assertEqual(error["code"], "workflow_environment_error")
        self.assertEqual(error["next_action"], "retry_same_RTL")
        self.assertEqual(error["execution_phase"], "prepare_synthesis_artifact_directory")
        self.assertEqual((error["exception_class"], error["errno"], error["winerror"]), ("FileNotFoundError", errno.ENOENT, 206))
        self.assertNotIn("SECRET", json.dumps(error))
        self.assertEqual(run["checks"], {})

    def test_synthesis_input_write_error_retains_phase_without_raw_path(self):
        directory = allocate_synthesis_directory(self.config)
        with patch("pathlib.Path.write_text", side_effect=PermissionError(errno.EACCES, "SECRET_PATH")), \
                patch("hullcirq.workflow.execute_fixed") as tool:
            with self.assertRaises(DomainError) as caught:
                synthesize_generic("module scalar; endmodule", "scalar", self.config, directory)
        tool.assert_not_called()
        self.assertEqual(caught.exception.execution_diagnostic["execution_phase"], "prepare_synthesis_inputs")
        self.assertNotIn("SECRET", caught.exception.message)

    def test_other_worker_exceptions_preserve_safe_identity_without_environment_claim(self):
        manager, run = self.manager()
        with patch("hullcirq.workflow.synthesize_generic", side_effect=ValueError("SECRET_TOKEN")):
            WorkflowManager._execute(manager, run["id"], "module scalar; endmodule", threading.Event())
        self.assertEqual(run["error"]["exception_class"], "ValueError")
        self.assertEqual(run["error"]["execution_phase"], "execute_synthesis")
        self.assertEqual(run["error"]["code"], "workflow_error")
        self.assertNotIn("next_action", run["error"])
        self.assertNotIn("SECRET", json.dumps(run["error"]))

    def test_isolated_OS_probe_of_former_248_character_directory(self):
        """Record capability, not a universal Windows long-path assumption."""
        if os.name != "nt":
            self.skipTest("Windows legacy path-limit probe only")
        base = self.root / "legacy_probe"
        base.mkdir()
        padding = 248 - len(str(base)) - 1
        self.assertGreater(padding, 0)
        old = base / ("x" * padding)
        result = {"directory_characters": len(str(old)), "candidate_characters": len(str(old / "candidate.v"))}
        try:
            old.mkdir()
            (old / "candidate.v").write_text("SOFTWARE_QA_PATH_PROBE_ONLY\n", encoding="utf-8")
            result["outcome"] = "supported_on_this_runtime"
        except OSError as error:
            result.update(outcome="legacy_path_failed", **workflow_exception_diagnostic(error, "isolated_OS_path_probe"))
        print("ISOLATED_PATH_PROBE " + json.dumps(result, sort_keys=True))
        self.assertEqual(result["directory_characters"], 248)


if __name__ == "__main__":
    unittest.main()
