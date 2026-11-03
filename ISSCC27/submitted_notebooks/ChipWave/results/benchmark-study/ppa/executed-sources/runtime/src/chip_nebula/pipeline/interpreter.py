"""DAG-level pipeline interpreter with per-class retry budgets and snap-back.

The interpreter has two scheduling layers:

* **Global DAG** (`run()` main loop) — submits stages whose `depends_on` is
  satisfied; responds to their completion results by updating stage_status
  and handling snap-back signals.

* **Local stage loop** (`_execute_stage_loop`) — iterates on one stage,
  reading the agent's `Error-Class:` markers each round and keeping
  accumulated per-class counters against each class's `retry_budget`.
  Terminal paths produce one of three return shapes:

    - StageResult(passed=True, ...) — gates all passed
    - StageResult(passed=False, rollback_target=X, ...) — snap-back request
    - StageResult(passed=False, rollback_target=None, ...) — terminal failure

Snap-back cascading: when a snap-back is requested, the main loop resets
`target`, `self`, and the transitive downstream subtree rooted at `target`
back to `pending`. The DAG then naturally re-submits them as their
dependencies are re-satisfied. A `global_rollback_budget` counter bounds
this to prevent oscillation.
"""
from collections import defaultdict, deque
from concurrent.futures import Future, ThreadPoolExecutor, wait as fut_wait
from datetime import datetime
from pathlib import Path
from typing import Optional
import threading

_NL = chr(10)

from chip_nebula.gates.error_parser import parse_errors_from_reports
from chip_nebula.models.gate_report import GateReport
from chip_nebula.models.task_manifest import (
    DEFAULT_SESSION_TOKEN_THRESHOLD,
    AggregatedArtifact,
    ErrorClassSpec,
    ExitCriterion,
    FileTarget,
    PipelineResult,
    PredecessorFailureContext,
    PredecessorInfo,
    PreviousAttempt,
    StageResult,
    TaskContext,
    TaskError,
    TaskManifest,
)
from chip_nebula.pipeline.artifact_store import PipelineArtifactStore
from chip_nebula.pipeline.context import PipelineContext
from chip_nebula.pipeline.error_classes import (
    parse_error_classes_from_log,
    pick_winner_class,
    resolve_error_classes,
)
from chip_nebula.pipeline.parser import PipelineConfig
from chip_nebula.adapters.base import build_git_discipline, session_registry


class PipelineError(Exception):
    pass


_DEFAULT_GLOBAL_ROLLBACK_BUDGET = 5


def _summarize_failure(gate_results, agent_result, class_name: str, reason: str) -> str:
    """One-paragraph description of why an iteration failed, stored in
    PreviousAttempt.agent_notes and shown to the next agent run.
    """
    parts: list[str] = [f"class={class_name}"]
    if reason:
        parts.append(f"reason={reason[:200]}")
    failed = getattr(gate_results, "failed", None) or []
    for r in failed[:2]:
        evidence = (getattr(r, "evidence", "") or "").strip()
        if evidence:
            parts.append(f"[{getattr(r, 'check_type', '?')}] {evidence[:200]}")
    if agent_result is not None:
        err = getattr(agent_result, "error", None)
        if err:
            parts.append(f"adapter_error={str(err)[:200]}")
    return " | ".join(parts)


