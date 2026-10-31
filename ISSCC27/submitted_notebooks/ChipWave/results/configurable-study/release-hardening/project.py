import os
import re
import shutil
import subprocess
import threading
import uuid
import yaml
from pathlib import Path
from typing import Optional

_DEFAULT_SPARSE_PATTERNS = None  # None means full checkout (no sparse restriction)

# Default tool catalogue.  If the caller does not supply a `tools` list to
# init_project(), we scan $PATH and only record binaries that are actually
# installed.  Users may override with proprietary tools (VCS, Xcelium, DC,
# PT, Innovus, Spyglass) via the SKILL interview.
_DEFAULT_TOOL_CANDIDATES = {
    "verilator": "open-source SV linter / cycle-accurate simulator",
    "iverilog": "open-source Verilog simulator, cross-check for verilator",
    "yosys": "open-source synthesis and netlist analysis",
    "sta": "open-source static timing analysis (OpenSTA)",
    "surfer": "waveform viewer for generated VCD/FST dumps",
    "python": "project scripts: perf models, regression runners, report parsers",
    "make": "legacy build / regression entry points if present",
    "gtkwave": "waveform viewer (GTKWave)",
    "cocotb-config": "Python-based testbench framework (cocotb)",
    "pytest": "Python test framework",
}

def _scan_installed_tools() -> list[dict]:
    """Scan $PATH for known EDA/scripting tools and return only those found."""
    found = []
    for name, purpose in _DEFAULT_TOOL_CANDIDATES.items():
        if shutil.which(name):
            found.append({"name": name, "purpose": purpose})
    return found


def _infer_sparse_patterns(project_root: Path) -> list[str] | None:
    """Scan top-level directories under project_root (excluding hidden dirs)
    and return them as candidate sparse-checkout patterns.

    Returns None if the project root has no recognizable subdirectories,
    signalling that a full checkout should be used.
    """
    candidates = []
    for entry in project_root.iterdir():
        if entry.is_dir() and not entry.name.startswith("."):
            candidates.append(entry.name)
    return candidates if candidates else None


# Serialize worktree creation so two threads cannot both pass the "does not
# exist" check and then both call `git worktree add` for the same path.
_WORKTREE_LOCK = threading.Lock()


def normalize_project_root(path: str | Path) -> Path:
    """Resolve a directory or a Chip Nebula ``*.cnprj`` entry file.

    The project file is intentionally portable and lives at the project root,
    so callers that only need a working directory can consistently use its
    parent.  The workbench performs the schema validation after opening it.
    """
    resolved = Path(path).expanduser().resolve()
    if resolved.suffix.lower() == ".cnprj":
        if not resolved.is_file():
            raise FileNotFoundError(f"Chip Nebula project file not found: {resolved}")
        return resolved.parent
    if not resolved.is_dir():
        raise FileNotFoundError(f"Chip Nebula project directory not found: {resolved}")
    return resolved


def project_definition_files(project_root: str | Path) -> list[Path]:
    """Return every top-level project entry, with a case-insensitive suffix.

    Linux filenames are case-sensitive while desktop file associations are
    not.  Keeping discovery in one helper prevents ``DESIGN.CNPRJ`` from being
    accepted by Electron but silently ignored by the Python services.
    """
    root = Path(project_root).expanduser().resolve()
    if not root.is_dir():
        return []
    return sorted(
        (
            path for path in root.iterdir()
            if path.suffix.lower() == ".cnprj"
            and (path.is_file() or path.is_symlink())
        ),
        key=lambda path: (path.name.casefold(), path.name),
    )


