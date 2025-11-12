from typing import Optional, Type
from os import path, makedirs
from shutil import rmtree
from multiprocessing.pool import ThreadPool

from ..flow import FlowConfigDict, FlowPlatformConfigDict, FlowTools
from ..utils.time import start_time_count, get_elapsed_time

from ._types import JobConfig, JobRun, PPAJobArgs

class PPARunner:
	design_name: str
	tools: FlowTools
	platform_config: FlowPlatformConfigDict
	global_flow_config: FlowConfigDict
	jobs: list[JobConfig]
	job_runs: list[JobRun] = []
	work_home: str
	max_concurrent_jobs: int = 1
	threads_per_job: int = 4
	job_runner: Type[ThreadPool]
	jobs_queue: list[PPAJobArgs] = []

	from ._job_queue import __clear_job_queue__, __get_job_args__, __job_runner__

	def __init__(
		self,
		design_name: str,
		tools: FlowTools,
		global_flow_config: FlowConfigDict,
		platform_config: FlowPlatformConfigDict = {},
		jobs: list[JobConfig] = [],
		max_concurrent_jobs: int = 1,
		threads_per_job: int = 4,
		work_home: Optional[str] = None
	):
		self.design_name = design_name
		self.tools = tools
		self.platform_config = platform_config
		self.global_flow_config = global_flow_config
		self.jobs = jobs
		self.work_home = work_home if work_home != None else path.abspath(path.join('.', 'runs', design_name))
		self.max_concurrent_jobs = max_concurrent_jobs
		self.threads_per_job = threads_per_job
		self.job_runner = ThreadPool(self.max_concurrent_jobs)

	def set_platform(self, platform: FlowPlatformConfigDict):
		self.platform_config = platform

	def add_job(self, job: JobConfig):
		self.jobs.append(job)

	def run_all_jobs(self):
		start_time = start_time_count()

		run_number = 0
		while len(self.jobs) > 0:
			job = self.jobs.pop(0)
			run_number += 1

			job_work_home = path.join(self.work_home, f"{run_number}_{job['module_name']}_{job['mode']}")
			# Create a clean job work home
			if path.exists(job_work_home):
				rmtree(job_work_home)
			makedirs(job_work_home)

			print(f"Running PPA {'Optimization' if job['mode'] == 'opt' else 'Sweep'} job for module `{job['module_name']}`.")

			job_args = self.__get_job_args__(job, job_work_home)
			self.jobs_queue.append(job_args)

		# Run the list of jobs
		self.__clear_job_queue__()

		print(f"Completed all jobs. Total time elapsed: {get_elapsed_time(start_time).format()}.")
