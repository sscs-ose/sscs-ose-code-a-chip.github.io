"""Versioned, read-only guidance for the desktop stage advisors.

This content can improve through evaluation, but it never grants permissions or
changes deterministic design, acceptance, or physical signoff gates.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path


_CATALOG = Path(__file__).resolve().parents[1] / "configs/stage_skills/desktop-advisor-v1.json"
_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


class StageSkillError(ValueError):
    """A stage skill is missing or cannot be bound to an immutable version."""


@dataclass(frozen=True)
class StageSkill:
    id: str
    version: str
    workspace: str
    instructions: str
    digest: str

    def as_record(self) -> dict[str, str]:
        return {
            "id": self.id,
            "version": self.version,
            "workspace": self.workspace,
            "instructions": self.instructions,
            "digest": self.digest,
        }


def _digest(document: dict[str, str]) -> str:
    canonical = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def load_stage_skill(workspace: str, *, catalog: Path = _CATALOG) -> StageSkill:
    """Freeze the selected stage guidance into a run record before dispatch."""
    try:
        document = json.loads(catalog.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise StageSkillError("stage skill catalog is missing or unreadable") from exc
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise StageSkillError("unsupported stage skill catalog schema")
    identity, version = document.get("id"), document.get("version")
    common, workspaces = document.get("common"), document.get("workspaces")
    if (
        not isinstance(identity, str) or not identity
        or not isinstance(version, str) or not _VERSION.fullmatch(version)
        or not isinstance(common, str) or not common.strip()
        or not isinstance(workspaces, dict)
        or any(not isinstance(name, str) or not isinstance(value, str) or not value.strip()
               for name, value in workspaces.items())
    ):
        raise StageSkillError("invalid stage skill catalog")
    guidance = workspaces.get(workspace)
    if not isinstance(guidance, str) or not guidance.strip():
        raise StageSkillError(f"no stage skill for workspace: {workspace}")
    instructions = common.strip() + "\n" + guidance.strip()
    bound = {
        "id": identity, "version": version, "workspace": workspace,
        "instructions": instructions,
    }
    return StageSkill(**bound, digest=_digest(bound))


def verify_stage_skill(record: dict[str, str]) -> None:
    """Reject a changed recorded skill instead of silently using new guidance."""
    bound = {
        name: record.get(name) for name in ("id", "version", "workspace", "instructions")
    }
    if any(not isinstance(value, str) or not value for value in bound.values()):
        raise StageSkillError("recorded stage skill is incomplete")
    if record.get("digest") != _digest(bound):
        raise StageSkillError("recorded stage skill digest changed")
