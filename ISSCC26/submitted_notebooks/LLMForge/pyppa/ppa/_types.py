from typing import TypedDict, Union, Any, Callable, TypeAlias, Literal

from ..utils.config_sweep import ParameterSweepDict, ParameterListDict
from ..flow import FlowConfigDict
from ..tools.blueprint import PostSynthPPAStats, SynthStats
from ..utils.time import TimeElapsed

class OptSuggestion(TypedDict):
	flow_config: Union[FlowConfigDict, None]
	hyperparameters: Union[dict, None]

class OptimizerReturnType(TypedDict):
	opt_complete: bool
	next_suggestions: Union[list[OptSuggestion], None]
	context: Union[Any, None]

class PPARun(TypedDict):
	module_name: str
	"""The name of the Verilog module."""
	run_number: int
	"""The index of the PPA run."""
	run_dir: str
	"""The path to the directory in which the job was run."""
	flow_config: FlowConfigDict
	"""The complete flow configuration for the run."""
	hyperparameters: dict[str, Any]
	"""The set of hyperparameters used for the run."""

	preprocess_time: TimeElapsed
	"""The time taken for the preprocessing step."""

	synth_stats: SynthStats
	"""The synthesis stats."""
	synth_time: TimeElapsed
	"""The time taken for the synthesis step."""

	ppa_stats: PostSynthPPAStats
	"""The PPA stats."""
	ppa_time: TimeElapsed
	"""The time taken for the post-synthesis PPA step."""

	total_time_taken: TimeElapsed
	"""The total time elapsed in the run."""

FlowConfigSweepDict: TypeAlias = Union[dict[str, Union[ParameterSweepDict, ParameterListDict]], FlowConfigDict]
HyperparameterSweepDict: TypeAlias = dict[str, Union[ParameterSweepDict, ParameterListDict, Any]]
class SweepJobConfig(TypedDict):
	name: str
	"""The name of the Verilog module to run the PPA analysis on."""
	mode: Literal['sweep']
	"""Either `opt` (Optimization) or `sweep`.

	In `sweep` mode, `hyperparameters` and `flow_config` dicts are provided that list either arrays of values for each parameter or a dict of `min`, `max`, and `step` to sweep. Every possible combination of the values each parameter can take will be swept and the corresponding PPA resutls will be reported."""
	hyperparameters: HyperparameterSweepDict
	flow_config: FlowConfigSweepDict
	max_threads: Union[int, None]
	"""The number of allowable threads to use for the job. The global `threads_per_job` is used if this is not set."""

Optimizer: TypeAlias = Callable[[int, Union[list[PPARun]], Any], OptimizerReturnType]
class OptJobConfig(TypedDict):
	name: str
	"""The name of the Verilog module to run the PPA analysis on."""
	mode: Literal['opt']
	"""Either `opt` (Optimization) or `sweep`.

	In `opt` mode, the `optimizer` function provides the next set of parameters to try and the PPA results of each iteration are given as parameter to the function."""
	optimizer: Optimizer
	"""A function that evaluates the previous iteration's PPA results (list) and suggests the next list of set of parameters to test. Return `{'opt_complete': True}` to mark the completion of the optimization either by meeting the target or otherwise.

	Return `{`opt_complete`: False, `flow_config`: {...}, `hyperparameters`: {...}, `context`: {...}} to suggest the next set of flow config parameters and hyperparameters to test. The `context` field is an optional value that will be given as argument for the next iteration.

	The function should accept the following arguments:
	- `iteration_number`: The iteration number for the _previous_ iteration. A `0` iteration number represents the start of the optimization and will have no PPA results.
	- `ppa_results`: A list of dicts of type `PPARun` that contains the flow configuration, hyperparameters, times taken, and PPA stats of the previous iteration. The format of this dictionary is identical to the PPA results returned in the `sweep` mode.
	- `context`: The same context that was provided in the previous iteration
	"""
	max_threads: Union[int, None]
	"""The number of allowable threads to use for the job. The global `threads_per_job` is used if this is not set."""

JobConfig: TypeAlias = Union[SweepJobConfig, OptJobConfig]

class JobRun(TypedDict):
	job: JobConfig
	ppa_runs: list[PPARun]

class PPASweepJobArgs(TypedDict):
	job_config: JobConfig
	mode: Literal['sweep']
	job_work_home: str
	module_name: str
	max_threads: int
	flow_config: FlowConfigSweepDict
	hyperparameters: HyperparameterSweepDict

class PPAOptJobArgs(TypedDict):
	job_config: JobConfig
	mode: Literal['opt']
	job_work_home: str
	module_name: str
	max_threads: int
	optimizer: Optimizer

PPAJobArgs: TypeAlias = Union[PPAOptJobArgs, PPASweepJobArgs]