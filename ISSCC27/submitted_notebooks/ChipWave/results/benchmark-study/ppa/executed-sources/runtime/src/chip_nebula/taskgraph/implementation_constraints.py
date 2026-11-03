"""Validation helpers for PREPARE implementation constraints.

The project-constraints Agent may propose questions before a human decision,
but it may only materialize the final constraint document after that decision
barrier has closed.  These helpers are deliberately deterministic so an Agent
cannot publish an incomplete or stale implementation baseline.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Mapping


class ImplementationConstraintsError(ValueError):
    """The proposed project implementation constraints are not publishable."""


PROJECT_CONSTRAINT_CATEGORIES = (
    "platform_pvt",
    "clock_sta",
    "physical_io_boundary",
    "io_timing",
    "power_reset",
    "memory_implementation",
    "memory_access_latency",
    "floorplan",
    "ppa",
    "cdc_exceptions",
    "signoff_level",
)


def project_constraint_category(*values: object) -> str:
    """Return the stable engineering category represented by a decision.

    Project-constraint decision request Artifact IDs are intentionally random,
    while their engineering meaning must survive a signed-spec revision.  This
    small classifier provides a migration path for historical requests and is
    also stored explicitly on newly published requests.
    """

    rules = (
        ("memory_access_latency", (
            "ram512-access", "memory-access", "access-latency", "read latency",
            "访问延迟", "读延迟", "时延语义",
        )),
        ("platform_pvt", (
            "platform-pvt", "target platform", "pvt", "工艺平台", "目标平台",
            "工艺角", "process corner",
        )),
        ("clock_sta", (
            "clock-sta", "primary-clock", "clock contract", "时钟与 sta",
            "时钟约束", "时序预算", "clock period",
        )),
        ("physical_io_boundary", (
            "physical-io", "io-boundary", "pad boundary", "pad ring",
            "物理 io", "封装边界", "pad 边界",
        )),
        ("io_timing", (
            "io-timing", "input delay", "output delay", "io 时序",
            "接口时序", "输入输出延迟",
        )),
        ("power_reset", (
            "power-voltage-reset", "power intent", "voltage", "供电",
            "电压", "复位意图", "power domain",
        )),
        ("memory_implementation", (
            "memory-implementation", "sram", "memory macro", "ram512",
            "存储器实现", "存储宏", "内存宏",
        )),
        ("floorplan", (
            "floorplan", "utilization", "布局规划", "利用率", "die area",
        )),
        ("ppa", (
            "ppa", "area-power", "面积功耗", "面积目标", "功耗目标",
        )),
        ("cdc_exceptions", (
            "cdc", "physical-exception", "timing exception", "跨时钟",
            "时序例外", "同步器",
        )),
        ("signoff_level", (
            "signoff", "delivery-level", "签核", "交付等级", "交付范围",
        )),
    )
    for value in values:
        text = str(value or "").lower()
        category = next((category for category, needles in rules if any(
            needle in text for needle in needles
        )), "")
        if category:
            return category
    return ""


def unavailable_constraint_categories(
    document: Mapping[str, Any], *,
    available_platforms: set[str] | frozenset[str],
    available_corners: Mapping[str, set[str] | frozenset[str]] | None = None,
    available_memory_macros: set[str] | frozenset[str] | None = None,
    available_memory_macro_views: Mapping[str, Mapping[str, str]] | None = None,
) -> set[str]:
    """Return prior choices that the installed tool inventory cannot honor."""

    invalid: set[str] = set()
    platform = str(document.get("platform", "")).strip()
    corner = str(document.get("corner", "")).strip()
    if (
        not platform or platform not in available_platforms
        or available_corners is not None
        and corner not in available_corners.get(platform, set())
    ):
        invalid.add("platform_pvt")
    memory = document.get("memory")
    if isinstance(memory, Mapping) and memory.get("policy") == "hard_macro_required":
        required_views = {
            str(item).strip() for item in memory.get("required_views", []) if str(item).strip()
        }
        for instance in memory.get("instances", []):
            if not isinstance(instance, Mapping):
                invalid.add("memory_implementation")
                continue
            macro = str(instance.get("macro", "")).strip()
            if not macro or (
                available_memory_macros is not None and macro not in available_memory_macros
            ):
                invalid.add("memory_implementation")
                continue
            if available_memory_macro_views is not None:
                views = available_memory_macro_views.get(macro, {})
                if required_views - set(views):
                    invalid.add("memory_implementation")
    return invalid


def implementation_constraints_semantic_digest(
    document: Mapping[str, Any], *, spec_digest: str,
) -> str:
    """Hash meaning without treating integral JSON numbers as a new baseline."""

    def canonical(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {str(key): canonical(item) for key, item in value.items()}
        if isinstance(value, list):
            return [canonical(item) for item in value]
        if type(value) is float and math.isfinite(value) and value.is_integer():
            return int(value)
        return value

    encoded = json.dumps(
        canonical(document), ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(encoded + spec_digest.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def validate_constraint_questions(
    document: Any, *, spec_revision_id: str, allow_empty: bool = True,
) -> list[dict[str, Any]]:
    if not isinstance(document, list):
        raise ImplementationConstraintsError("project constraint questions must be a list")
    if not document and not allow_empty:
        raise ImplementationConstraintsError(
            "project constraint analysis must produce at least one human decision"
        )
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(document):
        if not isinstance(raw, Mapping):
            raise ImplementationConstraintsError(f"constraint question {index} must be an object")
        issue_id = str(raw.get("id", "")).strip()
        title = str(raw.get("title", "")).strip()
        context = str(raw.get("context", "")).strip()
        options = raw.get("options")
        if not issue_id or issue_id in seen:
            raise ImplementationConstraintsError(
                f"constraint question {index} needs a unique non-empty id"
            )
        if not title or not context:
            raise ImplementationConstraintsError(
                f"constraint question {issue_id} needs title and context"
            )
        if not isinstance(options, list) or len(options) < 2:
            raise ImplementationConstraintsError(
                f"constraint question {issue_id} needs at least two options"
            )
        option_keys: set[str] = set()
        normalized_options: list[dict[str, str]] = []
        for option in options:
            if not isinstance(option, Mapping):
                raise ImplementationConstraintsError(
                    f"constraint question {issue_id} has a non-object option"
                )
            key = str(option.get("key", "")).strip()
            label = str(option.get("label", "")).strip()
            description = str(option.get("description", "")).strip()
            if not key or key in option_keys or not label or not description:
                raise ImplementationConstraintsError(
                    f"constraint question {issue_id} options need unique key, label and description"
                )
            option_keys.add(key)
            normalized_options.append({
                "key": key, "label": label, "description": description,
            })
        recommendation = str(raw.get("recommendation", "")).strip()
        if recommendation and recommendation not in option_keys:
            raise ImplementationConstraintsError(
                f"constraint question {issue_id} recommendation is not an option"
            )
        bound_revision = str(raw.get("spec_revision_id", spec_revision_id)).strip()
        if bound_revision != spec_revision_id:
            raise ImplementationConstraintsError(
                f"constraint question {issue_id} is bound to a stale specification"
            )
        seen.add(issue_id)
        result.append({
            "id": issue_id,
            "title": title,
            "context": context,
            "options": normalized_options,
            **({"recommendation": recommendation} if recommendation else {}),
            "blocking": bool(raw.get("blocking", True)),
            "spec_revision_id": spec_revision_id,
        })
    return result


def missing_implementation_parameters(document: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Keep the Author's parameter requests until their actual values are supplied."""
    completion = document.get("completion", {})
    if not isinstance(completion, Mapping):
        raise ImplementationConstraintsError("completion must be an object")
    requests = completion.get("missing_parameters", [])
    if not isinstance(requests, list) or any(
        not isinstance(item, Mapping) or not isinstance(item.get("fields"), list)
        or any(not isinstance(field, str) for field in item["fields"])
        for item in requests
    ):
        raise ImplementationConstraintsError("missing_parameters must contain field lists")

    def incomplete(value: Any) -> bool:
        if isinstance(value, (list, dict)):
            values = value.values() if isinstance(value, dict) else value
            return not value or any(incomplete(item) for item in values)
        return value is None or value == ""

    missing = []
    for item in requests:
        fields = []
        for path in item["fields"]:
            if not re.fullmatch(r"[A-Za-z_]\w*(?:\[\d+\]|\.[A-Za-z_]\w*)*", path):
                raise ImplementationConstraintsError(f"invalid parameter path: {path}")
            value: Any = document
            for token in re.findall(r"[A-Za-z_]\w*|\d+", path):
                if isinstance(value, Mapping):
                    value = value.get(token)
                elif isinstance(value, list) and token.isdigit() and int(token) < len(value):
                    value = value[int(token)]
                else:
                    value = None
            if incomplete(value):
                fields.append(path)
        if fields:
            missing.append({**item, "fields": fields})
    return missing


