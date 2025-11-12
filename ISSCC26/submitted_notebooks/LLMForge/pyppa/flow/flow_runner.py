from typing import Union, TypedDict, Any

from os import makedirs, path
from shutil import copyfile
from mako.template import Template
import re

from ..tools.blueprint import SynthTool, SynthStats, PPATool, PostSynthPPAStats, VerilogSimTool

from ..utils.time import start_time_count, get_elapsed_time, TimeElapsed

from .common_config import FlowCommonConfigDict, FlowCommonConfig
from .platform_config import FlowPlatformConfigDict, FlowPlatformConfig
from .design_config import FlowDesignConfigDict, FlowDesignConfig

from ._flow_utils import markDontUse

FlowConfigDict = Union[FlowCommonConfigDict, FlowPlatformConfigDict, FlowDesignConfigDict]

class FlowTools(TypedDict):
	verilog_sim_tool: VerilogSimTool
	synth_tool: SynthTool
	ppa_tool: PPATool

class FlowRunner(FlowCommonConfig, FlowPlatformConfig, FlowDesignConfig):
	tools: FlowTools
	configopts: Union[FlowConfigDict, dict]
	config: FlowConfigDict
	hyperparameters: dict[str, Any]

	def __init__(
		self,
		tools: FlowTools,
		configopts: Union[FlowConfigDict, dict],
		hyperparameters: dict[str, Any]
	):
		self.tools = tools
		self.configopts = configopts.copy()
		self.config = configopts.copy()
		self.hyperparameters = hyperparameters

		FlowCommonConfig.__init__(self)
		FlowPlatformConfig.__init__(self)
		FlowDesignConfig.__init__(self)

	def get(self, key: str):
		if key in self.config:
			return self.config[key]
		else:
			return None

	def set(self, key, value):
		self.config[key] = value

		self.calculate_dirs()

	def get_env(self):
		"""Returns the corresponding environment variables for the given configuration."""

		return FlowDesignConfig.get_env(
			self,
			FlowPlatformConfig.get_env(
				self,
				FlowCommonConfig.get_env(self, self.config)
			)
		)

	def preprocess(self) -> TimeElapsed:
		start_time = start_time_count()

		# Add hyperparameters to source verilog templates
		processed_verilog_dir = path.join(self.get('WORK_HOME'), 'src')
		if not path.exists(processed_verilog_dir):
			makedirs(processed_verilog_dir)

		processed_verilog_files = []
		for filepath in self.get('VERILOG_FILES'):
			with open(filepath) as file:
				filename = path.basename(filepath)
				processed_filepath = path.join(processed_verilog_dir, filename)
				template = Template(text=file.read())

				with open(processed_filepath, "w") as new_sdc_file:
					new_sdc_file.write(template.render(**self.hyperparameters))
					processed_verilog_files.append(processed_filepath)

		self.set('VERILOG_FILES', processed_verilog_files)

		# Add formal pdk verilog (cells blackbox) to the list of verilog files
		self.set('VERILOG_FILES', [self.get('FORMAL_PDK_VERILOG'), *self.get('VERILOG_FILES')])

		# Create output directories
		makedirs(path.join(self.get('OBJECTS_DIR'), 'lib'), exist_ok = True)
		makedirs(self.get('RESULTS_DIR'), exist_ok = True)
		makedirs(self.get('REPORTS_DIR'), exist_ok = True)
		makedirs(self.get('LOG_DIR'), exist_ok = True)
		PREPROC_LOG_FILE = path.join(self.get('LOG_DIR'), '0_preprocess.log')

		# Mark libraries as dont use
		dont_use_libs = []

		with open(PREPROC_LOG_FILE, 'w') as log_file:
			for lib_file in self.get('LIB_FILES') + self.get('ADDITIONAL_LIB_FILES'):
				output_file = path.join(self.get('OBJECTS_DIR'), 'lib', path.basename(lib_file))
				markDontUse(
					patterns=' '.join(self.get('DONT_USE_CELLS')),
					inputFile=lib_file,
					outputFile=output_file,
					logFile=log_file
				)
				dont_use_libs.append(output_file)

		self.set('DONT_USE_LIBS', dont_use_libs)
		self.set('DONT_USE_SC_LIB', self.get('DONT_USE_LIBS')[0])

		with open(self.get('SDC_FILE')) as sdc_file:
			# Move the SDC file into the objects dir and add the hyperparameters to it
			new_sdc_file_path = path.join(self.get('OBJECTS_DIR'), path.basename(self.get('SDC_FILE')))

			with open(self.get('SDC_FILE')) as sdc_template_file:
				sdc_template = Template(text=sdc_template_file.read())

				with open(new_sdc_file_path, "w") as new_sdc_file:
					new_sdc_file.write(sdc_template.render(**self.hyperparameters))

				# Update the SDC file path
				self.set('SDC_FILE', new_sdc_file_path)

		# Read the new SDC file for reading clock period for setting the yosys-abc clock period value
		if self.get('ABC_CLOCK_PERIOD_IN_PS') is not None:
			with open(self.get('SDC_FILE')) as sdc_file:
				# Match for set clk_period or -period statements
				clk_period_matches = re.search(pattern="^set\s+clk_period\s+(\S+).*|.*-period\s+(\S+).*", flags=re.MULTILINE, string=sdc_file.read())

				if clk_period_matches is not None and len(clk_period_matches.groups()) > 0:
					self.set('ABC_CLOCK_PERIOD_IN_PS', float(clk_period_matches.group(1))*1000)  # Convert to ps

		elapsed_time = get_elapsed_time(start_time)

		return elapsed_time

	def verilog_sim(self) -> tuple[str, TimeElapsed]:
		start_time = start_time_count()
		sim_dir = path.join(self.get('OBJECTS_DIR'), f"{self.get('VERILOG_SIM_TYPE')}_sim")

		if not path.exists(sim_dir):
			makedirs(sim_dir)

		# Process the template Verilog testbench files and store them in sim_dir/tb
		processed_tb_dir = path.join(sim_dir, 'tb')
		if not path.exists(processed_tb_dir):
			makedirs(processed_tb_dir)

		# The paths to the processed testbench files
		final_tb_files = []

		for filepath in self.get('VERILOG_TESTBENCH_FILES'):
			with open(filepath) as file:
				filename = path.basename(filepath)
				processed_filepath = path.join(processed_tb_dir, filename)
				template = Template(text=file.read())

				with open(processed_filepath, "w") as new_sdc_file:
					new_sdc_file.write(template.render(**self.hyperparameters))
					final_tb_files.append(processed_filepath)

		dumpfile_dir = self.tools['verilog_sim_tool'].run_sim(
			verilog_files=[self.get('FORMAL_PDK_VERILOG'), path.join(self.get('RESULTS_DIR'), '1_synth.v')] if self.get('VERILOG_SIM_TYPE') == 'postsynth' else self.get('VERILOG_FILES'),
			testbench_module=self.get('VERILOG_TESTBENCH_MODULE'),
			testbench_files=final_tb_files,
			obj_dir=sim_dir,
			vcd_file=self.get('VERILOG_VCD_NAME'),
			log_dir=self.get('LOG_DIR'),
			env=self.get_env()
		)

		dumpfile_path = path.join(dumpfile_dir, self.get('VERILOG_VCD_NAME'))
		self.set('STA_VCD_FILE', dumpfile_path)

		elapsed_time = get_elapsed_time(start_time)

		return dumpfile_path, elapsed_time

	def synthesis(self) -> tuple[SynthStats, TimeElapsed]:
		start_time = start_time_count()

		SYNTH_OUTPUT_FILE = path.join(self.get('RESULTS_DIR'), '1_1_yosys.v')

		self.tools['synth_tool'].run_synth(env=self.get_env(), log_dir=self.get('LOG_DIR'))

		# Copy results
		copyfile(SYNTH_OUTPUT_FILE, path.join(self.get('RESULTS_DIR'), '1_synth.v'))
		copyfile(self.get('SDC_FILE'), path.join(self.get('RESULTS_DIR'), '1_synth.sdc'))

		elapsed_time = get_elapsed_time(start_time)

		with open(path.join(self.get('REPORTS_DIR'), 'synth_stat.json')) as statsfile:
			stats = self.tools['synth_tool'].parse_synth_stats(statsfile.read())

			return stats, elapsed_time

	def postsynth_ppa(self) -> tuple[PostSynthPPAStats, TimeElapsed]:
		start_time = start_time_count()

		makedirs(self.get('RESULTS_DIR'), exist_ok = True)
		makedirs(self.get('LOG_DIR'), exist_ok = True)

		ppa_stats = self.tools['ppa_tool'].run_postsynth_ppa(self.get_env(), self.get('LOG_DIR'), self.get('REPORTS_DIR'))

		elapsed_time = get_elapsed_time(start_time)

		return ppa_stats, elapsed_time

	def floorplan(self) -> TimeElapsed:
		start_time = start_time_count()

		makedirs(self.get('RESULTS_DIR'), exist_ok = True)
		makedirs(self.get('LOG_DIR'), exist_ok = True)

		self.tools['ppa_tool'].run_floorplanning(self.get_env(), self.get('LOG_DIR'))

		elapsed_time = get_elapsed_time(start_time)

		return elapsed_time