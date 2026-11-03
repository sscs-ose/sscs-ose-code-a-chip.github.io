"""Configuration-aware testbench for the DLL simulator.

This testbench is driven by the controller and DCDL configurations that
exist under ``librelane/design``. It only runs closed-loop simulations
for combinations the Python simulator actually models.
"""

from __future__ import annotations

import json
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from simulator import (
        EdgeLevelPhaseDetector,
        FilteredController,
        InverterCondDCDL,
        InverterDCDL,
        InverterGlitchFreeDCDL,
        LockedController,
        NandDCDL,
        PhaseDetector,
        PFDPhaseDetector,
        SaturateController,
        SingleFlipFlopPhaseDetector,
        VariableStepController,
        simulate,
    )
    from simulator.zdb_demo import run_zdb_demo
else:
    from . import (
        EdgeLevelPhaseDetector,
        FilteredController,
        InverterCondDCDL,
        InverterDCDL,
        InverterGlitchFreeDCDL,
        LockedController,
        NandDCDL,
        PhaseDetector,
        PFDPhaseDetector,
        SaturateController,
        SingleFlipFlopPhaseDetector,
        VariableStepController,
        simulate,
    )
    from .zdb_demo import run_zdb_demo


ROOT = Path(__file__).resolve().parents[1]
DESIGN_ROOT = ROOT / "librelane" / "design"


def load_config(config_dir: str) -> dict:
    with (DESIGN_ROOT / config_dir / "config.json").open() as f:
        return json.load(f)


PHASE_DETECTOR_CONFIGS = {
    "phase_detector_syn_ff1": "phase_detector_syn_ff1",
    "phase_detector_syn_edge": "phase_detector_syn_edge",
    "phase_detector_syn_pfd": "phase_detector_syn_pfd",
}


@dataclass(frozen=True)
class ControllerSpec:
    config_dir: str
    factory: object


@dataclass(frozen=True)
class DCDLSpec:
    config_dir: str
    factory: object
    integration_target_ctrl: int | None
    wrapped_one_hot: bool = False


CONTROLLERS = {
    "controller_saturate": ControllerSpec(
        config_dir="controller_saturate",
        factory=lambda bits, init=0: SaturateController(ctrl_bits=bits, init_ctrl=init),
    ),
    "controller_filtered": ControllerSpec(
        config_dir="controller_filtered",
        factory=lambda bits, init=0: FilteredController(
            ctrl_bits=bits, init_ctrl=init, filter_len=3
        ),
    ),
    "controller_locked": ControllerSpec(
        config_dir="controller_locked",
        factory=lambda bits, init=0: LockedController(
            ctrl_bits=bits, init_ctrl=init, acquire_step=2, track_step=1, quiet_cycles=4
        ),
    ),
    "controller_variable_step": ControllerSpec(
        config_dir="controller_variable_step",
        factory=lambda bits, init=0: VariableStepController(
            ctrl_bits=bits, init_ctrl=init, big_step=2, med_step=1, big_thresh=4, med_thresh=2
        ),
    ),
}


DCDLS = {
    "inv_dcdl": DCDLSpec(
        config_dir="inv_dcdl",
        factory=lambda: InverterDCDL(
            num_cells=8,
            first_cell_delay_ps=200.0,
            remaining_cell_delay_ps=150.0,
            mux_delay_ps=50.0,
        ),
        integration_target_ctrl=4,
    ),
    "inv_dcdl_cond": DCDLSpec(
        config_dir="inv_dcdl_cond",
        factory=lambda: InverterCondDCDL(
            num_cells=8,
            first_cell_delay_ps=200.0,
            remaining_cell_delay_ps=150.0,
            mux_delay_ps=50.0,
            xnor_delay_ps=30.0,
        ),
        integration_target_ctrl=4,
    ),
    "glitch_free_reference": DCDLSpec(
        config_dir="inv_dcdl",
        factory=lambda: InverterGlitchFreeDCDL(
            num_cells=8,
            first_cell_delay_ps=50.0,
            remaining_cell_delay_ps=40.0,
            nand_delay_ps=20.0,
        ),
        integration_target_ctrl=4,
    ),
    "nand_dcdl": DCDLSpec(
        config_dir="nand_dcdl",
        factory=lambda: NandDCDL(num_cells=8, first_cell_delay_ps=106.67, remaining_cell_delay_ps=72.68),
        integration_target_ctrl=4,
    ),
}