def ensure_project_definition(project_root: str | Path, name: str = "") -> Path:
    """Create the single portable ``*.cnprj`` entry file when absent."""
    root = Path(project_root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"project root is not a directory: {root}")
    manifests = project_definition_files(root)
    if len(manifests) > 1:
        raise ValueError("project root contains more than one .cnprj file")
    if manifests:
        return manifests[0]
    project_name = name.strip() or root.name
    safe_name = re.sub(
        r"[\\/\x00-\x1f\x7f]+", "-", project_name,
    ).strip(" .") or "chip-nebula-project"
    manifest = root / f"{safe_name}.cnprj"
    content = yaml.safe_dump({
        "format": "chip-nebula-project",
        "format_version": 1,
        "project_id": f"cnprj-{uuid.uuid4().hex}",
        "name": project_name,
        "root": ".",
        "workbench": {
            "config": "workbench.yaml",
            "template": "workbench.yaml",
        },
    }, allow_unicode=True, sort_keys=False)
    probe = manifest.with_name(f".{manifest.name}.{uuid.uuid4().hex}.tmp")
    try:
        probe.write_text(content, encoding="utf-8")
        probe.replace(manifest)
    finally:
        probe.unlink(missing_ok=True)
    return manifest


def create_blank_project(
    project_path: str | Path, project_name: str = "",
) -> Path:
    """Create a minimal, versioned desktop project and return its entry file.

    This is the desktop equivalent of an IDE's *New Project* action.  It does
    not invent RTL or claim that validation is configured: the generated
    fileset is intentionally empty until the user adds or creates sources.
    """
    target = Path(project_path).expanduser().resolve()
    name = project_name.strip() or target.name
    if not name or any(ord(character) < 32 or ord(character) == 127 for character in name):
        raise ValueError("工程名称不能为空或包含控制字符")
    if target.exists() and not target.is_dir():
        raise ValueError(f"目标路径不是目录：{target}")
    if target.exists() and any(target.iterdir()):
        raise ValueError(f"目标目录必须不存在或为空：{target}")

    if not shutil.which("git"):
        raise RuntimeError("新建版本化工程需要 Git，请先安装 Git")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.parent / f".{target.name}.chip-nebula-{uuid.uuid4().hex}"
    staging.mkdir()

    def git(*args: str) -> None:
        result = subprocess.run(
            ["git", *args], cwd=staging, capture_output=True, text=True,
        )
        if result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip()
            detail = message or f"git {' '.join(args)} 执行失败"
            raise RuntimeError(f"创建 Git 基线失败：{detail}")

    try:
        for relative in ("rtl", "tb", "constraints", "ip"):
            directory = staging / relative
            directory.mkdir()
            (directory / ".gitkeep").write_text("", encoding="utf-8")

        (staging / ".gitignore").write_text(
            ".chip_nebula/\n"
            "build/\n"
            "validation/\n"
            "physical/build/\n"
            "*.vvp\n"
            "*.vcd\n"
            "*.fst\n"
            "__pycache__/\n"
            "*.py[cod]\n",
            encoding="utf-8",
        )
        (staging / "workbench.yaml").write_text(yaml.safe_dump({
            "top_module": "",
            "top_parameters": {},
            "source_globs": [
                "rtl/**/*.sv", "rtl/**/*.v", "rtl/**/*.svh", "rtl/**/*.vh",
                "src/**/*.sv", "src/**/*.v", "src/**/*.svh", "src/**/*.vh",
            ],
            "validation_mode": "fileset",
            "design_files": [],
            "testbench_files": [],
            "simulation_assets": [],
            "include_dirs": [],
            "defines": [],
            "filelists": [],
            "simulation_top": "",
            "write_paths": ["rtl/**", "src/**", "integration/**"],
            "workdir": ".",
            "timeout": 900,
            "agent_timeout": 3600,
            "success_pattern": "",
            "report_globs": [],
            "waveform_globs": ["**/*.vcd", "**/*.fst"],
        }, allow_unicode=True, sort_keys=False), encoding="utf-8")
        manifest = ensure_project_definition(staging, name)

        git("init")
        git("symbolic-ref", "HEAD", "refs/heads/main")
        git("-c", "user.name=Chip Nebula", "-c", "user.email=nebula@localhost",
            "add", ".")
        git("-c", "user.name=Chip Nebula", "-c", "user.email=nebula@localhost",
            "commit", "-m", "initial Chip Nebula project")
        if target.exists() and any(target.iterdir()):
            raise ValueError(f"创建期间目标目录出现了其他文件，未覆盖：{target}")
        staging.replace(target)
        return target / manifest.name
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _run_git(args: list[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        capture_output=True, text=True, cwd=cwd,
    )


def _is_valid_project_root(path: Path) -> bool:
    """Check if a directory looks like a chip-nebula project root."""
    return (path / ".chip_nebula").is_dir() and (path / ".chip_nebula" / "chip_nebula.yaml").exists()


def find_project_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """Find the project root (main git checkout) via git worktree list.

    Validates that the found directory contains .chip_nebula/chip_nebula.yaml
    to avoid returning the ChipNebula platform installation directory.
    """
    cwd = Path(start_path) if start_path else Path.cwd()

    result = _run_git(["worktree", "list", "--porcelain"], cwd=cwd)
    if result.returncode == 0:
        main_path = _parse_main_worktree(result.stdout)
        if main_path is not None and main_path.is_dir() and _is_valid_project_root(main_path):
            return main_path

    return _find_by_upward_search(cwd)


def _parse_main_worktree(porcelain_output: str) -> Optional[Path]:
    """Parse 'git worktree list --porcelain' output; first record = main."""
    for line in porcelain_output.splitlines():
        if line.startswith("worktree "):
            return Path(line[len("worktree "):])
    return None


def _find_by_upward_search(start: Path) -> Optional[Path]:
    current = start.resolve()
    for _ in range(10):
        if (current / ".chip_nebula").is_dir():
            return current
        if (current / ".git").exists():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent
    return None


def get_chip_nebula_dir(project_root: Optional[Path] = None) -> Path:
    root = project_root or find_project_root()
    if root is None:
        raise FileNotFoundError(
            "Project root not found. Run 'chip-nebula init' in your project directory."
        )
    return root / ".chip_nebula"


def get_worktrees_dir(project_root: Optional[Path] = None) -> Path:
    return get_chip_nebula_dir(project_root) / "worktrees"


def get_agents_dir(project_root: Optional[Path] = None) -> Path:
    return get_chip_nebula_dir(project_root) / "agents"


def get_pipelines_dir(project_root: Optional[Path] = None) -> Path:
    return get_chip_nebula_dir(project_root) / "pipelines"


def get_roles_dir(project_root: Optional[Path] = None) -> Path:
    return get_chip_nebula_dir(project_root) / "roles"


def get_recipes_dir(project_root: Optional[Path] = None) -> Path:
    return get_chip_nebula_dir(project_root) / "recipes"


def get_shared_dir(project_root: Optional[Path] = None) -> Path:
    return get_chip_nebula_dir(project_root) / "shared"


def get_skills_dir(project_root: Optional[Path] = None) -> Path:
    return get_shared_dir(project_root) / "skills"


def get_memory_dir(project_root: Optional[Path] = None) -> Path:
    return get_shared_dir(project_root) / "memory"


def get_templates_dir(project_root: Optional[Path] = None) -> Path:
    return get_shared_dir(project_root) / "templates"


def load_project_config(project_root: Optional[Path] = None) -> dict:
    config_path = get_chip_nebula_dir(project_root) / "chip_nebula.yaml"
    if not config_path.exists():
        return {}
    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def load_agent_config(
    agent_type: str,
    project_root: Optional[Path] = None,
    module: Optional[str] = None,
) -> dict:
    """Load agent YAML with module override support.

    Resolution order:
      1. `.chip_nebula/agents/<module>/<agent_type>.yaml` (if module given)
      2. `.chip_nebula/agents/common/<agent_type>.yaml`
      3. `.chip_nebula/agents/<agent_type>.yaml` (legacy flat layout)

    Returns {} if no config is found.
    """
    if not agent_type:
        return {}
    agents_dir = get_agents_dir(project_root)
    candidates: list[Path] = []
    if module:
        candidates.append(agents_dir / module / f"{agent_type}.yaml")
    candidates.append(agents_dir / "common" / f"{agent_type}.yaml")
    candidates.append(agents_dir / f"{agent_type}.yaml")

    for config_path in candidates:
        if not config_path.exists():
            continue
        try:
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def infer_module_from_pipeline_path(
    pipeline_path: str | Path,
    project_root: Optional[Path] = None,
) -> Optional[str]:
    """Infer the module name from a pipeline file path.

    For `.chip_nebula/pipelines/<module>/<file>.yaml` returns `<module>`.
    For files directly under `pipelines/common/` or outside the pipelines
    directory, returns None.
    """
    path = Path(pipeline_path).resolve()
    root = project_root or find_project_root()
    if root is None:
        return None
    pipelines_dir = get_pipelines_dir(root)
    try:
        rel = path.relative_to(pipelines_dir)
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) < 2:
        return None
    module = parts[0]
    if module == "common":
        return None
    return module


