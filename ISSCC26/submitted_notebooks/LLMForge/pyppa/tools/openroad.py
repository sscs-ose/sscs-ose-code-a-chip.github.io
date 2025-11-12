from os import path
import re
from .blueprint import PPATool, PostSynthPPAStats, PowerReport

class OpenROAD(PPATool):
	def __init__(self, scripts_dir: str, default_args: list[str] = [], cmd: str = 'openroad'):
		super().__init__(scripts_dir, default_args + ['-exit', '-no_init'], cmd)

	def _call_tool(self, args: list[str], env: dict | None, logfile: str | None, cwd: str | None = None):
		return super()._call_tool(args, {**env, 'SCRIPTS_DIR': self.scripts_dir}, logfile, cwd)

	def __run_step(self, step_name: str, script: str, env: dict[str, str], log_dir: str):
		script_path = path.join(self.scripts_dir, f'{script}.tcl')
		metricsfile_path = path.join(log_dir, f'{step_name}.json')
		logfile_path = path.join(log_dir, f'{step_name}.log')

		self._call_tool([script_path, "-metrics", metricsfile_path], env, logfile_path)

	def run_postsynth_ppa(self, env: dict[str, str], log_dir: str, reports_dir: str) -> PostSynthPPAStats:
		self.__run_step('1_2_postsynth_ppa', 'run_postsynth_ppa', env, log_dir)
		return self.__parse_postsynth_ppa_stats(log_dir, reports_dir)

	def __parse_postsynth_ppa_stats(self, log_dir: str, reports_dir: str) -> PostSynthPPAStats:
		parsed_stats: PostSynthPPAStats = {}

		with open(path.join(log_dir, '1_2_postsynth_ppa.log')) as logfile:
			raw_stats = logfile.read()

			seq_captures = re.findall('Sequential Cells Count: (\d+)', raw_stats)
			parsed_stats['num_sequential_cells'] = int(seq_captures[0]) if len(seq_captures) > 0 else None

			comb_captures = re.findall('Combinational Cells Count: (\d+)', raw_stats)
			parsed_stats['num_combinational_cells'] = int(comb_captures[0]) if len(comb_captures) > 0 else None

			# Capture STA results
			parsed_stats['sta'] = {}

			clk_period_captures = re.findall('Clock ([^\s]+) min period ([\d\.]+)', raw_stats)
			clk_slack_captures = re.findall('Clock ([^\s]+) worst slack ([\d\.\-]+)', raw_stats)

			for (captures, prop) in [(clk_period_captures, 'clk_period'), (clk_slack_captures, 'clk_slack')]:
				for capture in captures:
					if capture[0] in parsed_stats['sta'].keys():
						parsed_stats['sta'][capture[0]][prop] = float(capture[1])
					else:
						parsed_stats['sta'][capture[0]] = {prop: float(capture[1]), 'clk_name': capture[0]}

			return {
				**parsed_stats,
				'power_report': self.__parse_power_report(reports_dir)
			}

	def __parse_power_report(self, reports_dir: str) -> PowerReport:
		parsed_report: PowerReport = {}

		with open(path.join(reports_dir, '1_synth_power_report.txt')) as report_txt:
			raw_report = report_txt.read()

			parse_total_percent = False
			for line in raw_report.lower().splitlines():
				values = line.split()

				for power_entry in ('sequential', 'combinational', 'clock', 'macro', 'pad', 'total'):
					if values[0] == power_entry:
						parsed_report[power_entry] = {
							'internal_power': float(values[1]),
							'switching_power': float(values[2]),
							'leakage_power': float(values[3]),
							'total_power': float(values[4]),
							'percentage': float(values[5].replace('%', ''))
						}
				if parse_total_percent:
					parsed_report['total_percentages'] = {
						'internal_power': float(values[0].replace('%', '')),
						'switching_power': float(values[1].replace('%', '')),
						'leakage_power': float(values[2].replace('%', ''))
					}
				parse_total_percent = values[0] == 'total'

			return parsed_report