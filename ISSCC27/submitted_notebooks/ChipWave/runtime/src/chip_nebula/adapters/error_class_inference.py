"""Shared helper for recovering Error-Class tags from agent output.

Agents do not always follow the strict ``Error-Class: <name>`` /
``Error-Class-Reason: ...`` contract.  They sometimes emit the class in
Chinese headers (``错误分类（rtl_bug）``), inside code blocks
(``class=rtl_bug``), or as a route target (``route → rtl_coding``).

This module provides a single, adapter-agnostic inference function that maps
those soft signals back to configured error classes so the pipeline can route
correctly instead of falling back to ``unknown``.
"""

import re
from typing import Any


def extract_reason_snippet(text: str, start: int, end: int) -> str:
    """Return the line containing the matched span, with markdown noise removed."""
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end == -1:
        line_end = len(text)
    snippet = text[line_start:line_end].strip()
    snippet = re.sub(r"[`#*]", "", snippet)
    return snippet[:200]


def infer_error_class(
    output_text: str,
    class_specs: dict[str, Any],
) -> tuple[str, str] | None:
    """Recover an error-class tag when the agent forgot the strict format.

    Agents sometimes emit ``class=rtl_bug`` inside code blocks, Chinese
    headers like ``错误分类（rtl_bug）``, or ``route → rtl_coding``.  When
    the strict ``Error-Class:`` tag is missing, this helper maps those
    soft signals back to a configured class so the interpreter can route
    correctly instead of falling back to ``unknown``.

    Args:
        output_text: The raw text produced by the agent.
        class_specs: Mapping from class name to ``ErrorClassSpec``.

    Returns:
        ``(class_name, reason)`` for the highest-priority inferred class,
        or ``None`` if no soft signal is found or if a valid strict tag
        already exists in ``output_text``.
    """
    if not class_specs:
        return None

    # If the agent already emitted a valid strict tag, do not override it.
    from chip_nebula.pipeline.error_classes import parse_error_classes_from_log

    if parse_error_classes_from_log(output_text):
        return None

    candidates: list[tuple[str, str]] = []
    lower_text = output_text.lower()

    # Pattern 1: class=xxx or class : xxx (often inside code blocks)
    for match in re.finditer(
        r"(?:^|\s|[`#*（(])class\s*[=:]\s*([A-Za-z_][A-Za-z0-9_]*)",
        output_text,
        re.MULTILINE,
    ):
        name = match.group(1)
        if name in class_specs:
            snippet = extract_reason_snippet(
                output_text, match.start(), match.end()
            )
            candidates.append((name, snippet))

    # Pattern 2: Chinese "错误分类（xxx）"
    for match in re.finditer(
        r"错误分类\s*[（(]\s*([A-Za-z_][A-Za-z0-9_]*)",
        output_text,
    ):
        name = match.group(1)
        if name in class_specs:
            snippet = extract_reason_snippet(
                output_text, match.start(), match.end()
            )
            candidates.append((name, snippet))

    # Pattern 3: route target → map back to class with matching route_to
    route_targets: list[tuple[str, int, int]] = []
    for pattern in [
        r"\broute\w*\s*[→:]\s*([A-Za-z_][A-Za-z0-9_]*)",
        r"路由\s*[→:]\s*([A-Za-z_][A-Za-z0-9_]*)",
        r"route[_\s]to\s*[:=]?\s*([A-Za-z_][A-Za-z0-9_]*)",
    ]:
        for match in re.finditer(pattern, output_text, re.IGNORECASE):
            route_targets.append((match.group(1), match.start(), match.end()))

    # Pattern 4: "classified `xxx`" or "class: `xxx`"
    classified_names: list[tuple[str, int, int]] = []
    for pattern in [
        r"(?:classified|classification)\s*[`\[]?([A-Za-z_][A-Za-z0-9_]*)[`\]]?",
        r"(?:class|错误分类)\s*[:：]\s*`([A-Za-z_][A-Za-z0-9_]*)`",
    ]:
        for match in re.finditer(pattern, output_text, re.IGNORECASE):
            classified_names.append((match.group(1), match.start(), match.end()))

    for name, start, end in classified_names:
        if name in class_specs:
            snippet = extract_reason_snippet(output_text, start, end)
            candidates.append((name, snippet))

    # Map route targets back to classes whose route_to matches the target.
    for target, start, end in route_targets:
        for name, spec in class_specs.items():
            route_to = getattr(spec, "route_to", "")
            if route_to == target and target != "self":
                snippet = extract_reason_snippet(output_text, start, end)
                candidates.append((name, snippet))

    if not candidates:
        return None

    # Pick highest priority class; tie-break by first textual occurrence
    def sort_key(item: tuple[str, str]) -> tuple[int, int]:
        name, _ = item
        first_pos = lower_text.find(name.lower())
        return (-class_specs[name].priority, first_pos)

    candidates.sort(key=sort_key)
    winner, snippet = candidates[0]
    return winner, snippet or f"agent mentioned `{winner}` (auto-detected)"