def get_sparse_patterns(project_root: Optional[Path] = None) -> list[str] | None:
    config = load_project_config(project_root)
    patterns = config.get("sparse_checkout")
    if patterns is None:
        return None  # full checkout
    if not isinstance(patterns, list):
        return None
    # Never let `.chip_nebula/` leak into a worktree — its presence would
    # duplicate (and potentially desync) the canonical agents/pipelines
    # configs in the main checkout. Silently filter it out; logging lives
    # in create_worktree()'s post-checkout assertion.
    filtered = [p for p in patterns if not _is_chip_nebula_pattern(p)]
    # Empty list means "no restriction" → fall back to full checkout
    return filtered if filtered else None


def _is_chip_nebula_pattern(pattern: str) -> bool:
    s = pattern.strip().lstrip("/").rstrip("/")
    return s == ".chip_nebula" or s.startswith(".chip_nebula/")


def is_in_worktree(path: Optional[Path] = None) -> bool:
    cwd = Path(path) if path else Path.cwd()
    result = _run_git(["worktree", "list", "--porcelain"], cwd=cwd)
    if result.returncode != 0:
        return False
    main_path = _parse_main_worktree(result.stdout)
    if main_path is None:
        return False
    return cwd.resolve() != main_path.resolve()


def init_project(
    project_path: Optional[Path] = None,
    project_name: str = "",
    top_module: str = "",
    model_provider: str = "deepseek",
    model_name: str = "deepseek-v4-pro",
    tools: Optional[list[dict]] = None,
    sparse_checkout: Optional[list[str]] = None,
) -> Path:
    target = Path(project_path) if project_path else Path.cwd()
    target = target.resolve()

    nebula_dir = target / ".chip_nebula"
    nebula_dir.mkdir(parents=True, exist_ok=True)

    agents_dir = nebula_dir / "agents"
    agents_common_dir = agents_dir / "common"
    pipelines_dir = nebula_dir / "pipelines"
    pipelines_common_dir = pipelines_dir / "common"
    roles_dir = nebula_dir / "roles"
    recipes_dir = nebula_dir / "recipes"
    shared_dir = nebula_dir / "shared"
    skills_dir = shared_dir / "skills"
    memory_dir = shared_dir / "memory"
    templates_dir = shared_dir / "templates"
    worktrees_dir = nebula_dir / "worktrees"

    for d in [agents_dir, agents_common_dir, pipelines_dir, pipelines_common_dir,
              roles_dir, recipes_dir,
              skills_dir, memory_dir, templates_dir, worktrees_dir]:
        d.mkdir(parents=True, exist_ok=True)

    _copy_platform_templates("agents", agents_dir)
    _copy_platform_templates("pipelines", pipelines_dir)
    _copy_platform_templates("roles", roles_dir)
    _copy_platform_templates("recipes", recipes_dir)
    _copy_platform_templates("skills", skills_dir)

    # Install packaged skills into the shared platform tree and every supported
    # framework discovery directory.  Using one installer keeps a freshly
    # initialized project identical to a project reopened by the desktop app.
    ensure_platform_assets(target)

    # --- dynamic defaults -------------------------------------------------
    resolved_tools = tools if tools is not None else _scan_installed_tools()
    if sparse_checkout is None:
        # None explicitly passed → full checkout (no sparse restriction)
        resolved_sparse = None
    elif sparse_checkout == []:
        # Empty list → let caller decide later; store empty for SKILL to fill
        resolved_sparse = []
    else:
        resolved_sparse = list(sparse_checkout)

    config = {
        "name": project_name or target.name,
        "top_module": top_module,
        "model": {
            "provider": model_provider,
            "model": model_name,
        },
        "sparse_checkout": resolved_sparse,
        "tools": resolved_tools,
    }
    config_path = nebula_dir / "chip_nebula.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    _update_gitignore(target)
    ensure_project_definition(target, project_name or target.name)

    return nebula_dir


