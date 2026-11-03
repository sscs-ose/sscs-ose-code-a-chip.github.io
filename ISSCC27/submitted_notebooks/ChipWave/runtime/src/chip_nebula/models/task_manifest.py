from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# Centralised default so all layers (interpreter, adapters) share one source of truth.
# When you need to change the threshold, change it here — nowhere else.
DEFAULT_SESSION_TOKEN_THRESHOLD = 220_000


@dataclass
class FileTarget:
    path: str
    status: str  # "create" | "modify" | "keep" | "delete"
    reason: str = ""


@dataclass
class TaskError:
    file: str
    line: int
    code: str
    severity: str  # "ERROR" | "WARNING" | "INFO"
    message: str


@dataclass
class PreviousAttempt:
    iteration: int
    result: str
    agent_notes: str = ""
    error_class: str = ""


@dataclass
class ErrorClassSpec:
    """How a given error class is handled by the stage loop.

    Populated from the merge of platform defaults + agent YAML + stage-level
    override. `route_to` may be `"self"` (terminal failure when budget runs
    out) or a concrete stage name (triggers snap-back when budget runs out).
    """
    name: str
    priority: int = 0
    retry_budget: int = 0
    route_to: str = "self"
    description: str = ""


@dataclass
class PredecessorFailureContext:
    """Injected into a TaskManifest when the stage is the destination of a
    snap-back from a downstream stage that classified its failure.

    The downstream stage is reporting, in effect: "I tried N times; my best
    diagnosis is that the error class is X; here are the structured errors
    and the files I touched. Please fix upstream."
    """
    source_stage: str = ""
    error_class: str = ""
    error_class_reason: str = ""
    errors: list = field(default_factory=list)  # list[TaskError]
    previous_attempts: list = field(default_factory=list)  # list[PreviousAttempt]
    modified_files: list[str] = field(default_factory=list)
    iteration_count: int = 0
    execution_log: str = ""


@dataclass
class TaskContext:
    module: str = ""
    description: str = ""
    interface_doc: str = ""
    top_module: str = ""
    system_prompt: str = ""


@dataclass
class PredecessorInfo:
    statuses: dict[str, str] = field(default_factory=dict)
    files: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    decisions: list[str] = field(default_factory=list)
    interface_changes: dict[str, list[dict]] = field(default_factory=dict)
    failures: Optional[list] = None
    logs: dict[str, str] = field(default_factory=dict)