def validate_implementation_constraints(
    document: Any, *, spec_revision_id: str,
    available_platforms: set[str] | frozenset[str],
    available_corners: Mapping[str, set[str] | frozenset[str]] | None = None,
    available_memory_macros: set[str] | frozenset[str] | None = None,
    available_memory_macro_views: Mapping[str, Mapping[str, str]] | None = None,
    available_platform_details: Mapping[str, Mapping[str, Any]] | None = None,
    required_decision_ids: set[str] | frozenset[str] | None = None,
    require_frozen: bool = True,
    allow_incomplete: bool = False,
) -> dict[str, Any]:
    if not isinstance(document, Mapping):
        raise ImplementationConstraintsError("implementation constraints must be an object")
    if document.get("schema_version") != 1:
        raise ImplementationConstraintsError("implementation constraints need schema_version: 1")
    status = str(document.get("status", "")).strip()
    allowed_statuses = {"frozen"} if require_frozen else {"draft", "frozen"}
    if status not in allowed_statuses:
        raise ImplementationConstraintsError(
            "implementation constraints must have status: "
            + ("frozen" if require_frozen else "draft or frozen")
        )
    if str(document.get("spec_revision_id", "")) != spec_revision_id:
        raise ImplementationConstraintsError(
            "implementation constraints are not bound to the current signed specification"
        )
    platform = str(document.get("platform", "")).strip()
    if not platform or platform not in available_platforms:
        raise ImplementationConstraintsError(
            f"implementation platform is unavailable: {platform or '(empty)'}"
        )
    corner = str(document.get("corner", "")).strip()
    if not corner:
        raise ImplementationConstraintsError("implementation constraints need a corner")
    if available_corners is not None and corner not in available_corners.get(platform, set()):
        raise ImplementationConstraintsError(
            f"implementation corner is unavailable for {platform}: {corner}"
        )
    decision_ids = document.get("decision_ids")
    if not isinstance(decision_ids, list) or any(
        not isinstance(item, str) or not item.strip() for item in decision_ids
    ):
        raise ImplementationConstraintsError(
            "implementation constraints must cite the human decision_ids used to create them"
        )
    normalized_decision_ids = list(dict.fromkeys(str(item).strip() for item in decision_ids))
    if required_decision_ids is not None and set(normalized_decision_ids) != set(required_decision_ids):
        missing = sorted(set(required_decision_ids) - set(normalized_decision_ids))
        unexpected = sorted(set(normalized_decision_ids) - set(required_decision_ids))
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if unexpected:
            details.append("unexpected " + ", ".join(unexpected))
        raise ImplementationConstraintsError(
            "implementation constraints decision_ids do not match the resolved human decisions"
            + (": " + "; ".join(details) if details else "")
        )


    io = document.get("io")
    power = document.get("power")
    if not isinstance(io, Mapping) or not isinstance(power, Mapping):
        raise ImplementationConstraintsError("implementation constraints need io and power objects")
    clocks = document.get("clocks")
    if not isinstance(clocks, list) or not clocks:
        raise ImplementationConstraintsError("implementation constraints need at least one clock")
    if allow_incomplete:
        if require_frozen or status != "draft":
            raise ImplementationConstraintsError("incomplete constraints may only be saved as a draft")
        if any(not isinstance(clock, Mapping) for clock in clocks):
            raise ImplementationConstraintsError("draft clocks must be objects")
        for key in ("ppa", "floorplan", "memory", "completion"):
            if key in document and not isinstance(document[key], Mapping):
                raise ImplementationConstraintsError(f"draft {key} must be an object")
        memory = document.get("memory", {})
        instances = memory.get("instances", [])
        if not isinstance(instances, list) or any(not isinstance(item, Mapping) for item in instances):
            raise ImplementationConstraintsError("draft memory.instances must be a list of objects")
        missing_implementation_parameters(document)
        try:
            return json.loads(json.dumps(document, allow_nan=False))
        except (TypeError, ValueError) as exc:
            raise ImplementationConstraintsError("draft must contain finite JSON values") from exc
    normalized_clocks: list[dict[str, Any]] = []
    seen_clocks: set[str] = set()
    for index, raw in enumerate(clocks):
        if not isinstance(raw, Mapping):
            raise ImplementationConstraintsError(f"clock {index} must be an object")
        name = str(raw.get("name", "")).strip()
        port = str(raw.get("port", "")).strip()
        period = raw.get("period_ns")
        if (
            not name or name in seen_clocks or not port
            or type(period) not in {int, float}
            or not math.isfinite(float(period)) or float(period) <= 0
        ):
            raise ImplementationConstraintsError(
                f"clock {index} needs unique name, port and positive finite period_ns"
            )
        uncertainty = raw.get("uncertainty_ns", 0.0)
        if (
            type(uncertainty) not in {int, float}
            or not math.isfinite(float(uncertainty)) or float(uncertainty) < 0
        ):
            raise ImplementationConstraintsError(f"clock {name} has invalid uncertainty_ns")
        waveform = raw.get("waveform_ns", [0.0, float(period) / 2.0])
        if (
            not isinstance(waveform, list) or len(waveform) != 2
            or any(type(value) not in {int, float} for value in waveform)
            or not 0 <= float(waveform[0]) < float(waveform[1]) <= float(period)
        ):
            raise ImplementationConstraintsError(f"clock {name} has invalid waveform_ns")
        seen_clocks.add(name)
        normalized_clocks.append({
            **dict(raw),
            "name": name,
            "port": port,
            "period_ns": float(period),
            "waveform_ns": [float(waveform[0]), float(waveform[1])],
            "uncertainty_ns": float(uncertainty),
        })
    ppa = document.get("ppa")
    if isinstance(ppa, Mapping) and "frequency_mhz" in ppa:
        frequency = ppa.get("frequency_mhz")
        if (
            type(frequency) not in {int, float}
            or not math.isfinite(float(frequency)) or float(frequency) <= 0
        ):
            raise ImplementationConstraintsError("ppa.frequency_mhz must be positive and finite")
        clock_frequency = 1000.0 / normalized_clocks[0]["period_ns"]
        if not math.isclose(float(frequency), clock_frequency, rel_tol=1e-6, abs_tol=1e-6):
            raise ImplementationConstraintsError(
                "ppa.frequency_mhz must match the primary clock period_ns"
            )

    memory = document.get("memory")
    normalized_memory: dict[str, Any] | None = None
    if memory is not None:
        if not isinstance(memory, Mapping):
            raise ImplementationConstraintsError("implementation constraints memory must be an object")
        instances = memory.get("instances", [])
        if not isinstance(instances, list):
            raise ImplementationConstraintsError("implementation constraints memory.instances must be a list")
        if memory.get("policy") == "hard_macro_required" and not instances:
            raise ImplementationConstraintsError(
                "hard_macro_required memory policy needs at least one mapped instance"
            )
        required_views_raw = memory.get("required_views", [])
        if not isinstance(required_views_raw, list) or any(
            not isinstance(item, str) or not item.strip()
            for item in required_views_raw
        ):
            raise ImplementationConstraintsError(
                "implementation constraints memory.required_views must be a list of view names"
            )
        required_views = list(dict.fromkeys(
            str(item).strip() for item in required_views_raw
        ))
        if memory.get("policy") == "hard_macro_required":
            pnr_views = {"behavioral", "liberty", "lef", "gds"}
            missing_pnr_views = sorted(pnr_views - set(required_views))
            if missing_pnr_views:
                raise ImplementationConstraintsError(
                    "hard_macro_required memory baseline is missing required PnR views: "
                    + ", ".join(missing_pnr_views)
                )
        normalized_instances: list[dict[str, Any]] = []
        for index, instance in enumerate(instances):
            if not isinstance(instance, Mapping):
                raise ImplementationConstraintsError(f"memory instance {index} must be an object")
            macro = str(instance.get("macro", "")).strip()
            if memory.get("policy") == "hard_macro_required" and not macro:
                raise ImplementationConstraintsError(
                    f"memory instance {index} needs a macro under hard_macro_required policy"
                )
            if (
                macro and available_memory_macros is not None
                and macro not in available_memory_macros
            ):
                raise ImplementationConstraintsError(
                    f"implementation memory macro is unavailable: {macro}"
                )
            normalized_instance = dict(instance)
            if macro and available_memory_macro_views is not None:
                views = available_memory_macro_views.get(macro)
                if not views:
                    raise ImplementationConstraintsError(
                        f"implementation memory macro has no resolved views: {macro}"
                    )
                missing_views = sorted(set(required_views) - set(views))
                if missing_views:
                    raise ImplementationConstraintsError(
                        f"implementation memory macro {macro} is missing required views: "
                        + ", ".join(missing_views)
                    )
                normalized_instance["views"] = dict(views)
            normalized_instances.append(normalized_instance)
        normalized_memory = {
            **dict(memory),
            "required_views": required_views,
            "instances": normalized_instances,
        }
    if require_frozen:
        missing = missing_implementation_parameters(document)
        if missing:
            fields = [field for item in missing for field in item["fields"]]
            raise ImplementationConstraintsError("implementation constraints need parameters: " + ", ".join(fields))
    platform_lock = document.get("platform_lock")
    if (
        not isinstance(platform_lock, Mapping)
        and available_platform_details is not None
        and platform in available_platform_details
    ):
        platform_lock = dict(available_platform_details[platform])
    return {
        **dict(document),
        "schema_version": 1,
        "status": status,
        "spec_revision_id": spec_revision_id,
        "platform": platform,
        "corner": corner,
        "clocks": normalized_clocks,
        "io": dict(io),
        "power": dict(power),
        "decision_ids": normalized_decision_ids,
        **({"memory": normalized_memory} if normalized_memory is not None else {}),
        **({"platform_lock": platform_lock} if isinstance(platform_lock, Mapping) else {}),
    }


