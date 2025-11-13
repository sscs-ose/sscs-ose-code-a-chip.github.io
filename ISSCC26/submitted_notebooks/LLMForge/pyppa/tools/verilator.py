from os import path
from shutil import copyfile
from .blueprint import VerilogSimTool
from .blueprint import call_cmd

class Verilator(VerilogSimTool):
	def __init__(self, scripts_dir: str, default_args: list[str] = [], cmd: str = "verilator"):
		super().__init__(scripts_dir, default_args + ['--timescale', '1ns/1ns', '--trace'], cmd)

	def run_sim(
		self,
		verilog_files: list[str],
		testbench_module: str,
		testbench_file: str,
		obj_dir: str,
		vcd_file: str,
		log_dir: str,
		env: dict[str, str]
	):
		temp_files_dir = path.join(obj_dir, 'verilator')

		self._call_tool(
			args=['--top-module', testbench_module, '-cc', *verilog_files, '--exe', testbench_file, '--Mdir', temp_files_dir],
			env=env,
			logfile=path.join(log_dir, '0_1_1_verilator_compile.log')
		)

		copyfile(testbench_file, path.join(temp_files_dir, 'verilator', testbench_file))

		call_cmd(
			cmd='make',
			args=['-f', path.join(temp_files_dir, f"V{testbench_module}.mk"), f"V{testbench_module}"],
			env=env,
			logfile=path.join(log_dir, '0_1_2_verilator_make.log'),
			cwd=temp_files_dir
		)

		executable = path.join(temp_files_dir, testbench_module)
		exec_logfile = path.join(log_dir, '0_1_3_verilator_exec.log')

		if path.exists(executable):
			call_cmd(
				cmd=executable,
				args=[],
				env=env,
				logfile=exec_logfile
			)
		else:
			with open(exec_logfile, 'w') as logfile:
				logfile.write(f"Verilator compiled executable {executable} not found.")

