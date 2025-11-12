from os import path, mkdir
import shutil
from .blueprint import VerilogSimTool, call_cmd

class Iverilog(VerilogSimTool):
	vvp_cmd: str
	defautl_vvp_args: list[str]

	def __init__(self, scripts_dir: str, default_args: list[str] = ["-g2005-sv"], cmd: str = "iverilog", default_vvp_args: list[str] = [], vvp_command: str = "vvp"):
		super().__init__(scripts_dir, default_args, cmd)
		self.defautl_vvp_args = default_vvp_args
		self.vvp_cmd = shutil.which(vvp_command)

	def run_sim(
		self,
		verilog_files: list[str],
		testbench_files: list[str],
		testbench_module: str,
		obj_dir: str,
		vcd_file: str,
		log_dir: str,
		env: dict[str, str]
	):
		objects_dir = path.join(obj_dir, 'iverilog')
		if not path.exists(objects_dir):
			mkdir(objects_dir)

		# Compile the testbench
		self._call_tool(
			args=[
				'-o', testbench_module,
				'-s', testbench_module,
				*[path.abspath(file) for file in verilog_files + testbench_files]
			],
			logfile=path.join(log_dir, 'iverilog_compile.log'),
			cwd=objects_dir,
			env={}
		)

		# Run the testbench
		call_cmd(
			cmd=self.vvp_cmd,
			args=self.defautl_vvp_args + [testbench_module],
			logfile=path.join(log_dir, 'iverilog_run.log'),
			cwd=objects_dir,
			env={}
		)

		return objects_dir