def render_sdc(
    document: Mapping[str, Any], *,
    authored_document: Mapping[str, Any] | None = None,
    authored_sdc: bytes | None = None,
) -> str:
    """Render the declared clock, IO, reset and electrical timing budgets."""
    if "sdc_sha256" in document or "sdc_sha256" in (authored_document or {}):
        if authored_document is None or authored_sdc is None:
            raise ImplementationConstraintsError("Author SDC and original constraints are required")
        if {**authored_document, "status": document["status"]} != document:
            raise ImplementationConstraintsError(
                "Edited implementation constraints require a regenerated, verified author SDC"
            )
        digest = str(authored_document.get("sdc_sha256", "")).removeprefix("sha256:")
        if hashlib.sha256(authored_sdc).hexdigest() != digest:
            raise ImplementationConstraintsError("Author SDC digest does not match the implementation constraints draft")
        return authored_sdc.decode("utf-8")
    lines = [
        "# Generated from frozen implementation.constraints.json",
        "# OpenSTA lacks Synopsys remove_from_collection; provide a list-compatible fallback.",
        "if {[llength [info commands remove_from_collection]] == 0} {",
        "  proc remove_from_collection {collection removed} {",
        "    set result {}",
        "    foreach object $collection {",
        "      if {[lsearch -exact $removed $object] < 0} { lappend result $object }",
        "    }",
        "    return $result",
        "  }",
        "}",
    ]
    for clock in document["clocks"]:
        waveform = clock["waveform_ns"]
        clocks = f"[get_clocks {{{clock['name']}}}]"
        ports = f"[get_ports {{{clock['port']}}}]"
        lines.append(
            f"create_clock -name {clock['name']} -period {clock['period_ns']:g} "
            f"-waveform {{{waveform[0]:g} {waveform[1]:g}}} {ports}"
        )
        if any(key in clock for key in ("setup_uncertainty_ns", "hold_uncertainty_ns")):
            for kind in ("setup", "hold"):
                value = clock.get(f"{kind}_uncertainty_ns", clock.get("uncertainty_ns", 0))
                lines.append(f"set_clock_uncertainty -{kind} {_sdc_number(value)} {clocks}")
        elif float(clock.get("uncertainty_ns", 0.0)):
            lines.append(f"set_clock_uncertainty {_sdc_number(clock['uncertainty_ns'])} {clocks}")
        for kind, value in clock.get("source_latency_ns", {}).items():
            if kind not in {"early", "late"}:
                raise ImplementationConstraintsError("source_latency_ns needs early/late values")
            lines.append(f"set_clock_latency -source -{kind} {_sdc_number(value)} {clocks}")
        for kind, value in clock.get("input_transition_ns", {}).items():
            if kind not in {"rise_min", "rise_max", "fall_min", "fall_max"}:
                raise ImplementationConstraintsError("input_transition_ns needs rise/fall min/max values")
            flags = " ".join(f"-{part}" for part in kind.split("_"))
            lines.append(f"set_input_transition {flags} {_sdc_number(value)} {ports}")
    io = document.get("io", {})
    reference = io.get("reference_clock", document["clocks"][0]["name"])
    if reference not in {clock["name"] for clock in document["clocks"]}:
        raise ImplementationConstraintsError("io.reference_clock must name a declared clock")
    clocks = f"[get_clocks {{{reference}}}]"
    reset_ports = {str(item) for item in io.get("reset_ports", [])}
    reset = io.get("reset", {})
    if isinstance(reset, Mapping) and reset.get("port"):
        reset_ports.add(str(reset["port"]))
    clock_ports = {str(item["port"]) for item in document["clocks"]}
    excluded = " ".join(sorted(clock_ports | reset_ports))
    inputs = f"[remove_from_collection [all_inputs] [get_ports {{{excluded}}}]]"
    for direction, ports in (("input", inputs), ("output", "[all_outputs]")):
        maximum = io.get(f"{direction}_delay_ns")
        minimum = io.get(f"{direction}_delay_min_ns")
        if maximum is not None:
            flag = "-max " if minimum is not None else ""
            lines.append(f"set_{direction}_delay {flag}{_sdc_number(maximum)} -clock {clocks} {ports}")
        if minimum is not None:
            lines.append(f"set_{direction}_delay -min {_sdc_number(minimum)} -clock {clocks} {ports}")
    for model, ports in ((io, inputs), (reset, f"[get_ports {{{reset.get('port', '')}}}]")):
        for kind, value in model.get("transition_ns", model.get("input_transition_ns", {})).items():
            if kind not in {"rise_min", "rise_max", "fall_min", "fall_max"}:
                raise ImplementationConstraintsError("input transition needs rise/fall min/max values")
            flags = " ".join(f"-{part}" for part in kind.split("_"))
            lines.append(f"set_input_transition {flags} {_sdc_number(value)} {ports}")
    if reset.get("port") and reset.get("synchronous") is True:
        for kind in ("min", "max"):
            value = reset.get(f"input_delay_{kind}_ns")
            if value is not None:
                lines.append(f"set_input_delay -{kind} {_sdc_number(value)} -clock {clocks} [get_ports {{{reset['port']}}}]")
    if io.get("output_load_pf") is not None:
        lines.append("# Load is declared in pF, independently of the selected Liberty units.")
        lines.append(f"set_load [expr {{{_sdc_number(io['output_load_pf'])} * 1e-12 / [sta::unit_scale capacitance]}}] [all_outputs]")
    return "\n".join(lines) + "\n"


def _sdc_number(value: Any) -> str:
    if type(value) not in {int, float} or not math.isfinite(float(value)) or value < 0:
        raise ImplementationConstraintsError("SDC timing/electrical values must be finite non-negative numbers")
    return f"{value:g}"