def _platform_skill_tree_matches(source: Path, destination: Path) -> bool:
    """Whether every packaged Skill file exists unchanged in a project copy."""
    if not destination.is_dir():
        return False
    for source_file in source.rglob("*"):
        if not source_file.is_file():
            continue
        destination_file = destination / source_file.relative_to(source)
        if not destination_file.is_file():
            return False
        if destination_file.read_bytes() != source_file.read_bytes():
            return False
    return True


def ensure_framework_skills(project_root: Path) -> bool:
    """Install packaged Skills only into Agent framework discovery trees.

    This deliberately does not create ``.chip_nebula`` state.  Task Graph
    worktrees use it so framework context is available without changing the
    files eligible for an immutable Artifact commit.
    """
    import chip_nebula

    root = Path(project_root)
    skills_src = Path(chip_nebula.__file__).parent / "configs" / "skills"
    if not skills_src.is_dir():
        return False
    destinations = (
        root / ".claude" / "skills",
        root / ".codex" / "skills",
    )
    outdated = any(
        not _platform_skill_tree_matches(skills_src, destination)
        for destination in destinations
    )
    if not outdated:
        return False
    for destination in destinations:
        destination.mkdir(parents=True, exist_ok=True)
        for skill_dir in skills_src.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").is_file():
                shutil.copytree(
                    skill_dir, destination / skill_dir.name, dirs_exist_ok=True,
                )
    return True


