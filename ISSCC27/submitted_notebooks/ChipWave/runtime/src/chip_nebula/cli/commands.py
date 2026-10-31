import argparse
import json
import signal
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

from chip_nebula.models.gate_report import GateReport, GateResult
from chip_nebula.pipeline.parser import PipelineParser
from chip_nebula.env.validator import validate_environment
from chip_nebula.validation import validate_project_yaml, print_validation_report
from chip_nebula.project import (
    find_project_root, init_project, create_worktree, remove_worktree,
    normalize_project_root, create_blank_project,
    get_pipelines_dir, get_agents_dir, get_chip_nebula_dir,
    load_project_config, is_in_worktree, get_sparse_patterns,
)
from chip_nebula.dashboard.app import create_app


def cmd_init(args):
    try:
        project_dir = init_project(
            project_path=Path("."),
            project_name=args.name or "",
            top_module=args.top_module or "",
            model_provider=args.model_provider,
            model_name=args.model,
        )
        print(f"Initialized Chip Nebula project in {project_dir}")
        return 0
    except Exception as e:
        print(f"Error initializing project: {e}", file=sys.stderr)
        return 1


def cmd_example(args):
    """Create a writable, versioned copy of a built-in RTL example."""
    import shutil
    import subprocess
    import chip_nebula
    from chip_nebula.project import ensure_project_definition

    source = Path(chip_nebula.__file__).parent / "configs" / "examples" / args.name
    target = Path(args.directory).expanduser().resolve()
    try:
        if not source.is_dir():
            raise ValueError(f"unknown example: {args.name}")
        if target.exists() and any(target.iterdir()):
            raise ValueError(f"destination is not empty: {target}")
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            source, target, dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(
                ".git", ".chip_nebula", "build", "validation", "__pycache__",
                "*.py[cod]", "*.vvp", "*.vcd", "*.fst",
            ),
        )
        ignore_file = target / ".gitignore"
        ignored = ignore_file.read_text(encoding="utf-8") if ignore_file.is_file() else ""
        for entry in (
            ".chip_nebula/", "build/", "validation/", "*.vvp", "*.vcd",
            "*.fst", "__pycache__/", "*.py[cod]",
        ):
            if entry not in ignored.splitlines():
                ignored += ("" if not ignored or ignored.endswith("\n") else "\n") + entry + "\n"
        ignore_file.write_text(ignored, encoding="utf-8")
        ensure_project_definition(target, target.name)
        # Wheel extraction may not preserve executable mode bits on packaged
        # example runners.  Built-in shell entrypoints are trusted package
        # data and must remain directly runnable after copying.
        for runner in target.rglob("*.sh"):
            runner.chmod(runner.stat().st_mode | 0o111)
        subprocess.run(["git", "init", "-b", "main"], cwd=target, check=True, capture_output=True)
        subprocess.run(
            ["git", "-c", "user.name=Chip Nebula", "-c", "user.email=nebula@localhost",
             "add", "."], cwd=target, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-c", "user.name=Chip Nebula", "-c", "user.email=nebula@localhost",
             "commit", "-m", "initial RTL workbench example"],
            cwd=target, check=True, capture_output=True,
        )
        print(f"Created {args.name} example in {target}")
        return 0
    except Exception as exc:
        print(f"Example creation failed: {exc}", file=sys.stderr)
        return 1


def cmd_new(args):
    """Create a minimal project with a portable ``*.cnprj`` entry file."""
    try:
        manifest = create_blank_project(args.directory, args.name or "")
        print(f"已创建 Chip Nebula 工程：{manifest}")
        return 0
    except Exception as exc:
        print(f"创建工程失败：{exc}", file=sys.stderr)
        return 1


def _get_project_root_or_fail(args):
    if hasattr(args, 'project_root') and args.project_root:
        try:
            return normalize_project_root(args.project_root)
        except FileNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
    try:
        root = find_project_root()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Are you in a ChipWave project? Try running 'chipwave init'.", file=sys.stderr)
        sys.exit(1)
    if root is None:
        print("Error: project root not found.", file=sys.stderr)
        print("Are you in a ChipWave project? Try running 'chipwave init'.", file=sys.stderr)
        sys.exit(1)
    return root


def cmd_validate_env(args):
    project_root = _get_project_root_or_fail(args)
    if project_root is None:
        print("Error: project root not found", file=sys.stderr)
        return 1
    req_file = project_root / "requirements.txt"
    report = validate_environment(
        requirements_file=str(req_file) if req_file.exists() else None,
        project_root=str(project_root),
    )
    print("=" * 60)
    print(f"Environment Validation Report (Project: {project_root})")
    print("=" * 60)
    for result in report.results:
        icon = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗"}.get(result.status, "?")
        print(f"  [{icon}] {result.name}: {result.message}")
        if result.suggestion:
            print(f"       → {result.suggestion}")
    print()
    if report.all_pass:
        print("All checks passed. Environment is ready.")
    else:
        print(f"{len(report.failures)} failure(s) found. Fix before running pipelines.")
    return 0 if report.all_pass else 1