@dataclass
class TaskManifest:
    task_id: str
    feature_id: str
    stage: str
    assigned_agent: str
    context: TaskContext = field(default_factory=TaskContext)
    target: list[FileTarget] = field(default_factory=list)
    errors: list[TaskError] = field(default_factory=list)
    completion_criteria: list[str] = field(default_factory=list)
    # Human-readable rendering of immutable, recipe-declared file contracts.
    # Kept separate from completion_criteria so adapters do not present files
    # the Agent must produce as opaque post-run Gates.
    artifact_output_contracts: list[str] = field(default_factory=list)
    previous_attempt: Optional[PreviousAttempt] = None
    parent_task: str = ""
    iteration: int = 0
    max_iterations: int = 5
    pipeline: str = ""
    description: str = ""
    framework: str = "opencode"
    relevant_skills: list[str] = field(default_factory=list)
    timeout: int = 10800
    # Mutable per-Run timeout control written by the Task Graph runtime.  It is
    # deliberately separate from the immutable Task timeout: the dashboard may
    # extend the deadline of an already running attempt.
    timeout_control_path: str = ""
    run_id: str = ""
    max_turns_per_session: int = 30
    predecessor_info: Optional[PredecessorInfo] = None
    predecessor_failure_context: Optional[PredecessorFailureContext] = None
    model: str = ""
    model_provider: str = ""
    # Optional framework-native reasoning level.  Keeping this explicit in the
    # immutable Attempt contract avoids depending on a developer's global CLI
    # configuration, which can otherwise turn the same Task into a multi-hour
    # run on another machine.
    reasoning_effort: str = ""
    # Glob allow-list inherited from the agent YAML. Post-run the adapter
    # checks every changed path in the worktree against this; any path not
    # matching is flagged as scope_violation. Empty list = no enforcement.
    write_paths: list[str] = field(default_factory=list)
    # TaskGraph v2 carries the complete Task permission snapshot. Adapters that
    # can enforce read/tool access do so before dispatch; every adapter receives
    # the same values in the immutable prompt even when its host cannot provide
    # an OS-level read sandbox.
    read_paths: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    reuse_session: bool = False
    session_id: str = ""
    # Full prompt sovereignty escape hatch for non-pipeline orchestrators
    # (e.g. the roundtable feature). When set, adapters return this verbatim
    # from their prompt builder, skipping build_agent_prompt /
    # build_continuation_prompt entirely (including _FINAL_INSTRUCTION).
    # Pipeline code never sets it, so pipeline prompts are byte-identical.
    prompt_override: Optional[str] = None
    # Direct-edit desktop tasks operate in the user's current checkout.  Their
    # caller owns snapshot-based rollback; adapters must never run git checkout
    # there because that could destroy pre-existing staged/unstaged content.
    live_workspace: bool = False
    # Per-stage cached-token threshold. When the adapter estimates that a
    # reused session has consumed at least this many cached input tokens, it
    # forces a fresh session to avoid third-party-provider context-window
    # mis-detection that silently truncates long conversations.
    session_token_threshold: int = DEFAULT_SESSION_TOKEN_THRESHOLD

    def to_dict(self) -> dict:
        result = {
            "task_id": self.task_id,
            "feature_id": self.feature_id,
            "parent_task": self.parent_task,
            "pipeline": self.pipeline,
            "stage": self.stage,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "assigned_agent": self.assigned_agent,
            "description": self.description,
            "context": {
                "module": self.context.module,
                "description": self.context.description,
                "interface_doc": self.context.interface_doc,
                "top_module": self.context.top_module,
            },
            "target": {
                "files": [
                    {"path": f.path, "status": f.status, "reason": f.reason}
                    for f in self.target
                ]
            },
            "errors": [
                {
                    "file": e.file, "line": e.line, "code": e.code,
                    "severity": e.severity, "message": e.message,
                }
                for e in self.errors
            ],
            "completion_criteria": self.completion_criteria,
            "artifact_output_contracts": self.artifact_output_contracts,
            "read_paths": self.read_paths,
            "write_paths": self.write_paths,
            "allowed_tools": self.allowed_tools,
            "framework": self.framework,
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
        }
        if self.previous_attempt:
            result["previous_attempt"] = {
                "iteration": self.previous_attempt.iteration,
                "result": self.previous_attempt.result,
                "agent_notes": self.previous_attempt.agent_notes,
                "error_class": self.previous_attempt.error_class,
            }
        if self.predecessor_info:
            pi = self.predecessor_info
            result["predecessor_info"] = {
                "statuses": pi.statuses,
                "files": pi.files,
                "metrics": pi.metrics,
                "decisions": pi.decisions,
                "interface_changes": pi.interface_changes,
                "failures": pi.failures,
                "logs": pi.logs,
            }
        if self.predecessor_failure_context:
            pfc = self.predecessor_failure_context
            result["predecessor_failure_context"] = {
                "source_stage": pfc.source_stage,
                "error_class": pfc.error_class,
                "error_class_reason": pfc.error_class_reason,
                "errors": [
                    {"file": e.file, "line": e.line, "code": e.code,
                     "severity": e.severity, "message": e.message}
                    for e in pfc.errors
                ],
                "previous_attempts": [
                    {"iteration": pa.iteration, "result": pa.result,
                     "agent_notes": pa.agent_notes, "error_class": pa.error_class}
                    for pa in pfc.previous_attempts
                ],
                "modified_files": pfc.modified_files,
                "iteration_count": pfc.iteration_count,
            }
        result["reuse_session"] = self.reuse_session
        result["session_id"] = self.session_id
        return result