def ensure_platform_assets(project_root: Path) -> dict:
    """桌面端打开/新建工程时的幂等平台资产刷新。

    与 ``init_project`` 不同，这里只更新平台自有资产（skills）并记录平台版本，
    不触碰用户的 roles/recipes/config（那些是工程可编辑的覆盖层）。
    已在旧版本平台初始化过的工程，版本不同则刷新技能包。
    """
    import chip_nebula

    root = Path(project_root)
    nebula_dir = root / ".chip_nebula"
    version_file = nebula_dir / "platform_version"
    installed = (
        version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else ""
    )
    current = chip_nebula.__version__
    skills_src = Path(chip_nebula.__file__).parent / "configs" / "skills"
    skills_dir = nebula_dir / "shared" / "skills"
    framework_skill_dirs = (root / ".claude" / "skills", root / ".codex" / "skills")
    refreshed = False
    skills_outdated = skills_src.is_dir() and (
        not _platform_skill_tree_matches(skills_src, skills_dir)
        or any(
            not _platform_skill_tree_matches(skills_src, target)
            for target in framework_skill_dirs
        )
    )
    if (installed != current or skills_outdated) and skills_src.is_dir():
        skills_dir.mkdir(parents=True, exist_ok=True)
        for skill_dir in skills_src.iterdir():
            if not skill_dir.is_dir() or not (skill_dir / "SKILL.md").is_file():
                continue
            dest = skills_dir / skill_dir.name
            shutil.copytree(skill_dir, dest, dirs_exist_ok=True)
        ensure_framework_skills(root)
        refreshed = True
    version_file.parent.mkdir(parents=True, exist_ok=True)
    version_file.write_text(current + "\n", encoding="utf-8")
    return {"platform_version": current, "skills_refreshed": refreshed}


