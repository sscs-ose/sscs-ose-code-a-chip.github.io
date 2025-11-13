from typing import TypedDict, Union
from os import path

class __FlowConfigDirectories(TypedDict):
	"""The flow directories."""
	WORK_HOME: str
	"""The directory in which all the outputs are generated."""
	RESULTS_DIR: str
	"""The directory in which all flow results will be generated. Default: `[work_home]/results`"""
	LOG_DIR: str
	"""The directory in which all log files will be generated. Default: `[work_home]/logs`"""
	REPORTS_DIR: str
	"""The directory in which all reports will be generated. Default: `[work_home]/reports`"""
	OBJECTS_DIR: str
	"""The directory in which all objects will be generated. Default: `[work_home]/objects`"""

class __FlowConfigTools(TypedDict):
	"""The tool configurations."""

FlowCommonConfigDict = Union[__FlowConfigDirectories, __FlowConfigTools]

FLOW_COMMON_CONFIG_DEFAULTS: FlowCommonConfigDict = {
	'WORK_HOME': path.abspath('.')
}

class FlowCommonConfig:
	configopts: Union[FlowCommonConfigDict, dict]
	config: FlowCommonConfigDict

	def __init__(self):
		# self.configopts = configopts.copy()
		self.config = {**FLOW_COMMON_CONFIG_DEFAULTS, **self.config}

		self.calculate_dirs()

	def calculate_dirs(self):
		# Set defaults for generated directories
		self.config['RESULTS_DIR'] = self.configopts.get('RESULTS_DIR', path.join(self.config['WORK_HOME'], 'results'))
		self.config['LOG_DIR'] = self.configopts.get('LOG_DIR', path.join(self.config['WORK_HOME'], 'logs'))
		self.config['REPORTS_DIR'] = self.configopts.get('REPORTS_DIR', path.join(self.config['WORK_HOME'], 'reports'))
		self.config['OBJECTS_DIR'] = self.configopts.get('OBJECTS_DIR', path.join(self.config['WORK_HOME'], 'objects'))

	from ._get_env import get_env