class ConfigDiscoveryTests(unittest.TestCase):
    def test_phase_detector_configs_exist(self) -> None:
        for name, config_dir in PHASE_DETECTOR_CONFIGS.items():
            config = load_config(config_dir)
            self.assertIn("VERILOG_FILES", config, name)

    def test_controller_configs_exist(self) -> None:
        for name, spec in CONTROLLERS.items():
            config = load_config(spec.config_dir)
            self.assertIn("VERILOG_FILES", config, name)

    def test_dcdl_configs_exist(self) -> None:
        for name, spec in DCDLS.items():
            config = load_config(spec.config_dir)
            self.assertIn("VERILOG_FILES", config, name)


class ControllerModelTests(unittest.TestCase):
    def test_all_supported_controllers_update_and_reset(self) -> None:
        for name, spec in CONTROLLERS.items():
            with self.subTest(controller=name):
                c = spec.factory(6, 8)
                before = c.ctrl
                c.update(1, 0)
                self.assertGreaterEqual(c.ctrl, before)
                c.reset()
                self.assertEqual(c.ctrl, 8)


class PhaseDetectorModelTests(unittest.TestCase):
    def test_base_phase_detector_direction_and_timing(self) -> None:
        pd = PhaseDetector(up_prop_delay_ps=80.0, down_prop_delay_ps=120.0)

        self.assertEqual(pd.detect(0.0, 500.0), (1, 0, 580.0))
        self.assertEqual(pd.detect(500.0, 0.0), (0, 1, 620.0))
        self.assertEqual(pd.detect(100.0, 100.0), (0, 0, 100.0))
        self.assertEqual(pd.prop_delay_ps, 120.0)

    def test_single_flip_flop_phase_detector_uses_characterized_delays(self) -> None:
        pd = SingleFlipFlopPhaseDetector()

        self.assertAlmostEqual(pd.up_prop_delay_ps, 348.78)
        self.assertAlmostEqual(pd.down_prop_delay_ps, 2348.25)
        self.assertEqual(pd.detect(0.0, 100.0), (1, 0, 448.78))
        self.assertEqual(pd.detect(100.0, 0.0), (0, 1, 2448.25))

    def test_concrete_phase_detectors_expose_expected_delays(self) -> None:
        edge = EdgeLevelPhaseDetector()
        pfd = PFDPhaseDetector()

        self.assertAlmostEqual(edge.up_prop_delay_ps, 242.81)
        self.assertAlmostEqual(edge.down_prop_delay_ps, 242.81)
        self.assertAlmostEqual(pfd.up_prop_delay_ps, 353.95)
        self.assertAlmostEqual(pfd.down_prop_delay_ps, 352.99)
        self.assertLess(abs(pfd.up_prop_delay_ps - pfd.down_prop_delay_ps), 1.0)


class DCDLModelTests(unittest.TestCase):
    def test_binary_tap_dcdls_are_monotonic(self) -> None:
        for name in ("inv_dcdl", "inv_dcdl_cond", "glitch_free_reference"):
            with self.subTest(dcdl=name):
                d = DCDLS[name].factory()
                delays = [d.delay(i) for i in range(8)]
                self.assertTrue(all(a < b for a, b in zip(delays, delays[1:])), delays)

    def test_nand_dcdl_stage_enable_semantics(self) -> None:
        d = DCDLS["nand_dcdl"].factory()
        full_delay = 106.67 + 7 * 72.68

        self.assertAlmostEqual(d.delay(0x00), full_delay, places=6)
        self.assertAlmostEqual(d.delay(0xFF), 0.0, places=6)
        self.assertAlmostEqual(d.delay(0x01), full_delay - 106.67, places=6)
        self.assertAlmostEqual(d.delay(0x02), full_delay - 72.68, places=6)
        self.assertAlmostEqual(d.delay(0x03), full_delay - 106.67 - 72.68, places=6)

    def test_nand_dcdl_prefix_clear_words_increase_delay(self) -> None:
        d = DCDLS["nand_dcdl"].factory()
        full_mask = (1 << 8) - 1
        words = [full_mask ^ ((1 << active) - 1) if active > 0 else full_mask for active in range(9)]
        delays = [d.delay(word) for word in words]
        self.assertTrue(all(a < b for a, b in zip(delays, delays[1:])), delays)