def _copy_platform_templates(subdir: str, dest: Path) -> None:
    import chip_nebula
    template_dir = Path(chip_nebula.__file__).parent / "configs" / subdir
    if not template_dir.is_dir():
        return

    if subdir in ("agents", "pipelines"):
        common_dir = dest / "common"
        common_dir.mkdir(parents=True, exist_ok=True)
        for yaml_file in template_dir.glob("*.yaml"):
            if not yaml_file.is_file():
                continue
            if yaml_file.name.startswith("_"):
                shutil.copy2(yaml_file, dest / yaml_file.name)
            else:
                shutil.copy2(yaml_file, common_dir / yaml_file.name)
    else:
        for yaml_file in template_dir.glob("*.yaml"):
            if yaml_file.is_file():
                shutil.copy2(yaml_file, dest / yaml_file.name)

    # Nested configs (skills): copy subdirectories preserving structure
    for child_dir in template_dir.iterdir():
        if child_dir.is_dir():
            target_dir = dest / child_dir.name
            shutil.copytree(child_dir, target_dir, dirs_exist_ok=True)


def _update_gitignore(project_root: Path) -> None:
    gitignore = project_root / ".gitignore"
    entries = [
        "# Chip Nebula",
        ".chip_nebula/worktrees/",
        ".chip_nebula/shared/memory/",
    ]

    existing = set()
    if gitignore.exists():
        existing = set(gitignore.read_text().splitlines())

    new_lines = []
    for entry in entries:
        if entry not in existing:
            new_lines.append(entry)

    if new_lines:
        with open(gitignore, "a") as f:
            if gitignore.exists() and gitignore.read_text()[-1:] != "\n":
                f.write("\n")
            f.write("\n".join(new_lines) + "\n")


def create_worktree(feature_id: str, project_root: Optional[Path] = None) -> Path:
    root = project_root or find_project_root()
    if root is None:
        raise FileNotFoundError("Project root not found")

    worktrees_dir = get_worktrees_dir(root)
    worktree_path = worktrees_dir / feature_id
    branch_name = f"feat-{feature_id.replace('__', '-')}"

    with _WORKTREE_LOCK:
        if worktree_path.exists():
            git_file = worktree_path / ".git"
            if git_file.exists():
                return worktree_path
            raise RuntimeError(
                f"{worktree_path} exists but is not a git worktree. "
                "Delete it first (e.g. chip-nebula worktree-cleanup --force)."
            )

        _ensure_has_branch(root)

        _run_git(["worktree", "prune"], cwd=root)

        result = _run_git(
            ["worktree", "add", "--no-checkout", str(worktree_path), "-b", branch_name],
            cwd=root,
        )
        if result.returncode != 0:
            result = _run_git(
                ["worktree", "add", "--no-checkout", str(worktree_path), branch_name],
                cwd=root,
            )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create worktree: {result.stderr}")

        patterns = get_sparse_patterns(root)
        if patterns is None:
            # Full checkout — disable sparse restrictions
            _run_git(
                ["sparse-checkout", "disable"],
                cwd=worktree_path,
            )
        else:
            _run_git(
                ["sparse-checkout", "init", "--cone"],
                cwd=worktree_path,
            )
            _run_git(
                ["sparse-checkout", "set"] + patterns,
                cwd=worktree_path,
            )
        _run_git(
            ["checkout", branch_name],
            cwd=worktree_path,
        )

        _init_worktree_dirs(worktree_path)
        _symlink_skills(worktree_path, root)
        _assert_no_chip_nebula_in_worktree(worktree_path)

    return worktree_path


