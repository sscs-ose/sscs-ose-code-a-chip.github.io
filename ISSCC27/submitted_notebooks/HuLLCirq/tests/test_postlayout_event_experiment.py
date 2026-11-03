"""Original-job binding guard software QA; never launches EDA or adopts S14.

The fixture below is an exact metadata copy from the completed same-GUI-job
experiment. It is retained here so guard QA does not require ignored .work
artifacts. Mutations test provenance admission, never substitute circuit data.
"""
import copy
import hashlib
import json
from pathlib import Path
import runpy
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.domain import DomainError

SCRIPT = runpy.run_path(str(ROOT / "scripts/audit_postlayout_event_experiment.py"))
validate_original_binding = SCRIPT["validate_original_binding"]
FIXTURE_ORIGIN = ".work/m2l/dynamic/original-job-xbd2e32a/source-binding.json"
FIXTURE_RAW_SHA256 = "1d45c2293922ecb0d6241392c9f1fd2879a8cc448ac3de07a18f9b2a33835d87"
FIXTURE_RAW = '{\r\n  "kind": "hullcirq-unchanged-original-job-event-experiment-v1",\r\n  "original_folder": "C:\\\\dev\\\\isscc2027-code-a-chip\\\\ISSCC27\\\\submitted_notebooks\\\\HuLLCirq\\\\.work\\\\m2k\\\\dynamic\\\\original-job-yfyg25m7",\r\n  "original_evidence_sha256": "93bfa502b27afec1e56f6e676d9e475b94ac57759431e94b46c071aa62d35850",\r\n  "original_source_binding": {\r\n    "layout_run_id": "physical-workflow-f678bc2dd59949219132a7de80eb12af",\r\n    "layout_record_sha256": "dd606fdf01f4b3a7dbb9f3aee515cb695c2e2ebb201a9681367d7b38ac3f47fc",\r\n    "drc_run_id": "drc-workflow-fc1c027a6910443b9dd851790e8d0473",\r\n    "drc_record_sha256": "1dc5072106946cda413e24804020934102c582bcb0da6801de6e90163dc0816c",\r\n    "lvs_run_id": "lvs-workflow-1abf90a7beea438e9d50bac5cf517368",\r\n    "lvs_record_sha256": "d2b02b5b7b9ea51d737e7b6d3f49cf1f7d55046beda8b1a7e87f999c09393133",\r\n    "revision_id": "revision-4d479dc8032644ca96961d4128481094",\r\n    "verification_plan_sha256": "878fd99750c890a7c358ca0858b12d57fadfcce8036796bcb2713d56ace9d6d7"\r\n  },\r\n  "original_execution_audits": {\r\n    "compile": {\r\n      "kind": "hullcirq-postlayout-completed-execution-audit-v1",\r\n      "operation": "compile",\r\n      "worker_version": "hullcirq-postlayout-worker-v2",\r\n      "request_sha256": "7fa45ebb1c23ebcc0458b28bd26329eba72c74ee67726dd562a36b7573d9d1d5",\r\n      "worker_sha256": "1ef52ce064ddd736eef2fc5e88b193a4815b8444325d96f4d660b50bfc7382a0",\r\n      "process_start_sha256": "f7fb173c1c353033bfa900628044300e7b4cf336a4c2e0dcf5d5fc15a2b303bd",\r\n      "process_result_sha256": "8e74980d795b56afdfa737a55462f8149ec4de681a5de8dc40b5e240dbfcaaaf",\r\n      "configuration_sha256": "7a7d191035b8a26be508db65877fa53dfa29626bad61c3cd4f267123e06d03a4",\r\n      "input_files_sha256": {\r\n        "primitives.v": "7d4b1441d06b0f2b9662befa675a0484d77149e04eb42a5f1fa2d4cfded7b2ce",\r\n        "original-cell-models.v": "12d5d6448ccf265c544d88402d5c10ab6de9bee8b8cde48eee1f31ea8c3c3e45",\r\n        "input.nl.v": "aa87faca88e5fac7df4fe9cebe91d924de09857a5c0e74914fac61baec8a6a8f",\r\n        "timed-testbench.v": "784e8b683338bf4266fc227c86568b4e7a8661f0cd3cd41b8706e369ab5c9c05",\r\n        "input.sdf": "477b34cf25b9be2b0312ae34e1a4632590eecd31fe63d02518d7663d4b3f3702"\r\n      },\r\n      "execution_binding_verified": true,\r\n      "process_group_cleanup_verified": true,\r\n      "circuit_validation_status": "Not evaluated",\r\n      "adoption_permitted": false\r\n    },\r\n    "simulate": {\r\n      "kind": "hullcirq-postlayout-completed-execution-audit-v1",\r\n      "operation": "simulate",\r\n      "worker_version": "hullcirq-postlayout-worker-v2",\r\n      "request_sha256": "1b6659d34402fb21894ae836a3d1db447ca2c620ddf50ec66851eabb04e3864e",\r\n      "worker_sha256": "1ef52ce064ddd736eef2fc5e88b193a4815b8444325d96f4d660b50bfc7382a0",\r\n      "process_start_sha256": "8f69893fb4b0078724e1373fec2407fc77e382016f5b8f1f2fc1050e041f65ec",\r\n      "process_result_sha256": "f654bc0e5ea203dfc1f3f57103aaca0eab1dcddf518e781b915b241d5e7e1b42",\r\n      "configuration_sha256": "7a7d191035b8a26be508db65877fa53dfa29626bad61c3cd4f267123e06d03a4",\r\n      "input_files_sha256": {\r\n        "primitives.v": "7d4b1441d06b0f2b9662befa675a0484d77149e04eb42a5f1fa2d4cfded7b2ce",\r\n        "original-cell-models.v": "12d5d6448ccf265c544d88402d5c10ab6de9bee8b8cde48eee1f31ea8c3c3e45",\r\n        "input.nl.v": "aa87faca88e5fac7df4fe9cebe91d924de09857a5c0e74914fac61baec8a6a8f",\r\n        "timed-testbench.v": "784e8b683338bf4266fc227c86568b4e7a8661f0cd3cd41b8706e369ab5c9c05",\r\n        "input.sdf": "477b34cf25b9be2b0312ae34e1a4632590eecd31fe63d02518d7663d4b3f3702",\r\n        "simulation.vvp": "b9fb8b58a009b0f349cd627dd1874ee44c4b28379d5b558883b6fc613114fd3a",\r\n        "hullcirq_readback.vpi": "3a5c10e7bcfc12e98cd37a2c16a74ffd2503385f7cb8851d8d2aea712bbe97e3",\r\n        "hullcirq_readback.c": "5e476247443e686b95b781b6945882c79c440477ea40f4bbeab3039236ee2e08",\r\n        "sdf-readback-manifest.tsv": "cf5d42a93b750a3cc2339c574d36db88fa58931279b95ca86a9904fd7da964da"\r\n      },\r\n      "execution_binding_verified": true,\r\n      "process_group_cleanup_verified": true,\r\n      "circuit_validation_status": "Not evaluated",\r\n      "adoption_permitted": false\r\n    }\r\n  },\r\n  "unchanged_inputs": {\r\n    "hullcirq_readback.c": "5e476247443e686b95b781b6945882c79c440477ea40f4bbeab3039236ee2e08",\r\n    "hullcirq_readback.vpi": "3a5c10e7bcfc12e98cd37a2c16a74ffd2503385f7cb8851d8d2aea712bbe97e3",\r\n    "input.nl.v": "aa87faca88e5fac7df4fe9cebe91d924de09857a5c0e74914fac61baec8a6a8f",\r\n    "input.sdf": "477b34cf25b9be2b0312ae34e1a4632590eecd31fe63d02518d7663d4b3f3702",\r\n    "original-cell-models.v": "12d5d6448ccf265c544d88402d5c10ab6de9bee8b8cde48eee1f31ea8c3c3e45",\r\n    "primitives.v": "7d4b1441d06b0f2b9662befa675a0484d77149e04eb42a5f1fa2d4cfded7b2ce",\r\n    "sdf-readback-manifest.tsv": "cf5d42a93b750a3cc2339c574d36db88fa58931279b95ca86a9904fd7da964da",\r\n    "testbench-adapter.json": "3ceabf3e71da0823cc4a80c2273cbb0ff861d544e2b3f2e69bb7aa07def919f5",\r\n    "timed-testbench.v": "784e8b683338bf4266fc227c86568b4e7a8661f0cd3cd41b8706e369ab5c9c05",\r\n    "verification-plan.json": "70edc4953ae35708211ba5bd1d5d33279ed933e35d23c686dda9fd5713f338fb"\r\n  },\r\n  "original_job_changed": false,\r\n  "rtl_changed": false,\r\n  "sdf_changed": false,\r\n  "cell_models_changed": false,\r\n  "event_plugin_inputs": {\r\n    "hullcirq_readback.vpi": "3a5c10e7bcfc12e98cd37a2c16a74ffd2503385f7cb8851d8d2aea712bbe97e3",\r\n    "hullcirq_readback.c": "5e476247443e686b95b781b6945882c79c440477ea40f4bbeab3039236ee2e08",\r\n    "sdf-readback-manifest.tsv": "cf5d42a93b750a3cc2339c574d36db88fa58931279b95ca86a9904fd7da964da",\r\n    "postlayout_event_capture.c": "0ac1830699df1436182803cd31d377ec355b44db4f11ba85dd5f10e5fc1726cd",\r\n    "hullcirq_event_capture.vpi": "8f06ee2a54191de017dad678f899b7910e150444ebaede356296fdbabca56283",\r\n    "event-signal-manifest.tsv": "46a7593396792f43238f5bf3673cde1a9b1fa9d4cddd82d1d74e8215f294fb19"\r\n  },\r\n  "scope": "event-observation experiment; native delay-binding issues remain; no adoption",\r\n  "adoption_permitted": false\r\n}\r\n'


class PostlayoutEventExperimentGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = json.loads(FIXTURE_RAW)
        # The helper consumes only this retained evidence projection. Keeping
        # it in the software fixture makes source-only QA copies reproducible.
        cls.evidence = {"original_source_binding": copy.deepcopy(cls.original["original_source_binding"])}

    def binding(self):
        value = copy.deepcopy(self.original)
        # Resolve only the software fixture's checkout location. The original
        # experiment and its raw binding above are never rewritten or replayed.
        value["original_folder"] = str(SCRIPT["SOURCE"])
        return value

    def reject(self, value):
        with self.assertRaises(DomainError):
            validate_original_binding(value, self.evidence)

    def test_exact_completed_job_metadata_is_admitted_without_mutation(self):
        self.assertEqual(hashlib.sha256(FIXTURE_RAW.encode("utf-8")).hexdigest(), FIXTURE_RAW_SHA256)
        binding = self.binding()
        before = copy.deepcopy(binding)
        validate_original_binding(binding, self.evidence)
        self.assertEqual(binding, before)
        self.assertIs(binding["adoption_permitted"], False)

    def test_each_of_ten_original_inputs_is_mandatory(self):
        self.assertEqual(len(self.original["unchanged_inputs"]), 10)
        for name in self.original["unchanged_inputs"]:
            with self.subTest(name=name):
                binding = self.binding()
                del binding["unchanged_inputs"][name]
                self.reject(binding)

    def test_extra_original_input_is_not_admitted(self):
        binding = self.binding()
        binding["unchanged_inputs"]["different-testbench.v"] = "0" * 64
        self.reject(binding)

    def test_non_mapping_original_input_sets_are_rejected(self):
        for value in (None, [], True, "input.nl.v"):
            with self.subTest(value=value):
                binding = self.binding()
                binding["unchanged_inputs"] = value
                self.reject(binding)

    def test_original_binding_kind_is_mandatory_and_exact(self):
        for value in (None, "hullcirq-substitute-job-event-experiment-v1", 1):
            with self.subTest(value=value):
                binding = self.binding()
                binding["kind"] = value
                self.reject(binding)
        binding = self.binding()
        del binding["kind"]
        self.reject(binding)

    def test_original_source_folder_cannot_be_redirected(self):
        for value in (None, ".work/m2k/dynamic/original-job-yfyg25m7", self.original["original_folder"] + "-other"):
            with self.subTest(value=value):
                binding = self.binding()
                binding["original_folder"] = value
                self.reject(binding)

    def test_adoption_permission_requires_exact_false(self):
        for value in (True, None, 0, "false"):
            with self.subTest(value=value):
                binding = self.binding()
                binding["adoption_permitted"] = value
                self.reject(binding)
        binding = self.binding()
        del binding["adoption_permitted"]
        self.reject(binding)

    def test_each_source_change_flag_requires_exact_false(self):
        for name in ("original_job_changed", "rtl_changed", "sdf_changed", "cell_models_changed"):
            for value in (True, None, 0, "false"):
                with self.subTest(name=name, value=value):
                    binding = self.binding()
                    binding[name] = value
                    self.reject(binding)
            binding = self.binding()
            del binding[name]
            self.reject(binding)

    def test_previous_diagnostic_evidence_hash_is_mandatory(self):
        for value in (None, "0" * 64, ""):
            with self.subTest(value=value):
                binding = self.binding()
                binding["original_evidence_sha256"] = value
                self.reject(binding)

    def test_each_adopted_source_identity_is_mandatory_and_unchanged(self):
        for name in self.original["original_source_binding"]:
            for mutation in ("omit", "change"):
                with self.subTest(name=name, mutation=mutation):
                    binding = self.binding()
                    if mutation == "omit":
                        del binding["original_source_binding"][name]
                    else:
                        binding["original_source_binding"][name] += "-changed"
                    self.reject(binding)
        binding = self.binding()
        binding["original_source_binding"]["extra_adopted_record"] = "unknown"
        self.reject(binding)

    def test_each_observer_source_binary_and_manifest_pin_is_mandatory(self):
        self.assertEqual(len(self.original["event_plugin_inputs"]), 6)
        for name in self.original["event_plugin_inputs"]:
            for mutation in ("omit", "change"):
                with self.subTest(name=name, mutation=mutation):
                    binding = self.binding()
                    if mutation == "omit":
                        del binding["event_plugin_inputs"][name]
                    else:
                        binding["event_plugin_inputs"][name] = "0" * 64
                    self.reject(binding)

    def test_extra_or_untyped_observer_pins_are_rejected(self):
        binding = self.binding()
        binding["event_plugin_inputs"]["other.vpi"] = "0" * 64
        self.reject(binding)
        for value in (None, [], True):
            with self.subTest(value=value):
                binding = self.binding()
                binding["event_plugin_inputs"] = value
                self.reject(binding)

    def test_top_level_binding_must_be_an_object(self):
        for value in (None, [], True, "binding"):
            with self.subTest(value=value):
                self.reject(value)


if __name__ == "__main__":
    unittest.main()
