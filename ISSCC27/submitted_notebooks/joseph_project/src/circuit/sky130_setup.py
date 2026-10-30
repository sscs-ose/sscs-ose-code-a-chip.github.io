"""Discover and validate a local, traceable subset of the SKY130 PDK."""

from dataclasses import dataclass
import os
from pathlib import Path
import re
from typing import Optional, Tuple


REQUIRED_DEVICE_MODELS: Tuple[str, ...] = (
    "sky130_fd_pr__nfet_01v8",
    "sky130_fd_pr__pfet_01v8",
    "sky130_fd_pr__nfet_01v8_lvt",
    "sky130_fd_pr__pfet_01v8_lvt",
)


@dataclass(frozen=True)
class Sky130ModelSetup:
    """Result of locating the model include needed by the generated netlist."""

    model_file: Optional[Path]
    checked_paths: Tuple[Path, ...]
    found_models: Tuple[str, ...]
    missing_models: Tuple[str, ...]

    @property
    def ready(self) -> bool:
        return self.model_file is not None and not self.missing_models

    @property
    def status(self) -> str:
        if self.ready:
            return "SKY130_MODELS_READY"
        if self.model_file is None:
            return "SKY130_MODELS_NOT_FOUND"
        return "SKY130_MODELS_INCOMPLETE"


def _candidate_model_paths(project_dir: Optional[str] = None) -> Tuple[Path, ...]:
    candidates = []
    explicit = os.environ.get("SKY130_MODEL_FILE")
    if explicit:
        candidates.append(Path(explicit).expanduser())

    pdk_root = os.environ.get("PDK_ROOT")
    if pdk_root:
        sky130 = Path(pdk_root).expanduser() / "sky130A"
        candidates.extend(
            (
                sky130 / "libs.tech" / "ngspice" / "sky130.lib.spice",
                sky130 / "libs.tech" / "ngspice" / "sky130.lib",
                sky130 / "libs.tech" / "ngspice" / "models" / "sky130.lib.spice",
            )
        )

    candidates.extend(
        (
            Path("/usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"),
            Path("/usr/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"),
        )
    )
    if project_dir:
        project = Path(project_dir)
        candidates.extend(
            (
                project / "data" / "models" / "sky130.lib.spice",
                project / "data" / "models" / "sky130_models.spice",
                project / "data" / "models" / "sky130_fd_pr" / "models" / "sky130_neurodyn_tt.lib.spice",
            )
        )

    unique = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return tuple(unique)


def _model_names(model_file: Path) -> Tuple[str, ...]:
    found = set()
    visited = set()
    pending = [model_file]
    while pending:
        current = pending.pop()
        if current in visited or not current.is_file():
            continue
        visited.add(current)
        text = current.read_text(encoding="utf-8", errors="replace")
        for model_name in REQUIRED_DEVICE_MODELS:
            pattern = (
                rf"(?im)^\s*\.(?:model|subckt)\s+"
                rf"{re.escape(model_name)}(?:\s|\(|$)"
            )
            if re.search(pattern, text):
                found.add(model_name)
        for include_name in re.findall(r'(?im)^\s*\.include\s+"?([^"\s]+)', text):
            include_path = Path(include_name)
            if not include_path.is_absolute():
                include_path = current.parent / include_path
            pending.append(include_path.resolve())
    return tuple(name for name in REQUIRED_DEVICE_MODELS if name in found)


def discover_sky130_models(project_dir: Optional[str] = None) -> Sky130ModelSetup:
    """Find an installed or explicitly supplied SKY130 model include.

    This function never downloads the PDK. It only inspects an explicit
    ``SKY130_MODEL_FILE``, ``PDK_ROOT/sky130A``, standard Linux install paths,
    and an optional project-local ``data/models`` directory.
    """

    checked = _candidate_model_paths(project_dir)
    for candidate in checked:
        if candidate.is_file():
            found = _model_names(candidate)
            missing = tuple(name for name in REQUIRED_DEVICE_MODELS if name not in found)
            return Sky130ModelSetup(candidate, checked, found, missing)
    return Sky130ModelSetup(None, checked, tuple(), REQUIRED_DEVICE_MODELS)
