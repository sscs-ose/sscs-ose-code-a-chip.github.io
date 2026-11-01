"""Version selection/retention fixtures; no GUI, models or actual EDA tools."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from hullcirq import block_layout as v1, block_recipe as recipes, physical_tools as tools
from hullcirq.domain import DomainError
from hullcirq.physical_workflow import _file_ids, _required_files
from hullcirq.verification import _wsl_path, object_hash
import test_block_layout as fixtures
import test_physical_tools as tool_fixtures


class BlockRecipeDispatchTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.BlockLayoutTests(methodName="runTest")
        fixture.setUp()
        self.plan, self.synthesis = copy.deepcopy(fixture.plan), copy.deepcopy(fixture.synthesis)
        self.design = {**copy.deepcopy(fixture.design), "physical_design": self.plan}
        self.manifest = {"nodes": [{"node_id": "npu2-pe", "module_name": "pe"}]}
        physical = tool_fixtures.PhysicalToolTests(methodName="runTest")
        physical.setUp()
        self.base = physical.config
        self.base["pdk_root"] = str(ROOT / ".work/software-fixture/pdks")
        self.settings = physical.settings
        self.synthesis["modules"][self.settings["top_module"]] = self.synthesis["modules"].pop("top")

    def configuration(self, recipe):
        # This helper intentionally uses the frozen v1 constructor, then selects
        # an exact requested profile; it never applies today's latest choice.
        result = v1.effective_configuration(self.base, self.design, ROOT)
        result["profile"] = json.loads((ROOT / "configs" / recipe.profile_file).read_text(encoding="utf-8"))
        return result

    def test_v1_saved_dispatch_is_not_promoted_to_latest(self):
        config = self.configuration(recipes.V1)
        before = copy.deepcopy(config)
        self.assertIs(recipes.recipe_for(config), recipes.V1)
        self.assertIs(recipes.runtime_for(config), v1)
        self.assertEqual(recipes.source_input(config, self.manifest, self.settings["top_module"]),
                         v1.source_input(config, self.manifest, self.settings["top_module"]))
        self.assertEqual(config, before)
        self.assertNotEqual(recipes.V1, recipes.LATEST)

    def test_fresh_explicit_plan_selects_latest_without_mutating_source(self):
        base = copy.deepcopy(self.base)
        base.update(resume={"old": True}, repair_source_binding={}, repair_checkpoint_inventory={})
        before, design_before = copy.deepcopy(base), copy.deepcopy(self.design)
        config = recipes.effective_configuration(base, self.design, ROOT)
        self.assertIs(recipes.recipe_for(config), recipes.V2)
        self.assertEqual(config["block_plan"], self.plan)
        self.assertEqual(config["block_plan_sha256"], object_hash(self.plan))
        for field in ("resume", "repair_source_binding", "repair_checkpoint_inventory"):
            self.assertNotIn(field, config)
        self.assertEqual(base, before)
        self.assertEqual(self.design, design_before)
        self.assertEqual(recipes.source_input(config, self.manifest, self.settings["top_module"]),
                         recipes.runtime_for(config).source_input(config, self.manifest, self.settings["top_module"]))

    def test_absent_null_and_explicit_mixed_keep_original_projection(self):
        for physical in (None, {"version": "mixed-v1"}):
            design = {**self.design, "physical_design": physical}
            self.assertEqual(recipes.effective_configuration(self.base, design, ROOT),
                             v1.effective_configuration(self.base, design, ROOT))
        design = copy.deepcopy(self.design)
        design.pop("physical_design")
        self.assertEqual(recipes.effective_configuration(self.base, design, ROOT), self.base)
        self.assertIsNone(recipes.recipe_for(self.base))
        self.assertFalse(recipes.is_block_configuration(self.base))

    def test_unknown_block_recipe_fails_closed_in_all_dispatch_entries(self):
        invalid = copy.deepcopy(self.base)
        invalid["profile"]["profile_version"] = "hullcirq-sky130-block-regions-v999"
        calls = (lambda: recipes.recipe_for(invalid), lambda: recipes.is_block_configuration(invalid),
                 lambda: recipes.runtime_for(invalid), lambda: recipes.source_input(invalid, self.manifest, "top"),
                 lambda: recipes.effective_configuration(invalid, self.design, ROOT),
                 lambda: tools.configuration_projection(self.settings, invalid, self.manifest),
                 lambda: tools.fixed_commands(invalid, Path(invalid["working_directory"]) / "hullcirq-layout-test"))
        for call in calls:
            with self.subTest(call=call), self.assertRaises(DomainError) as error:
                call()
            self.assertEqual(error.exception.code, "block_region_recipe_unsupported")

    def test_each_saved_profile_projects_its_own_exact_config_and_command(self):
        for recipe in (recipes.V1, recipes.V2):
            with self.subTest(recipe=recipe.profile_version):
                config = self.configuration(recipe)
                expected = copy.deepcopy(config["profile"]["config"])
                expected.update(DESIGN_NAME=self.settings["top_module"],
                                VERILOG_FILES=["dir::candidate_top.v", "dir::npu2-pe.v"],
                                CLOCK_PORT="clk", CLOCK_PERIOD=50,
                                PNR_SDC_FILE="dir::physical.sdc", SIGNOFF_SDC_FILE="dir::physical.sdc",
                                CORE_AREA=self.plan["core_um"], DIE_AREA=[0, 0, 120, 120],
                                HULLCIRQ_BLOCK_INPUT="dir::block-input.json")
                self.assertEqual(tools.configuration_projection(self.settings, config, self.manifest), expected)
                folder = Path(config["working_directory"]) / "hullcirq-layout-test"
                command = tools.fixed_commands(config, folder)[1]
                self.assertIn(recipe.flow, command)
                self.assertIn(_wsl_path(folder / recipe.launcher), command)
                self.assertNotIn("--with-initial-state", command)
                for path, expected_hash in ((ROOT / "scripts" / recipe.launcher, recipe.flow_sha256),
                                            (ROOT / "src/hullcirq" / recipe.runtime_file, recipe.runtime_sha256),
                                            (ROOT / "configs" / recipe.profile_file, recipe.profile_sha256)):
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected_hash)

    def test_changed_profile_or_runtime_is_rejected_without_changing_v1_pins(self):
        self.assertEqual(tools.BLOCK_FLOW_SHA, recipes.V1.flow_sha256)
        self.assertEqual(tools.BLOCK_RUNTIME_SHA, recipes.V1.runtime_sha256)
        for recipe in (recipes.V1, recipes.V2):
            config = self.configuration(recipe)
            config["profile"]["config"]["FP_CORE_UTIL"] = 99
            with self.subTest(recipe=recipe.profile_version), self.assertRaises(DomainError):
                tools.configuration_projection(self.settings, config, self.manifest)
            config = self.configuration(recipe)
            with patch.object(tools, "sha", return_value="0" * 64), self.assertRaises(DomainError) as error:
                tools.configuration_projection(self.settings, config, self.manifest)
            self.assertEqual(error.exception.code, "block_region_recipe_changed")

    def test_old_non_grid_v1_failure_reconstructs_exact_but_fresh_input_is_blocked(self):
        self.plan["regions"][0]["rect_um"][0] += 0.001
        saved = self.configuration(recipes.V1)
        before = copy.deepcopy(saved)
        projected = tools.configuration_projection(self.settings, saved, self.manifest)
        self.assertEqual(projected["CORE_AREA"], self.plan["core_um"])
        self.assertEqual(recipes.source_input(saved, self.manifest, self.settings["top_module"])["plan"], self.plan)
        self.assertEqual(saved, before)
        with self.assertRaises(DomainError) as error:
            tools.effective_configuration(self.base, self.design, ROOT)
        self.assertEqual(error.exception.code, "block_region_coordinate_grid")

    def test_failed_runs_retain_selected_launcher_and_same_eight_artifact_ids(self):
        with tempfile.TemporaryDirectory(prefix="block-recipe-qa-", dir=ROOT / ".work") as temp:
            for recipe in (recipes.V1, recipes.V2):
                with self.subTest(recipe=recipe.profile_version):
                    folder = Path(temp) / recipe.profile_version
                    folder.mkdir()
                    for filename in ("block-input.json", "block-plan.json", "block-synthesis.json", "block-ownership.json",
                                     "block-region-capacity.json", "block-placement-proof.json"):
                        (folder / filename).write_text("{}\n", encoding="utf-8")
                    (folder / recipe.launcher).write_bytes((ROOT / "scripts" / recipe.launcher).read_bytes())
                    (folder / "block_layout_runtime.py").write_bytes((ROOT / "src/hullcirq" / recipe.runtime_file).read_bytes())
                    result = {"placement_mode": v1.VERSION, "artifacts_directory": str(folder), "artifacts": [],
                              "source_bundle": [{"file": "candidate_top.v"}, {"file": "npu2-pe.v"}]}
                    tools._retain_available(result, self.manifest, self.configuration(recipe))
                    entries = {entry["id"]: entry for entry in result["artifacts"]}
                    self.assertEqual(set(entries), v1.BLOCK_ARTIFACTS)
                    self.assertEqual(entries["block-flow"]["relative_path"], recipe.launcher)
                    self.assertEqual(entries["block-flow"]["sha256"], recipe.flow_sha256)
                    self.assertEqual(entries["block-runtime"]["sha256"], recipe.runtime_sha256)
                    self.assertTrue(v1.BLOCK_ARTIFACTS <= _file_ids(result))
                    self.assertTrue(v1.BLOCK_ARTIFACTS <= _required_files(result))

    def test_checks_rebuild_with_selected_runtime_not_latest(self):
        for recipe in (recipes.V1, recipes.V2):
            config = self.configuration(recipe)
            selected = recipes.runtime_for(config)
            runtime_inputs = recipes.source_input(config, self.manifest, self.settings["top_module"])
            ownership = selected.build_ownership(self.synthesis, runtime_inputs)
            proof = {"cells": [cell for region in ownership["regions"] for cell in region["cells"]]}
            values = {"block-input": runtime_inputs, "block-plan": self.plan,
                      "block-synthesis": self.synthesis, "block-ownership": ownership,
                      "block-placement-proof": proof, "block-capacity": {}}
            paths = {name: Path(name) for name in (*values, "def")}
            with patch.object(tools, "load", side_effect=lambda p: values[str(p)]), \
                    patch.object(Path, "read_text", return_value="fixture DEF"), \
                    patch.object(selected, "validate_capacity") as capacity, \
                    patch.object(selected, "validate_placement") as placement, \
                    patch.object(selected, "validate_def_binding") as definition:
                checks = tools._block_region_checks(config, self.manifest, self.settings, paths)
            capacity.assert_called_once_with(ownership, {})
            placement.assert_called_once_with(ownership, proof)
            definition.assert_called_once_with("fixture DEF", ownership, proof)
            self.assertEqual(checks["mapped_cells"], 4)
            self.assertEqual(checks["ownership_origin"], ownership["ownership_origin"])


if __name__ == "__main__":
    unittest.main()