def cmd_toolchain(args):
    from chip_nebula.env.toolchain import (
        check_rtl_to_gds_toolchain, compact_rtl_to_gds_toolchain,
        install_rtl_to_gds_toolchain,
        load_rtl_to_gds_requirements,
        report_json, requirements_path,
    )

    if args.action == "requirements":
        if args.json:
            print(json.dumps(load_rtl_to_gds_requirements(), ensure_ascii=False, indent=2))
        else:
            print(requirements_path())
        return 0
    if args.action == "compact":
        if not args.toolchain_root:
            raise SystemExit("toolchain compact requires --toolchain-root")
        components = ("sky130-demo-ram512",) if args.include_ram512 else ()
        result = compact_rtl_to_gds_toolchain(
            Path(args.toolchain_root), include_components=components,
        )
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"Compacted ORFS runtime: {result['orfs_root']}")
            print(f"  revision: {result['revision']}")
            print(f"  optional components: {', '.join(result['components']) or 'none'}")
        return 0
    if args.action == "install":
        root = (
            Path(args.toolchain_root).expanduser().resolve()
            if args.toolchain_root
            else Path.home() / ".cache" / "chip-nebula" / "rtl2gds-tools"
        )
        components = ("sky130-demo-ram512",) if args.include_ram512 else ()
        result = install_rtl_to_gds_toolchain(
            root, include_components=components, replace=args.replace,
        )
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"Installed ORFS runtime: {result['orfs_root']}")
            print(f"  strategy: {result['strategy']}")
            print(f"  revision: {result['revision']}")
            print(f"  environment: source {result['environment_file']}")
            report = result["check"]
            print(f"RTL-to-GDS toolchain: {'READY' if report['ready'] else 'NOT READY'}")
            for failure in report["failures"]:
                print(f"  - {failure}")
        return 0 if result["check"]["ready"] else 1
    report = check_rtl_to_gds_toolchain(
        toolchain_root=Path(args.toolchain_root).expanduser().resolve()
        if args.toolchain_root else None,
        orfs_root=Path(args.orfs_root).expanduser().resolve()
        if args.orfs_root else None,
    )
    if args.json:
        print(report_json(report))
    else:
        print(f"RTL-to-GDS toolchain: {'READY' if report['ready'] else 'NOT READY'}")
        for name, result in report["tools"].items():
            state = "PASS" if result["version_ready"] and all(
                item["passed"] for item in result["capabilities"]
            ) else "FAIL"
            print(f"  [{state}] {name}: {result['version'] or 'not found'}")
        print(
            f"  [{'PASS' if report['orfs']['ready'] else 'FAIL'}] ORFS: "
            f"{report['orfs']['revision'] or 'not found'}"
        )
        for failure in report["failures"]:
            print(f"    - {failure}")
    return 0 if report["ready"] else 1


def cmd_validate_yaml(args):
    project_root = _get_project_root_or_fail(args)
    errors = validate_project_yaml(project_root)
    if errors:
        print_validation_report(errors)
        return 1
    print("All project YAML configs are valid.")
    print("Note: files starting with '_' (e.g., _agent_meta.yaml) are templates and skipped.")
    return 0