class ClosedLoopDLLTests(unittest.TestCase):
    def test_zdb_path_converges_with_pfd_saturate_nand(self) -> None:
        trace, clk_period_ps = run_zdb_demo(target_tap=41, init_ctrl=0, num_cycles=120, settle_cycles=3)

        self.assertGreater(len(trace), 0)
        self.assertAlmostEqual(clk_period_ps, 3013.87, places=2)
        self.assertEqual(trace[-1].phase_error_ps, 0.0)
        self.assertEqual(trace[-1].up, 0)
        self.assertEqual(trace[-1].down, 0)
        self.assertEqual(trace[-1].ctrl_index, 41)

    def test_pfd_detector_reaches_zero_error_on_binary_dcdls(self) -> None:
        detector = PFDPhaseDetector()

        for dcdl_name in ("inv_dcdl", "inv_dcdl_cond"):
            dcdl_spec = DCDLS[dcdl_name]
            target_period_ps = dcdl_spec.factory().delay(dcdl_spec.integration_target_ctrl)
            trace = simulate(
                detector,
                SaturateController(ctrl_bits=3, init_ctrl=max(0, dcdl_spec.integration_target_ctrl - 2)),
                dcdl_spec.factory(),
                target_period_ps,
                120,
            )
            self.assertIn(0.0, trace["phase_error"][-20:], trace["phase_error"][-10:])

    def test_supported_controllers_reach_zero_error_on_binary_dcdls(self) -> None:
        detector = EdgeLevelPhaseDetector()

        for dcdl_name in ("inv_dcdl", "inv_dcdl_cond"):
            dcdl_spec = DCDLS[dcdl_name]
            target_period_ps = dcdl_spec.factory().delay(dcdl_spec.integration_target_ctrl)
            for controller_name, controller_spec in CONTROLLERS.items():
                with self.subTest(dcdl=dcdl_name, controller=controller_name):
                    trace = simulate(
                        detector,
                        controller_spec.factory(3, max(0, dcdl_spec.integration_target_ctrl - 2)),
                        dcdl_spec.factory(),
                        target_period_ps,
                        120,
                    )
                    self.assertIn(0.0, trace["phase_error"][-20:], trace["phase_error"][-10:])

    def test_glitch_free_dcdl_reaches_target_window(self) -> None:
        spec = DCDLS["glitch_free_reference"]
        trace = simulate(
            EdgeLevelPhaseDetector(),
            SaturateController(ctrl_bits=3, init_ctrl=0),
            spec.factory(),
            spec.factory().delay(spec.integration_target_ctrl),
            80,
        )
        self.assertLessEqual(min(abs(err) for err in trace["phase_error"][-20:]), 40.0, trace["phase_error"][-10:])

    def test_nand_dcdl_one_hot_words_remove_exact_stage_delay(self) -> None:
        dcdl = DCDLS["nand_dcdl"].factory()
        full_delay = 106.67 + 7 * 72.68
        expected = [full_delay - 106.67] + [full_delay - 72.68 for _ in range(7)]
        actual = [dcdl.delay(1 << i) for i in range(8)]
        for idx, (got, want) in enumerate(zip(actual, expected)):
            self.assertAlmostEqual(got, want, places=6, msg=f"tap {idx}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
