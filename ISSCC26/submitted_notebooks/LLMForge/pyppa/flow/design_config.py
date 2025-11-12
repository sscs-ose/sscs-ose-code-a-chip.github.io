from typing import TypedDict, Union
from os import path
from ..utils.path_utils import enumerate_dir_recursive

class __DesignCommonConfig(TypedDict):
	"""The common design configuration."""
	DESIGN_NAME: str
	"""The name of the design."""
	VERILOG_FILES: list[str]
	"""The paths to the design Verilog files."""
	SDC_FILE: str
	"""The path to design constraint (SDC) file. Default: `./constraint.sdc"""
	ABC_AREA: bool
	"""Whether to use `ABC_AREA` strategy for Yosys synthesis. Setting it to false will use `ABC_SPEED` strategy. Default: `False`"""
	ABC_CLOCK_PERIOD_IN_PS: float
	"""Clock period to be used by STA during synthesis. Default value read from `constraint.sdc`."""
	ADDITIONAL_LIB_FILES: list[str]
	"""Paths to additional `.lib` files included for the design. These files are appended to the platform lib files."""

class __STAConfig(TypedDict):
	RUN_VERILOG_SIM: bool
	"""Runs Verilog simulations to generate a VCD file."""
	VERILOG_SIM_TYPE: str
	"""`presynth` (Pre synthesis) or `postsynth` (Post synthesis)"""
	VERILOG_TESTBENCH_FILES: list[str]
	"""Verilog simulation testbench files. The files can use Mako's templating syntax with the hyperparameters."""
	VERILOG_TESTBENCH_MODULE: str
	"""The Verilog module name of the simulation testbench."""
	VERILOG_VCD_NAME: str
	"""Name of the VCD dumpfile generated in verilog simulation."""
	USE_STA_VCD: bool
	"""Whether to use the simulated VCD file for improving estimates in the STA power report."""
	STA_TB_DUT_INSTANCE: str
	"""The name of the DUT (device under test) instance in the Verilog testbench used for STA."""

class __DesignSynthConfig(TypedDict):
	"""The synthesis design configuration."""
	USE_YOSYS_SV_PLUGIN: bool
	"""Whether to use the [Synlig](https://github.com/chipsalliance/synlig) SystemVerilog plugin for Yosys. (Default: `False`)"""
	SYNTH_HIERARCHICAL: bool
	"""Whether to run hierarchical synthesis. Default: `false`"""
	PRESERVE_HIERARCHY_MODULES: list[str]
	"""List of modules to preserve during flattening. This is applicable only if `SYNTH_HIERARCHICAL` is set to `False`."""
	SYNTH_ARGS: str
	"""Optional arguments given to the Yosys `synth` command."""

class __DesignFloorplanConfig(TypedDict):
	"""The floorplan design configuration."""
	FLOORPLAN_DEF: str
	"""Use the DEF file to initialize floorplan."""
	DIE_AREA: tuple[float, float, float, float]
	"""The die area specified as a tuple of lower-left and upper-right corners in microns (X1,Y1,X2,Y2). This variable is ignored if `CORE_UTILIZATION` and `CORE_ASPECT_RATIO` are defined."""
	CORE_AREA: tuple[float, float, float, float]
	"""The core area specified as a tuple of lower-left and upper-right corners in microns (X1,Y1,X2,Y2). This variable is ignored if `CORE_UTILIZATION` and `CORE_ASPECT_RATIO` are defined."""
	CORE_UTILIZATION: float
	"""The core utilization percentage (0-100). Overrides `DIE_AREA` and `CORE_AREA`."""
	CORE_ASPECT_RATIO: float
	"""The core aspect ratio (height / width). This values is ignored if `CORE_UTILIZATION` undefined."""
	CORE_MARGIN: int
	"""The margin between the core area and die area, in multiples of SITE heights. The margin is applied to each side. This variable is ignored if `CORE_UTILIZATION` is undefined."""
	PLACE_PINS_ARGS: str
	"""Arguments for io pin placement."""

FlowDesignConfigDict = Union[__DesignCommonConfig, __STAConfig, __DesignSynthConfig, __DesignFloorplanConfig]

FLOW_DESIGN_CONFIG_DEFAULTS: FlowDesignConfigDict = {
	'ABC_AREA': False,
	'ABC_CLOCK_PERIOD_IN_PS': 0,
	'PLACE_PINS_ARGS': '',
	'RUN_VERILOG_SIM': False,
	'USE_STA_VCD': False,
	'STA_TB_DUT_INSTANCE': 'dut',
	'USE_YOSYS_SV_PLUGIN': False,
	'SYNTH_HIERARCHICAL': True,
	'PRESERVE_HIERARCHY_MODULES': [],
	'SYNTH_ARGS': '',
	'ADDITIONAL_LIB_FILES': []
}

# FLOW_DESIGN_CONFIG_DEFAULTS: FlowDesignConfigDict = {
# 	'ABC_AREA': False,
# 	'ABC_CLOCK_PERIOD_IN_PS': 0,
# 	'PLACE_PINS_ARGS': '',
# 	'RUN_VERILOG_SIM': False,
# 	'USE_STA_VCD': False,
# 	'STA_TB_DUT_INSTANCE': 'dut',
# 	'USE_YOSYS_SV_PLUGIN': False,
# 	'SYNTH_HIERARCHICAL': True,
# 	'PRESERVE_HIERARCHY_MODULES': [],
# 	'SYNTH_ARGS': '',
# 	'ADDITIONAL_LIB_FILES': []
# }


class FlowDesignConfig:
	configopts: Union[FlowDesignConfigDict, dict]
	config: FlowDesignConfigDict

	def __init__(self):
		# self.configopts = configopts.copy()
		self.config = {**FLOW_DESIGN_CONFIG_DEFAULTS, **self.config}

		self.config['SDC_FILE'] = self.config.get('SDC_FILE', 'constraint.sdc')

		# Set the default verilog testbench module name as {DESIGN_NAME}_tb
		self.config['VERILOG_TESTBENCH_MODULE'] = self.config.get('VERILOG_TESTBENCH_MODULE', f"{self.config['DESIGN_NAME']}_tb")

		# Set the default verilog sim dumpfile names as {DESIGN_NAME}.vcd
		self.config['VERILOG_VCD_NAME'] = self.config.get('VERILOG_VCD_NAME', f"{self.config['DESIGN_NAME']}.vcd")

		# Recursively read directories for verilog file lists
		for key in ('VERILOG_FILES', 'VERILOG_TESTBENCH_FILES'):
			if key in self.config:
				verilog_paths = []
				for verilog_path in self.config[key]:
					if path.exists(verilog_path):
						if path.isdir(verilog_path):
							verilog_paths.extend(enumerate_dir_recursive(verilog_path))
						else:
							verilog_paths.append(verilog_path)

				self.config[key] = verilog_paths

	from ._get_env import get_env