@dataclass
class AgentResult:
    success: bool
    files_modified: list[str] = field(default_factory=list)
    execution_log: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    duration_seconds: float = 0.0
    error: Optional[str] = None
    session_id: str = ""
    cache_read_input_tokens: int = 0


@dataclass
class StageArtifact:
    stage_name: str
    iteration: int
    passed: bool
    timestamp: datetime = field(default_factory=datetime.now)
    files_modified: list[str] = field(default_factory=list)
    files_created: list[str] = field(default_factory=list)
    gate_reports: list = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    decisions: list[str] = field(default_factory=list)
    interface_changes: list[dict] = field(default_factory=list)
    current_status: str = "PENDING"
    previous_attempt: Optional[dict] = None
    pending_failure_context: Optional[dict] = None
    session_id: str = ""
    execution_log: str = ""

    def __post_init__(self):
        if self.current_status == "PENDING":
            self.current_status = "PASS" if self.passed else "FAIL"


@dataclass
class FailedStageInfo:
    stage: str
    iteration: int
    errors: list[dict] = field(default_factory=list)


@dataclass
class AggregatedArtifact:
    all_passed: bool = True
    all_files_modified: set = field(default_factory=set)
    all_files_created: set = field(default_factory=set)
    metrics: dict[str, float] = field(default_factory=dict)
    decisions: list[str] = field(default_factory=list)
    interface_changes: dict[str, list[dict]] = field(default_factory=dict)
    failures: list[FailedStageInfo] = field(default_factory=list)


@dataclass
class StageResult:
    name: str
    passed: bool
    iteration: int = 0
    gate_reports: list = field(default_factory=list)
    execution_log: str = ""
    files_modified: list[str] = field(default_factory=list)
    rollback_target: Optional[str] = None
    # True when rollback_target is a FORWARD route (target is downstream of
    # this stage): the stage is promoted to passed-with-caveat and the target
    # subtree is reset, instead of the classic snap-back reset of self+target.
    route_forward: bool = False
    failure_context: Optional[PredecessorFailureContext] = None
    previous_attempt: Optional[dict] = None
    session_id: str = ""


@dataclass
class PipelineResult:
    all_passed: bool
    stage_results: dict[str, StageResult] = field(default_factory=dict)
    total_iterations: int = 0
    duration_seconds: float = 0.0
    # Stages left in "stopped" at the end of the run (user-suspended).
    # They do NOT fail the verdict, but are surfaced for annotation.
    stopped_stages: list[str] = field(default_factory=list)
    # Stopped stages plus any pending stages stranded downstream of them
    # (they could never become ready). Purely informational.
    suspended_stages: list[str] = field(default_factory=list)


@dataclass
class PipelineState:
    feature_id: str
    current_stage: str = ""
    stage_status: dict[str, str] = field(default_factory=dict)
    iteration_counts: dict[str, int] = field(default_factory=dict)
    last_updated: str = ""


@dataclass
class Workspace:
    id: str
    root: Path = field(default_factory=Path)
    spec_dir: Path = field(default_factory=Path)
    rtl_dir: Path = field(default_factory=Path)
    tb_dir: Path = field(default_factory=Path)
    constraints_dir: Optional[Path] = None
    results_dir: Path = field(default_factory=Path)
    pipeline_state: Optional[PipelineState] = None


@dataclass
class ExitCriterion:
    type: str  # tool_check | coverage_check | metric_check | file_check | regex_check | post_route_consistency | report_verdict
    level: str = "L1"
    command: str = ""
    expected: str = ""
    timeout: int = 120
    metric: str = ""
    operator: str = ">="
    threshold: float = 0.0
    source: str = ""
    paths: list[str] = field(default_factory=list)
    min_files: int = 0
    # Regex-check specific fields
    pattern: str = ""              # regex pattern to search for
    must_not_match: bool = True    # if True, fail when pattern is found
    must_match: bool = False       # if True, fail when pattern is NOT found (inverse of must_not_match)
    error_class: str = ""          # error class to inject on failure
    on_failure: str = ""            # retry | agent_decides | report
