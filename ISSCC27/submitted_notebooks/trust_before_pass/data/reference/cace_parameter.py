# Copyright 2024 Efabless Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import re
import sys
import copy
import textwrap
import traceback
import subprocess
from statistics import median, mean
from enum import Enum
from abc import abstractmethod, ABC
from threading import Thread
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool
from matplotlib.figure import Figure
from typing import (
    Any,
    List,
    Callable,
    Optional,
    Set,
    Union,
    Tuple,
    Sequence,
    Dict,
    ClassVar,
    Type,
    Generic,
    TypeVar,
)

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_agg import FigureCanvasAgg

from ..common import slugify
from ..common.safe_eval import safe_eval
from ..common.misc import mkdirp
from ..common.spiceunits import spice_unit_convert
from ..common.common import linseq, logseq
from ..config import Variable, Result
from ..logging import (
    dbg,
    verbose,
    info,
    subproc,
    rule,
    success,
    warn,
    err,
)


class ResultType(Enum):
    UNKNOWN = 0
    ERROR = 1
    SUCCESS = 2
    FAILURE = 3
    SKIPPED = 4
    CANCELED = 5

    def __str__(self):
        if self.value == ResultType.UNKNOWN.value:
            return "Unknown ❓"
        elif self.value == ResultType.ERROR.value:
            return "Error ❗"
        elif self.value == ResultType.SUCCESS.value:
            return "Pass ✅"
        elif self.value == ResultType.FAILURE.value:
            return "Fail ❌"
        elif self.value == ResultType.SKIPPED.value:
            return "Skip 🟧"
        elif self.value == ResultType.CANCELED.value:
            return "Cancel 🟧"
        else:
            return "???"


class NamedResult:
    """
    Holds the named result of a parameter.
    For example "lvs_errors"
    """

    def __init__(self, name):
        self.name = name
        self.values = []
        # Maximum/minimum/median of the values
        self.result = {
            "minimum": None,
            "typical": None,
            "maximum": None,
        }
        # 'pass' or 'fail'
        self.status = {
            "minimum": None,
            "typical": None,
            "maximum": None,
        }

    def __repr__(self):
        return f"{self.name} with values {self.values}"

    def __str__(self):
        return f"{self.name} with values {self.values}"


class Condition:
    def __init__(self):
        self.name = None
        self.description = None
        self.display = None
        self.unit = None
        self.spec = {}
        self.values = []

    def __repr__(self):
        return f"{self.name} with spec {self.spec} and values {self.values}"

    def __str__(self):
        return f"{self.name} {self.description} {self.display} {self.unit} {self.spec} {self.values}"

    def generate_values(self):
        self.values = [val for val in self.condition_gen()]

    def condition_gen(self):
        """
        Define a generator for conditions.
        """

        if "enumerate" in self.spec:
            for i in self.spec["enumerate"]:
                yield i

        if "step" in self.spec:
            if not "minimum" in self.spec or not "maximum" in self.spec:
                err(f"Step specified in condition, but no minimum/maximum: {self}")

            if "typical" in self.spec:
                yield self.spec["typical"]

            # Linear step
            if self.spec["step"] == "linear":
                stepsize = 1
                if "stepsize" in self.spec:
                    stepsize = float(self.spec["stepsize"])

                yield from linseq(
                    float(self.spec["minimum"]),
                    float(self.spec["maximum"]),
                    stepsize,
                )

            # Logarithmic step
            elif self.spec["step"] == "logarithmic":
                stepsize = 2
                if "stepsize" in self.spec:
                    stepsize = float(self.spec["stepsize"])

                yield from logseq(
                    float(self.spec["minimum"]),
                    float(self.spec["maximum"]),
                    stepsize,
                )

            else:
                err(f'Unknown step type {self.spec["step"]} in condition: {self}')
        else:
            if "minimum" in self.spec:
                yield self.spec["minimum"]
            if "typical" in self.spec:
                yield self.spec["typical"]
            if "maximum" in self.spec:
                yield self.spec["maximum"]


