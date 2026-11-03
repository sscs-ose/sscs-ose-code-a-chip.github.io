"""Pure/mocked generic cycle QA; no DUT, model, EDA or live project run."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
from hullcirq import generic_verification as generic
from hullcirq import verification
from hullcirq.domain import DomainError, revision_hashes
from hullcirq.context import node_fingerprint, physical_interface
from hullcirq.implementation_specs import build_node_implementation_spec


def interface(active="high", period=50):
    return {"module_name": "CedarCore", "ports": [
        {"name": "tick", "direction": "input", "width": 1, "signed": False},
        {"name": "clear_n", "direction": "input", "width": 1, "signed": False},
        {"name": "operand", "direction": "input", "width": 8, "signed": True},
        {"name": "enable", "direction": "input", "width": 1, "signed": False},
        {"name": "result", "direction": "output", "width": 9, "signed": True},
        {"name": "done", "direction": "output", "width": 1, "signed": False}],
        "clock": {"port": "tick", "period_ns": period},
        "reset": {"port": "clear_n", "active": active, "kind": "synchronous"}}


def contract():
    return {"kind": generic.KIND, "version": 1, "cycles": [
        {"reset": 1, "drive": {"operand": 0, "enable": 0}, "expect": {"result": 0, "done": 0}},
        {"reset": 0, "drive": {"operand": -7, "enable": 1}, "expect": {"result": -14, "done": 1}},
        {"reset": 0, "drive": {"operand": 12, "enable": 1}, "expect": {"result": 24, "done": 1}}]}


def runtime(plan):
    ports = {p["name"]: p for p in plan["interface"]["ports"]}
    lines = [f"HULLCIRQ_CYCLE cycle={index} signal={name} value={generic.exact_integer(value) & ((1 << ports[name]['width'])-1):x}"
             for index, cycle in enumerate(plan["contract"]["cycles"]) for name, value in cycle["expect"].items()]
    return "\n".join(lines + [f"HULLCIRQ_PASS vectors={plan['vector_count']} vector_hash={plan['vector_hash']}"]) + "\n"


class GenericCyclePlanTests(unittest.TestCase):
    def test_arbitrary_names_multiport_signed_values_and_exact_rebuild(self):
        plan = generic.build_cycle_plan(interface(), contract(), "arbitrary-block")
        generic.validate_cycle_plan(plan)
        verification.validate_plan(plan)
        self.assertEqual(verification.verification_template_version(plan), generic.TEMPLATE)
        self.assertEqual(plan["testbench_module"], "__hullcirq_contract_tb")
        self.assertEqual(plan["dut_instance"], "dut")
        self.assertEqual(plan["vector_count"], 3)
        self.assertEqual(plan["coverage"]["output_assertions"], 6)
        self.assertIn("9'h1f2", plan["testbench"])
        self.assertIn("!==", plan["testbench"])
        self.assertEqual(plan["public_boundary_vector_hash"], plan["vector_hash"])

    def test_low_reset_and_original_period_are_preserved_in_tb(self):
        plan = generic.build_cycle_plan(interface("low", 12.5), contract())
        self.assertEqual(plan["stimulus_timing"]["period_ps"], 12500)
        self.assertEqual(plan["stimulus_timing"]["half_period_ps"], 6250)
        self.assertEqual(plan["stimulus_timing"]["sample_after_rising_ps"], 1000)
        self.assertIn("hc_p1=1'b0;", plan["testbench"])
        self.assertIn("hc_p1=1'b1;", plan["testbench"])
        self.assertEqual(generic.parse_cycle_runtime(runtime(plan), plan)["validation_status"], "Passed")

    def test_missing_extra_unknown_bool_and_out_of_range_values_fail_closed(self):
        changes = [lambda c: c["cycles"][1]["expect"].pop("done"),
                   lambda c: c["cycles"][1]["drive"].pop("operand"),
                   lambda c: c["cycles"][1]["expect"].update(extra=0),
                   lambda c: c["cycles"][1]["expect"].update(result="x"),
                   lambda c: c["cycles"][1]["expect"].update(done=True),
                   lambda c: c["cycles"][1]["drive"].update(operand=128),
                   lambda c: c["cycles"][1]["expect"].update(result=-257),
                   lambda c: c.update(python="return DUT.output"),
                   lambda c: c.update(version=True)]
        for change in changes:
            value = contract()
            change(value)
            with self.subTest(change=change), self.assertRaises(DomainError):
                generic.build_cycle_plan(interface(), value)

    def test_reset_only_constant_drive_or_first_nonreset_are_rejected(self):
        for mode in ("first", "reset_only", "constant"):
            value = contract()
            if mode == "first": value["cycles"][0]["reset"] = 0
            elif mode == "reset_only":
                for row in value["cycles"]: row["reset"] = 1
            else:
                for row in value["cycles"]: row["drive"] = {"operand": 0, "enable": 0}
            with self.subTest(mode=mode), self.assertRaises(DomainError):
                generic.build_cycle_plan(interface(), value)

    def test_invalid_interface_clock_grid_and_injection_names_reject(self):
        for period in (True, float("nan"), float("inf"), 0, 0.003, 1.0001):
            with self.subTest(period=period), self.assertRaises(DomainError):
                generic.build_cycle_plan(interface(period=period), contract())
        value = interface()
        value["module_name"] = "injected; $finish"
        with self.assertRaises(DomainError): generic.build_cycle_plan(value, contract())
        value = interface()
        value["reset"]["kind"] = "asynchronous"
        with self.assertRaises(DomainError): generic.build_cycle_plan(value, contract())

    def test_json_key_order_does_not_change_frozen_testbench(self):
        original = contract()
        reordered = copy.deepcopy(original)
        for row in reordered["cycles"]:
            row["drive"] = dict(reversed(list(row["drive"].items())))
            row["expect"] = dict(reversed(list(row["expect"].items())))
        self.assertEqual(generic.build_cycle_plan(interface(), original), generic.build_cycle_plan(interface(), reordered))

    def test_tampering_with_expect_interface_timing_or_testbench_rejects(self):
        plan = generic.build_cycle_plan(interface(), contract())
        for field in ("testbench", "vector_hash", "reference_trace_hash"):
            value = copy.deepcopy(plan)
            value[field] = "changed"
            with self.subTest(field=field), self.assertRaises(DomainError): generic.validate_cycle_plan(value)
        value = copy.deepcopy(plan)
        value["contract"]["cycles"][1]["expect"]["result"] = 0
        with self.assertRaises(DomainError): generic.validate_cycle_plan(value)

    def test_complete_actual_samples_pass_missing_duplicate_xz_wrong_order_fail(self):
        plan = generic.build_cycle_plan(interface(), contract())
        good = runtime(plan)
        result = generic.parse_cycle_runtime(good, plan)
        self.assertEqual(result["validation_status"], "Passed")
        self.assertEqual(result["checked_output_samples"], 6)
        self.assertEqual(len(result["records"]), 6)
        lines = good.splitlines()
        variants = ["\n".join(lines[1:]), good + lines[0] + "\n", good.replace("value=1f2", "value=xxx"),
                    good.replace("value=1f2", "value=000"), "\n".join([lines[1], lines[0], *lines[2:]]),
                    good + "HULLCIRQ_FAIL explicit\n", good + lines[-1] + "\n", lines[-1] + "\n"]
        for value in variants:
            with self.subTest(value=value[:40]):
                self.assertEqual(generic.parse_cycle_runtime(value, plan)["validation_status"], "Failed")

    def test_asserted_trace_and_coverage_are_finite_saved_requirements(self):
        plan = generic.build_cycle_plan(interface(), contract())
        trace = generic.cycle_asserted_trace(plan)
        self.assertEqual(trace[1]["asserted_after"], {"result": -14, "done": 1})
        self.assertEqual(trace[0]["asserted_before"], {})
        self.assertEqual(sum(len(row["asserted_after"]) for row in trace), plan["coverage"]["output_assertions"])

    def test_no_clock_reset_duplicate_ports_and_empty_outputs_are_rejected(self):
        for mode in ("missing_clock", "duplicate", "no_output"):
            value = interface()
            if mode == "missing_clock": value["ports"] = value["ports"][1:]
            elif mode == "duplicate": value["ports"].append(copy.deepcopy(value["ports"][0]))
            else: value["ports"] = [p for p in value["ports"] if p["direction"] != "output"]
            with self.subTest(mode=mode), self.assertRaises(DomainError): generic.build_cycle_plan(value, contract())

    def test_wide_decimal_strings_preserve_encoding_and_exact_hash_oracle(self):
        i = interface()
        i["ports"][2].update(width=64, signed=False)
        i["ports"][4].update(width=64, signed=True)
        c = contract()
        c["cycles"][1]["drive"]["operand"] = "18446744073709551615"
        c["cycles"][1]["expect"]["result"] = "-9223372036854775808"
        plan = generic.build_cycle_plan(i, c)
        self.assertEqual(plan["contract"]["cycles"][1]["drive"]["operand"], "18446744073709551615")
        self.assertEqual(plan["public_boundary_vectors"][1]["expect"]["result"], "-9223372036854775808")
        self.assertIn("64'hffffffffffffffff", plan["testbench"])
        self.assertIn("64'h8000000000000000", plan["testbench"])
        generic.validate_cycle_plan(plan)
        self.assertEqual(generic.parse_cycle_runtime(runtime(plan), plan)["validation_status"], "Passed")

    def test_noncanonical_decimal_strings_and_encoding_only_variation_reject(self):
        for text in ("+1", "01", "-0", " 1", "1.0", "1e3", "0x10", "x", "z"):
            c = contract()
            c["cycles"][1]["drive"]["operand"] = text
            with self.subTest(text=text), self.assertRaises(DomainError): generic.build_cycle_plan(interface(), c)
        c = contract()
        for index, row in enumerate(c["cycles"]):
            row["drive"] = {"operand": "0" if index else 0, "enable": "0" if index else 0}
        with self.assertRaises(DomainError): generic.build_cycle_plan(interface(), c)

    def test_fixed_tool_boundary_requires_complete_actual_samples_not_pass_marker_only(self):
        plan = generic.build_cycle_plan(interface(), contract())
        def command(stdout=""):
            return {"executed": True, "status": "Completed", "exit_code": 0, "stdout": stdout, "stderr": ""}
        for stdout, expected in ((runtime(plan), "Passed"), (runtime(plan).splitlines()[-1] + "\n", "Failed")):
            with tempfile.TemporaryDirectory() as folder, patch.object(verification, "execute_fixed", side_effect=[command(), command(), command(stdout)]):
                result = verification.verify_behavior("module CedarCore(); endmodule", plan,
                    {"kind": "native", "executable": str(Path(folder) / "iverilog.exe")}, working_directory=folder)
            self.assertEqual(result["validation_status"], expected)
            self.assertEqual(result["cycle_runtime"]["validation_status"], expected)

    def test_simulator_error_fatal_diagnostics_cannot_be_hidden_by_pass_marker(self):
        plan = generic.build_cycle_plan(interface(), contract())
        good = runtime(plan)
        for diagnostic in ("ERROR: model assertion", "FATAL: rejected", "  error: bad value", "** Error: failing model", "UVM_FATAL bad", "vvp: error model"):
            with self.subTest(diagnostic=diagnostic):
                self.assertEqual(generic.parse_cycle_runtime(diagnostic + "\n" + good, plan)["validation_status"], "Failed")
                self.assertEqual(generic.parse_cycle_runtime(good, plan, diagnostic)["validation_status"], "Failed")
        self.assertEqual(generic.parse_cycle_runtime("WARNING: informational\n" + good, plan, "warning: precision")["validation_status"], "Passed")

    def test_tb_module_avoids_all_reserved_source_names_and_binds_rebuild(self):
        value = interface()
        value["module_name"] = "__hullcirq_contract_tb"
        reserved = ["__hullcirq_contract_tb_1", "__hullcirq_contract_tb_2", "AnotherModule"]
        plan = generic.build_cycle_plan(value, contract(), reserved_module_names=reserved)
        self.assertEqual(plan["testbench_module"], "__hullcirq_contract_tb_3")
        self.assertEqual(plan["reserved_module_names"], sorted([value["module_name"], *reserved]))
        self.assertIn("module __hullcirq_contract_tb_3;", plan["testbench"])
        self.assertIn("__hullcirq_contract_tb dut", plan["testbench"])
        generic.validate_cycle_plan(plan)
        changed = copy.deepcopy(plan)
        changed["reserved_module_names"].append("__hullcirq_contract_tb_3")
        with self.assertRaises(DomainError): generic.validate_cycle_plan(changed)


class GenericNodeAndSpecTests(unittest.TestCase):
    def design(self, node_id="cedar-node"):
        design = json.loads((ROOT / "examples/npu_2x2_explicit_project.json").read_text(encoding="utf-8"))
        node = copy.deepcopy(next(n for n in design["nodes"] if n["id"] == "npu2-pe00"))
        node.update(id=node_id, module_name="CedarElement")
        design["nodes"], design["edges"] = [node], []
        node["verification"] = {"kind": generic.KIND, "version": 1, "cycles": [
            {"reset": 1, "drive": {"pair": 0, "pair_valid": 0, "sum_ready": 0}, "expect": {"pair_ready": 0, "sum": 0, "sum_valid": 0}},
            {"reset": 0, "drive": {"pair": 1, "pair_valid": 1, "sum_ready": 1}, "expect": {"pair_ready": 1, "sum": -7, "sum_valid": 1}}]}
        # Use the actual physical boundary's saved names, not a node-id adapter.
        expanded = physical_interface(design, node)
        ins = [p for p in expanded["ports"] if p["direction"] == "input" and p["role"] not in ("clock", "reset")]
        outs = [p for p in expanded["ports"] if p["direction"] == "output"]
        node["verification"]["cycles"] = [{"reset": reset,
            "drive": {p["name"]: 0 if reset else 1 for p in ins},
            "expect": {p["name"]: 0 if reset else 1 for p in outs}} for reset in (1, 0)]
        return design, node

    def test_explicit_generic_kind_precedes_legacy_node_id_gate_and_shared_array(self):
        for node_id in ("cedar-node", "npu2-pe"):
            design, node = self.design(node_id)
            node["instance_array"] = {"rows": 2, "columns": 2}
            plan = verification.build_verification_plan(design, node_id)
            self.assertEqual(plan["kind"], generic.KIND)
            self.assertEqual(plan["module_name"], "CedarElement")
            generic.validate_cycle_plan(plan)

    def test_s06_rebuild_changes_when_saved_expectations_or_period_change(self):
        design, node = self.design()
        plan = verification.build_verification_plan(design, node["id"])
        node["verification"]["cycles"][1]["expect"][plan["signal_checks"][0]] = 0
        self.assertNotEqual(plan, verification.build_verification_plan(design, node["id"]))

    def test_s06_current_guard_rebuilds_generic_contract_and_checks_pure_cache(self):
        from hullcirq.workflow import ensure_current_verification_plan
        design, node = self.design()
        plan = verification.build_verification_plan(design, node["id"])
        ensure_current_verification_plan(design, node["id"], plan)
        cache = {}
        ensure_current_verification_plan(design, node["id"], plan, rebuilt_plans=cache)
        self.assertEqual(list(cache.values()), [plan])
        changed = copy.deepcopy(design)
        changed["nodes"][0]["verification"]["cycles"][1]["expect"][plan["signal_checks"][0]] = 0
        with self.assertRaises(DomainError): ensure_current_verification_plan(changed, node["id"], plan)
        wrong = verification.build_verification_plan(changed, node["id"])
        with self.assertRaises(DomainError):
            ensure_current_verification_plan(design, node["id"], plan,
                rebuilt_plans={(node["id"], generic.TEMPLATE): wrong})

    def fixture_chain(self):
        design, node = self.design()
        plan = verification.build_verification_plan(design, node["id"])
        i = physical_interface(design, node)
        decl = []
        for p in i["ports"]:
            decl.append(p["direction"] + (" signed" if p["signed"] else "") +
                        (" [" + str(p["width"]-1) + ":0]" if p["width"] > 1 else "") + " " + p["name"])
        rtl = "module " + i["module_name"] + "(" + ",".join(decl) + "); endmodule\n"
        sha = verification.content_hash(rtl)
        fingerprint = node_fingerprint(design, node["id"])
        candidate = {"id": "fixture-candidate", "node_id": node["id"], "revision_id": "fixture-revision",
                     "execution_status": "Completed", "validation_status": "Passed", "rtl": rtl, "rtl_sha256": sha,
                     "input_hash": fingerprint, "checks": {"interface": {"validation_status": "Passed"}}}
        base = {"workflow_scope_version": "stage-boundary-v2", "execution_status": "Completed", "validation_status": "Passed",
                "candidate_id": candidate["id"], "node_id": node["id"], "revision_id": candidate["revision_id"],
                "input_hash": fingerprint, "design_hash": revision_hashes(design)["semantic_hash"], "rtl_sha256": sha,
                "module_name": i["module_name"], "netlist": rtl, "netlist_sha256": sha}
        synthesis = {**base, "id": "fixture-synthesis", "stage_id": "local_synthesis", "verification_plan": None,
                     "vector_hash": None, "testbench_sha256": None, "checks": {"validation_status": "Passed", "executed": True, "exit_code": 0,
                     "rtl_sha256": sha, "netlist_sha256": sha, "netlist": rtl, "scope": "generic_technology_independent_no_pdk_no_delay"}}
        stdout = runtime(plan)
        simulation = {**base, "id": "fixture-simulation", "stage_id": "local_netlist_simulation", "prior_run_id": synthesis["id"],
                      "verification_plan": plan, "vector_hash": plan["vector_hash"], "testbench_sha256": plan["testbench_sha256"],
                      "checks": {"validation_status": "Passed", "executed": True, "exit_code": 0, "stdout": stdout,
                      "rtl_sha256": sha, **{key: plan[key] for key in ("vector_hash", "testbench_sha256", "reference_trace_hash", "vector_count", "coverage")},
                      "commands": [{"executed": True, "status": "Completed", "exit_code": 0, "stdout": stdout if n==2 else ""} for n in range(3)]}}
        for run in (synthesis, simulation): run["record_hash"] = verification.object_hash(run)
        return design, candidate, synthesis, simulation

    def test_s07_generic_trace_retains_all_output_checks_and_no_npu_claim(self):
        spec = build_node_implementation_spec(*self.fixture_chain())
        self.assertEqual(spec["checks"]["validation_status"], "Passed")
        self.assertEqual(spec["observed_facts"]["checked_assertion_count"], 6)
        self.assertEqual(spec["observed_facts"]["trace"][0]["asserted_before"], {})
        self.assertTrue(any("saved node cycle vectors" in s for s in spec["unverified_limits"]))
        self.assertFalse(any("16-PE" in s for s in spec["unverified_limits"]))

    def test_s07_cannot_accept_pass_marker_without_required_actual_samples(self):
        data = self.fixture_chain()
        simulation = data[3]
        text = simulation["checks"]["stdout"].splitlines()[-1] + "\n"
        simulation["checks"]["stdout"] = text
        simulation["checks"]["commands"][-1]["stdout"] = text
        simulation.pop("record_hash")
        simulation["record_hash"] = verification.object_hash(simulation)
        with self.assertRaises(DomainError) as caught: build_node_implementation_spec(*data)
        self.assertEqual(caught.exception.code, "simulation_cycle_samples_missing")


if __name__ == "__main__":
    unittest.main()