class DAGPipelineInterpreter:
    def __init__(
        self,
        pipeline_config: PipelineConfig,
        *,
        artifact_dir: Optional[Path] = None,
        reuse_sessions: bool = True,
    ):
        self.config = pipeline_config
        self.stages = pipeline_config.stages
        self.stage_names = set(self.stages.keys())
        self.dependency_graph = self._build_graph()
        self._detect_cycles()
        self.stage_status: dict[str, str] = {}
        self.stage_results: dict[str, StageResult] = {}
        self.iteration_counters: dict[str, int] = defaultdict(int)
        self.artifact_store = PipelineArtifactStore(persist_dir=artifact_dir)
        self._pending_failure_contexts: dict[str, PredecessorFailureContext] = {}
        self._session_ids: dict[str, list[str]] = {}
        self._reuse_sessions: bool = reuse_sessions
        self.feature_id: str = ""
        self.top_module: str = ""
        self.framework: str = ""
        self._current_workspace: Optional[Path] = None
        raw_budget = getattr(pipeline_config, "global_rollback_budget", None)
        self.global_rollback_budget = int(
            raw_budget if raw_budget is not None else _DEFAULT_GLOBAL_ROLLBACK_BUDGET
        )
        self.rollbacks_executed = 0

        for name in self.stage_names:
            self.stage_status[name] = "pending"

    # ------------------------------------------------------------------ DAG

    def _build_graph(self) -> dict[str, set[str]]:
        graph: dict[str, set[str]] = defaultdict(set)
        for name, stage in self.stages.items():
            for dep in stage.get("depends_on", []):
                if dep not in self.stages:
                    raise PipelineError(
                        f"Stage '{name}' depends_on '{dep}' which is not defined"
                    )
                graph[dep].add(name)
        return graph

    def _detect_cycles(self):
        visited: set[str] = set()
        path: list[str] = []

        def dfs(node: str):
            if node in path:
                cycle_start = path.index(node)
                cycle = " -> ".join(path[cycle_start:] + [node])
                raise PipelineError(f"Cycle detected: {cycle}")
            if node in visited:
                return
            visited.add(node)
            path.append(node)
            for next_node in self.dependency_graph.get(node, set()):
                dfs(next_node)
            path.pop()

        for name in self.stage_names:
            dfs(name)

    def _ready_stages(self) -> list[str]:
        ready: list[str] = []
        for name in self.stage_names:
            # "stopped" is treated as intentionally suspended by the user and
            # must not be rescheduled until an explicit resume/Inject operation
            # or a snap-back resets it to pending.
            # "skipped" is set by Inject/from-stage operations on non-passed
            # upstream stages: never scheduled, but counts as satisfied for
            # dependency purposes (the user takes responsibility for the
            # workspace state upstream of the inject point).
            if self.stage_status[name] in ("running", "passed", "failed", "blocked", "stopped", "skipped"):
                continue
            deps = self.stages[name].get("depends_on", [])
            if any(self.stage_status.get(d) in ("failed", "blocked") for d in deps):
                # Transitively block downstream stages so the DAG terminates.
                self.stage_status[name] = "blocked"
                continue
            if all(self.stage_status.get(d) in ("passed", "skipped") for d in deps):
                ready.append(name)
        return ready

    def _downstream_closure(self, start: str) -> set[str]:
        """Return all stages transitively downstream of `start` (excluding
        `start` itself). Used to compute the snap-back reset subtree.
        """
        seen: set[str] = set()
        q = deque([start])
        while q:
            node = q.popleft()
            for succ in self.dependency_graph.get(node, set()):
                if succ in seen:
                    continue
                seen.add(succ)
                q.append(succ)
        return seen

    def _do_snap_back(self, self_stage: str, target: str) -> None:
        """Reset target + self + downstream subtree back to pending so the
        DAG naturally re-submits them.

        Precondition: caller has already checked global_rollback_budget.
        """
        # Drop any cached StageResult for stages being re-run so the final
        # pipeline verdict reflects the final re-run results only.
        to_reset = {target, self_stage}
        to_reset.update(self._downstream_closure(target))
        for name in to_reset:
            self.stage_status[name] = "pending"
            self.stage_results.pop(name, None)
            self.iteration_counters[name] = 0
            # Force a fresh agent session on re-run. The upstream failure
            # context is already injected into the new TaskManifest, so a
            # clean session avoids stale conversation state and oversized
            # context windows.
            self._session_ids.pop(name, None)

    def _do_forward_route(
        self, self_stage: str, result: StageResult, context: PipelineContext
    ) -> None:
        """Forward route: `result.rollback_target` is downstream of
        `self_stage`. Promote self to passed-with-caveat so the DAG can
        schedule the route target, and reset the target subtree to pending.

        Unlike `_do_snap_back`, self is NOT reset (its partial output is
        accepted as-is), and no rollback budget is consumed — the pipeline
        is moving in its natural downstream direction (e.g. rtl_coding
        reporting ut_env_defect routes forward to lint_review so the UT
        environment gets rebuilt downstream).
        """
        target = result.rollback_target
        to_reset = {target}
        to_reset.update(self._downstream_closure(target))
        to_reset.discard(self_stage)
        for name in to_reset:
            self.stage_status[name] = "pending"
            self.stage_results.pop(name, None)
            self.iteration_counters[name] = 0
            # Fresh agent session on re-run, same rationale as snap-back.
            self._session_ids.pop(name, None)

        forwarded = StageResult(
            name=self_stage,
            passed=True,
            iteration=result.iteration,
            gate_reports=list(result.gate_reports) + [GateReport(
                level="L1", check_type="pipeline", passed=True,
                evidence=(
                    f"forward-routed to '{target}' before all gates passed; "
                    "remaining gate failures are deferred downstream"
                ),
                suggestion="",
            )],
            execution_log=result.execution_log,
            files_modified=list(result.files_modified),
            session_id=result.session_id,
        )
        self.stage_status[self_stage] = "passed"
        self.stage_results[self_stage] = forwarded
        self.artifact_store.record(self_stage, forwarded, context)

    def run(
        self,
        context: PipelineContext,
        max_workers: int = 8,
        adapter=None,
        exit_gate=None,
        workspace_manager=None,
        stop_event: threading.Event | None = None,
    ) -> PipelineResult:
        self._exec_adapter = adapter
        self._exit_gate = exit_gate
        self._wm = workspace_manager

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures: dict[str, Future] = {}

            while True:
                if stop_event is not None and stop_event.is_set():
                    return self._handle_stop_during_run(futures, context)

                ready = self._ready_stages()

                for name in ready:
                    if name not in futures:
                        self.stage_status[name] = "running"
                        if self._current_workspace:
                            self.save_state(self._current_workspace)
                        deps = self.stages[name].get("depends_on", [])
                        aggregated = self.artifact_store.get_aggregated(deps)
                        stage_ctx = context.clone()
                        stage_ctx.set_predecessor_info(aggregated)
                        pending_ctx = self._pending_failure_contexts.pop(name, None)
                        futures[name] = executor.submit(
                            self._execute_stage_loop, name, stage_ctx, pending_ctx,
                        )

                if not futures:
                    break

                done, _ = fut_wait(futures.values(), return_when="FIRST_COMPLETED", timeout=1)

                for future in done:
                    stage_name = self._find_key(futures, future)
                    try:
                        result = future.result()
                    except Exception as exc:
                        result = StageResult(
                            name=stage_name, passed=False, iteration=0,
                            gate_reports=[GateReport(
                                level="L1", check_type="system",
                                passed=False,
                                evidence=str(exc),
                                suggestion="Check pipeline configuration",
                            )],
                        )

                    del futures[stage_name]

                    if result.rollback_target and result.route_forward:
                        # Forward route: the target is DOWNSTREAM of this
                        # stage, so this is the pipeline moving in its
                        # natural direction — it is not a rollback and does
                        # NOT consume global_rollback_budget.
                        agent_type = self.stages[stage_name].get("agent", "unknown")
                        agent_cfg = self._load_agent_cfg(agent_type)
                        self._stage_deliverables(
                            stage_name, self.stages[stage_name], agent_cfg,
                            result.session_id or "",
                        )
                        # Carry the classified failure context forward so the
                        # route target's next run can render it.
                        if result.failure_context is not None:
                            self._pending_failure_contexts[result.rollback_target] = result.failure_context
                        self._do_forward_route(stage_name, result, context)
                        self.artifact_store.record(
                            f"{stage_name}.forward-{result.rollback_target}",
                            result, context,
                        )
                        if self._current_workspace:
                            self.save_state(self._current_workspace)
                        continue

                    if result.rollback_target and self.rollbacks_executed < self.global_rollback_budget:
                        # Before snap-back, git-add the failing stage's
                        # in-scope deliverables so the rollback target starts
                        # from a clean committed workspace.
                        agent_type = self.stages[stage_name].get("agent", "unknown")
                        agent_cfg = self._load_agent_cfg(agent_type)
                        self._stage_deliverables(
                            stage_name, self.stages[stage_name], agent_cfg,
                            result.session_id or "",
                        )

                        # Carry forward the classified failure context so the
                        # rollback target's next run can render it.
                        if result.failure_context is not None:
                            self._pending_failure_contexts[result.rollback_target] = result.failure_context
                        self._do_snap_back(stage_name, result.rollback_target)
                        self.rollbacks_executed += 1
                        # Record this rolled-back result under a historical
                        # key so the artifact store keeps a trail.
                        self.artifact_store.record(
                            f"{stage_name}.rollback-{self.rollbacks_executed}",
                            result, context,
                        )
                        if self._current_workspace:
                            self.save_state(self._current_workspace)
                        continue

                    # Terminal path: promote to passed/failed and record.
                    if result.rollback_target:
                        # Wanted to rollback but budget exhausted; annotate.
                        result.gate_reports = list(result.gate_reports) + [GateReport(
                            level="L1", check_type="pipeline", passed=False,
                            evidence=(
                                f"global_rollback_budget ({self.global_rollback_budget}) "
                                f"exhausted; rollback to '{result.rollback_target}' denied"
                            ),
                            suggestion="Raise global_rollback_budget or investigate oscillation.",
                        )]
                        result.rollback_target = None

                    self.stage_status[stage_name] = "passed" if result.passed else "failed"
                    self.stage_results[stage_name] = result
                    self.artifact_store.record(stage_name, result, context)
                    if self._current_workspace:
                        self.save_state(self._current_workspace)

        # Verdict is three-way:
        #   - any failed/blocked   → FAILED
        #   - otherwise            → PASSED, where stages left "stopped"
        #     (user-suspended) or left "pending" downstream of a stopped
        #     stage (they could never become ready, since stopped does not
        #     satisfy dependencies) count as suspended, not failure.
        stopped_stages = sorted(
            n for n, s in self.stage_status.items() if s == "stopped"
        )
        suspended = set(stopped_stages)
        for name in stopped_stages:
            suspended.update(self._downstream_closure(name))
        any_failed = any(
            s in ("failed", "blocked") for s in self.stage_status.values()
        )
        all_passed = not any_failed and all(
            s in ("passed", "skipped") or n in suspended
            for n, s in self.stage_status.items()
        )
        suspended_stages = sorted(
            n for n in suspended
            if self.stage_status.get(n) in ("stopped", "pending")
        )
        total_iters = sum(r.iteration for r in self.stage_results.values())
        return PipelineResult(
            all_passed=all_passed,
            stage_results=self.stage_results,
            total_iterations=total_iters,
            stopped_stages=stopped_stages,
            suspended_stages=suspended_stages,
        )

    def _handle_stop_during_run(
        self,
        futures: dict[str, Future],
        context: PipelineContext,
    ) -> PipelineResult:
        """Gracefully stop a running pipeline: cancel pending futures, terminate
        active adapter sessions, mark running stages as stopped, and save state.
        """
        running = list(futures.keys())
        for future in futures.values():
            if not future.done():
                future.cancel()

        for stage_name in running:
            self.stage_status[stage_name] = "stopped"
            feature_id = self.feature_id or self.stages[stage_name].get("feature", "default")
            active_session = session_registry.get(feature_id, stage_name)
            if not active_session:
                session_ids = self._session_ids.get(stage_name, [])
                active_session = session_ids[-1] if session_ids else ""
            if active_session and self._exec_adapter is not None:
                if hasattr(self._exec_adapter, "terminate"):
                    self._exec_adapter.terminate(active_session)

        if self._current_workspace:
            self.save_state(self._current_workspace)

        stopped_stages = sorted(
            n for n, s in self.stage_status.items() if s == "stopped"
        )
        suspended = set(stopped_stages)
        for name in stopped_stages:
            suspended.update(self._downstream_closure(name))
        any_failed = any(
            s in ("failed", "blocked") for s in self.stage_status.values()
        )
        all_passed = not any_failed and all(
            s in ("passed", "skipped") or n in suspended
            for n, s in self.stage_status.items()
        )
        suspended_stages = sorted(
            n for n in suspended
            if self.stage_status.get(n) in ("stopped", "pending")
        )
        total_iters = sum(r.iteration for r in self.stage_results.values())
        return PipelineResult(
            all_passed=all_passed,
            stage_results=self.stage_results,
            total_iterations=total_iters,
            stopped_stages=stopped_stages,
            suspended_stages=suspended_stages,
        )

    def _find_key(self, futures: dict[str, Future], future: Future) -> str:
        for key, val in futures.items():
            if val is future:
                return key
        return "unknown"

    def _resolve_templates(self, stage: dict) -> dict:
        import copy
        resolved = copy.deepcopy(stage)
        replacements = {}
        if self.feature_id:
            replacements["{feature_id}"] = self.feature_id
        if self.top_module:
            replacements["{top_module}"] = self.top_module
        if not replacements:
            return resolved
        def _walk(obj):
            if isinstance(obj, dict):
                return {k: _walk(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_walk(v) for v in obj]
            if isinstance(obj, str):
                for placeholder, value in replacements.items():
                    obj = obj.replace(placeholder, value)
                return obj
            return obj
        return _walk(resolved)

    # ---------------------------------------------------------------- stage

    def _execute_stage_loop(
        self, stage_name: str, context: PipelineContext,
        predecessor_failure: Optional[PredecessorFailureContext],
    ) -> StageResult:
        stage = self.stages[stage_name]
        stage_max_iter = int(stage.get("max_iterations", 3))
        max_iter = stage.get("max_iterations", stage_max_iter)
        import sys
        print(f"  [{stage_name}] starting (agent={stage.get('agent','?')}, max_iter={max_iter})", file=sys.stderr, flush=True)

        agent_type = stage.get("agent", "rtl-designer")
        agent_cfg = self._load_agent_cfg(agent_type)
        class_specs = resolve_error_classes(agent_cfg, stage)

        iter_by_class: dict[str, int] = defaultdict(int)
        history: list[PreviousAttempt] = []
        last_gate_results = None
        last_agent_result = None
        last_class = ""
        last_reason = ""
        carried_errors: list[TaskError] = []
        previous_attempt: Optional[PreviousAttempt] = None

        for total_iter in range(1, stage_max_iter + 1):
            self.iteration_counters[stage_name] = total_iter

            import sys
            print(f"  [{stage_name}] iter {total_iter}/{stage_max_iter} running...", file=sys.stderr, flush=True)

            agent_result = self._run_agent(
                stage_name, stage, context,
                carried_errors=carried_errors,
                previous_attempt=previous_attempt,
                predecessor_failure=predecessor_failure,
                agent_cfg=agent_cfg,
                class_specs=class_specs,
            )
            last_agent_result = agent_result
            session_id = (
                getattr(agent_result, "session_id", "") or ""
                if agent_result is not None
                else ""
            )
            if session_id:
                self._session_ids.setdefault(stage_name, []).append(session_id)

            # ---- Plan B: inter-iteration token fuse ----
            if agent_result is not None:
                cache_read = getattr(agent_result, "cache_read_input_tokens", 0)
                threshold = stage.get("session_token_threshold", DEFAULT_SESSION_TOKEN_THRESHOLD)
                if cache_read >= threshold:
                    print(
                        f"  [{stage_name}] cache_read_input_tokens={cache_read} >= {threshold}; "
                        "forcing new session on next iteration.",
                        file=sys.stderr, flush=True,
                    )
                    self._session_ids[stage_name] = []

            # If the agent succeeded, check gates. Otherwise skip gate check
            # and classify whatever context we have (parsed tag, or fall
            # back to transient_error).
            agent_ok = bool(getattr(agent_result, "success", False)) if agent_result is not None else False
            gate_results = None
            if agent_ok:
                gate_results = self._run_gates(stage_name, stage, context)
                last_gate_results = gate_results
                if gate_results.all_passed:
                    # After gates pass, ask the agent to stage deliverable files
                    # so that subsequent scope checks can distinguish tracked
                    # legal changes from untracked artifacts.
                    staging_ok, staging_log = self._stage_deliverables(
                        stage_name, stage, agent_cfg, session_id
                    )
                    execution_log = agent_result.execution_log or ""
                    if staging_log:
                        execution_log += _NL + "[post-gate staging]" + _NL + staging_log
                    if staging_ok:
                        iter_result = StageResult(
                            name=stage_name,
                            passed=True,
                            iteration=total_iter,
                            gate_reports=gate_results.reports,
                            execution_log=execution_log,
                            files_modified=list(agent_result.files_modified or []),
                            previous_attempt=_attempt_to_dict(previous_attempt) if previous_attempt else None,
                            session_id=session_id,
                        )
                        self.artifact_store.record(
                            f"{stage_name}.iter-{total_iter}", iter_result, context
                        )
                        if self._current_workspace:
                            self.save_state(self._current_workspace)
                        return iter_result

                    # Staging failed.  Pretend the agent failed so the normal
                    # classification path below retries/escalates.
                    agent_result.success = False
                    agent_result.execution_log = execution_log
                    agent_result.error = "post-gate git-add staging failed"
                    agent_ok = False

            # Classify the iteration.
            log_text = getattr(agent_result, "execution_log", "") or ""
            # The agent's own self-classification is more informed than the
            # static error_class tags gates inject into their evidence, so
            # parse the agent log FIRST. Only when the agent reported
            # nothing do we fall back to gate-injected markers (e.g.
            # regex_check's blocking_defect, tool_check's configured
            # error_class). This keeps a gate's static tag from out-prioritizing
            # an explicit agent report (e.g. rtl_bug 88 vs ut_env_defect 70).
            tagged_pairs = parse_error_classes_from_log(log_text)
            if not tagged_pairs and gate_results is not None:
                gate_text = ""
                for report in getattr(gate_results, "reports", []) or []:
                    if not getattr(report, "passed", True) and getattr(report, "evidence", ""):
                        gate_text += _NL + report.evidence
                tagged_pairs = parse_error_classes_from_log(gate_text)
            if tagged_pairs:
                reported_classes = [n for n, _ in tagged_pairs]
                reason_by_class = {n: r for n, r in tagged_pairs}
            else:
                reported_classes = []
                reason_by_class = {}

            if not agent_ok and not reported_classes:
                # Adapter-detected scope violation takes priority over
                # transient_error so the stage retries with scope-violation
                # context instead of silently treating it as a crash.
                agent_error = getattr(agent_result, "error", "") or ""
                if "scope violation" in agent_error.lower():
                    reported_classes = ["scope_violation"]
                    reason_by_class["scope_violation"] = agent_error
                else:
                    # Crash/timeout without a tag → transient.
                    reported_classes = ["transient_error"]
                    reason_by_class["transient_error"] = (
                        agent_error or "agent execution failed"
                    )
            elif not reported_classes:
                # Completed but did not tag + gate failed.
                reported_classes = ["unknown"]
                reason_by_class["unknown"] = "gate failed, agent did not tag an error class"

            winner = pick_winner_class(reported_classes, class_specs)
            last_class = winner
            last_reason = reason_by_class.get(winner, "")

            import sys
            print(
                f"  [{stage_name}] iter {total_iter} FAILED — class={winner}, "
                f"reason={last_reason[:300]}",
                file=sys.stderr, flush=True,
            )

            # Every reported class (that's known) gets its counter bumped —
            # this is the "accumulating" semantics users chose.
            for name in reported_classes:
                if name in class_specs:
                    iter_by_class[name] += 1
                else:
                    iter_by_class["unknown"] += 1

            # Structured errors for the next iteration's manifest (A7).
            if gate_results is not None:
                tool_hint = self._tool_hint_for_stage(stage)
                carried_errors = parse_errors_from_reports(
                    gate_results.failed if hasattr(gate_results, "failed") else [],
                    tool_hint=tool_hint,
                )
            else:
                carried_errors = []

            previous_attempt = PreviousAttempt(
                iteration=total_iter,
                result="failed",
                agent_notes=_summarize_failure(gate_results, agent_result, winner, last_reason),
                error_class=winner,
            )
            history.append(previous_attempt)
            iter_result = StageResult(
                name=stage_name,
                passed=False,
                iteration=total_iter,
                gate_reports=list(gate_results.reports) if gate_results else [],
                execution_log=getattr(agent_result, "execution_log", "") or "",
                files_modified=list(getattr(agent_result, "files_modified", []) or []),
                previous_attempt=_attempt_to_dict(history[-2]) if len(history) >= 2 else None,
                session_id=session_id,
            )
            self.artifact_store.record(
                f"{stage_name}.iter-{total_iter}", iter_result, context
            )
            if self._current_workspace:
                self.save_state(self._current_workspace)

            # Decide: retry this stage, or escalate (snap-back or terminal)?
            # retry_budget=N means "tolerate this class up to N occurrences,
            # escalate on the (N+1)th". Since we bumped the counter above,
            # we compare the post-bump counter directly:
            #   budget=0 → counter=1>0 on first occurrence → escalate
            #   budget=3 → counter=1..3 stays, counter=4>3 → escalate
            winner_spec = class_specs[winner]
            if iter_by_class[winner] > winner_spec.retry_budget:
                return self._escalate(
                    stage_name=stage_name,
                    stage=stage,
                    winner=winner,
                    winner_spec=winner_spec,
                    reason=last_reason,
                    reported=reported_classes,
                    gate_results=gate_results,
                    agent_result=agent_result,
                    history=history,
                    carried_errors=carried_errors,
                    total_iter=total_iter,
                )

        # Ran out of stage-level iterations with neither a pass nor an
        # escalation trigger. Escalate using the last winning class.
        return self._escalate(
            stage_name=stage_name,
            stage=stage,
            winner=last_class or "unknown",
            winner_spec=class_specs.get(last_class or "unknown",
                                        class_specs["unknown"]),
            reason=last_reason or f"stage max_iterations={stage_max_iter} reached",
            reported=[last_class] if last_class else ["unknown"],
            gate_results=last_gate_results,
            agent_result=last_agent_result,
            history=history,
            carried_errors=carried_errors,
            total_iter=stage_max_iter,
        )

    def _escalate(
        self, *, stage_name: str, stage: dict,
        winner: str, winner_spec: ErrorClassSpec,
        reason: str,
        reported: list[str],
        gate_results,
        agent_result,
        history: list[PreviousAttempt],
        carried_errors: list[TaskError],
        total_iter: int,
    ) -> StageResult:
        """Build the StageResult representing escalation after budget/max-iter
        exhaustion. Either requests a route (rollback_target set — snap-back
        when the target is upstream, forward-route when it is downstream) or
        falls through to terminal failure (rollback_target=None).
        """
        base_reports = list(gate_results.reports) if gate_results else []

        context_snapshot = PredecessorFailureContext(
            source_stage=stage_name,
            error_class=winner,
            error_class_reason=reason,
            execution_log=getattr(agent_result, "execution_log", "") or "",
            errors=list(carried_errors),
            previous_attempts=list(history),
            modified_files=list(getattr(agent_result, "files_modified", []) or []),
            iteration_count=total_iter,
        )

        def terminal(note: str) -> StageResult:
            return StageResult(
                name=stage_name,
                passed=False,
                iteration=total_iter,
                gate_reports=base_reports + [GateReport(
                    level="L1", check_type="pipeline", passed=False,
                    evidence=f"class={winner}; {note}",
                    suggestion="",
                )],
                execution_log=getattr(agent_result, "execution_log", "") or "",
                files_modified=list(getattr(agent_result, "files_modified", []) or []),
                previous_attempt=_attempt_to_dict(history[-1]) if history else None,
            )

        def route(target: str, via: str) -> StageResult:
            forward = target in self._downstream_closure(stage_name)
            verb = "forward-route" if forward else "snap-back"
            return StageResult(
                name=stage_name,
                passed=False,
                iteration=total_iter,
                gate_reports=base_reports + [GateReport(
                    level="L1", check_type="pipeline", passed=False,
                    evidence=f"class={winner}; requesting {verb} to '{target}' ({via})",
                    suggestion=(
                        f"'{target}' will run next; this stage is promoted to "
                        "passed-with-caveat."
                        if forward else
                        f"'{target}' will re-run; downstream subtree reset."
                    ),
                )],
                execution_log=getattr(agent_result, "execution_log", "") or "",
                files_modified=list(getattr(agent_result, "files_modified", []) or []),
                rollback_target=target,
                route_forward=forward,
                failure_context=context_snapshot,
                previous_attempt=_attempt_to_dict(history[-1]) if history else None,
            )

        # 1. error-class route_to resolves to an actual stage → route.
        #    Direction (forward vs snap-back) is derived from the DAG.
        if winner_spec.route_to in self.stages and winner_spec.route_to != stage_name:
            return route(winner_spec.route_to, "error_class route_to")

        on_fail = stage.get("on_fail", {}) if isinstance(stage.get("on_fail"), dict) else {}

        # 2. on_fail.target_map routes the winning class to a stage.
        target_map = on_fail.get("target_map", {})
        mapped = target_map.get(winner, "") if isinstance(target_map, dict) else ""
        if mapped and mapped in self.stages and mapped != stage_name:
            return route(mapped, "on_fail.target_map")

        # 3. stage has explicit on_fail.target → route.
        #    This takes precedence over route_to=self so a stage that the
        #    user configured with a rollback target does not spin locally
        #    until terminal failure.
        fallback = on_fail.get("target", "")
        if fallback and fallback in self.stages and fallback != stage_name:
            return route(fallback, "on_fail.target")

        # 4. route_to=self → terminal failure for this stage.
        if winner_spec.route_to == "self":
            return terminal("route_to=self, escalation becomes terminal failure")

        return terminal(
            f"no valid rollback target (winner_spec.route_to='{winner_spec.route_to}' "
            f"not in pipeline; on_fail.target='{fallback}' not usable)"
        )

    @staticmethod
    def _tool_hint_for_stage(stage: dict) -> str:
        criteria = stage.get("exit_criteria", [])
        for crit in criteria:
            if isinstance(crit, dict):
                cmd = crit.get("command", "").lower()
                for tool in ("verilator", "yosys", "pytest", "python"):
                    if tool in cmd:
                        return tool
        return ""

    # ------------------------------------------------------------- per-iter

    def _load_agent_cfg(self, agent_type: str) -> dict:
        from chip_nebula.project import (
            find_project_root,
            load_agent_config,
            infer_module_from_pipeline_path,
        )
        try:
            project_root = find_project_root()
        except Exception:
            project_root = None
        module = None
        source_path = getattr(self.config, "source_path", None)
        if source_path is not None and project_root is not None:
            module = infer_module_from_pipeline_path(source_path, project_root)
        return load_agent_config(agent_type, project_root, module=module) or {}

    def _stage_deliverables(
        self,
        stage_name: str,
        stage: dict,
        agent_cfg: dict,
        prior_session_id: str,
    ) -> tuple[bool, str]:
        """After gates pass, run a short agent session to `git add` deliverable
        files inside write_paths.

        This keeps build artifacts and auxiliary test files untracked while
        making the stage's real outputs tracked, so downstream scope checks
        can tell legal changes apart from transient generated files.
        """
        if not self._exec_adapter or not self._current_workspace:
            return True, "no adapter/workspace; skipping staging"

        from chip_nebula.adapters.scope_check import detect_changed_paths, violations
        from chip_nebula.project import find_project_root, load_project_config

        workspace = self._current_workspace
        write_paths = list(agent_cfg.get("write_paths") or [])
        if not write_paths:
            return True, "no write_paths configured; skipping staging"

        changed = detect_changed_paths(workspace)
        deliverables = [p for p in changed if not violations([p], write_paths)]
        if not deliverables:
            return True, "no changed deliverables to stage"

        # Build a minimal manifest for the post-gate staging session.
        project_root = find_project_root()
        project_cfg = load_project_config(project_root)
        project_model = project_cfg.get("model", {}) if isinstance(project_cfg, dict) else {}
        staging_model_cfg = project_cfg.get("staging_model", {}) if isinstance(project_cfg, dict) else {}
        framework = (
            stage.get("framework")
            or agent_cfg.get("framework")
            or "opencode"
        )
        # Prefer the dedicated staging model if configured; otherwise fall back
        # to the stage's normal model.
        model = staging_model_cfg.get("model") or stage.get("model") or agent_cfg.get("model") or project_model.get("model", "")
        model_provider = (
            staging_model_cfg.get("provider")
            or stage.get("model_provider")
            or agent_cfg.get("model_provider")
            or project_model.get("provider", "")
        )

        system_prompt = (
            "You are a post-gate staging assistant. The main agent for this "
            f"stage has just passed all verification gates. Your ONLY job is to "
            "stage deliverable files with `git add`.\n\n"
            "Instructions:\n"
            "1. Run `git status --porcelain` to see changed/untracked files.\n"
            "2. Run `git add` on every deliverable file created or modified by "
            "the stage that falls inside the Write Scope below.\n"
            "3. Only add source/deliverable files (e.g., RTL, documentation, "
            "test source). Do NOT add build artifacts, generated files "
            "(except generated files by Chisel, e.g. generated_sv/*.sv), "
            "coverage data, object files, or any file outside the Write Scope.\n"
            "4. Do NOT modify file contents. Do NOT run tests or lint.\n"
            "5. After staging, report 'ALL GATES PASSED'.\n\n"
            "Write Scope (stage only these paths):\n"
            + "\n".join(f"- {p}" for p in write_paths)
            + build_git_discipline(allow_git_add=True)
        )

        manifest = TaskManifest(
            task_id=f"{stage_name}-stage",
            feature_id=self.feature_id or stage.get("feature", "default"),
            pipeline=self.config.name,
            stage=f"{stage_name}__staging",
            assigned_agent=stage.get("agent", "unknown"),
            iteration=1,
            max_iterations=1,
            context=TaskContext(
                module=self.feature_id or stage.get("feature", "default"),
                description=f"Stage deliverable files for {stage_name}",
                system_prompt=system_prompt,
            ),
            description=f"Git-add deliverable files in write_paths for {stage_name}",
            framework=framework,
            timeout=min(agent_cfg.get("timeout", 300), 300),
            max_turns_per_session=10,
            model=model,
            model_provider=model_provider,
            write_paths=write_paths,
            reuse_session=False,
            session_id="",
        )

        try:
            if hasattr(self._exec_adapter, "dispatch"):
                result = self._exec_adapter.dispatch(
                    manifest, workspace, project_root=project_root,
                )
            else:
                result = self._exec_adapter.execute(
                    manifest, workspace, project_root=project_root,
                )
        except Exception as exc:
            return False, f"staging session raised exception: {exc}"

        if result is None:
            return False, "staging session returned None"

        log = getattr(result, "execution_log", "") or ""
        success = bool(getattr(result, "success", False))
        if not success:
            error = getattr(result, "error", "") or "unknown error"
            return False, f"staging session failed: {error}\n{log}"

        return True, log

    def _run_agent(
        self, stage_name: str, stage: dict, context: PipelineContext,
        *,
        carried_errors: Optional[list[TaskError]] = None,
        previous_attempt: Optional[PreviousAttempt] = None,
        predecessor_failure: Optional[PredecessorFailureContext] = None,
        agent_cfg: Optional[dict] = None,
        class_specs: Optional[dict[str, ErrorClassSpec]] = None,
    ) -> Optional[object]:
        if not self._exec_adapter:
            return None

        stage = self._resolve_templates(stage)

        agent_type = stage.get("agent", "rtl-designer")
        feature_id = self.feature_id or stage.get("feature", "default")
        agent_cfg = agent_cfg if agent_cfg is not None else self._load_agent_cfg(agent_type)
        class_specs = class_specs if class_specs is not None else resolve_error_classes(agent_cfg, stage)

        from chip_nebula.project import (
            find_project_root, create_worktree, load_project_config,
        )

        project_root = find_project_root()
        project_cfg = load_project_config(project_root)
        project_model = project_cfg.get("model", {}) if isinstance(project_cfg, dict) else {}

        deps = stage.get("depends_on", [])
        aggregated = self.artifact_store.get_aggregated(deps)

        criteria_list = stage.get("exit_criteria", [])
        completion_criteria: list[str] = []
        for crit in criteria_list:
            if isinstance(crit, dict):
                cmd = crit.get("command", "")
                if cmd:
                    criteria_text = f"Run: {cmd}"
                    expected = crit.get("expected", "")
                    if expected:
                        criteria_text += f" (expected: {expected})"
                    completion_criteria.append(criteria_text)
                paths = crit.get("paths", [])
                if paths:
                    completion_criteria.append(
                        f"Eiles exists: {', '.join(paths)}"
                    )

        if aggregated.all_files_modified:
            target_files = [
                FileTarget(path=f, status="modify", reason="Predecessor modified")
                for f in aggregated.all_files_modified
            ]
        else:
            write_paths = agent_cfg.get("write_paths") or []
            patterns = [p for p in write_paths if p and not p.startswith("!")]
            if patterns:
                target_files = [
                    FileTarget(path=patterns[0], status="create",
                               reason=f"Default target from agent write_paths")
                ]
            else:
                target_files = []

        # Precedence for runtime knobs: stage YAML > agent YAML > project defaults.
        framework = (
            stage.get("framework")
            or agent_cfg.get("framework")
            or "opencode"
        )
        timeout = stage.get("timeout", agent_cfg.get("timeout", 10800))
        max_turns = stage.get(
            "max_turns_per_session",
            agent_cfg.get("max_turns_per_session", 30),
        )
        model = stage.get("model") or agent_cfg.get("model") or project_model.get("model", "")
        model_provider = (
            stage.get("model_provider")
            or agent_cfg.get("model_provider")
            or project_model.get("provider", "")
        )
        _sessions = self._session_ids.get(stage_name, [])
        existing_session_id = _sessions[-1] if _sessions else ""
        predecessor_info = _aggregated_to_predecessor_info(aggregated)

        # Pull upstream execution logs that this stage explicitly wants to receive.
        receive_logs_from = stage.get("receive_logs_from", [])
        if receive_logs_from:
            logs: dict[str, str] = {}
            for upstream_stage in receive_logs_from:
                artifact = self.artifact_store.records.get(upstream_stage)
                if artifact is None:
                    continue
                log = getattr(artifact, "execution_log", "") or ""
                if log:
                    # Cap each log so the prompt does not explode.
                    limit = 8000
                    if len(log) > limit:
                        log = log[:limit] + f"\n... ({len(log) - limit} chars truncated)"
                    logs[upstream_stage] = log
            predecessor_info.logs = logs

        manifest = TaskManifest(
            task_id=f"{stage_name}-t{self.iteration_counters.get(stage_name, 1)}",
            feature_id=feature_id,
            pipeline=self.config.name,
            stage=stage_name,
            assigned_agent=agent_type,
            iteration=self.iteration_counters.get(stage_name, 1),
            max_iterations=stage.get("max_iterations", 3),
            context=TaskContext(
                module=feature_id,
                description=stage.get("description", f"Stage: {stage_name}"),
                top_module=stage.get("top_module", ""),
                system_prompt=agent_cfg.get("system_prompt_template", ""),
            ),
            target=target_files,
            errors=list(carried_errors or []),
            previous_attempt=previous_attempt,
            predecessor_failure_context=predecessor_failure,
            completion_criteria=completion_criteria,
            framework=framework,
            timeout=timeout,
            max_turns_per_session=max_turns,
            relevant_skills=agent_cfg.get("skills", []) or [],
            model=model,
            model_provider=model_provider,
            write_paths=list(agent_cfg.get("write_paths") or []),
            reuse_session=self._reuse_sessions,
            session_id=existing_session_id,
            session_token_threshold=stage.get(
                "session_token_threshold",
                agent_cfg.get("session_token_threshold", DEFAULT_SESSION_TOKEN_THRESHOLD),
            ),
            predecessor_info=predecessor_info,
        )

        setattr(manifest, "_error_class_specs", class_specs)
        setattr(manifest, "_exit_criteria", criteria_list)

        workspace = create_worktree(feature_id, project_root)
        self._current_workspace = workspace
        if self._wm:
            try:
                ws = self._wm.get_workspace(feature_id)
                workspace = ws.root
            except Exception:
                pass

        self.save_state(workspace)

        try:
            if hasattr(self._exec_adapter, "dispatch"):
                return self._exec_adapter.dispatch(
                    manifest, workspace, project_root=project_root,
                )
            return self._exec_adapter.execute(
                manifest, workspace, project_root=project_root,
            )
        except Exception:
            return None

    def _run_gates(
        self, stage_name: str, stage: dict, context: PipelineContext
    ) -> object:
        stage = self._resolve_templates(stage)
        criteria_list = stage.get("exit_criteria", [])
        if not criteria_list:
            from chip_nebula.models.gate_report import GateReport, GateResult
            return GateResult(all_passed=True, reports=[])

        exit_criteria: list[ExitCriterion] = []
        for crit in criteria_list:
            if isinstance(crit, dict):
                exit_criteria.append(ExitCriterion(
                    type=crit.get("type", "tool_check"),
                    level=crit.get("level", "L1"),
                    command=crit.get("command", ""),
                    expected=crit.get("expected", ""),
                    timeout=crit.get("timeout", 120),
                    metric=crit.get("metric", ""),
                    operator=crit.get("operator", ">="),
                    threshold=crit.get("threshold", 0.0),
                    source=crit.get("source", ""),
                    paths=crit.get("paths", []),
                    min_files=crit.get("min_files", 0),
                    pattern=crit.get("pattern", ""),
                    must_not_match=(
                        not crit["must_match"] if "must_match" in crit
                        else crit.get("must_not_match", True)
                    ),
                    error_class=crit.get("error_class", ""),
                ))

        if self._exit_gate:
            feature_id = self.feature_id or stage.get("feature", "default")
            from chip_nebula.project import find_project_root, create_worktree
            project_root = find_project_root()
            workspace = create_worktree(feature_id, project_root)
            return self._exit_gate.check(exit_criteria, workspace)

        from chip_nebula.models.gate_report import GateReport, GateResult
        return GateResult(all_passed=True, reports=[
            GateReport(level="L1", check_type="noop", passed=True,
                       evidence="No exit gate configured - automatically passed")
        ])

    def get_status_summary(self) -> dict:
        return {
            "stages": self.stage_status,
            "results": {
                name: {"passed": r.passed, "iteration": r.iteration}
                for name, r in self.stage_results.items()
            },
            "iterations": dict(self.iteration_counters),
            "rollbacks_executed": self.rollbacks_executed,
            "global_rollback_budget": self.global_rollback_budget,
        }

    def save_state(self, workspace: Path) -> None:
        state = {
            "feature_id": self.feature_id,
            "pipeline": self.config.name,
            "pipeline_path": str(self.config.source_path) if self.config.source_path else "",
            "run_id": getattr(self, "run_id", ""),
            "framework": getattr(self, "framework", ""),
            "stage_status": dict(self.stage_status),
            "iteration_counters": dict(self.iteration_counters),
            "rollbacks_executed": self.rollbacks_executed,
            "global_rollback_budget": self.global_rollback_budget,
            "pending_failure_contexts": {
                k: _pfc_to_dict(v)
                for k, v in self._pending_failure_contexts.items()
            },
            "session_ids": dict(self._session_ids),
            "last_updated": datetime.now().isoformat(),
        }
        state_path = workspace / ".pipeline_state.json"
        import json
        state_path.write_text(json.dumps(state, indent=2, default=str))

    @classmethod
    def load_state(cls, workspace: Path) -> Optional[dict]:
        state_path = workspace / ".pipeline_state.json"
        if not state_path.exists():
            return None
        import json
        return json.loads(state_path.read_text())

    def apply_state(self, state: dict) -> None:
        self.stage_status.update(state.get("stage_status", {}))
        self.iteration_counters.update(state.get("iteration_counters", {}))
        self.rollbacks_executed = state.get("rollbacks_executed", 0)
        raw_session_ids = state.get("session_ids", {})
        for k, v in raw_session_ids.items():
            if isinstance(v, str):
                self._session_ids[k] = [v] if v else []
            elif isinstance(v, list):
                self._session_ids[k] = v
        for name, ctx_dict in (state.get("pending_failure_contexts") or {}).items():
            self._pending_failure_contexts[name] = _dict_to_pfc(ctx_dict)
        # Consistency fix: if a stage was reset to pending (e.g. after a
        # snap-back) its transitive downstream must also be reset so the DAG
        # re-runs the full chain rather than leaving stale passed/failed
        # stages from an older state snapshot. "skipped" downstream is also
        # reset: a snap-back revives the whole chain by design.
        for name in list(self.stage_names):
            if self.stage_status.get(name) == "pending":
                for succ in self._downstream_closure(name):
                    if self.stage_status.get(succ) in ("passed", "failed", "skipped"):
                        self.stage_status[succ] = "pending"
                        self.stage_results.pop(succ, None)
                        self.iteration_counters[succ] = 0


def _attempt_to_dict(pa) -> Optional[dict]:
    if pa is None:
        return None
    return {
        "iteration": pa.iteration,
        "result": pa.result,
        "agent_notes": pa.agent_notes,
        "error_class": pa.error_class,
    }


def _dict_to_pfc(d: dict) -> Optional[PredecessorFailureContext]:
    if not d:
        return None
    return PredecessorFailureContext(
        source_stage=d.get("source_stage", ""),
        error_class=d.get("error_class", ""),
        error_class_reason=d.get("error_class_reason", ""),
        execution_log=d.get("execution_log", ""),
        errors=[TaskError(**e) for e in (d.get("errors") or [])],
        previous_attempts=[PreviousAttempt(**pa) for pa in (d.get("previous_attempts") or [])],
        modified_files=d.get("modified_files", []),
        iteration_count=d.get("iteration_count", 0),
    )


def _pfc_to_dict(pfc) -> dict:
    return {
        "source_stage": pfc.source_stage,
        "error_class": pfc.error_class,
        "error_class_reason": pfc.error_class_reason,
        "execution_log": pfc.execution_log,
        "errors": [
            {"file": e.file, "line": e.line, "code": e.code,
             "severity": e.severity, "message": e.message}
            for e in (pfc.errors or [])
        ],
        "previous_attempts": [
            {"iteration": pa.iteration, "result": pa.result,
             "agent_notes": pa.agent_notes, "error_class": pa.error_class}
            for pa in (pfc.previous_attempts or [])
        ],
        "modified_files": pfc.modified_files,
        "iteration_count": pfc.iteration_count,
    }


def _aggregated_to_predecessor_info(aggregated: AggregatedArtifact) -> PredecessorInfo:
    return PredecessorInfo(
        statuses={},
        files=list(aggregated.all_files_modified | aggregated.all_files_created),
        metrics=dict(aggregated.metrics),
        decisions=list(aggregated.decisions),
        interface_changes=dict(aggregated.interface_changes),
        failures=[
            {
                "stage": f.stage,
                "iteration": f.iteration,
                "errors": f.errors,
            }
            for f in aggregated.failures
        ],
    )
