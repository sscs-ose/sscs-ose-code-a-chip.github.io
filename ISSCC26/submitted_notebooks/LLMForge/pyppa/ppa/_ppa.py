import json
from os import path

from ..flow import FlowRunner
from ..utils.time import TimeElapsed

from ._types import PPARun

def __save_ppa_results__(
	work_home: str,
	ppa_results: PPARun
):
	class DefaultEncoder(json.JSONEncoder):
		def default(self, o):
			return o.__dict__

	with open(path.join(work_home, 'ppa.json'), 'w') as ppa_file:
		json.dump(
			ppa_results,
			ppa_file,
			indent=2,
			cls=DefaultEncoder
		)

def __get_ppa_results__(
	runner: FlowRunner,
	run_number: int,
	run_dir: str
) -> PPARun:
	# Preprocess platform files
	preprocess_time = runner.preprocess()

	# Run presynthesis simulations if enabled
	if runner.get('RUN_VERILOG_SIM') and runner.get('VERILOG_SIM_TYPE') == 'presynth':
		_, sim_time = runner.verilog_sim()

	# Synthesis
	synth_stats, synth_time = runner.synthesis()

	# Run postsynthesis simulations if enabled
	if runner.get('RUN_VERILOG_SIM') and runner.get('VERILOG_SIM_TYPE') == 'postsynth':
		_, sim_time = runner.verilog_sim()

	# Run post-synth PPA and generate power report
	ppa_stats, ppa_time = runner.postsynth_ppa()

	total_time_taken = TimeElapsed.combined(preprocess_time, synth_time, ppa_time)

	results: PPARun = {
		'module_name': runner.get('DESIGN_NAME'),
		'run_number': run_number,
		'run_dir': run_dir,
		'flow_config': runner.configopts,
		'hyperparameters': runner.hyperparameters,

		'preprocess_time': preprocess_time,

		'synth_stats': synth_stats,
		'synth_time': synth_time,

		'ppa_stats': ppa_stats,
		'ppa_time': ppa_time,

		'total_time_taken': total_time_taken
	}

	return results

def __ppa_runner__(
	flow_runner: FlowRunner,
	work_home: str,
	iteration_number: int
) -> PPARun:
	# Get the results for this iteration
	run_results: PPARun = __get_ppa_results__(
		flow_runner,
		iteration_number,
		work_home
	)

	# Save and return the results for the run
	__save_ppa_results__(work_home, run_results)
	return run_results