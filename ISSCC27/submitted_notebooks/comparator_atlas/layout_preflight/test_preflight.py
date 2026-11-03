import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("preflight", Path(__file__).with_name("preflight.py"))
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)

DEVICE = {"cell": "test", "model": "sky130_fd_pr__nfet_01v8_lvt", "w_um": 0.42, "l_um": 4}
ROUTE = dict(DEVICE, ports=preflight.ROUTE_PORTS, device_pins=preflight.ROUTE_DEVICE_PINS)


class EvidenceChecks(unittest.TestCase):
    def parse(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.spice"
            path.write_text(text)
            return preflight.read_spice(path)

    def branched_rc(self):
        net = self.parse(preflight.independent_reference(DEVICE))
        net["devices"][0]["pins"][0] = "device_d"
        net["resistors"] = [
            {"name": "R1", "nodes": ["D", "junction"], "value": 10},
            {"name": "R2", "nodes": ["junction", "upper"], "value": 20},
            {"name": "R3", "nodes": ["junction", "lower"], "value": 30},
            {"name": "R4", "nodes": ["upper", "device_d"], "value": 5},
            {"name": "R5", "nodes": ["lower", "device_d"], "value": 7},
        ]
        net["capacitors"] = [{"name": "C1", "nodes": ["upper", "B"], "value": 1e-15,
                              "annotation": "**FLOATING"}]
        return net

    def test_independent_reference_and_units(self):
        net = self.parse(preflight.independent_reference(DEVICE))
        self.assertEqual(preflight.check_devices(net, DEVICE)[0]["l_um"], 4)
        self.assertAlmostEqual(preflight.spice_number("0.0123f"), 1.23e-17)
        self.assertEqual(preflight.spice_number("1e2"), 100)

    def test_mutations_are_real_and_independent(self):
        for mutation in ("connection", "bulk", "width", "flavor"):
            with self.subTest(mutation=mutation):
                net = self.parse(preflight.independent_reference(DEVICE, mutation))
                with self.assertRaises(AssertionError):
                    preflight.check_devices(net, DEVICE)

    def test_empty_lvs_cannot_pass(self):
        net = self.parse(".subckt test D G S B\n.ends\n")
        with self.assertRaises(AssertionError):
            preflight.check_devices(net, DEVICE)

    def test_two_device_reference_preserves_both_independent_loads(self):
        net = self.parse(preflight.independent_reference(ROUTE))
        self.assertEqual(net["ports"], ["D", "G", "S", "B", "G2", "S2"])
        self.assertEqual([device["pins"] for device in net["devices"]],
                         [["D", "G", "S", "B"], ["D", "G2", "S2", "B"]])
        net["devices"].reverse()
        self.assertEqual(len(preflight.check_devices(net, ROUTE)), 2)
        self.assertEqual(preflight.ROUTE_DEVICE_PINS[0], ["D", "G", "S", "B"])

    def test_missing_duplicate_or_misconnected_second_device_fails(self):
        for mutation in ("missing", "duplicate", "gate", "bulk", "width", "length", "m", "model", "ports"):
            with self.subTest(mutation=mutation):
                net = self.parse(preflight.independent_reference(ROUTE))
                if mutation == "missing":
                    net["devices"].pop()
                elif mutation == "duplicate":
                    net["devices"][1] = net["devices"][0]
                elif mutation in ("gate", "bulk"):
                    net["devices"][1]["pins"][1 if mutation == "gate" else 3] = "S2"
                elif mutation in ("width", "length"):
                    net["devices"][1]["w_um" if mutation == "width" else "l_um"] *= 2
                elif mutation == "m":
                    net["devices"][1]["m"] = 2
                elif mutation == "model":
                    net["devices"][1]["model"] = "sky130_fd_pr__nfet_01v8"
                else:
                    net["ports"][-2:] = ["S2", "G2"]
                with self.assertRaises(AssertionError):
                    preflight.check_devices(net, ROUTE)

    def test_top_contract_is_checked_before_netgen(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            wrong = dict(DEVICE, cell="wrong")
            (out / "test.lvs.spice").write_text(preflight.independent_reference(wrong))
            with patch.object(preflight, "run_logged") as run:
                with self.assertRaisesRegex(AssertionError, "Wrong extracted top cell"):
                    preflight.run_lvs(out, DEVICE)
                run.assert_not_called()

    def test_missing_or_malformed_wrapper_rejected(self):
        source = preflight.independent_reference(DEVICE)
        for text in (source.replace(".ends test", ""), source.replace(".ends test", ".ends other"),
                     source.replace(".subckt test D G S B\n", "")):
            with self.subTest(text=text), self.assertRaises(AssertionError):
                self.parse(text)

    def test_netgen_property_failure_is_not_a_missing_comparison(self):
        result = preflight.lvs_outcome("PREFLIGHT_LVS_RESULT -3 -3", "width")
        self.assertFalse(result["expected_match"])
        for text, mutation in (("PREFLIGHT_LVS_RESULT -1 -1", "width"),
                               ("PREFLIGHT_LVS_RESULT 0 0", "width"),
                               ("PREFLIGHT_LVS_RESULT 1 1", "flavor"),
                               ("PREFLIGHT_LVS_RESULT -3 -3", None)):
            with self.subTest(text=text, mutation=mutation), self.assertRaises(AssertionError):
                preflight.lvs_outcome(text, mutation)
        self.assertTrue(preflight.lvs_outcome("PREFLIGHT_LVS_RESULT 1 1", None)["expected_match"])

    def test_scale_directive_rejected(self):
        with self.assertRaises(AssertionError):
            self.parse(".option scale=1e-6\n" + preflight.independent_reference(DEVICE))

    def test_c_only_is_not_rc(self):
        net = self.parse(preflight.independent_reference(DEVICE))
        net["capacitors"] = [{"name": "C1", "nodes": ["D", "B"], "value": 1e-15}]
        with self.assertRaises(AssertionError):
            preflight.rc_metrics(net, DEVICE)

    def test_rc_must_reach_the_transistor(self):
        net = self.branched_rc()
        net["devices"][0]["pins"][0] = "unconnected_device"
        with self.assertRaises(AssertionError):
            preflight.rc_metrics(net, DEVICE)
        net["devices"][0]["pins"][0] = "device_d"
        metrics = preflight.rc_metrics(net, DEVICE)
        self.assertEqual(metrics["drain_resistance_sum_ohm"], 72)
        self.assertEqual(metrics["drain_branch_nodes"], ["junction"])
        self.assertEqual(metrics["floating_annotated_capacitors_checked"], ["C1"])

    def test_floating_annotations_are_retained_and_connectivity_checked(self):
        source = preflight.independent_reference(DEVICE).replace(
            ".ends test", "C1 D B 1f ; **FLOATING\n.ends test")
        parsed = self.parse(source)
        self.assertEqual(parsed["capacitors"][0]["annotation"], "**FLOATING")
        self.assertEqual(parsed["capacitors"][0]["nodes"], ["D", "B"])
        self.assertEqual(parsed["capacitors"][0]["value"], 1e-15)
        net = self.branched_rc()
        net["capacitors"].append({"name": "C2", "nodes": ["unanchored", "B"],
                                  "value": 1e-15, "annotation": "**FLOATING"})
        with self.assertRaisesRegex(AssertionError, "Unanchored parasitic"):
            preflight.rc_metrics(net, DEVICE)

    def test_resistive_terminal_short_is_not_valid_pex(self):
        net = self.branched_rc()
        net["resistors"].append({"name": "Rbad", "nodes": ["D", "G"], "value": 10})
        with self.assertRaisesRegex(AssertionError, "Unexpected resistive short"):
            preflight.rc_metrics(net, DEVICE)

    def test_point_to_point_chain_is_not_a_branched_probe(self):
        net = self.branched_rc()
        net["resistors"] = [
            {"name": "R1", "nodes": ["D", "upper"], "value": 10},
            {"name": "R2", "nodes": ["upper", "device_d"], "value": 20},
        ]
        with self.assertRaisesRegex(AssertionError, "No extracted branch junction"):
            preflight.rc_metrics(net, DEVICE)

    def test_branched_rc_reaches_two_distinct_transistor_endpoints(self):
        net = self.parse(preflight.independent_reference(ROUTE))
        for i, device in enumerate(net["devices"]):
            device["pins"][0] = f"drain{i}"
        net["resistors"] = [
            {"name": "R1", "nodes": ["D", "junction"], "value": 10},
            {"name": "R2", "nodes": ["junction", "drain0"], "value": 20},
            {"name": "R3", "nodes": ["junction", "drain1"], "value": 30},
        ]
        net["capacitors"] = [
            {"name": "C1", "nodes": ["drain0", "B"], "value": 1e-15},
            {"name": "C2", "nodes": ["drain1", "B"], "value": 2e-15},
        ]
        metrics = preflight.rc_metrics(net, ROUTE)
        self.assertEqual(metrics["drain_transistor_terminals"], ["drain0", "drain1"])
        self.assertEqual(metrics["drain_branch_nodes"], ["junction"])
        net["devices"][1]["pins"][0] = "drain0"
        with self.assertRaisesRegex(AssertionError, "distinct drain endpoint"):
            preflight.rc_metrics(net, ROUTE)
        net["devices"][1]["pins"][0] = "drain1"
        net["devices"][1]["pins"][2] = "S"
        with self.assertRaisesRegex(AssertionError, "misconnected physical transistor"):
            preflight.rc_metrics(net, ROUTE)

    def test_real_six_port_contract_is_checked_before_netgen(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            (out / "test.lvs.spice").write_text(preflight.independent_reference(ROUTE))
            (out / "test.ext").write_text(
                "".join(f'port "{pin}" {i} 0 0 0 0 m1\n'
                        for i, pin in enumerate(preflight.PRIMITIVE_PORTS, start=1)))
            with patch.object(preflight, "run_logged") as run:
                with self.assertRaisesRegex(AssertionError, "Missing/misordered real extraction ports"):
                    preflight.run_lvs(out, ROUTE)
                run.assert_not_called()

    def test_gate_area_requires_connected_geometry_and_real_grid(self):
        mag = {"label_positions": {"G": [0, 0, 0, 0]},
               "rectangles": {"metal1": [[-29, -23, 29, 23], [100, 100, 300, 300]],
                              "viali": [[-17, -17, 17, 17]]}}
        self.assertAlmostEqual(preflight.metal1_area_at_pin_um2(mag, "G", 0.005), 0.0667)
        mag["rectangles"]["metal1"].append([-30, -22, 30, 58])
        self.assertAlmostEqual(preflight.metal1_area_at_pin_um2(mag, "G", 0.005), 0.12145)
        with self.assertRaises(AssertionError):
            preflight.metal1_area_at_pin_um2(mag, "G", 0)

    def test_empty_geometry_is_not_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty"
            path.write_text("magic\ntech sky130A\n<< end >>\n")
            with self.assertRaises(AssertionError):
                preflight.inspect_mag(path)
            path.write_bytes(b"\x00\x04\x04\x00")
            with self.assertRaises(AssertionError):
                preflight.inspect_gds(path)


if __name__ == "__main__":
    unittest.main()