def cmd_parse_pipeline(args):
    project_root = _get_project_root_or_fail(args)
    parser = PipelineParser()
    path = Path(args.pipeline_file)
    
    if not path.is_absolute():
        pipelines_dir = get_pipelines_dir(project_root)
        if (pipelines_dir / path).exists():
            path = pipelines_dir / path
            
    try:
        config = parser.parse_file(path)
        issues = parser.validate(config)
        print(f"Pipeline: {config.name} v{config.version}")
        print(f"Description: {config.description}")
        print(f"Stages: {len(config.stages)}")
        print()
        for name, stage in config.stages.items():
            deps = stage.get("depends_on", [])
            dep_str = f"depends_on: [{', '.join(deps)}]" if deps else "no dependencies"
            criteria = stage.get("exit_criteria", [])
            print(f"  [{stage.get('agent', '?')}] {name}")
            print(f"    {dep_str}")
            print(f"    gates: {len(criteria)}")
        if issues:
            print(f"\nValidation issues ({len(issues)}):")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\nPipeline validation: PASSED")
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error parsing pipeline: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_run_pipeline(args):
    """Deprecated legacy runner retained only for migration observation."""
    from chip_nebula.pipeline.interpreter import DAGPipelineInterpreter
    from chip_nebula.pipeline.context import PipelineContext

    print(
        "WARNING: legacy-run uses the deprecated mutable Stage/snap-back engine. "
        "Define a Recipe v2 workflow and use 'chipwave run' for new work.",
        file=sys.stderr,
    )
    project_root = _get_project_root_or_fail(args)

    yaml_errors = validate_project_yaml(project_root)
    if yaml_errors:
        print_validation_report(yaml_errors)
        return 1
    else:
        print("  YAML validation: PASSED")

    parser = PipelineParser()
    path = Path(args.pipeline_file)

    if not path.is_absolute():
        pipelines_dir = get_pipelines_dir(project_root)
        if (pipelines_dir / path).exists():
            path = pipelines_dir / path

    try:
        config = parser.parse_file(path)
        issues = parser.validate(config)
        if issues:
            print("Pipeline validation failed:")
            for issue in issues:
                print(f"  - {issue}")
            return 1
    except Exception as e:
        print(f"Error parsing pipeline: {e}", file=sys.stderr)
        return 1

    from chip_nebula.adapters.pool_manager import AgentPoolManager
    from chip_nebula.workspace.manager import WorkspaceManager
    from chip_nebula.gates.exit_gate import ExitGate
    from chip_nebula.pipeline.artifact_store import PipelineArtifactStore
    from chip_nebula.project import get_memory_dir, create_worktree, get_worktrees_dir
    from datetime import datetime
    import uuid

    run_id = args.run_id or (
        datetime.now().strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
    )
    artifact_dir = get_memory_dir(project_root) / "artifacts" / config.name / run_id

    wm = WorkspaceManager(project_root=project_root)
    ctx = PipelineContext()

    feature_id = args.feature or ""
    top_module_from_cfg = (load_project_config(project_root) or {}).get("top_module", "")

    reuse_sessions = getattr(args, "reuse_sessions", True)
    interpreter = DAGPipelineInterpreter(
        config, artifact_dir=artifact_dir, reuse_sessions=reuse_sessions,
    )
    interpreter.feature_id = feature_id
    interpreter.top_module = top_module_from_cfg
    interpreter.run_id = run_id
    # Empty string means "auto": pick framework from stage/agent YAML.
    interpreter.framework = args.framework or ""

    state = None
    if args.resume:
        if not feature_id:
            print("Error: --feature is required with --resume", file=sys.stderr)
            return 1
        worktree = get_worktrees_dir(project_root) / feature_id
        state = DAGPipelineInterpreter.load_state(worktree)
        if state is None:
            print(f"No state found in {worktree}, starting fresh", file=sys.stderr)

    # Framework is a runtime/run-level choice, not persisted in pipeline state.
    # Use the CLI flag if provided; otherwise let stage/agent YAML decide.
    effective_framework = args.framework
    # Empty string means "auto": pick framework from stage/agent YAML.
    interpreter.framework = effective_framework or ""

    default_framework = effective_framework or "mock"
    force_framework = effective_framework is not None
    adapter = AgentPoolManager(
        default_framework=default_framework,
        force_framework=force_framework,
    )
    # Only skip exit gates when the run is explicitly forced to the mock
    # framework. In auto mode we let stage/agent YAML pick the framework
    # and run real exit gates.
    exit_gate = None if effective_framework == "mock" else ExitGate()

    if state is not None:
        interpreter.apply_state(state)
        store = PipelineArtifactStore.load_from_disk(artifact_dir)
        interpreter.artifact_store = store
        # "running" stages are always resubmitted. "stopped" stages are
        # user-suspended: a plain resume revives them (legacy behavior),
        # but an Inject/from-stage resume (--preserve-stopped, used by
        # the dashboard) must keep them frozen — the inject target's
        # upstream was already marked "skipped" in the state file, and
        # reviving unrelated stopped stages would restart work the user
        # deliberately suspended.
        preserve_stopped = getattr(args, "preserve_stopped", False)
        interrupted = [
            name
            for name, status in interpreter.stage_status.items()
            if status == "running"
            or (status == "stopped" and not preserve_stopped)
        ]
        for name in interrupted:
            interpreter.stage_status[name] = "pending"
            interpreter.iteration_counters[name] = 0
        interpreter.save_state(worktree)
        print(f"Resumed {state['pipeline']} from {worktree}")
        for name, status in interpreter.stage_status.items():
            marker = "✓" if status == "passed" else ("✗" if status == "failed" else "○")
            print(f"  [{marker}] {name} ({status})")

    print(f"Running pipeline: {config.name}")
    print(f"Run ID: {run_id}")
    print(f"Stages: {len(config.stages)}")
    print(f"Max workers: {args.workers}")
    print(f"Artifacts: {artifact_dir}")
    print("-" * 60)

    stop_event = threading.Event()
    received_signal: list[int] = []

    def _signal_handler(signum: int, frame: object) -> None:
        print(f"\nReceived signal {signum}, stopping pipeline gracefully...", file=sys.stderr)
        received_signal.append(signum)
        stop_event.set()

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    result = interpreter.run(
        context=ctx,
        max_workers=args.workers,
        adapter=adapter,
        exit_gate=exit_gate,
        workspace_manager=wm,
        stop_event=stop_event,
    )

    if received_signal:
        print(f"Pipeline stopped by signal {received_signal[-1]}.", file=sys.stderr)
        return 128 + received_signal[-1]

    verdict = "PASSED" if result.all_passed else "FAILED"
    if result.all_passed and result.suspended_stages:
        verdict += (
            f" ({len(result.suspended_stages)} stage(s) suspended by user: "
            + ", ".join(result.suspended_stages) + ")"
        )
    print(f"\nPipeline {verdict}")
    print(f"Total iterations: {result.total_iterations}")
    print()
    for name, stage_result in result.stage_results.items():
        status = "✓" if stage_result.passed else "✗"
        print(f"  [{status}] {name} ({stage_result.iteration} iterations)")

    return 0 if result.all_passed else 1


