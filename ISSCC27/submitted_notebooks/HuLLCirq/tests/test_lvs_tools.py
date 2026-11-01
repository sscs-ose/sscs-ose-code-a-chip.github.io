"""Isolated LVS adapter QA. All small circuit texts are declared software fixtures.

These fixtures exercise rejection and provenance rules. They never execute EDA
or replace the original GUI NPU inputs used by the actual demonstration.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq import lvs_tools as lvs
from hullcirq.domain import DomainError
from hullcirq.verification import object_hash, _wsl_path
import test_physical_tools as physical_fixtures


LOGICAL = """module software_qa_top (a, z);
input a;
output z;
wire n;
assign n = a;
sky130_fd_sc_hd__buf_1 u0 (.A(n), .X(z));
endmodule
"""
POWERED = """module software_qa_top (a, z, VPWR, VGND);
input a;
output z;
wire n;
inout VPWR;
inout VGND;
wire VPWR;
wire VGND;
assign n = a;
sky130_fd_sc_hd__buf_1 u0 (.A(n), .X(z), .VPWR(VPWR), .VGND(VGND), .VPB(VPWR), .VNB(VGND));
sky130_fd_sc_hd__fill_1 fill0 (.VPWR(VPWR), .VGND(VGND), .VPB(VPWR), .VNB(VGND));
endmodule
"""
DEF = """VERSION 5.8 ;
DESIGN software_qa_top ;
COMPONENTS 2 ;
- u0 sky130_fd_sc_hd__buf_1 + PLACED ( 0 0 ) N ;
- fill0 sky130_fd_sc_hd__fill_1 + PLACED ( 1 0 ) N ;
END COMPONENTS
END DESIGN
"""


class LvsBindingTests(unittest.TestCase):
    def bind(self, logical=LOGICAL, powered=POWERED, definition=DEF, top="software_qa_top"):
        return lvs.bind_powered_netlist(logical, powered, definition, top)

    def test_saved_powered_companion_requires_complete_signal_and_def_correspondence(self):
        summary = self.bind()
        self.assertEqual(summary["validation_status"], "Passed")
        self.assertEqual(summary["logical_instances"], 1)
        self.assertEqual(summary["powered_instances"], 2)
        self.assertEqual(summary["power_only_physical_instances"], 1)
        self.assertEqual(summary["signal_pin_connections"], 2)
        self.assertEqual(summary["supply_pin_bindings"], {"VPWR": "VPWR", "VPB": "VPWR", "VGND": "VGND", "VNB": "VGND"})

    def test_wrong_top_or_reordered_signal_ports_cannot_be_bound(self):
        for powered, top in ((POWERED, "another_top"), (POWERED.replace("(a, z, VPWR, VGND)", "(z, a, VPWR, VGND)"), "software_qa_top"), (POWERED.replace("software_qa_top", "other_top"), "software_qa_top")):
            with self.subTest(top=top), self.assertRaises(DomainError):
                self.bind(powered=powered, top=top)

    def test_changed_signal_connection_declaration_assignment_or_cell_rejected(self):
        changes = [(".A(n)", ".A(a)"), ("wire n;", "wire other;"), ("assign n = a;", "assign n = z;"), ("__buf_1 u0", "__inv_1 u0")]
        for old, new in changes:
            with self.subTest(change=(old, new)), self.assertRaises(DomainError):
                self.bind(powered=POWERED.replace(old, new))

    def test_missing_reversed_or_rewired_supply_and_well_pins_rejected(self):
        changes = [(".VPB(VPWR)", ".VPB(VGND)"), (".VNB(VGND)", ".VNB(VPWR)"), (", .VPB(VPWR)", ""), (".VPWR(VPWR)", ".VPWR(n)")]
        for old, new in changes:
            with self.subTest(change=(old, new)), self.assertRaises(DomainError):
                self.bind(powered=POWERED.replace(old, new, 1))

    def test_def_missing_extra_duplicate_count_or_changed_master_rejected(self):
        variants = [DEF.replace("COMPONENTS 2", "COMPONENTS 1"), DEF.replace("- fill0", "- ghost"), DEF.replace("- fill0", "- u0"), DEF.replace("__buf_1 +", "__inv_1 +"), DEF.replace("DESIGN software_qa_top", "DESIGN other_top")]
        for definition in variants:
            with self.subTest(definition=definition), self.assertRaises(DomainError):
                self.bind(definition=definition)

    def test_only_def_backed_power_only_physical_cells_may_extend_the_signal_graph(self):
        for powered, definition in ((POWERED.replace("__fill_1 fill0", "__buf_1 fill0"), DEF.replace("__fill_1 +", "__buf_1 +")), (POWERED.replace("__fill_1 fill0 (", "__fill_1 fill0 (.A(a), "), DEF)):
            with self.subTest(powered=powered), self.assertRaises(DomainError):
                self.bind(powered=powered, definition=definition)

    def test_unrecognized_or_incomplete_flat_netlist_is_never_silently_skipped(self):
        variants = [LOGICAL + "endmodule", LOGICAL.replace("wire n;", "// ignored signal\nwire n;"), LOGICAL.replace("wire n;", "/* ignored signal */wire n;"), LOGICAL.replace(".A(n)", ".A(n), .A(a)"), LOGICAL.replace(".A(n)", "n"), LOGICAL.replace("sky130_fd_sc_hd__buf_1 u0 (.A(n), .X(z));", ""), LOGICAL.replace("sky130_fd_sc_hd__buf_1 u0", "mystery token extra u0")]
        for logical in variants:
            with self.subTest(logical=logical), self.assertRaises(DomainError):
                self.bind(logical=logical)

    def test_escaped_instance_names_preserve_the_same_def_identity(self):
        summary = self.bind(logical=LOGICAL.replace(" u0 ", " \\nested.u0 "), powered=POWERED.replace(" u0 ", " \\nested.u0 "), definition=DEF.replace("- u0 ", "- nested.u0 "))
        self.assertEqual(summary["logical_instances"], 1)

    def test_signal_netlist_may_already_contain_every_physical_cell_with_empty_pins(self):
        logical = LOGICAL.replace("endmodule", "sky130_fd_sc_hd__fill_1 fill0 ();\nendmodule")
        summary = self.bind(logical=logical)
        self.assertEqual(summary["logical_instances"], 2)
        self.assertEqual(summary["powered_instances"], 2)
        self.assertEqual(summary["power_only_physical_instances"], 1)
        self.assertEqual(summary["signal_pin_connections"], 2)

    def test_recorded_tap_cell_two_supply_pins_are_valid_with_original_empty_pin_instance(self):
        logical = LOGICAL.replace("endmodule", "sky130_fd_sc_hd__tapvpwrvgnd_1 fill0 ();\nendmodule")
        powered = POWERED.replace("sky130_fd_sc_hd__fill_1 fill0 (.VPWR(VPWR), .VGND(VGND), .VPB(VPWR), .VNB(VGND));", "sky130_fd_sc_hd__tapvpwrvgnd_1 fill0 (.VPWR(VPWR), .VGND(VGND));")
        definition = DEF.replace("__fill_1", "__tapvpwrvgnd_1")
        summary = self.bind(logical=logical, powered=powered, definition=definition)
        self.assertEqual(summary["logical_instances"], 2)
        self.assertEqual(summary["tap_cell_supply_pins"], {"VPWR": "VPWR", "VGND": "VGND"})
        for wrong in (powered.replace("fill0 (.VPWR(VPWR)", "fill0 (.VPWR(VGND)"), powered.replace("fill0 (.VPWR(VPWR), .VGND(VGND))", "fill0 (.VPWR(VPWR))"), powered.replace("fill0 (.VPWR(VPWR), .VGND(VGND))", "fill0 (.VPWR(VPWR), .VGND(VGND), .A(a))")):
            with self.subTest(powered=wrong), self.assertRaises(DomainError):
                self.bind(logical=logical, powered=wrong, definition=definition)

    def test_count_missing_bool_fraction_negative_string_and_nonfinite_rejected(self):
        self.assertEqual(lvs._count(0), 0); self.assertEqual(lvs._count(7), 7)
        for value in (None, False, True, 0.0, 0.5, -1, "0", float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), self.assertRaises(DomainError):
                lvs._count(value)


class LvsSavedSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hullcirq-lvs-source-software-qa-")
        self.addCleanup(self.temp.cleanup); self.folder = Path(self.temp.name)
        files = {"gds": ("saved.gds", b"SOFTWARE QA ONLY: not real GDS"), "def": ("saved.def", DEF.encode()), "netlist": ("saved.nl.v", LOGICAL.encode())}
        (self.folder / "saved.pnl.v").write_text(POWERED, encoding="utf-8", newline="\n")
        pointers = {"gds": str(self.folder / "saved.gds"), "def": str(self.folder / "saved.def"), "nl": str(self.folder / "saved.nl.v"), "pnl": str(self.folder / "saved.pnl.v")}
        files["final-state"] = ("state.json", json.dumps(pointers).encode())
        entries = []
        for identifier, (name, raw) in files.items():
            (self.folder / name).write_bytes(raw)
            entries.append({"id": identifier, "relative_path": name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "content_type": "application/octet-stream"})
        self.layout = {"settings": {"top_module": "software_qa_top"}, "checks": {"artifacts_directory": str(self.folder), "artifacts": entries}}

    def test_original_source_bytes_immutable_and_powered_hash_is_new_s13_observation(self):
        before = copy.deepcopy(self.layout); original = {p.name: p.read_bytes() for p in self.folder.iterdir()}
        result = lvs.source_inputs(self.layout)
        self.assertEqual(set(result), {"gds", "def", "netlist", "powered_netlist"})
        self.assertEqual(result["powered_netlist"]["origin"], "original_S11_state_pointer_observed_at_S13_start")
        self.assertEqual(result["powered_netlist"]["sha256"], hashlib.sha256(original["saved.pnl.v"]).hexdigest())
        self.assertEqual(result["powered_netlist"]["binding"]["validation_status"], "Passed")
        self.assertEqual(self.layout, before); self.assertEqual({p.name: p.read_bytes() for p in self.folder.iterdir()}, original)

    def test_retained_gds_def_netlist_or_state_byte_changes_rejected(self):
        for entry in self.layout["checks"]["artifacts"]:
            p = self.folder / entry["relative_path"]; old = p.read_bytes(); p.write_bytes(old + b" ")
            try:
                with self.subTest(identifier=entry["id"]), self.assertRaises(DomainError):
                    lvs.source_inputs(self.layout)
            finally:
                p.write_bytes(old)

    def test_powered_pointer_and_adopted_gds_pointer_cannot_escape_or_retarget(self):
        for key, destination in (("pnl", str(self.folder.parent / "outside.pnl.v")), ("gds", str(self.folder / "saved.pnl.v"))):
            p = self.folder / "state.json"; old = p.read_bytes(); state = json.loads(old); state[key] = destination; raw = json.dumps(state).encode(); p.write_bytes(raw)
            altered = copy.deepcopy(self.layout); e = next(item for item in altered["checks"]["artifacts"] if item["id"] == "final-state"); e.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            try:
                with self.subTest(key=key), self.assertRaises(DomainError):
                    lvs.source_inputs(altered)
            finally:
                p.write_bytes(old)


class LvsRecipeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hullcirq-lvs-recipe-software-qa-")
        self.addCleanup(self.temp.cleanup); self.folder = Path(self.temp.name)
        prior = physical_fixtures.PhysicalToolTests(); prior.setUp()
        prior.config["pdk_root"] = str(self.folder / "software-qa-pdk")
        self.layout = {"id": "software-qa-layout", "settings": prior.settings, "runtime_configuration": prior.config}
        self.drc = {"layout_snapshot": copy.deepcopy(self.layout), "layout_record_sha256": object_hash(self.layout)}
        self.config = {"physical_runtime": copy.deepcopy(prior.config), "working_directory": str(self.folder), "profile": json.loads((ROOT / "configs/lvs_profile_sky130.json").read_text(encoding="utf-8"))}

    def test_recipe_extracts_gds_and_compares_without_rtl_generation_or_physical_rerun(self):
        originals = copy.deepcopy((self.layout, self.drc, self.config))
        projected = lvs.configuration_projection(self.drc, self.layout, self.config)
        self.assertEqual(projected["meta"]["flow"], ["Magic.SpiceExtraction", "Netgen.LVS"])
        self.assertTrue(projected["MAGIC_EXT_USE_GDS"]); self.assertFalse(projected["MAGIC_EXT_ABSTRACT"])
        self.assertIsNone(projected["MAGIC_EXT_ABSTRACT_CELLS"]); self.assertIsNone(projected["LVS_IGNORE_CELLS"])
        self.assertNotIn("VERILOG_FILES", projected)
        self.assertEqual((self.layout, self.drc, self.config), originals)

    def test_extracted_spice_path_is_safely_derived_from_saved_layout_top(self):
        # The historical top preserves its exact frozen artifact table.
        self.assertEqual(lvs._fixed_files(self.layout),lvs.FIXED_FILES)
        explicit=copy.deepcopy(self.layout);explicit['settings']['top_module']='hullcirq_npu2_top'
        files=lvs._fixed_files(explicit)
        self.assertEqual(files['extracted-spice'],'runs/lvs/1-magic-spiceextraction/hullcirq_npu2_top.spice')
        self.assertEqual({key:value for key,value in files.items() if key!='extracted-spice'},
                         {key:value for key,value in lvs.FIXED_FILES.items() if key!='extracted-spice'})
        for top in ('../escape','nested/path','nested\\path','1top','module',''):
            changed=copy.deepcopy(explicit);changed['settings']['top_module']=top
            with self.subTest(top=top),self.assertRaises(DomainError):lvs._fixed_files(changed)

    def test_runtime_source_snapshot_hash_and_ignore_or_abstraction_changes_rejected(self):
        for what in ("runtime", "snapshot", "snapshot_hash", "ignore", "abstract"):
            drc, layout, configuration = copy.deepcopy((self.drc, self.layout, self.config))
            if what == "runtime": configuration["physical_runtime"]["pdk_revision"] = "different"
            elif what == "snapshot": drc["layout_snapshot"]["id"] = "different"
            elif what == "snapshot_hash": drc["layout_record_sha256"] = "0" * 64
            elif what == "ignore": configuration["profile"]["config"]["LVS_IGNORE_CELLS"] = ["software_qa_missing_cell"]
            else: configuration["profile"]["config"]["MAGIC_EXT_ABSTRACT"] = True
            with self.subTest(what=what), self.assertRaises(DomainError):
                lvs.configuration_projection(drc, layout, configuration)

    def test_fixed_commands_use_only_version_capture_and_the_explicit_initial_state(self):
        commands = lvs.fixed_commands(self.config, self.folder / "hullcirq-lvs-software-qa")
        self.assertEqual(len(commands), 2)
        self.assertIn("--with-initial-state", commands[1]); self.assertIn("--run-tag", commands[1])
        self.assertNotIn("Classic", commands[1]); self.assertNotIn("--from", commands[1]); self.assertNotIn("--to", commands[1])
        for destination in (self.folder / "outside", self.folder.parent / "hullcirq-lvs-outside"):
            with self.subTest(destination=destination), self.assertRaises(DomainError):
                lvs.fixed_commands(self.config, destination)

    def test_absent_runtime_is_unavailable_without_starting_eda(self):
        self.assertFalse(lvs.lvs_capability(None)["available"])
        self.assertFalse(lvs.lvs_capability(self.config)["available"])

    def test_full_extraction_v2_profile_preserves_exact_circuit_and_comparison_configuration(self):
        configuration = copy.deepcopy(self.config)
        configuration["profile"] = json.loads((ROOT / "configs/lvs_profile_sky130_v2.json").read_bytes())
        original = copy.deepcopy((self.drc, self.layout, configuration))
        projected = lvs.configuration_projection(self.drc, self.layout, configuration)
        self.assertEqual(projected, lvs.configuration_projection(self.drc, self.layout, self.config))
        self.assertTrue(configuration["profile"]["force_full_extraction"])
        self.assertEqual((self.drc, self.layout, configuration), original)
        for key in ("force_full_extraction", "variant_hash", "replacement", "ignore", "abstract"):
            changed = copy.deepcopy(configuration)
            if key == "force_full_extraction": changed["profile"][key] = False
            elif key == "variant_hash": changed["profile"]["extraction_variant"]["script_sha256"] = "0" * 64
            elif key == "replacement": changed["profile"]["extraction_variant"]["replacement"]["count"] = 2
            elif key == "ignore": changed["profile"]["config"]["LVS_IGNORE_CELLS"] = ["software_qa_ignored_cell"]
            else: changed["profile"]["config"]["MAGIC_EXT_ABSTRACT"] = True
            with self.subTest(changed=key), self.assertRaises(DomainError):
                lvs.configuration_projection(self.drc, self.layout, changed)

    def test_full_extraction_v2_fixed_command_uses_frozen_sibling_python_launcher(self):
        configuration = copy.deepcopy(self.config)
        configuration["profile"] = json.loads((ROOT / "configs/lvs_profile_sky130_v2.json").read_bytes())
        destination = self.folder / "hullcirq-lvs-software-qa"
        commands = lvs.fixed_commands(configuration, destination)
        self.assertEqual(len(commands), 2)
        argv = commands[1][commands[1].index("--exec") + 1:]
        self.assertEqual(argv[:3], [configuration["physical_runtime"]["executable"], "python3", _wsl_path(destination / "run_full_lvs.py")])
        self.assertNotIn("librelane", argv)
        self.assertEqual(argv[argv.index("--with-initial-state") + 1], _wsl_path(destination / "initial-state.json"))


class LvsFullExtractionLauncherTests(unittest.TestCase):
    """The actual CLI is replaced by an explicit software-only callback."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hullcirq-lvs-launcher-software-qa-")
        self.addCleanup(self.temp.cleanup); self.folder = Path(self.temp.name)
        self.profile = json.loads((ROOT / "configs/lvs_profile_sky130_v2.json").read_bytes())
        variant = self.profile["extraction_variant"]
        self.launcher = (ROOT / variant["launcher_path"]).read_bytes()
        self.full = (ROOT / variant["script_path"]).read_bytes()
        self.upstream = self.full.replace(b"\nextract all\n", b"\nextract\n", 1)
        self.path = self.folder / "run_full_lvs.py"; self.path.write_bytes(self.launcher)
        self.full_path = self.folder / "extract_spice_full.tcl"; self.full_path.write_bytes(self.full)
        self.upstream_path = self.folder / "upstream-extract-spice.tcl"; self.upstream_path.write_bytes(self.upstream)
        specification = importlib.util.spec_from_file_location("software_qa_full_lvs_launcher", self.path)
        self.module = importlib.util.module_from_spec(specification); specification.loader.exec_module(self.module)
        upstream_path = self.upstream_path
        self.original_method = lambda instance: str(upstream_path)
        self.extraction = type("SoftwareQaExtraction", (), {"id": "Magic.SpiceExtraction", "get_script_path": self.original_method})
        self.calls = []
        def cli(*, args):
            self.calls.append({"args": args, "script": self.extraction.get_script_path(None)})
            return 42
        magic = types.ModuleType("librelane.steps.magic"); magic.SpiceExtraction = self.extraction
        main = types.ModuleType("librelane.__main__"); main.cli = cli
        self.modules = {"librelane": types.ModuleType("librelane"), "librelane.steps": types.ModuleType("librelane.steps"), "librelane.steps.magic": magic, "librelane.__main__": main}

    def dispatch(self, release="3.0.16", arguments=None):
        with patch.dict(sys.modules, self.modules), patch.object(self.module.importlib.metadata, "version", return_value=release):
            return self.module.main(["--software-qa-only"] if arguments is None else arguments)

    def test_versioned_sources_have_exact_frozen_hashes_and_only_one_tcl_line_changes(self):
        variant = self.profile["extraction_variant"]
        for raw, key in ((self.launcher, "launcher_sha256"), (self.full, "script_sha256"), (self.upstream, "upstream_sha256")):
            self.assertEqual(hashlib.sha256(raw).hexdigest(), variant[key])
        self.assertEqual(self.upstream.count(b"\nextract\n"), 1)
        self.assertEqual(self.full, self.upstream.replace(b"\nextract\n", b"\nextract all\n", 1))
        self.assertEqual(variant["replacement"], {"from": "extract", "to": "extract all", "count": 1})

    def test_launcher_selects_only_fixed_extraction_script_and_restores_registered_step(self):
        self.assertEqual(self.dispatch(), 42)
        self.assertEqual(self.calls, [{"args": ["--software-qa-only"], "script": str(self.full_path.resolve())}])
        self.assertIs(self.extraction.get_script_path, self.original_method)

    def test_changed_release_upstream_or_full_tcl_is_rejected_before_cli_dispatch(self):
        with self.assertRaises(RuntimeError): self.dispatch(release="software-qa-wrong-release")
        for path, raw in ((self.upstream_path, self.upstream), (self.full_path, self.full)):
            path.write_bytes(raw + b"\n# SOFTWARE QA changed source\n")
            with self.subTest(path=path.name), self.assertRaises(RuntimeError): self.dispatch()
            path.write_bytes(raw)
        self.assertEqual(self.calls, [])
        self.assertIs(self.extraction.get_script_path, self.original_method)

    def test_launcher_restores_original_script_method_when_mocked_cli_fails(self):
        def rejected_cli(*, args): raise RuntimeError("SOFTWARE QA simulated CLI exception; no EDA invoked")
        self.modules["librelane.__main__"].cli = rejected_cli
        with self.assertRaisesRegex(RuntimeError, "SOFTWARE QA"):
            self.dispatch()
        self.assertIs(self.extraction.get_script_path, self.original_method)

    def variant_stdout(self, logical, **overrides):
        variant = self.profile["extraction_variant"]
        banner = {"librelane": "3.0.16", "entrypoint": "librelane.__main__.cli", "step": "Magic.SpiceExtraction", "upstream_script_sha256": variant["upstream_sha256"], "script": _wsl_path(logical / "extract_spice_full.tcl"), "script_sha256": variant["script_sha256"], "change": "extract -> extract all", "added_abstract_cells": 0, "added_ignore_rules": 0, **overrides}
        return "SOFTWARE QA ONLY: no EDA invoked\nHuLLCirq full extraction launcher: " + json.dumps(banner) + "\n"

    def test_both_fixed_variant_sources_are_identified_for_required_retention(self):
        files = lvs._variant_files(self.profile)
        self.assertEqual(set(files), {"run_full_lvs.py", "extract_spice_full.tcl"})
        for name, (source, expected) in files.items():
            self.assertEqual(source.name, name)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), expected)
        incremental = json.loads((ROOT / "configs/lvs_profile_sky130.json").read_bytes())
        self.assertEqual(lvs._variant_files(incremental), {})

    def test_portable_variant_validation_requires_original_launcher_and_tcl_bytes(self):
        logical = self.folder / "separate-logical-worker-location"
        stdout = self.variant_stdout(logical)
        lvs._validate_variant(self.profile, self.folder, logical, stdout)
        for path, original in ((self.path, self.launcher), (self.full_path, self.full)):
            path.unlink()
            with self.subTest(missing=path.name), self.assertRaises((DomainError, OSError)):
                lvs._validate_variant(self.profile, self.folder, logical, stdout)
            path.write_bytes(original + b"\n# SOFTWARE QA modified retained source\n")
            with self.subTest(changed=path.name), self.assertRaises(DomainError) as caught:
                lvs._validate_variant(self.profile, self.folder, logical, stdout)
            self.assertEqual(caught.exception.code, "lvs_runtime_conflict")
            path.write_bytes(original)
        lvs._validate_variant(self.profile, self.folder, logical, stdout)

    def test_variant_banner_requires_unique_exact_dispatch_and_logical_script_binding(self):
        logical = self.folder / "separate-logical-worker-location"
        valid = self.variant_stdout(logical)
        invalid = ["", valid + valid, "HuLLCirq full extraction launcher: {", self.variant_stdout(self.folder)]
        invalid.extend(self.variant_stdout(logical, **changes) for changes in (
            {"librelane": "software-qa-other-release"}, {"step": "Magic.SOFTWARE_QA_OTHER"},
            {"upstream_script_sha256": "0" * 64}, {"script_sha256": "0" * 64},
            {"change": "extract -> abstract"}, {"added_abstract_cells": 1}, {"added_ignore_rules": 1},
            {"added_abstract_cells": False}, {"extra_software_qa_field": True},
        ))
        for stdout in invalid:
            with self.subTest(stdout=stdout), self.assertRaises((DomainError, ValueError)):
                lvs._validate_variant(self.profile, self.folder, logical, stdout)

    def test_variant_reversal_must_reconstruct_the_exact_frozen_upstream_tcl(self):
        logical = self.folder / "separate-logical-worker-location"
        changed = copy.deepcopy(self.profile)
        changed["extraction_variant"]["upstream_sha256"] = "0" * 64
        with self.assertRaises(DomainError) as caught:
            lvs._validate_variant(changed, self.folder, logical, self.variant_stdout(logical))
        self.assertEqual(caught.exception.code, "lvs_runtime_conflict")


class LvsReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hullcirq-lvs-report-software-qa-")
        self.addCleanup(self.temp.cleanup); self.folder = Path(self.temp.name)
        self.layout = {"settings": {"top_module": "software_qa_top"}}
        self.metrics = {name: 0 for name in lvs.METRIC_NAMES.values()}
        self.metrics["magic__illegal_overlap__count"] = 0
        self.stats = [{"name": ["software_qa_top", "software_qa_top"], "nets": [2, 2], "devices": [[["software_qa_device", 1]], [["software_qa_device", 1]]], "pins": [["a", "z"], ["a", "z"]]}]
        self.report = "SOFTWARE QA ONLY: no Netgen was executed\nFinal result: Circuits match uniquely.\n"
        self.markers = "<report-database><categories/><items/></report-database>"

    def write(self, stats=None, metrics=None, report=None, markers=None):
        values = {"metrics": json.dumps(self.metrics if metrics is None else metrics), "lvs-json": json.dumps(self.stats if stats is None else stats), "lvs-report": self.report if report is None else report, "extraction-markers": self.markers if markers is None else markers}
        for identifier, raw in values.items():
            path = self.folder / lvs.FIXED_FILES[identifier]; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(raw, encoding="utf-8")

    def summary(self):
        return lvs.summarize(self.folder, self.layout)

    def test_complete_zero_metrics_empty_markers_and_explicit_top_unique_match_are_required(self):
        self.write(); summary, metrics, checks = self.summary()
        self.assertEqual(summary["lvs"]["match_status"], "Unique match")
        self.assertEqual(summary["lvs"]["comparison_count"], 1); self.assertEqual(summary["mismatches"], [])
        self.assertEqual(metrics, self.metrics)
        self.assertEqual(checks["lvs"]["validation_status"], "Passed"); self.assertEqual(checks["extraction"]["validation_status"], "Passed")

    def test_finite_mismatches_are_failed_and_all_raw_mismatch_details_remain_available(self):
        stats = copy.deepcopy(self.stats); stats[-1]["badnets"] = [{"software_qa_unmatched_net": "original_n"}]
        metrics = dict(self.metrics); metrics[lvs.METRIC_NAMES["unmatched_net_count"]] = 1; metrics[lvs.METRIC_NAMES["error_count"]] = 1
        self.write(stats=stats, metrics=metrics, report="SOFTWARE QA ONLY\nFinal result: Circuits do not match.\n")
        summary, _, checks = self.summary()
        self.assertEqual(checks["lvs"]["validation_status"], "Failed"); self.assertEqual(checks["extraction"]["validation_status"], "Passed")
        self.assertEqual(summary["mismatches"], stats)

    def test_subcircuit_property_failures_cannot_be_hidden_by_clean_top_counts(self):
        stats = [{"name": ["software_qa_child", "software_qa_child"], "properties": [{"software_qa_property": [1, 2]}]}, *copy.deepcopy(self.stats)]
        metrics = dict(self.metrics); metrics[lvs.METRIC_NAMES["property_fail_count"]] = 1; metrics[lvs.METRIC_NAMES["error_count"]] = 1
        self.write(stats=stats, metrics=metrics, report="SOFTWARE QA ONLY\nFinal result: Property errors found.\n")
        summary, _, checks = self.summary()
        self.assertEqual(checks["lvs"]["validation_status"], "Failed"); self.assertEqual(summary["mismatches"], stats[:1])

    def test_issue104_unique_match_and_zero_metrics_do_not_override_raw_property_errors(self):
        for warning in ("Property errors were found.", "The following cells had property errors:", "PROPERTY ERRORS WERE FOUND."):
            self.write(report=self.report + warning + "\nsoftware_qa_child\n")
            with self.subTest(warning=warning), self.assertRaises(DomainError) as caught:
                self.summary()
            self.assertEqual(caught.exception.code, "lvs_unreported_mismatch")

    def test_hierarchical_badnets_cannot_disappear_behind_zero_top_metrics(self):
        child = {"name": ["software_qa_child", "software_qa_child"], "badnets": [{"software_qa_unmatched_net": "child_n"}]}
        self.write(stats=[child, *copy.deepcopy(self.stats)])
        with self.assertRaises(DomainError) as caught:
            self.summary()
        self.assertEqual(caught.exception.code, "lvs_unreported_mismatch")

    def test_reported_property_error_with_nonzero_counts_remains_inspectable_failed_result(self):
        child = {"name": ["software_qa_child", "software_qa_child"], "properties": [{"software_qa_property": [1, 2]}]}
        metrics = dict(self.metrics); metrics[lvs.METRIC_NAMES["property_fail_count"]] = 1; metrics[lvs.METRIC_NAMES["error_count"]] = 1
        self.write(stats=[child, *copy.deepcopy(self.stats)], metrics=metrics, report=self.report + "Property errors were found.\nThe following cells had property errors:\nsoftware_qa_child\n")
        summary, saved_metrics, checks = self.summary()
        self.assertEqual(checks["lvs"]["validation_status"], "Failed")
        self.assertEqual(summary["lvs"]["match_status"], "Unique match")
        self.assertEqual(summary["lvs"]["property_fail_count"], 1)
        self.assertEqual(summary["mismatches"], [child]); self.assertEqual(saved_metrics, metrics)

    def test_each_final_metric_missing_invalid_or_nonfinite_is_rejected(self):
        for key in self.metrics:
            for value in (None, False, True, 0.0, -1, "0", float("nan"), float("inf")):
                metrics = dict(self.metrics); metrics[key] = value; self.write(metrics=metrics)
                with self.subTest(key=key, value=value), self.assertRaises((DomainError, ValueError)):
                    self.summary()
            metrics = dict(self.metrics); del metrics[key]; self.write(metrics=metrics)
            with self.subTest(missing=key), self.assertRaises((DomainError, ValueError)):
                self.summary()

    def test_missing_or_wrong_final_top_and_empty_comparison_lists_rejected(self):
        variants = [[], {}, [None], [{"name": ["other_top", "other_top"]}], [*self.stats, {"name": ["other_top", "other_top"]}]]
        for stats in variants:
            self.write(stats=stats)
            with self.subTest(stats=stats), self.assertRaises((DomainError, ValueError)):
                self.summary()

    def test_truncated_empty_or_invalid_net_device_and_pin_pairs_rejected(self):
        variants = [("nets", [2]), ("nets", [2, 0]), ("nets", [2, False]), ("devices", [[[]], [[]]]), ("devices", [[["software_qa_device", 1]]]), ("devices", [[["software_qa_device", 1]], []]), ("devices", [[["software_qa_device", False]], [["software_qa_device", 1]]]), ("pins", [["a", "z"]]), ("pins", [["a", "z"], ["a"]]), ("pins", [["", "z"], ["a", "z"]])]
        for key, value in variants:
            stats = copy.deepcopy(self.stats); stats[-1][key] = value; self.write(stats=stats)
            with self.subTest(key=key, value=value), self.assertRaises((DomainError, ValueError)):
                self.summary()

    def test_malformed_json_or_nonlist_mismatch_fields_rejected(self):
        self.write(); path = self.folder / lvs.FIXED_FILES["lvs-json"]
        for raw in ("[", "null", '[{"name": ["software_qa_top", "software_qa_top"]}NaN]'):
            path.write_text(raw, encoding="utf-8")
            with self.subTest(raw=raw), self.assertRaises((DomainError, ValueError)):
                self.summary()
        for key in ("badnets", "badelements", "properties"):
            stats = copy.deepcopy(self.stats); stats[-1][key] = {}; self.write(stats=stats)
            with self.subTest(key=key), self.assertRaises(DomainError):
                self.summary()

    def test_zero_counts_and_tool_exit_text_cannot_replace_explicit_final_unique_match(self):
        for report in ("SOFTWARE QA ONLY: tool exit 0\n", "Final result: Circuits do not match.\n", "Circuits match uniquely.\nFinal result: incomplete", "Final result: Circuits match uniquely.\nFinal result: incomplete"):
            self.write(report=report)
            with self.subTest(report=report), self.assertRaises(DomainError):
                self.summary()

    def test_raw_json_differences_must_match_final_metrics(self):
        for key, value in (("nets", [2, 3]), ("devices", [[["software_qa_device", 1]], [["software_qa_device", 2]]]), ("pins", [["a", "z"], ["a", "different_z"]]), ("badnets", [{"software_qa_net": "n"}])):
            stats = copy.deepcopy(self.stats); stats[-1][key] = value; self.write(stats=stats)
            with self.subTest(key=key), self.assertRaises(DomainError):
                self.summary()

    def test_illegal_overlap_markers_must_match_metrics_and_incomplete_xml_is_rejected(self):
        marker = "<report-database><categories><category><name>overlap</name><description>Illegal overlap SOFTWARE QA</description></category></categories><items><item><category>'overlap'</category><cell>software_qa_top</cell><values><value>box (1,2;3,4)</value></values></item></items></report-database>"
        self.write(markers=marker)
        with self.assertRaises(DomainError): self.summary()
        metrics = dict(self.metrics); metrics["magic__illegal_overlap__count"] = 1; self.write(metrics=metrics, markers=marker)
        _, _, checks = self.summary(); self.assertEqual(checks["extraction"]["validation_status"], "Failed")
        for raw in ("<report-database/>", "<invalid/>", "<!DOCTYPE x><report-database><categories/><items/></report-database>"):
            self.write(markers=raw)
            with self.subTest(xml=raw), self.assertRaises((DomainError, ValueError)):
                self.summary()

    def test_mixed_extraction_feedback_counts_only_exact_upstream_illegal_overlap_phrase(self):
        descriptions = ["SOFTWARE QA device missing 1 terminal; connecting remainder to node VGND", "SOFTWARE QA could not determine device boundary", "SOFTWARE QA lower-case illegal overlap remains general feedback", "SOFTWARE QA Illegal overlap in device geometry"]
        categories = "".join(f"<category><name>SOFTWARE_QA_{i}</name><description>{text}</description></category>" for i, text in enumerate(descriptions))
        items = "".join(f"<item><category>'SOFTWARE_QA_{i}'</category><cell>software_qa_top</cell><multiplicity>1</multiplicity><values><value>SOFTWARE QA geometry {i}</value></values></item>" for i in range(len(descriptions)))
        markers = f"<report-database><categories>{categories}</categories><items>{items}</items></report-database>"
        metrics = dict(self.metrics); metrics["magic__illegal_overlap__count"] = 1
        self.write(metrics=metrics, markers=markers)
        summary, saved_metrics, checks = self.summary()
        extraction = summary["extraction"]
        self.assertEqual(extraction["illegal_overlap_count"], 1)
        self.assertEqual(extraction["feedback_item_count"], 4)
        self.assertEqual(extraction["non_overlap_feedback_count"], 3)
        self.assertEqual([v["description"] for v in extraction["feedback"]], descriptions)
        self.assertEqual([v["geometry"] for v in extraction["feedback"]], [[f"SOFTWARE QA geometry {i}"] for i in range(4)])
        self.assertEqual([v["count"] for v in extraction["feedback_categories"]], [1, 1, 1, 1])
        self.assertEqual(checks["extraction"]["validation_status"], "Failed")
        self.assertEqual(checks["lvs"]["validation_status"], "Passed"); self.assertEqual(saved_metrics, metrics)
        self.assertIn("does not assert", extraction["feedback_scope"])
        self.write(markers=markers)
        with self.assertRaises(DomainError) as caught:
            self.summary()
        self.assertEqual(caught.exception.code, "lvs_overlap_conflict")

    def test_non_overlap_feedback_is_disclosed_even_when_required_connectivity_checks_pass(self):
        markers = "<report-database><categories><category><name>SOFTWARE_QA_WARNING</name><description>SOFTWARE QA device missing terminal</description></category></categories><items><item><category>'SOFTWARE_QA_WARNING'</category><cell>software_qa_top</cell><values><value>SOFTWARE QA full geometry retained</value></values></item></items></report-database>"
        self.write(markers=markers)
        summary, _, checks = self.summary()
        self.assertEqual(summary["extraction"]["illegal_overlap_count"], 0)
        self.assertEqual(summary["extraction"]["feedback_item_count"], 1)
        self.assertEqual(summary["extraction"]["non_overlap_feedback_count"], 1)
        self.assertEqual(summary["extraction"]["feedback"][0]["description"], "SOFTWARE QA device missing terminal")
        self.assertEqual(checks["extraction"]["validation_status"], "Passed")
        self.assertIn("warnings are harmless or resolved", summary["extraction"]["feedback_scope"])


if __name__ == "__main__":
    unittest.main()
