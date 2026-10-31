import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


@dataclass
class ValidationResult:
    name: str
    status: str  # "PASS" | "WARN" | "FAIL"
    message: str
    suggestion: str = ""


@dataclass
class EnvironmentReport:
    all_pass: bool
    results: list[ValidationResult] = field(default_factory=list)

    @property
    def failures(self) -> list[ValidationResult]:
        return [r for r in self.results if r.status == "FAIL"]

    @property
    def warnings(self) -> list[ValidationResult]:
        return [r for r in self.results if r.status == "WARN"]


class EnvironmentValidator:
    def __init__(
        self,
        tool_base_path: Optional[Path] = None,
        project_root: Optional[Path] = None,
    ):
        self.tool_base_path = Path(tool_base_path or "tools")
        self.project_root = Path(project_root) if project_root else None

    def validate(self, requirements_file: Optional[str] = None) -> EnvironmentReport:
        results: list[ValidationResult] = []

        results.append(self._check_python_version())
        results.extend(self._check_agent_frameworks())
        results.extend(self._check_framework_dependencies())
        results.extend(self._check_eda_tools())
        if requirements_file:
            results.extend(self.check_python_packages(requirements_file))

        return EnvironmentReport(
            all_pass=not any(r.status == "FAIL" for r in results),
            results=results,
        )

    def _check_python_version(self) -> ValidationResult:
        version = sys.version_info
        if version >= (3, 11):
            return ValidationResult(
                name="Python Version",
                status="PASS",
                message=f"Python {version.major}.{version.minor}.{version.micro}",
            )
        return ValidationResult(
            name="Python Version",
            status="FAIL",
            message=f"Python {version.major}.{version.minor} (3.11+ required)",
            suggestion="Install Python 3.11 or later",
        )

    def _check_agent_frameworks(self) -> list[ValidationResult]:
        results: list[ValidationResult] = []

        frameworks = {
            "opencode": "OpenCode (recommended)",
            "claude": "Claude Code",
            "qodercli": "Qoder CLI",
            "codex": "Codex",
            "cc-switch": "cc-switch (model switching)",
        }

        for cmd, display_name in frameworks.items():
            path = shutil.which(cmd)
            if path:
                results.append(ValidationResult(
                    name=display_name,
                    status="PASS",
                    message=f"Found: {path}",
                ))
            else:
                if cmd == "opencode":
                    status = "WARN"
                    suggestion = "Install: npm install -g opencode"
                elif cmd == "claude":
                    status = "WARN"
                    suggestion = "Install: npm install -g @anthropic-ai/claude-code"
                elif cmd == "qodercli":
                    status = "WARN"
                    suggestion = "Install: npm install -g @qoder-ai/qoder-cli"
                elif cmd == "codex":
                    status = "WARN"
                    suggestion = "Install: npm install -g @openai/codex"
                else:
                    status = "WARN"
                    suggestion = "Install: npm install -g cc-switch"
                results.append(ValidationResult(
                    name=display_name,
                    status=status,
                    message=f"Not found in PATH",
                    suggestion=suggestion,
                ))

        return results

    def _discover_frameworks(self) -> set[str]:
        """Scan agent and pipeline YAMLs to find frameworks actually in use."""
        frameworks: set[str] = set()
        if self.project_root is None:
            return frameworks
        if yaml is None:
            return frameworks

        for subdir in ("agents", "pipelines"):
            base = self.project_root / ".chip_nebula" / subdir
            if not base.exists():
                continue
            for path in sorted(base.glob("*.yaml")):
                try:
                    with open(path, encoding="utf-8") as fh:
                        data = yaml.safe_load(fh)
                except Exception:
                    continue
                if not isinstance(data, dict):
                    continue

                # Agent YAML: top-level 'framework' field
                framework = data.get("framework")
                if isinstance(framework, str):
                    frameworks.add(framework)

                # Pipeline YAML: 'framework' may appear in stage config
                stages = data.get("stages", {})
                if isinstance(stages, dict):
                    for stage in stages.values():
                        if isinstance(stage, dict):
                            fw = stage.get("framework")
                            if isinstance(fw, str):
                                frameworks.add(fw)

        return frameworks

    def _check_framework_dependencies(self) -> list[ValidationResult]:
        """Check runtime dependencies for frameworks declared in project YAMLs."""
        results: list[ValidationResult] = []
        frameworks = self._discover_frameworks()

        if not frameworks:
            return results

        if yaml is None:
            results.append(ValidationResult(
                name="Framework Dependency Scan",
                status="WARN",
                message="PyYAML not installed; cannot scan framework usage",
                suggestion="pip install pyyaml",
            ))
            return results

        # Map framework name -> (dependency type, dependency name, install suggestion)
        framework_requirements = {
            "claudecode": {
                "kind": "python_package",
                "name": "claude_agent_sdk",
                "suggestion": "pip install claude-agent-sdk",
                "display": "Claude Code Agent SDK",
            },
            "opencode": {
                "kind": "cli",
                "name": "opencode",
                "suggestion": "npm install -g opencode",
                "display": "OpenCode CLI",
            },
            "qoder-cli": {
                "kind": "python_package",
                "name": "qoder_agent_sdk",
                "suggestion": "pip install qoder-agent-sdk",
                "display": "Qoder Agent SDK",
            },
            "qodercli": {
                "kind": "python_package",
                "name": "qoder_agent_sdk",
                "suggestion": "pip install qoder-agent-sdk",
                "display": "Qoder Agent SDK",
            },
            "codex": {
                "kind": "cli",
                "name": "codex",
                "suggestion": "npm install -g @openai/codex",
                "display": "Codex CLI",
            },
            "mock": {
                "kind": "none",
                "name": "",
                "suggestion": "",
                "display": "Mock Framework",
            },
        }

        for fw in sorted(frameworks):
            req = framework_requirements.get(fw)
            if req is None:
                results.append(ValidationResult(
                    name=f"Framework: {fw}",
                    status="WARN",
                    message=f"Unknown framework '{fw}' declared in project YAML",
                    suggestion="Check agent/pipeline YAML framework values",
                ))
                continue

            if req["kind"] == "none":
                continue

            if req["kind"] == "python_package":
                try:
                    __import__(req["name"])
                    results.append(ValidationResult(
                        name=req["display"],
                        status="PASS",
                        message=f"Python package '{req['name']}' is importable",
                    ))
                except ImportError:
                    results.append(ValidationResult(
                        name=req["display"],
                        status="FAIL",
                        message=f"Python package '{req['name']}' not found",
                        suggestion=req["suggestion"],
                    ))

            elif req["kind"] == "cli":
                path = shutil.which(req["name"])
                if path:
                    results.append(ValidationResult(
                        name=req["display"],
                        status="PASS",
                        message=f"Found: {path}",
                    ))
                else:
                    results.append(ValidationResult(
                        name=req["display"],
                        status="FAIL",
                        message=f"Command '{req['name']}' not found in PATH",
                        suggestion=req["suggestion"],
                    ))

        return results

    def _check_eda_tools(self) -> list[ValidationResult]:
        results: list[ValidationResult] = []

        eda_tools = {
            "verilator": {
                "display": "Verilator",
                "min_version": "5.0",
                "critical": True,
                "check_cmd": ["verilator", "--version"],
            },
            "yosys": {
                "display": "Yosys",
                "min_version": "0.30",
                "critical": False,
                "check_cmd": ["yosys", "-V"],
            },
        }

        for tool_name, tool_info in eda_tools.items():
            result = self._check_eda_tool(tool_name, tool_info)
            results.append(result)

        return results

    def _check_eda_tool(self, tool_name: str, tool_info: dict) -> ValidationResult:
        path = shutil.which(tool_name)
        if path:
            return ValidationResult(
                name=tool_info["display"],
                status="PASS",
                message=f"Found: {path}",
            )

        if tool_info["critical"]:
            return ValidationResult(
                name=tool_info["display"],
                status="FAIL",
                message=f"Not found in PATH",
                suggestion=f"Install {tool_info['display']} and add to PATH",
            )
        return ValidationResult(
            name=tool_info["display"],
            status="WARN",
            message=f"Not found in PATH (optional)",
            suggestion=f"Install {tool_info['display']} for full functionality",
        )

    def check_python_packages(self, requirements_file: str = "requirements.txt") -> list[ValidationResult]:
        results: list[ValidationResult] = []

        if not os.path.exists(requirements_file):
            return [ValidationResult(
                name="Python Packages",
                status="WARN",
                message=f"Requirements file not found: {requirements_file}",
            )]

        try:
            import pkg_resources
            with open(requirements_file) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    try:
                        pkg_resources.require(line)
                    except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict) as e:
                        results.append(ValidationResult(
                            name=f"Package: {line}",
                            status="WARN",
                            message=str(e),
                            suggestion=f"pip install {line}",
                        ))
        except ImportError:
            results.append(ValidationResult(
                name="Python Packages",
                status="WARN",
                message="pkg_resources not available, skipping package check",
            ))

        if not results:
            results.append(ValidationResult(
                name="Python Packages",
                status="PASS",
                message="All requirements satisfied",
            ))

        return results


def validate_environment(
    tool_base_path: Optional[str] = None,
    requirements_file: Optional[str] = None,
    project_root: Optional[str] = None,
) -> EnvironmentReport:
    validator = EnvironmentValidator(
        tool_base_path=Path(tool_base_path) if tool_base_path else None,
        project_root=Path(project_root) if project_root else None,
    )
    return validator.validate(requirements_file=requirements_file)