def _assert_no_chip_nebula_in_worktree(worktree_path: Path) -> None:
    """Cone-mode sparse-checkout already excludes `.chip_nebula/` (it's not
    in the include set), but the assertion catches the case where the
    repository's main branch committed this directory and the user's
    sparse_checkout config snuck it in through a glob we missed.
    """
    nebula = worktree_path / ".chip_nebula"
    if nebula.exists():
        import sys
        print(
            f"warning: {nebula} present in worktree; configs should live in "
            f"the main checkout only. Skill/agent lookups may be ambiguous.",
            file=sys.stderr,
        )


def _ensure_has_branch(repo_root: Path) -> None:
    """Refuse to operate on a repo with no commits; user must commit first."""
    result = _run_git(["rev-parse", "--verify", "HEAD"], cwd=repo_root)
    if result.returncode != 0:
        raise RuntimeError(
            f"Repository at {repo_root} has no commits yet. "
            "Please create an initial commit before running chip-nebula "
            "(e.g. `git add . && git commit -m 'init'`)."
        )


def _init_worktree_dirs(worktree: Path) -> None:
    dirs = ["results/lint", "results/sim", "results/sta"]
    for d in dirs:
        (worktree / d).mkdir(parents=True, exist_ok=True)


def _symlink_skills(worktree: Path, project_root: Path) -> None:
    skills_dir = get_skills_dir(project_root)
    skills_dir.mkdir(parents=True, exist_ok=True)
    claude_dir = worktree / ".claude"
    claude_dir.mkdir(exist_ok=True)
    skills_link = claude_dir / "skills"
    if not skills_link.exists():
        rel = os.path.relpath(skills_dir, skills_link.parent)
        skills_link.symlink_to(rel)


def remove_worktree(feature_id: str, project_root: Optional[Path] = None) -> None:
    root = project_root or find_project_root()
    if root is None:
        raise FileNotFoundError("Project root not found")

    worktree_path = get_worktrees_dir(root) / feature_id
    if not worktree_path.exists():
        return

    git_remove = _run_git(
        ["worktree", "remove", str(worktree_path), "--force"], cwd=root
    )
    if git_remove.returncode != 0:
        import shutil

        shutil.rmtree(worktree_path, ignore_errors=True)
        stale_admin = root / ".git" / "worktrees" / feature_id
        if stale_admin.exists():
            shutil.rmtree(stale_admin, ignore_errors=True)
        _run_git(["worktree", "prune"], cwd=root)


def worktree_has_uncommitted_changes(worktree_path: Path) -> bool:
    """Return True if the worktree has uncommitted changes (incl. untracked)."""
    result = _run_git(["status", "--porcelain"], cwd=worktree_path)
    if result.returncode != 0:
        return True
    return bool(result.stdout.strip())


def worktree_has_unmerged_commits(worktree_path: Path, base: str = "HEAD") -> bool:
    """Return True if branch has commits not reachable from any other branch.

    Conservative: if we can't determine, returns True to avoid data loss.
    """
    head = _run_git(["rev-parse", "HEAD"], cwd=worktree_path)
    if head.returncode != 0:
        return True
    branches = _run_git(
        ["for-each-ref", "--format=%(refname)", "refs/heads/"],
        cwd=worktree_path,
    )
    if branches.returncode != 0:
        return True
    current = _run_git(["symbolic-ref", "-q", "HEAD"], cwd=worktree_path)
    current_ref = current.stdout.strip() if current.returncode == 0 else ""
    others = [
        ref for ref in branches.stdout.split()
        if ref and ref != current_ref
    ]
    if not others:
        return True
    reachable = _run_git(
        ["rev-list", "--count", "HEAD", "--not"] + others,
        cwd=worktree_path,
    )
    if reachable.returncode != 0:
        return True
    try:
        return int(reachable.stdout.strip()) > 0
    except ValueError:
        return True