def cmd_list_workspaces(args):
    from chip_nebula.workspace.manager import WorkspaceManager
    
    project_root = _get_project_root_or_fail(args)

    wm = WorkspaceManager(project_root=project_root)
    workspaces = wm.list_workspaces()

    if workspaces:
        print(f"Workspaces ({len(workspaces)}):")
        for ws in workspaces:
            pip_state = wm.get_pipeline_state(ws)
            current = pip_state.current_stage or "idle"
            print(f"  - {ws}  [{current}]")
    else:
        print("No workspaces found.")


def cmd_create_workspace(args):
    from chip_nebula.workspace.manager import WorkspaceManager
    
    project_root = _get_project_root_or_fail(args)

    wm = WorkspaceManager(project_root=project_root)
    ws = wm.create(args.feature_id)
    print(f"Created workspace: {ws.id}")
    print(f"  Root: {ws.root}")
    print(f"  RTL:  {ws.rtl_dir}")
    print(f"  TB:   {ws.tb_dir}")


def cmd_skill_list(args):
    from chip_nebula.skills.generator import SkillGenerator
    
    project_root = _get_project_root_or_fail(args)

    gen = SkillGenerator(project_root=project_root)
    active = gen.list_active_skills()
    if active:
        print(f"Active skills ({len(active)}):")
        for name in active:
            skill = gen.get_skill(name)
            if skill:
                print(f"  - {skill.name} v{skill.version} ({skill.success_count} successes)")
    else:
        print("No active skills found.")


def cmd_worktree_cleanup(args):
    project_root = _get_project_root_or_fail(args)
    from chip_nebula.workspace.manager import WorkspaceManager
    from chip_nebula.project import (
        get_worktrees_dir,
        worktree_has_uncommitted_changes,
        worktree_has_unmerged_commits,
    )
    wm = WorkspaceManager(project_root=project_root)
    workspaces = wm.list_workspaces()

    cleaned = 0
    skipped = 0
    force = getattr(args, "force", False)
    for ws_id in workspaces:
        wt_path = get_worktrees_dir(project_root) / ws_id
        if not force:
            dirty = worktree_has_uncommitted_changes(wt_path)
            unmerged = worktree_has_unmerged_commits(wt_path)
            if dirty or unmerged:
                reasons = []
                if dirty:
                    reasons.append("uncommitted changes")
                if unmerged:
                    reasons.append("unmerged commits")
                print(f"Skipped {ws_id}: {', '.join(reasons)}")
                skipped += 1
                continue
        try:
            remove_worktree(ws_id, project_root)
            cleaned += 1
            print(f"Removed worktree: {ws_id}")
        except Exception as e:
            print(f"Failed to remove {ws_id}: {e}", file=sys.stderr)

    print(f"Cleanup complete. Removed {cleaned}, skipped {skipped}.")
    if skipped and not force:
        print("Use --force to remove worktrees with uncommitted/unmerged work (data may be lost).")
    return 0


def cmd_dashboard(args):
    import uvicorn

    project_root = _get_project_root_or_fail(args)
    app = create_app(project_root=project_root)

    host = args.host
    port = args.port
    url = f"http://{host}:{port}"
    print(f"Starting Chip Nebula dashboard at {url}")
    print(f"Project root: {project_root}")

    if not args.no_open:
        webbrowser.open(url)

    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0


# ---------------------------------------------------------------------------
#  roundtable — multi-agent roundtable discussions (docs/design/roundtable-design.md)
# ---------------------------------------------------------------------------

def cmd_roundtable_list(args):
    from chip_nebula.roundtable.store import list_tables

    project_root = _get_project_root_or_fail(args)
    tables = list_tables(project_root)
    if not tables:
        print("No roundtables found")
        return 0
    for t in tables:
        alive = "●" if t["alive"] else " "
        print(
            f"{alive} {t['table_id']}  [{t['status']}] "
            f"round {t['current_round']}/{t['max_rounds']}  "
            f"agents={t['num_agents']} humans={t['num_humans']}  "
            f"{t['topic'][:40]}"
        )
    return 0


def cmd_roundtable_new(args):
    from datetime import datetime
    import getpass
    import yaml
    from chip_nebula.roundtable.models import RoundtableConfig
    from chip_nebula.roundtable.store import create_table, new_table_id

    project_root = _get_project_root_or_fail(args)
    with open(args.config) as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("table_id", new_table_id(data.get("topic", "")))
    data.setdefault("created_by", getpass.getuser())
    data.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))
    cfg = RoundtableConfig.from_dict(data)
    issues = cfg.validate()
    if issues:
        for issue in issues:
            print(f"  - {issue}", file=sys.stderr)
        return 1
    tdir = create_table(project_root, cfg)
    print(f"Created roundtable '{cfg.table_id}' at {tdir}")
    if args.start:
        from chip_nebula.roundtable.runner import start_orchestrator
        pid = start_orchestrator(project_root, cfg.table_id)
        print(f"Orchestrator started (pid {pid})")
    else:
        print(f"Run it with: chipwave roundtable run {cfg.table_id}")
    return 0


def cmd_roundtable_run(args):
    from chip_nebula.roundtable.orchestrator import run_roundtable

    project_root = _get_project_root_or_fail(args)
    return run_roundtable(project_root, args.table_id)