class Parameter(ABC, Thread):
    """
    Base class for all parameters.
    """

    # Vectors in name[number|range] format
    vectrex = re.compile(r"([^\[]+)\[([0-9:]+)\]")

    # Class Variables
    id: str = NotImplemented
    config_vars: ClassVar[List[Variable]] = []
    config_results: ClassVar[List[Result]] = []

    # Instance Variables
    name: str

    @classmethod
    def __get_desc(Self) -> str:  # pragma: no cover
        if hasattr(Self, "long_name"):
            return Self.long_name
        elif hasattr(Self, "name"):
            return Self.name
        return Self.__name__

    @classmethod
    def get_help_md(
        Self,
        *,
        docstring_override: str = "",
        use_dropdown: bool = False,
        myst_anchors: bool = False,
    ):  # pragma: no cover
        """
        Renders Markdown help for this step to a string.
        """
        doc_string = docstring_override
        if Self.__doc__:
            doc_string = textwrap.dedent(Self.__doc__)

        result = f"ID: `{Self.id}`\n" + doc_string

        if len(Self.config_vars):
            config_var_anchors = f"({Self.id.lower()}-configuration-variables)="
            result += textwrap.dedent(f"""
                {config_var_anchors * myst_anchors}
                #### Configuration Variables
                """)
            result += Variable._render_table_md(
                Self.config_vars, myst_anchor_owner_id=Self.id if myst_anchors else None
            )

        if len(Self.config_results):
            config_result_anchors = f"({Self.id.lower()}-configuration-results)="
            result += textwrap.dedent(f"""
                {config_result_anchors * myst_anchors}
                #### Results
                """)
            result += Result._render_table_md(
                Self.config_results,
                myst_anchor_owner_id=Self.id if myst_anchors else None,
            )

        step_anchor = f"(step-{slugify(Self.id.lower())})="
        result = textwrap.dedent(f"""
                {step_anchor * myst_anchors}
                ### {Self.__get_desc()}
                """) + result

        return result

    def __init__(
        self,
        pname,
        config,
        param,
        datasheet,
        pdk,
        paths,
        runtime_options,
        run_dir,
        max_jobs,
        jobs_sem,
        start_cb=None,
        end_cb=None,
        cancel_cb=None,
        step_cb=None,
        *args,
        **kwargs,
    ):
        self.pname = pname
        self.config = config
        self.param = param
        self.datasheet = datasheet
        self.pdk = pdk
        self.paths = paths
        self.runtime_options = runtime_options
        self.run_dir = run_dir
        self.max_jobs = max_jobs
        self.jobs_sem = jobs_sem
        self.start_cb = start_cb
        self.end_cb = end_cb
        self.cancel_cb = cancel_cb
        self.step_cb = step_cb

        self.started = False

        self.harvested = False

        self.subproc_handle = None

        self.param_dir = os.path.abspath(
            os.path.join(self.run_dir, "parameters", pname)
        )

        # Get the name of the tool and input
        tool = self.param["tool"]
        if isinstance(tool, str):
            self.toolname = tool
            self.tooldict = None
        else:
            self.toolname = list(tool.keys())[0]
            self.tooldict = tool[self.toolname]

        self.results_dict = {}

        for result in self.config_results:
            self.add_result(NamedResult(result.name))

        self.plots_dict = {}
        self.result_type = ResultType.UNKNOWN

        self.canceled = False
        self.done = False

        super().__init__(*args, **kwargs)

    def add_result(self, arg: Result):
        self.results_dict[arg.name] = arg

    def get_result(self, name: str):
        if name in self.results_dict:
            return self.results_dict[name]

        return None

    def cancel(self, no_cb):
        info(f"Parameter {self.pname}: Canceled.")
        self.canceled = True

        if self.subproc_handle:
            self.subproc_handle.kill()

        if no_cb:
            self.cancel_cb = None

    def cancel_point(self):
        """If canceled, call the cancel cb and exit the thread"""

        if self.canceled:
            self.result_type = ResultType.CANCELED
            if self.cancel_cb:
                self.cancel_cb(self.param)
            sys.exit()

    def is_runnable(self):
        return True

    def run(self):

        self.started = True
        rule(f'Started {self.param["display"]}')

        # Create new parameter dir
        dbg(f"Creating directory: '{os.path.relpath(self.param_dir)}'.")
        mkdirp(self.param_dir)

        try:
            self.cancel_point()

            self.pre_start()

            if self.start_cb:
                self.start_cb(self.param, self.get_num_steps())

            self.cancel_point()

            # Run the implementation
            if self.is_runnable():
                self.implementation()

            self.cancel_point()

        except Exception:
            traceback.print_exc()
            self.result_type = ResultType.ERROR
            self.canceled = True

        if self.result_type == ResultType.SUCCESS:
            self.evaluate_result()

        # Set done before calling end cb
        self.done = True

        if self.end_cb:
            self.end_cb(self.param)

        rule(f'Completed {self.param["display"]}: {self.result_type}')

    @abstractmethod
    def implementation(self):
        pass

    def pre_start(self):
        pass

    def get_num_steps(self):
        return 1

    def run_subprocess(self, proc, args=[], env=None, input=None, cwd=None):

        dbg(
            f'Subprocess {proc} {" ".join(args)} at \'[repr.filename][link=file://{os.path.abspath(cwd)}]{os.path.relpath(cwd)}[/link][/repr.filename]\'…'
        )

        with subprocess.Popen(
            [proc] + args,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE if input else subprocess.DEVNULL,
            env=env,
            text=True,
        ) as process:

            self.subproc_handle = process

            if input != None:
                dbg(f"input: {input}")
            stdout, stderr = process.communicate(input)
            returncode = process.returncode

            if returncode != 0:
                err(f"Subprocess exited with error code {returncode}")

            # Print stderr
            if stderr and returncode != 0:
                err("Error output generated by subprocess:")
                for line in stderr.splitlines():
                    err(line.rstrip("\n"))
            else:
                dbg("Error output generated by subprocess:")
                for line in stderr.splitlines():
                    dbg(line.rstrip("\n"))

            # Write stderr to file
            if stderr:
                with open(f"{os.path.join(cwd, proc)}_stderr.out", "w") as stderr_file:
                    stderr_file.write(stderr)

            # Print stdout
            if stdout:
                dbg(f"Output from subprocess {proc}:")
                for line in stdout.splitlines():
                    dbg(line.rstrip())

            # Write stdout to file
            if stdout:
                with open(f"{os.path.join(cwd, proc)}_stdout.out", "w") as stdout_file:
                    stdout_file.write(stdout)

        self.subproc_handle = None

        return returncode

    def evaluate_result(self):

        defaults = {
            "minimum": {
                "fail": True,
                "calculation": "minimum",
                "limit": "above",
            },
            "typical": {
                "fail": False,
                "calculation": "median",
                "limit": "exact",
            },
            "maximum": {
                "fail": True,
                "calculation": "maximum",
                "limit": "below",
            },
        }

        # For each named result in the spec
        for named_result in self.param["spec"]:

            if not self.get_result(named_result):
                err(f'No result "{named_result}" available.')
                self.result_type = ResultType.ERROR
                continue

            # For each entry in the specs
            for entry in ["minimum", "typical", "maximum"]:

                if entry in self.param["spec"][named_result]:
                    value = self.param["spec"][named_result][entry]["value"]
                    fail = (
                        self.param["spec"][named_result][entry]["fail"]
                        if "fail" in self.param["spec"][named_result][entry]
                        else defaults[entry]["fail"]
                    )
                    calculation = (
                        self.param["spec"][named_result][entry]["calculation"]
                        if "calculation" in self.param["spec"][named_result][entry]
                        else defaults[entry]["calculation"]
                    )
                    limit = (
                        self.param["spec"][named_result][entry]["limit"]
                        if "limit" in self.param["spec"][named_result][entry]
                        else defaults[entry]["limit"]
                    )

                    # Check if there are values for the named result
                    if self.get_result(named_result).values:
                        values = self.get_result(named_result).values

                        # Calculate a single value from a vector
                        if calculation == "minimum":
                            result = min(values)
                        elif calculation == "maximum":
                            result = max(values)
                        elif calculation == "median":
                            result = median(values)
                        elif calculation == "average":
                            result = mean(values)
                        else:
                            err(f"Unknown calculation type: {calculation}")
                    else:
                        err(f'Result "{named_result}" is empty.')
                        self.result_type = ResultType.ERROR
                        result = None

                    self.get_result(named_result).result[entry] = result
                    dbg(f"Got {entry} result for {self.pname} {named_result}: {result}")

                    status = "pass"

                    # Check result against a limit
                    if value != "any" and fail == True:

                        # Prefer the local unit
                        unit = (
                            self.param["spec"][named_result]["unit"]
                            if "unit" in self.param["spec"][named_result]
                            else None
                        )

                        # Else use the global unit
                        if not unit:
                            unit = self.param["unit"] if "unit" in self.param else None

                        # Scale value with unit
                        if unit:
                            dbg(f"scaling {value} with {unit}")
                            value = spice_unit_convert(
                                (
                                    str(unit),
                                    str(value),
                                )
                            )
                            dbg(f"result: {value}")
                        if result != None:
                            dbg(
                                f"Checking result {result} against value {value} with limit {limit}."
                            )
                            if limit == "above":
                                if result < float(value):
                                    status = "fail"
                            elif limit == "below":
                                if result > float(value):
                                    status = "fail"
                            elif limit == "exact":
                                if result != float(value):
                                    status = "fail"
                            else:
                                err(f"Unknown limit type: {limit}")

                    self.get_result(named_result).status[entry] = status

                    dbg(f"Got {entry} status for {self.pname} {named_result}: {status}")

            # Final checks for failure
            for entry in ["minimum", "typical", "maximum"]:
                if self.get_result(named_result).result[entry]:
                    if self.get_result(named_result).status[entry] == "fail":
                        # If any spec fails, fail the whole parameter
                        self.result_type = ResultType.FAILURE

    def get_default_conditions(self):
        # Get the global default conditions
        conditions_default = {}

        for cond, spec in self.datasheet["default_conditions"].items():
            # Create new conditions
            new_cond = Condition()

            # Remove any bit slices
            pmatch = self.vectrex.match(cond)
            if pmatch:
                cond = pmatch.group(1)

            new_cond.name = cond

            for key, value in spec.items():
                if key == "description":
                    new_cond.description = value
                elif key == "display":
                    new_cond.display = value
                elif key == "unit":
                    new_cond.unit = value
                else:
                    new_cond.spec[key] = value

            # Add condition
            conditions_default[cond] = new_cond

        return conditions_default

    def get_param_conditions(self):
        # Get the conditions for this parameter
        conditions_param = {}

        for cond, spec in self.param["conditions"].items():
            # Create new conditions
            new_cond = Condition()

            # Remove any bit slices
            pmatch = self.vectrex.match(cond)
            if pmatch:
                cond = pmatch.group(1)

            new_cond.name = cond

            for key, value in spec.items():
                if key == "description":
                    new_cond.description = value
                elif key == "display":
                    new_cond.display = value
                elif key == "unit":
                    new_cond.unit = value
                else:
                    new_cond.spec[key] = value

            # Add condition
            conditions_param[cond] = new_cond

        return conditions_param

    def generate_condition_sets(self, conditions):
        num_sets = 1

        # Get the total number of condition sets
        for cond in conditions:
            num_sets *= max(len(conditions[cond].values), 1)

        # Get the condition sets for each simulation
        # (the unique combinations of all conditions)
        condition_sets = []
        cond_index = [0] * len(conditions)

        for _ in range(num_sets):
            condition_set = {}
            overflow = False

            for index, cond in enumerate(conditions):
                if conditions[cond].values:
                    if conditions[cond].unit:
                        value = conditions[cond].values[cond_index[index]]
                        unit = conditions[cond].unit
                        condition_set[cond] = spice_unit_convert(
                            (str(unit), str(value))
                        )
                    else:
                        condition_set[cond] = str(
                            conditions[cond].values[cond_index[index]]
                        )
                else:
                    condition_set[cond] = None

                # The first condition always increments its index
                if index == 0:
                    cond_index[index] += 1
                # The conditions that come after only increment
                # if the previous condition just overflowed
                elif overflow:
                    cond_index[index] += 1
                    overflow = False

                # Check whether the condition reached its maximum
                if cond_index[index] == max(len(conditions[cond].values), 1):
                    cond_index[index] = 0
                    overflow = True

            condition_sets.append(condition_set)

        return condition_sets

    def get_condition_names_used(self, template, escape=False):
        """
        Read a template file and record all of the variable names that will
        be substituted, so it is clear which local and global conditions
        need to be enumerated.
        """

        if not os.path.isfile(template):
            err(f"No such template file {template}.")
            return

        with open(template, "r") as ifile:
            simtext = ifile.read()

        simlines = simtext.splitlines()

        # Regular expressions
        # varex:		variable name {name}
        if escape:
            if self.datasheet["cace_format"] <= 5.0:
                varex = re.compile(r"\\\{([^ \}\t]+)\\\}")
            else:
                varex = re.compile(r"CACE\\\{([^ \}\t]+)\\\}")
        else:
            if self.datasheet["cace_format"] <= 5.0:
                varex = re.compile(r"\{([^ \}\t]+)\}")
            else:
                varex = re.compile(r"CACE\{([^ \}\t]+)\}")

        conditions = {}

        for line in simlines:
            for patmatch in varex.finditer(line):
                pattern = patmatch.group(1)
                default = None

                # For condition names in the form {cond=value}, use only the name
                if "=" in pattern:
                    pattern, default = pattern.split("=")

                # For condition names in the form {cond|value}, use only the name
                if "|" in pattern:
                    pattern, cond_type = pattern.split("|")

                # Remove any bit slices
                pmatch = self.vectrex.match(pattern)
                if pmatch:
                    pattern = pmatch.group(1)

                # Create new conditions
                new_cond = Condition()
                new_cond.name = pattern
                if default:
                    new_cond.spec["typical"] = default
                conditions[pattern] = new_cond

        return conditions

    def substitute(
        self,
        template_path,
        substituted_path,
        conditions_set,
        conditions,
        reserved,
        escape=False,
    ):
        # Regular expressions
        # varex:		variable name {name}
        # sweepex:		name in {cond|value} format
        # brackrex:		expressions in [expression] format

        if escape:
            if self.datasheet["cace_format"] <= 5.0:
                varex = re.compile(r"\\\{([^\\\}]+)\\\}")
                sweepex = re.compile(r"\\\{([^\\\}]+)\|([^ \\\}]+)\\\}")
                brackrex = re.compile(r"\[([^\]]+)\]")
            else:
                varex = re.compile(r"CACE\\\{([^\\\}]+)\\\}")
                sweepex = re.compile(r"CACE\\\{([^\\\}]+)\|([^ \\\}]+)\\\}")
                brackrex = re.compile(r"CACE\[([^\]]+)\]")
        else:
            if self.datasheet["cace_format"] <= 5.0:
                varex = re.compile(r"\{([^\}]+)\}")
                sweepex = re.compile(r"\{([^\}]+)\|([^ \}]+)\}")
                brackrex = re.compile(r"\[([^\]]+)\]")
            else:
                varex = re.compile(r"CACE\{([^\}]+)\}")
                sweepex = re.compile(r"CACE\{([^\}]+)\|([^ \}]+)\}")
                brackrex = re.compile(r"CACE\[([^\]]+)\]")

        if not os.path.isfile(template_path):
            err(f"Could not find template file {template_path}.")
            self.result_type = ResultType.ERROR
            return

        # Read template into a list
        with open(template_path, "r") as infile:
            template_text = infile.read()

        # Concatenate any continuation lines
        template_lines = template_text.replace("\n+", " ").splitlines()

        def varex_sub(matchobj):
            cond_name = matchobj.group(1)
            dbg(f"Found condition: {cond_name}.")

            # For condition names in the form {cond=value}, use only the name
            if "=" in cond_name:
                cond_name, default = cond_name.split("=")

            # Check for bit slices
            indices = None
            pmatch = self.vectrex.match(cond_name)
            if pmatch:
                cond_name = pmatch.group(1)
                indices = pmatch.group(2).split(":")

            # Check whether the condition is in the set
            if cond_name in conditions_set:

                # Condition not defined
                if conditions_set[cond_name] == None:
                    return matchobj.group(0)

                # Simply replace with the full value
                if not indices:
                    replace = str(conditions_set[cond_name])
                # Extract certain bits
                else:
                    try:

                        # Single bit
                        if len(indices) == 1:
                            # Convert number into binary first
                            length = int(indices[0]) + 1
                            binary = format(
                                int(conditions_set[cond_name]), f"0{length}b"
                            )
                            end = len(binary)
                            replace = binary[end - 1 - int(indices[0])]
                        # Bit slice
                        elif len(indices) == 1:
                            # Convert number into binary first
                            length = max(int(indices[0]) + 1, int(indices[1]) + 1)
                            binary = format(
                                int(conditions_set[cond_name]), f"0{length}b"
                            )
                            end = len(binary)
                            replace = binary[
                                end - 1 - int(indices[0]) : end - int(indices[1])
                            ]
                        else:
                            err(f"This bit slice is not supported: {matchobj.group(1)}")
                            return ""
                    except:
                        err(f"Can't extract bit from: {conditions_set[cond_name]}")
                        return ""

                dbg(f"Replacing with {replace}.")
                return replace
            else:
                err(f"Could not find {cond_name} in condition set.")

            # Error, do not change the condition value
            return matchobj.group(0)

        def sweepex_sub(matchobj):
            cond_name = matchobj.group(1)
            cond_type = matchobj.group(2)
            dbg(f"Found condition: {cond_name} with type {cond_type}.")

            if cond_name in conditions:
                if cond_type in conditions[cond_name].spec:
                    replace = str(conditions[cond_name].spec[cond_type])
                    dbg(f"Replacing with {replace}.")
                    return replace
                else:
                    err(f"Could not find {cond_type} in {cond_name} in conditions.")
            else:
                err(f"Could not find {cond_name} in conditions.")
            return ""

        def brackrex_sub(matchobj):
            expression = matchobj.group(1)
            dbg(f"Found expression: {expression}.")

            try:
                # Avoid catching simple array indexes like "v[0]".
                # Other non-expressions will just throw exceptions
                # when passed to safe_eval().
                btest = int(expression)
                return matchobj.group(0)
            except:
                pass

            try:
                return str(safe_eval(expression))
            except:
                err(f"Invalid expression: {expression}.")
            return matchobj.group(0)

        # Substitute values
        substituted_lines = []
        for template_line in template_lines:

            # Substitute variable name at {name|maximum}
            template_line = sweepex.sub(sweepex_sub, template_line)

            # Substitute variable name {name}
            template_line = varex.sub(varex_sub, template_line)

            # Evaluate expressions [2 + 2]
            template_line = brackrex.sub(brackrex_sub, template_line)

            substituted_lines.append(template_line)

        # Write the output file
        with open(substituted_path, "w") as outfile:
            for line in substituted_lines:
                outfile.write(f"{line}\n")

    def makeplot(
        self,
        plot_name,
        condition_sets,
        conditions,
        results_for_plot,
        collate_variable,
        parent=None,
    ):

        info(
            f'Parameter {self.param["name"]}: Plotting {plot_name} to \'[repr.filename][link=file://{os.path.abspath(self.param_dir)}]{os.path.relpath(self.param_dir)}[/link][/repr.filename]\'…'
        )

        if (
            not "yaxis" in self.param["plot"][plot_name]
            and not "xaxis" in self.param["plot"][plot_name]
        ):
            err(f"Neither yaxis nor xaxis specified in plot {plot_name}.")
            self.result_type = ResultType.ERROR
            return None

        xvariable = None
        if "xaxis" in self.param["plot"][plot_name]:

            xvariable = self.param["plot"][plot_name]["xaxis"]

            # Remove any bit slices
            pmatch = self.vectrex.match(xvariable)
            if pmatch:
                xvariable = pmatch.group(1)

        xdisplay = xvariable
        xunit = ""

        yvariables = []
        if "yaxis" in self.param["plot"][plot_name]:
            yvariables = self.param["plot"][plot_name]["yaxis"]

            # Make a list if there's only a single entry
            if not isinstance(yvariables, list):
                yvariables = [yvariables]

            for i, yvariable in enumerate(yvariables):
                # Remove any bit slices
                pmatch = self.vectrex.match(yvariable)
                if pmatch:
                    yvariables[i] = pmatch.group(1)

        ydisplays = {key: key for key in yvariables}
        yunits = {key: "" for key in yvariables}

        # Get global display and unit
        if "display" in self.param:
            xdisplay = self.param["display"]
        if "unit" in self.param:
            xunit = self.param["unit"]

        # If xvariable is a condition, get display and unit
        if xvariable in conditions:
            if conditions[xvariable].display:
                xdisplay = conditions[xvariable].display

            if conditions[xvariable].unit:
                xunit = conditions[xvariable].unit

        # If yvariable is a condition, get display and unit
        for yvariable in yvariables:
            if yvariable in conditions:
                if conditions[yvariable].display:
                    ydisplays[yvariable] = conditions[yvariable].display

                if conditions[yvariable].unit:
                    yunits[yvariable] = conditions[yvariable].unit

        # Get the plot type
        plot_type = "xyplot"
        if "type" in self.param["plot"][plot_name]:
            plot_type = self.param["plot"][plot_name]["type"]

        # Show limits in plots
        # true: always
        # false: never
        # auto: only if in range
        limits = "auto"
        if "limits" in self.param["plot"][plot_name]:
            limits = self.param["plot"][plot_name]["limits"]

        # Limit values
        minimum = None
        typical = None
        maximum = None

        # Get the limits
        if limits != False:

            # For the histogram get limits from the x variable
            if plot_type == "histogram":
                if xvariable in self.param["spec"]:
                    if "minimum" in self.param["spec"][xvariable]:
                        if "value" in self.param["spec"][xvariable]["minimum"]:
                            value = self.param["spec"][xvariable]["minimum"]["value"]
                            if value != "any":
                                minimum = float(value)

                    if "typical" in self.param["spec"][xvariable]:
                        if "value" in self.param["spec"][xvariable]["typical"]:
                            value = self.param["spec"][xvariable]["typical"]["value"]
                            if value != "any":
                                typical = float(value)

                    if "maximum" in self.param["spec"][xvariable]:
                        if "value" in self.param["spec"][xvariable]["maximum"]:
                            value = self.param["spec"][xvariable]["maximum"]["value"]
                            if value != "any":
                                maximum = float(value)

            # Else get limits from the first y variable
            else:
                if yvariables[0] in self.param["spec"]:
                    if "minimum" in self.param["spec"][yvariables[0]]:
                        if "value" in self.param["spec"][yvariables[0]]["minimum"]:
                            value = self.param["spec"][yvariables[0]]["minimum"][
                                "value"
                            ]
                            if value != "any":
                                minimum = float(value)

                    if "typical" in self.param["spec"][yvariables[0]]:
                        if "value" in self.param["spec"][yvariables[0]]["typical"]:
                            value = self.param["spec"][yvariables[0]]["typical"][
                                "value"
                            ]
                            if value != "any":
                                typical = float(value)

                    if "maximum" in self.param["spec"][yvariables[0]]:
                        if "value" in self.param["spec"][yvariables[0]]["maximum"]:
                            value = self.param["spec"][yvariables[0]]["maximum"][
                                "value"
                            ]
                            if value != "any":
                                maximum = float(value)

        # Overwrite with display and unit under "spec"
        if "spec" in self.param:
            if xvariable in self.param["spec"]:
                if "display" in self.param["spec"][xvariable]:
                    xdisplay = self.param["spec"][xvariable]["display"]
                if "unit" in self.param["spec"][xvariable]:
                    xunit = self.param["spec"][xvariable]["unit"]

            for yvariable in yvariables:
                if yvariable in self.param["spec"]:
                    if "display" in self.param["spec"][yvariable]:
                        ydisplays[yvariable] = self.param["spec"][yvariable]["display"]

                    if "unit" in self.param["spec"][yvariable]:
                        yunits[yvariable] = self.param["spec"][yvariable]["unit"]

        # Overwrite with display and unit under "variables"
        if "variables" in self.param:
            if xvariable in self.param["variables"]:
                if "display" in self.param["variables"][xvariable]:
                    xdisplay = self.param["variables"][xvariable]["display"]
                if "unit" in self.param["variables"][xvariable]:
                    xunit = self.param["variables"][xvariable]["unit"]

            for yvariable in yvariables:
                if yvariable in self.param["variables"]:
                    if "display" in self.param["variables"][yvariable]:
                        ydisplays[yvariable] = self.param["variables"][yvariable][
                            "display"
                        ]

                    if "unit" in self.param["variables"][yvariable]:
                        yunits[yvariable] = self.param["variables"][yvariable]["unit"]

        # Assemble the string displayed at the x-axis
        xdisplay = f"{xdisplay} ({xunit})" if xunit != "" else xdisplay

        # Assemble the string displayed at the y-axis
        ydisplay = ", ".join(
            [
                f"{value} ({unit})" if unit != "" else value
                for value, unit in zip(ydisplays.values(), yunits.values())
            ]
        )

        # Create a new figure
        fig = Figure()
        if parent == None:
            canvas = FigureCanvasAgg(fig)
        else:
            canvas = FigureCanvasTkAgg(fig, parent)

        # Set the title, if given
        if "title" in self.param["plot"][plot_name]:
            fig.suptitle(self.param["plot"][plot_name]["title"])

        # File format
        suffix = ".png"
        if "suffix" in self.param["plot"][plot_name]:
            suffix = self.param["plot"][plot_name]["suffix"]

        # Filename for the plot
        filename = f"{plot_name}{suffix}"

        # Create a new axis for the whole parameter
        ax = fig.add_subplot(111)

        # Set x and y labels
        ax.set_xlabel(xdisplay)
        ax.set_ylabel(ydisplay)

        # Enable the grid
        if "grid" in self.param["plot"][plot_name]:
            if self.param["plot"][plot_name]["grid"]:
                ax.grid(True)

        # Set opacity for histogram
        opacity = 1.0
        if len(condition_sets) > 1:
            opacity = 0.5

        # If the xvariable is a condition, remove it from the condition set
        # since it is displayed on the xaxis anyways and merge the results

        xvalues_list = []
        yvalues_list = []
        label_list = []

        if xvariable in conditions:

            new_condition_sets = []
            new_results_for_plot = []
            hashes = []

            # We only want ticks at certain locations
            try:
                ax.set_xticks(
                    ticks=conditions[xvariable].values,
                    labels=conditions[xvariable].values,
                )
            except:
                ax.set_xticks(
                    ticks=range(len(conditions[xvariable].values)),
                    labels=conditions[xvariable].values,
                )

            # Get the result
            for condition_set, results in zip(condition_sets, results_for_plot):

                # Create a deep copy of the condition set
                condition_set = copy.deepcopy(condition_set)

                # Remove the condition at the xaxis from the condition_set
                condition_set.pop(xvariable)

                # We also need to remove unique elements, or else no hash will match
                condition_set.pop("N")
                condition_set.pop("simpath")

                cur_hash = hash(frozenset(condition_set.items()))

                # Let' see if the condition set is not yet in the new condition sets
                if not cur_hash in hashes:
                    new_condition_sets.append(condition_set)
                    new_results_for_plot.append(copy.deepcopy(results))
                    hashes.append(cur_hash)

                # If it is already, we need to extend the results
                else:
                    for index, this_hash in enumerate(hashes):
                        # Found the condition set
                        if cur_hash == this_hash:
                            # Append to results
                            for key in new_results_for_plot[index].keys():
                                new_results_for_plot[index][key].extend(
                                    list(results[key])
                                )

            condition_sets = new_condition_sets
            results_for_plot = new_results_for_plot

        # Generate the x and y values
        for condition_set, results in zip(condition_sets, results_for_plot):

            xvalues = None
            if xvariable:
                # Is the variable a simulation result?
                if xvariable in results:
                    xvalues = results[xvariable]
                # Else it may be a condition?
                elif xvariable in conditions:
                    xvalues = conditions[xvariable].values
                else:
                    err(f"Unknown variable: {xvariable} in plot {plot_name}.")
                    self.result_type = ResultType.ERROR
                    return None

            xvalues_list.append(xvalues)

            yvalues = []
            for yvariable in yvariables:
                if yvariable:
                    # Is the variable a simulation result?
                    if yvariable in results:
                        yvalues.append(results[yvariable])
                    # Else it may be a condition?
                    elif yvariable in condition_set:
                        yvalues.append(condition_set[yvariable])
                    else:
                        err(f"Unknown variable: {yvariable} in plot {plot_name}.")
                        self.result_type = ResultType.ERROR
                        return None

            yvalues_list.append(yvalues)

            # Get the label for the legend
            label = []
            for condition in condition_set:
                if condition in conditions:
                    # Don't display the condition which was
                    # used to collate the values
                    if condition == collate_variable:
                        continue

                    # Only add conditions with more than one value
                    if len(conditions[condition].values) > 1:
                        label.append(f"{condition} = {condition_set[condition]}")
            label = ", ".join(label)

            label_list.append(label)

        for xvalues, yvalues, label in zip(xvalues_list, yvalues_list, label_list):

            marker = None
            if not isinstance(xvalues, list) or len(xvalues) == 1:
                marker = "o"

            for yvalue in yvalues:

                # Check length of x and y
                if len(xvalues) != len(yvalue):
                    err(
                        f"Length of x and y is not the same ({len(xvalues)}, {len(yvalue)})."
                    )
                    self.result_type = ResultType.ERROR
                    return None

                self.plot(
                    xvalues,
                    yvalue,
                    [ax],
                    plot_type,
                    label,
                    marker,
                    opacity,
                )

            if not yvalues:

                self.plot(
                    xvalues,
                    yvalues,
                    [ax],
                    plot_type,
                    label,
                    marker,
                    opacity,
                )

        # Plot limits
        if limits == True:
            # Use vertical lines
            if plot_type == "histogram":
                for limit in [minimum, typical, maximum]:
                    if limit:
                        ax.axvline(limit, color="black", linestyle=":")
            # Use horizontal lines
            else:
                for limit in [minimum, typical, maximum]:
                    if limit:
                        ax.axhline(limit, color="black", linestyle=":")

        # Only plot limits if in range
        if limits == "auto":
            # Use vertical lines
            if plot_type == "histogram":
                xlim = ax.get_xlim()
                xrange = xlim[1] - xlim[0]

                for limit in [minimum, typical, maximum]:
                    if (
                        limit
                        and (xlim[0] - xrange * 0.5) < limit
                        and (xlim[1] + xrange * 0.5) > limit
                    ):
                        ax.axvline(limit, color="black", linestyle=":")
            # Use horizontal lines
            else:
                ylim = ax.get_ylim()
                yrange = ylim[1] - ylim[0]

                for limit in [minimum, typical, maximum]:
                    if (
                        limit
                        and (ylim[0] - yrange * 0.5) < limit
                        and (ylim[1] + yrange * 0.5) > limit
                    ):
                        ax.axhline(limit, color="black", linestyle=":")

        # Enable the legend
        legend = None
        if len(condition_sets) > 1 or (
            "legend" in self.param["plot"][plot_name]
            and self.param["plot"][plot_name]["legend"]
        ):
            legend = ax.legend(loc=2, bbox_to_anchor=(1.04, 1), borderaxespad=0.0)

        # Save the figure for the whole parameter
        if legend:
            fig.savefig(
                os.path.join(self.param_dir, filename),
                bbox_inches="tight",
                bbox_extra_artists=[legend],
            )
        else:
            fig.savefig(os.path.join(self.param_dir, filename), bbox_inches="tight")

        self.plots_dict[plot_name] = canvas
        return canvas

    def plot(
        self,
        xvalues,
        yvalues,
        axes,
        plot_type="xyplot",
        label=None,
        marker=None,
        alpha=1.0,
    ):
        if plot_type == "histogram":
            for ax in axes:
                ax.hist(
                    xvalues,
                    bins="auto",
                    histtype="bar",
                    label=label,
                    alpha=alpha,
                )
        elif plot_type == "semilogx":
            for ax in axes:
                ax.semilogx(xvalues, yvalues, label=label, marker=marker)
        elif plot_type == "semilogy":
            for ax in axes:
                ax.semilogy(xvalues, yvalues, label=label, marker=marker)
        elif plot_type == "loglog":
            for ax in axes:
                ax.loglog(xvalues, yvalues, label=label, marker=marker)
        elif plot_type == "xyplot":
            for ax in axes:
                ax.plot(xvalues, yvalues, label=label, marker=marker)
        else:
            err(f"Unknown plot type: {plot_type}")
