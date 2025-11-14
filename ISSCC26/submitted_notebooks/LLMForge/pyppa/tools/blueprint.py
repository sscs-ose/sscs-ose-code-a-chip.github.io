import subprocess
import shutil
from typing import TypedDict, Optional

def call_cmd(cmd: str, args: list[str], env: Optional[dict], logfile: Optional[str], cwd: Optional[str] = None):
	if logfile:
		with open(logfile, 'w') as f:
			subprocess.run([cmd, *args], env=env, stdout=f, stderr=f, cwd=cwd)
	else:
		subprocess.run([cmd, *args], env=env)

class FlowTool:
	tool_executable: str
	tool_default_args: list[str]
	scripts_dir: str

	def __init__(self, scripts_dir: str, default_args: list[str] = [], cmd: Optional[str] = None):
		self.tool_executable = shutil.which(cmd)
		self.scripts_dir = scripts_dir
		self.tool_default_args = default_args

	def _call_tool(self, args: list[str], env: dict | None, logfile: str | None, cwd: str | None = None):
		call_cmd(
			cmd=self.tool_executable,
			args=self.tool_default_args + args,
			env=env,
			logfile=logfile,
			cwd=cwd
		)

class SynthStats(TypedDict):
	num_wires: int
	num_wire_bits: int
	num_public_wires: int
	num_memories: int
	num_memory_bits: int
	num_processes: int
	num_cells: int
	cell_counts: dict[str, int]
	module_area: float

class SynthTool(FlowTool):
	def run_synth(self, env: dict[str, str], log_dir: str = ""):
		"""Runs the synthesis script."""
		pass

	def parse_synth_stats(self, raw_stats: str) -> SynthStats:
		"""Parses generated synthesis stats."""
		pass

class STAReport(TypedDict):
	clk_name: str
	clk_period: float
	clk_slack: float

class PowerReportEntry(TypedDict):
	internal_power: float
	switching_power: float
	leakage_power: float
	total_power: float
	percentage: float

class PowerReportTotalPercentages(TypedDict):
	internal_power: float
	switching_power: float
	leakage_power: float

class PowerReport(TypedDict):
	sequential: PowerReportEntry
	combinational: PowerReportEntry
	clock: PowerReportEntry
	macro: PowerReportEntry
	pad: PowerReportEntry

	total: PowerReportEntry
	total_percentages: PowerReportTotalPercentages

class PostSynthPPAStats(TypedDict):
	num_sequential_cells: int
	num_combinational_cells: int
	sta: dict[str, STAReport]
	power_report: PowerReport

class PPATool(FlowTool):
	def run_postsynth_ppa(self, env: dict[str, str], log_dir: str, reports_dir: str) -> PostSynthPPAStats:
		"""Runs postsynthesis PPA."""
		pass

class VerilogSimTool(FlowTool):
	def run_sim(self,
		verilog_files: list[str],
		testbench_files: list[str],
		testbench_module: str,
		obj_dir: str,
		vcd_file: str,
		log_dir: str,
		env: dict[str, str]
	) -> str:
		"""Runs Verilog simulations and generates a VCD file. Returns the path to the directory in which the dumpfiles will be generated."""