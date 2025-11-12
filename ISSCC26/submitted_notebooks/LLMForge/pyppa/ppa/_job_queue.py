import json

from typing import Union
from os import path, makedirs
from shutil import rmtree
from multiprocessing import Pool

from ..utils.config_sweep import get_configs_iterator
from ..flow import FlowRunner

from ._types import PPAJobArgs, PPAOptJobArgs, PPASweepJobArgs, JobRun, PPARun, OptimizerReturnType, JobConfig
from ._ppa import __ppa_runner__

def __clear_job_queue__(self):
	"""Recursively clears the job queue. Adds new jobs (if any) to the pool once previous jobs have been cleared."""
	to_be_run = self.jobs_queue
	self.jobs_queue = []

	# Run the jobs
	job_runs = self.job_runner.starmap(self.__job_runner__, [[args] for args in to_be_run])

	self.job_runs.extend(job_runs)

	if len(self.jobs_queue) > 0:
		self.__clear_job_queue__()

def __save_config__(
	work_home: str,
	module: str,
	iteration_number: int,
	flow_config: dict,
	hyperparameters: dict
):
	with open(path.join(work_home, 'config.json'), 'w') as config_file:
		json.dump(
			{
				'module': module,
				'iteration_number': iteration_number,
				'flow_config': flow_config,
				'hyperparameters': hyperparameters
			},
			config_file,
			indent=2
		)

def __job_runner__(
	self,
	job_args: PPAJobArgs
) -> list[JobRun]:
	subjob_runner = Pool(job_args['max_threads'])
	subjobs = []

	if job_args['mode'] == "sweep": # Sweep job
		iteration_number = 1
		# Iterate every possible flow config
		for flow_config, _ in get_configs_iterator(job_args['flow_config']):
			# And every hyperparameter config
			for hyperparameters, _ in get_configs_iterator(job_args['hyperparameters']):
				# Create a clean iteration work home
				iter_work_home = path.join(job_args['job_work_home'], str(iteration_number))
				if path.exists(iter_work_home):
					rmtree(iter_work_home)
				makedirs(iter_work_home)

				# Write all the configurations to a file
				__save_config__(
					iter_work_home,
					job_args['module_name'],
					iteration_number,
					flow_config,
					hyperparameters
				)

				# Create a flow runner for this iteration
				flow_runner: FlowRunner = FlowRunner(
					self.tools,
					{
						**self.platform_config,
						**self.global_flow_config,
						**flow_config,
						'DESIGN_NAME': job_args['module_name'],
						'WORK_HOME': iter_work_home
					},
					hyperparameters
				)

				# Add the subjob to the subjob queue
				subjobs.append((flow_runner, iter_work_home, iteration_number))
				iteration_number += 1

		# Run (Sweep) all the subjobs
		ppa_runs = subjob_runner.starmap(__ppa_runner__, subjobs)
		job_run: JobRun = {
			'job': job_args['job_config'],
			'ppa_runs': ppa_runs
		}

		return job_run
	else: # Optimization job
		prev_iter_module_runs: Union[list[PPARun], None] = None
		iteration_number = 0
		context = None

		while True:
			next_iter: OptimizerReturnType = job_args['optimizer'](iteration_number, prev_iter_module_runs, context)
			opt_complete = next_iter.get('opt_complete', False)
			context = next_iter.get('context', None)
			iteration_number += 1

			if opt_complete:
				print(f"Optimization job complete for module {job_args['module_name']}.")
				return {
					'job': job_args['job_config'],
					'ppa_runs': prev_iter_module_runs
				}


			# Create a clean iteration work home
			iter_work_home = path.join(job_args['job_work_home'], str(iteration_number))
			if path.exists(iter_work_home):
				rmtree(iter_work_home)
			makedirs(iter_work_home)

			for i, suggestion in enumerate(next_iter['next_suggestions']):
				# Create a clean suggestion work home
				suggestion_work_home = path.join(iter_work_home, str(i))
				if path.exists(suggestion_work_home):
					rmtree(suggestion_work_home)
				makedirs(suggestion_work_home)

				# Write all the configurations to a file
				__save_config__(
					suggestion_work_home,
					job_args['module_name'],
					iteration_number,
					suggestion['flow_config'],
					suggestion['hyperparameters']
				)

				# Create a flow runner for this iteration
				flow_runner: FlowRunner = FlowRunner(
					self.tools,
					{
						**self.platform_config,
						**self.global_flow_config,
						**suggestion['flow_config'],
						'DESIGN_NAME': job_args['module_name'],
						'WORK_HOME': suggestion_work_home
					},
					suggestion['hyperparameters']
				)

				# Add the subjob to the subjob queue
				subjobs.append((flow_runner, suggestion_work_home, iteration_number))

			# Run all the subjobs and give it back to the optimizer for evaluation
			prev_iter_module_runs = subjob_runner.starmap(__ppa_runner__, subjobs)
			subjobs = []

def __get_job_args__(self, job: JobConfig, job_work_home: str):
	if job['mode'] == "opt": # Optimization mode
		job_args: PPAOptJobArgs = {
			'job_config': job,
			'mode': 'opt',
			'module_name': job['module_name'],
			'job_work_home': job_work_home,
			'max_threads': job.get('max_threads', self.threads_per_job),
			'optimizer': job['optimizer']
		}

		return job_args
	elif job['mode'] == 'sweep': # Sweep mode
		job_args: PPASweepJobArgs = {
			'job_config': job,
			'mode': 'sweep',
			'module_name': job['module_name'],
			'max_threads': job.get('max_threads', self.threads_per_job),
			'job_work_home': job_work_home,
			'flow_config': job['flow_config'],
			'hyperparameters': job['hyperparameters']
		}

		return job_args