def cmd_roundtable_stop(args):
    from chip_nebula.roundtable.runner import stop_orchestrator
    from chip_nebula.roundtable.models import STATUS_PAUSED, STATUS_RUNNING
    from chip_nebula.roundtable.store import (
        append_system_event, load_state, save_state, table_dir,
    )

    project_root = _get_project_root_or_fail(args)
    tdir = table_dir(project_root, args.table_id)
    if not tdir.exists():
        print(f"Roundtable '{args.table_id}' not found", file=sys.stderr)
        return 1
    stopped = stop_orchestrator(project_root, args.table_id)
    # The orchestrator checkpoints itself to paused on SIGTERM; after a
    # SIGKILL (or if no process was running) the CLI does it instead.
    state = load_state(tdir)
    if state.status == STATUS_RUNNING:
        state.status = STATUS_PAUSED
        state.run_pid = 0
        save_state(tdir, state)
        append_system_event(tdir, "圆桌已中止（可继续）")
    print("Stopped" if stopped else "No running orchestrator; state updated")
    return 0


def cmd_roundtable_destroy(args):
    import shutil
    from chip_nebula.roundtable.runner import stop_orchestrator
    from chip_nebula.roundtable.models import STATUS_DESTROYED
    from chip_nebula.roundtable.store import (
        append_system_event, load_state, save_state, table_dir,
    )

    project_root = _get_project_root_or_fail(args)
    tdir = table_dir(project_root, args.table_id)
    if not tdir.exists():
        print(f"Roundtable '{args.table_id}' not found", file=sys.stderr)
        return 1
    stop_orchestrator(project_root, args.table_id)
    if args.purge:
        shutil.rmtree(tdir, ignore_errors=True)
        print(f"Purged roundtable '{args.table_id}'")
        return 0
    state = load_state(tdir)
    state.status = STATUS_DESTROYED
    state.run_pid = 0
    save_state(tdir, state)
    append_system_event(tdir, "圆桌已销毁（保留只读存档）")
    print(f"Destroyed roundtable '{args.table_id}' (archive kept; --purge to delete)")
    return 0


def cmd_roundtable_transcript(args):
    from chip_nebula.roundtable.store import read_transcript, table_dir

    project_root = _get_project_root_or_fail(args)
    tdir = table_dir(project_root, args.table_id)
    if not tdir.exists():
        print(f"Roundtable '{args.table_id}' not found", file=sys.stderr)
        return 1
    for e in read_transcript(tdir):
        who = e.author_name + (" (人类)" if e.author_type == "human" else "")
        print(f"\n[#{e.seq} 第{e.round}轮 {e.kind} · {who}]")
        print(e.text)
    return 0


def _taskgraph_database(project_root: Path, explicit: str = "") -> Path:
    return Path(explicit).resolve() if explicit else (
        get_chip_nebula_dir(project_root) / "shared" / "memory" / "taskgraph-v2.db"
    )


def _parse_key_values(values: list[str]) -> dict[str, str]:
    result = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"expected KEY=VALUE, got {value!r}")
        key, item = value.split("=", 1)
        if not key or not item:
            raise ValueError(f"expected non-empty KEY=VALUE, got {value!r}")
        result[key] = item
    return result


