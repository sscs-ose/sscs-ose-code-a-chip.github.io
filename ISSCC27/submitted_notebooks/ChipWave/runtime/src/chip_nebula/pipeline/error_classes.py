"""Error-class model driving the v0.2 stage scheduler.

Three concerns live here:

1. **Parsing** agent output for `Error-Class:` / `Error-Class-Reason:` markers.
2. **Merging** platform defaults + agent YAML + stage-level override into a
   single class spec map that the stage loop can query.
3. **Priority resolution** when an agent reports multiple classes in one
   iteration.

Intentionally kept text-marker based (not a tool-call protocol) so existing
adapters work without modification — the agent just needs to follow the
output convention the adapter's prompt asks for.
"""
import re
from typing import Iterable

from chip_nebula.models.task_manifest import ErrorClassSpec


# Platform-baseline classes. Any agent YAML inherits these unless it
# explicitly overrides by name. They represent the minimum set the
# interpreter needs to function safely in the absence of agent YAML.
PLATFORM_DEFAULT_CLASSES: dict[str, ErrorClassSpec] = {
    "transient_error": ErrorClassSpec(
        name="transient_error",
        priority=95,
        retry_budget=3,
        route_to="self",
        description="Infrastructure / adapter / subprocess crash without "
                    "classification; usually recoverable by retry.",
    ),
    "scope_violation": ErrorClassSpec(
        name="scope_violation",
        priority=92,
        retry_budget=1,
        route_to="self",
        description="Agent wrote to paths outside its declared write_paths "
                    "allow-list. Adapter enforces this post-run via git "
                    "status. Usually indicates the agent is fixing something "
                    "outside its charter — one local retry, then failed.",
    ),
    "unknown": ErrorClassSpec(
        name="unknown",
        priority=10,
        retry_budget=3,
        route_to="",
        description="Agent completed but did not tag an error class and the "
                    "gate still failed; interpreter falls back here.",
    ),
}


_CLASS_LINE_RE = re.compile(
    r"^\s*(?:\*\*)?\s*Error-Class\s*:\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*(?:\*\*)?\s*$",
    re.MULTILINE,
)
_REASON_LINE_RE = re.compile(
    r"^\s*(?:\*\*)?\s*Error-Class-Reason\s*:\s*(?P<reason>.+?)\s*(?:\*\*)?\s*$",
    re.MULTILINE,
)


def parse_error_classes_from_log(log: str) -> list[tuple[str, str]]:
    """Extract (class_name, reason) pairs from an agent's execution log.

    The log format the adapter prompt asks agents to emit:

        Error-Class: dut_error
        Error-Class-Reason: Port width mismatch at dut.v:42

    Multiple pairs allowed (multi-error iteration). Reasons are loosely
    paired positionally: if there are as many Reason lines as Class lines
    we zip them; otherwise we attach every Reason to every Class's tuple
    (rare; keeps output lenient).
    """
    if not log:
        return []

    names = [m.group("name") for m in _CLASS_LINE_RE.finditer(log)]
    reasons = [m.group("reason").strip() for m in _REASON_LINE_RE.finditer(log)]

    if not names:
        return []

    if len(reasons) == len(names):
        return list(zip(names, reasons))

    # Unequal counts: give every class the joined reason text so no
    # information is lost, but don't silently drop tags.
    joined = " | ".join(reasons)
    return [(name, joined) for name in names]


def resolve_error_classes(
    agent_cfg: dict,
    stage_cfg: dict,
) -> dict[str, ErrorClassSpec]:
    """Merge platform defaults + agent YAML + stage YAML overrides.

    Precedence (later beats earlier):
        platform defaults  <  agent YAML  <  stage `error_classes_override`

    The returned dict always contains at least `transient_error` and
    `unknown` (inherited from platform defaults) so the caller never has
    to worry about KeyError on those fallbacks.
    """
    merged: dict[str, ErrorClassSpec] = {}
    for name, spec in PLATFORM_DEFAULT_CLASSES.items():
        merged[name] = ErrorClassSpec(
            name=spec.name, priority=spec.priority,
            retry_budget=spec.retry_budget, route_to=spec.route_to,
            description=spec.description,
        )

    for name, raw in (agent_cfg.get("error_classes") or {}).items():
        merged[name] = _merge_spec(merged.get(name), name, raw)

    for name, raw in (stage_cfg.get("error_classes_override") or {}).items():
        merged[name] = _merge_spec(merged.get(name), name, raw)

    return merged


def _merge_spec(
    base: ErrorClassSpec | None, name: str, raw: dict,
) -> ErrorClassSpec:
    if not isinstance(raw, dict):
        return base or ErrorClassSpec(name=name)
    seed = base or ErrorClassSpec(name=name)
    return ErrorClassSpec(
        name=name,
        priority=int(raw.get("priority", seed.priority)),
        retry_budget=int(raw.get("retry_budget", seed.retry_budget)),
        route_to=str(raw.get("route_to", seed.route_to)),
        description=str(raw.get("description", seed.description)),
    )


def pick_winner_class(
    reported: Iterable[str],
    specs: dict[str, ErrorClassSpec],
) -> str:
    """Return the highest-priority class name in `reported` that exists in
    `specs`. If none of the reported names is known, falls back to
    `"unknown"`.
    """
    candidates = [name for name in reported if name in specs]
    if not candidates:
        return "unknown"
    return max(candidates, key=lambda n: specs[n].priority)