def cmd_taskgraph_import_git(args):
    project_root = _get_project_root_or_fail(args)
    try:
        import subprocess
        from chip_nebula.taskgraph import (
            Artifact, ArtifactContent, ArtifactProducer,
            StaticTaskGraphStore,
        )
        commit = subprocess.run(
            ["git", "rev-parse", args.ref], cwd=project_root,
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        tree = subprocess.run(
            ["git", "rev-parse", f"{commit}^{{tree}}"], cwd=project_root,
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        artifact = Artifact(
            id=args.id, type="rtl.snapshot", schema_version=1,
            producer=ArtifactProducer(
                args.workflow or "external", f"human-{args.id}",
                f"external:{args.id}", "human", 1,
            ),
            content=ArtifactContent(kind="git", commit=commit, tree=tree, paths=tuple(args.path)),
            payload={"module": args.module, "commit": commit, "paths": list(args.path)},
            metadata={"workflow_id": args.workflow or "external"},
        )
        with StaticTaskGraphStore(
            _taskgraph_database(project_root, args.database),
        ) as store:
            store.register_evidence_artifacts((artifact,))
        print(f"Imported {artifact.id} -> {commit}")
        return 0
    except Exception as exc:
        print(f"Artifact import failed: {exc}", file=sys.stderr)
        return 1



# Static Task / continuing Attempt command surface.

def cmd_taskgraph_create(args):
    project_root = _get_project_root_or_fail(args)
    try:
        from chip_nebula.adapters.pool_manager import AgentPoolManager
        from chip_nebula.taskgraph.static_cli import (
            create_workflow, database_path, load_compiled_recipe,
        )
        recipe = Path(args.recipe).expanduser().resolve()
        framework = str(getattr(args, "framework", "") or "")
        model = str(getattr(args, "model", "") or "")
        reasoning_effort = str(getattr(args, "reasoning_effort", "") or "")
        baseline = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=project_root,
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        compiled = load_compiled_recipe(
            recipe, workflow_id=args.workflow,
            goal=f"Complete {recipe.stem} for project {project_root.name}",
            parameters=_parse_key_values(args.param),
            framework=framework, model=model, reasoning_effort=reasoning_effort,
            baseline_commit=baseline,
            workers=int(getattr(args, "workers", 4)),
        )
        pool = AgentPoolManager(
            default_framework=framework or compiled.planner.framework,
            force_framework=bool(framework),
        )
        create_workflow(
            project_root, database_path(project_root, args.database), compiled, pool,
        )
        print(f"Created and planned static workflow {args.workflow}: {len(compiled.tasks)} Tasks")
        return 0
    except Exception as exc:
        print(f"Task Graph creation failed: {exc}", file=sys.stderr)
        return 1


def cmd_taskgraph_status(args):
    project_root = _get_project_root_or_fail(args)
    try:
        from chip_nebula.taskgraph.static_cli import database_path, snapshot_text
        from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
        database = database_path(project_root, args.database)
        workflow_id = str(getattr(args, "workflow", "") or "")
        if not workflow_id:
            with StaticTaskGraphStore(database) as store:
                workflows = store.list_workflows()
            if not workflows:
                raise ValueError("no static TaskGraph Workflow exists")
            workflow_id = workflows[-1].id
        print(snapshot_text(database, workflow_id, as_json=args.json))
        return 0
    except Exception as exc:
        print(f"Task Graph status failed: {exc}", file=sys.stderr)
        return 1


def cmd_taskgraph_run(args):
    project_root = _get_project_root_or_fail(args)
    try:
        from chip_nebula.adapters.pool_manager import AgentPoolManager
        from chip_nebula.taskgraph.static_cli import database_path, run_workflow
        from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
        database = database_path(project_root, args.database)
        workflow_id = str(getattr(args, "workflow", "") or "")
        if not workflow_id:
            with StaticTaskGraphStore(database) as store:
                workflows = store.list_workflows()
            if not workflows:
                raise ValueError("no static TaskGraph Workflow exists")
            workflow_id = workflows[-1].id
        pool = AgentPoolManager(
            default_framework=str(args.framework or "codex"),
            force_framework=bool(args.framework),
        )
        status = run_workflow(
            project_root, database, workflow_id, pool, workers=int(args.workers),
            framework=str(args.framework or ""), model=str(args.model or ""),
            reasoning_effort=str(args.reasoning_effort or ""),
        )
        print(f"Static Task Graph {workflow_id}: {status.value}")
        return 0 if status.value == "complete" else 1
    except Exception as exc:
        print(f"Task Graph run failed: {exc}", file=sys.stderr)
        return 1


def cmd_taskgraph_start(args):
    project_root = _get_project_root_or_fail(args)
    try:
        from chip_nebula.adapters.pool_manager import AgentPoolManager
        from chip_nebula.taskgraph.static_cli import (
            create_workflow, database_path, load_compiled_recipe,
            prepare_workflow_resume, run_workflow,
        )
        from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
        recipe = Path(args.recipe).expanduser().resolve()
        database = database_path(project_root, args.database)
        parameters = _parse_key_values(args.param)
        framework = str(args.framework or "")
        model = str(args.model or "")
        reasoning_effort = str(getattr(args, "reasoning_effort", "") or "")
        with StaticTaskGraphStore(database) as store:
            existing = store.get_workflow(args.workflow)
        pool = AgentPoolManager(
            default_framework=framework or "codex", force_framework=bool(framework),
        )
        if existing is None:
            baseline = subprocess.run(
                ["git", "rev-parse", str(args.baseline)], cwd=project_root,
                check=True, capture_output=True, text=True,
            ).stdout.strip()
            compiled = load_compiled_recipe(
                recipe, workflow_id=args.workflow,
                goal=f"Complete {recipe.stem} for project {project_root.name}",
                parameters=parameters, framework=framework, model=model,
                reasoning_effort=reasoning_effort,
                baseline_commit=baseline, workers=int(args.workers),
            )
            create_workflow(project_root, database, compiled, pool)
        elif not args.resume:
            raise ValueError(f"workflow {args.workflow} already exists; use --resume")
        else:
            if existing.status.value == "planning":
                metadata = existing.metadata
                compiled = load_compiled_recipe(
                    Path(metadata["recipe_path"]), workflow_id=existing.id, goal=existing.goal,
                    parameters=metadata["parameters"],
                    framework=str(metadata.get("framework_override", "")),
                    model=str(metadata.get("model_override", "")),
                    reasoning_effort=str(metadata.get("reasoning_effort_override", "")),
                    baseline_commit=str(metadata.get("baseline_commit", "")),
                    workers=int(metadata.get("workers", 1)),
                )
                create_workflow(project_root, database, compiled, pool)
            prepare_workflow_resume(project_root, database, args.workflow)
        status = run_workflow(
            project_root, database, args.workflow, pool, workers=int(args.workers),
            framework=framework, model=model, reasoning_effort=reasoning_effort,
        )
        print(f"Static Task Graph {args.workflow}: {status.value}")
        return 0 if status.value == "complete" else 1
    except Exception as exc:
        print(f"Task Graph start failed: {exc}", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(
        prog="chipwave",
        description="ChipWave - Configurable AI Chip Design Workflows",
    )
    
    parser.add_argument("--project-root", help="Root directory of the project")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    p_internal = subparsers.add_parser("internal", help=argparse.SUPPRESS)
    p_internal.add_argument("domain", choices=["specification"])
    p_internal.add_argument("action", choices=[
        "ledger-shape-gate", "ledger-status-protection",
        "review-integrity-gate", "ledger-closure-gate",
        "compiler-check", "freeze-baseline",
        "freeze-project-constraints", "freeze-acceptance-plan",
    ])
    def run_internal(args):
        from chip_nebula.taskgraph.specification_flow import internal_command
        return internal_command(args.action)
    p_internal.set_defaults(func=run_internal)

    p_init = subparsers.add_parser("init", help="Initialize a new project")
    p_init.add_argument("--name", help="Project name")
    p_init.add_argument("--top-module", help="Top module name")
    p_init.add_argument("--model-provider", default="deepseek", help="Model provider")
    p_init.add_argument("--model", default="deepseek-v4-pro", help="Model name")
    p_init.set_defaults(func=cmd_init)

    p_example = subparsers.add_parser("example", help="Create a built-in RTL workbench example")
    p_example.add_argument("directory", help="Destination directory")
    p_example.add_argument("--name", default="rtl-counter", help="Built-in example name")
    p_example.set_defaults(func=cmd_example)

    p_new = subparsers.add_parser(
        "new", help="Create a blank RTL project with a .cnprj entry file",
    )
    p_new.add_argument("directory", help="Destination directory")
    p_new.add_argument("--name", help="Project display name")
    p_new.set_defaults(func=cmd_new)

    p_validate = subparsers.add_parser("validate", help="Validate environment")
    p_validate.set_defaults(func=cmd_validate_env)

    p_toolchain = subparsers.add_parser(
        "toolchain", help="Install and audit the pinned RTL-to-GDS toolchain runtime",
    )
    p_toolchain.add_argument(
        "action", choices=("requirements", "install", "check", "compact"),
    )
    p_toolchain.add_argument("--toolchain-root", default="")
    p_toolchain.add_argument("--orfs-root", default="")
    p_toolchain.add_argument("--json", action="store_true")
    p_toolchain.add_argument("--include-ram512", action="store_true")
    p_toolchain.add_argument(
        "--replace", action="store_true",
        help="Atomically replace an existing non-matching ORFS runtime during install",
    )
    p_toolchain.set_defaults(func=cmd_toolchain)

    p_validate_yaml = subparsers.add_parser("validate-yaml", help="Validate all project YAML configs")
    p_validate_yaml.set_defaults(func=cmd_validate_yaml)

    p_parse = subparsers.add_parser("parse", help="Parse and validate a pipeline YAML")
    p_parse.add_argument("pipeline_file", help="Path to pipeline YAML file")
    p_parse.set_defaults(func=cmd_parse_pipeline)

    p_run = subparsers.add_parser(
        "legacy-run", help="Run a deprecated snap-back Pipeline during migration"
    )
    p_run.add_argument("pipeline_file", help="Path to pipeline YAML file")
    p_run.add_argument("-w", "--workers", type=int, default=4, help="Max parallel workers (default: 4)")
    p_run.add_argument("-f", "--framework", default=None, help="Force all stages to use this agent framework; omit to use per-stage/agent config")
    p_run.add_argument("--feature", default="", help="Feature ID (replaces {feature_id} in pipeline template)")
    p_run.add_argument("--resume", action="store_true", help="Resume from previous interrupted run")
    p_run.add_argument(
        "--preserve-stopped",
        action="store_true",
        help="With --resume: keep 'stopped' stages frozen instead of "
             "resubmitting them (used by dashboard Inject / from-stage resume)",
    )
    p_run.add_argument(
        "--reuse-sessions",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Reuse agent conversations across stage re-executions (default: on)",
    )
    p_run.add_argument("--run-id", default="", help="Explicit run id (default: timestamp+random)")
    p_run.set_defaults(func=cmd_run_pipeline)

    p_run_v2 = subparsers.add_parser(
        "run", help="Run a versioned Task Graph Recipe (default engine)"
    )
    p_run_v2.add_argument("recipe")
    p_run_v2.add_argument("--workflow", required=True)
    p_run_v2.add_argument("--baseline", default="HEAD")
    p_run_v2.add_argument("--param", action="append", default=[])
    p_run_v2.add_argument("--database", default="")
    p_run_v2.add_argument("--framework", default=None)
    p_run_v2.add_argument("--model", default=None, help="Override the model for all Roles in this run")
    p_run_v2.add_argument("--reasoning-effort", default=None)
    p_run_v2.add_argument("--workers", type=int, default=4)
    p_run_v2.add_argument("--resume", action="store_true")
    p_run_v2.set_defaults(func=cmd_taskgraph_start)

    p_ws_list = subparsers.add_parser("ws-list", help="List all workspaces")
    p_ws_list.set_defaults(func=cmd_list_workspaces)

    p_ws_create = subparsers.add_parser("ws-create", help="Create a new workspace")
    p_ws_create.add_argument("feature_id", help="Feature ID for the workspace")
    p_ws_create.set_defaults(func=cmd_create_workspace)

    p_skills = subparsers.add_parser("skills", help="List active skills")
    p_skills.set_defaults(func=cmd_skill_list)
    
    p_cleanup = subparsers.add_parser("worktree-cleanup", help="Remove worktrees without uncommitted changes")
    p_cleanup.add_argument("--force", action="store_true",
                           help="Remove worktrees even with uncommitted/unmerged work (destructive)")
    p_cleanup.set_defaults(func=cmd_worktree_cleanup)

    p_dashboard = subparsers.add_parser("dashboard", help="Launch the web dashboard")
    p_dashboard.add_argument("--port", type=int, default=8080, help="Port to run on (default: 8080)")
    p_dashboard.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    p_dashboard.add_argument("--no-open", action="store_true", help="Do not open browser automatically")
    p_dashboard.set_defaults(func=cmd_dashboard)

    p_rt = subparsers.add_parser("roundtable", help="Multi-agent roundtable discussions")
    rt_sub = p_rt.add_subparsers(dest="rt_command", help="Roundtable actions")

    p_rt_list = rt_sub.add_parser("list", help="List all roundtables")
    p_rt_list.set_defaults(func=cmd_roundtable_list)

    p_rt_new = rt_sub.add_parser("new", help="Create a roundtable from a YAML config")
    p_rt_new.add_argument("--config", required=True, help="Path to roundtable YAML config")
    p_rt_new.add_argument("--start", action="store_true", help="Start the orchestrator immediately")
    p_rt_new.set_defaults(func=cmd_roundtable_new)

    p_rt_run = rt_sub.add_parser("run", help="Run/resume a roundtable orchestrator")
    p_rt_run.add_argument("table_id")
    p_rt_run.set_defaults(func=cmd_roundtable_run)

    p_rt_stop = rt_sub.add_parser("stop", help="Pause a running roundtable")
    p_rt_stop.add_argument("table_id")
    p_rt_stop.set_defaults(func=cmd_roundtable_stop)

    p_rt_destroy = rt_sub.add_parser("destroy", help="Destroy a roundtable (archive kept)")
    p_rt_destroy.add_argument("table_id")
    p_rt_destroy.add_argument("--purge", action="store_true", help="Physically delete the table directory")
    p_rt_destroy.set_defaults(func=cmd_roundtable_destroy)

    p_rt_transcript = rt_sub.add_parser("transcript", help="Print a roundtable transcript")
    p_rt_transcript.add_argument("table_id")
    p_rt_transcript.set_defaults(func=cmd_roundtable_transcript)

    p_tg = subparsers.add_parser("taskgraph", help="Versioned Artifact Task Graph")
    tg_sub = p_tg.add_subparsers(dest="tg_command", required=True)

    p_tg_import = tg_sub.add_parser("import-git", help="Import a Git revision as rtl.snapshot")
    p_tg_import.add_argument("--id", required=True)
    p_tg_import.add_argument("--ref", default="HEAD")
    p_tg_import.add_argument("--module", default="baseline")
    p_tg_import.add_argument("--path", action="append", default=[])
    p_tg_import.add_argument("--workflow", default="")
    p_tg_import.add_argument("--database", default="")
    p_tg_import.set_defaults(func=cmd_taskgraph_import_git)

    p_tg_create = tg_sub.add_parser("create", help="Compile a Recipe into persisted Tasks")
    p_tg_create.add_argument("recipe")
    p_tg_create.add_argument("--workflow", required=True)
    p_tg_create.add_argument("--param", action="append", default=[])
    p_tg_create.add_argument("--database", default="")
    p_tg_create.add_argument("--framework", default=None)
    p_tg_create.add_argument("--model", default=None)
    p_tg_create.add_argument("--reasoning-effort", default=None)
    p_tg_create.set_defaults(func=cmd_taskgraph_create)

    p_tg_status = tg_sub.add_parser("status", help="Show Task/Artifact graph state")
    p_tg_status.add_argument("--database", default="")
    p_tg_status.add_argument("--workflow", default="")
    p_tg_status.add_argument("--json", action="store_true")
    p_tg_status.set_defaults(func=cmd_taskgraph_status)

    p_tg_run = tg_sub.add_parser("run", help="Run ready Task Graph tasks")
    p_tg_run.add_argument("--workflow", default="", help="Only run tasks from this workflow")
    p_tg_run.add_argument("--database", default="")
    p_tg_run.add_argument("--framework", default=None)
    p_tg_run.add_argument("--model", default=None)
    p_tg_run.add_argument("--reasoning-effort", default=None)
    p_tg_run.add_argument("--workers", type=int, default=4)
    p_tg_run.set_defaults(func=cmd_taskgraph_run)

    p_tg_start = tg_sub.add_parser("start", help="Create and run a Recipe from a Git baseline")
    p_tg_start.add_argument("recipe")
    p_tg_start.add_argument("--workflow", required=True)
    p_tg_start.add_argument("--baseline", default="HEAD")
    p_tg_start.add_argument("--param", action="append", default=[])
    p_tg_start.add_argument("--database", default="")
    p_tg_start.add_argument("--framework", default=None)
    p_tg_start.add_argument("--model", default=None)
    p_tg_start.add_argument("--reasoning-effort", default=None)
    p_tg_start.add_argument("--workers", type=int, default=4)
    p_tg_start.add_argument("--resume", action="store_true")
    p_tg_start.set_defaults(func=cmd_taskgraph_start)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
