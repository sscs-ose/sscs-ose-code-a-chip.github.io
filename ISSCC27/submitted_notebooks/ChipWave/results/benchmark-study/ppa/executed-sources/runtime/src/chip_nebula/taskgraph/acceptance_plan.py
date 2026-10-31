"""验收计划（spec/acceptance.plan.yaml）格式校验与规整。

格式定义见 docs/design/specir-acceptance-plan.md。三层结构：
categories（功能/性能验收等分组）→ cards（可折叠验收大类，如"复位/上下电"）
→ items（一行一条的验收子项）。非法结构直接拒绝，缺 id 自动分配。
"""

from __future__ import annotations

from typing import Any, Mapping


def _require_mapping(value: Any, owner: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{owner} 必须是映射")
    return value


def provenance_design_groups(document: Mapping[str, Any]) -> set[str]:
    nodes = document.get("nodes")
    if not isinstance(nodes, list) or not nodes or any(not isinstance(node, dict) for node in nodes):
        raise ValueError("provenance needs a nonempty nodes list")
    node_ids = {str(node.get("id", "")) for node in nodes}
    groups: set[str] = set()
    for node in nodes:
        group = node.get("design_group")
        if not isinstance(group, str) or not group.strip() or group.strip() in node_ids:
            raise ValueError(f"provenance node {node.get('id', '')} needs a stable semantic design_group")
        groups.add(group.strip())
    return groups


def _validate_items(
    items: Any, card_title: str, prefix: str, *,
    known_requirement_ids: set[str] | None = None,
    known_design_groups: set[str] | None = None,
    require_complete: bool = False,
    reference_errors: list[str] | None = None,
    covered_requirement_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        raise ValueError(f"{card_title} 的 items 必须是列表")
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        item = _require_mapping(item, f"{card_title}.items[{index}]")
        title = str(item.get("title") or "").strip()
        if not title:
            raise ValueError(f"{card_title}.items[{index}] 缺少 title")
        item_id = str(item.get("id") or "").strip()
        if not item_id:
            candidate = f"{prefix}{index + 1}"
            suffix = 1
            while candidate in seen:
                suffix += 1
                candidate = f"{prefix}{index + 1}_{suffix}"
            item_id = candidate
        if item_id in seen:
            raise ValueError(f"{card_title} 内重复的子项 id: {item_id}")
        seen.add(item_id)
        detail = str(item.get("detail") or "").strip()
        requirement_ids = [
            str(value).strip() for value in item.get("requirement_ids", [])
            if str(value).strip()
        ] if isinstance(item.get("requirement_ids"), (list, tuple)) else []
        design_groups = [
            str(value).strip() for value in item.get("design_groups", [])
            if str(value).strip()
        ] if isinstance(item.get("design_groups"), (list, tuple)) else []
        if require_complete and not detail:
            raise ValueError(f"{card_title}.{item_id} 缺少可判定的 detail")
        item_errors: list[str] = []
        if "spec_nodes" in item:
            item_errors.append(
                f"{card_title}.{item_id} 使用了已废止的 spec_nodes；"
                "改用 requirement_ids / design_groups"
            )
        if require_complete and known_design_groups is not None and not design_groups:
            item_errors.append(f"{card_title}.{item_id} 缺少稳定 design_groups")
        if require_complete and not requirement_ids and not design_groups:
            item_errors.append(
                f"{card_title}.{item_id} 缺少 requirement_ids / design_groups"
            )
        invalid_requirement_ids = sorted({
            value for value in requirement_ids if not value.startswith("REQ-")
        })
        if invalid_requirement_ids:
            item_errors.append(
                f"{card_title}.{item_id} 的 requirement_ids 格式无效: "
                + ", ".join(invalid_requirement_ids)
            )
        unknown_requirement_ids = (
            sorted(set(requirement_ids) - known_requirement_ids)
            if known_requirement_ids is not None else []
        )
        if unknown_requirement_ids:
            item_errors.append(
                f"{card_title}.{item_id} 引用了不存在的 requirement: "
                + ", ".join(unknown_requirement_ids)
            )
        unknown_design_groups = (
            sorted(set(design_groups) - known_design_groups)
            if known_design_groups is not None else []
        )
        if unknown_design_groups:
            item_errors.append(
                f"{card_title}.{item_id} 引用了不存在的 design_group: "
                + ", ".join(unknown_design_groups)
            )
        if item_errors:
            if reference_errors is None:
                raise ValueError(item_errors[0])
            reference_errors.extend(item_errors)
        if covered_requirement_ids is not None:
            covered_requirement_ids.update(requirement_ids)
        normalized.append({
            **dict(item),
            "id": item_id,
            "title": title,
            **({"detail": detail} if detail else {}),
            **({"requirement_ids": requirement_ids} if requirement_ids else {}),
            **({"design_groups": design_groups} if design_groups else {}),
        })
    return normalized


def validate_acceptance_plan(
    document: Mapping[str, Any], *,
    known_requirement_ids: set[str] | None = None,
    known_design_groups: set[str] | None = None,
    required_requirement_ids: set[str] | None = None,
    require_complete: bool = False,
) -> dict[str, Any]:
    if not isinstance(document, Mapping):
        raise ValueError("验收计划必须是映射结构")
    version = document.get("version", 1)
    if version != 1:
        raise ValueError(f"unsupported acceptance plan version: {version}")

    reference_errors: list[str] = []
    covered_requirement_ids: set[str] = set()

    metrics = document.get("metrics", [])
    if not isinstance(metrics, list):
        raise ValueError("metrics 必须是列表")
    norm_metrics: list[dict[str, Any]] = []
    seen_metric_keys: set[str] = set()
    for index, item in enumerate(metrics):
        item = _require_mapping(item, f"metrics[{index}]")
        key = str(item.get("key") or "").strip()
        label = str(item.get("label") or "").strip()
        if not key or not label:
            raise ValueError(f"metrics[{index}] 缺少 key/label")
        if key in seen_metric_keys:
            raise ValueError(f"重复的指标 key: {key}")
        seen_metric_keys.add(key)
        if "target" not in item:
            raise ValueError(f"指标 {key} 缺少 target")
        basis = str(item.get("basis") or "").strip()
        if basis and basis not in {"requirement", "proposal"}:
            raise ValueError(f"指标 {key} 的 basis 必须是 requirement 或 proposal")
        if require_complete and not basis:
            raise ValueError(f"指标 {key} 缺少 basis")
        if "operator" in item and item["operator"] not in ("==", "!=", ">", ">=", "<", "<="):
            raise ValueError(f"指标 {key} 的 operator 必须是有效比较符")
        norm_metrics.append({
            **dict(item),
            "key": key,
            "label": label,
            "unit": str(item.get("unit") or ""),
            "target": item["target"],
            **({"basis": basis} if basis else {}),
            # section 用于 UI 分组（如 coverage 与资源指标之间画分隔线）
            **({"section": str(item["section"])} if item.get("section") else {}),
            **({"note": str(item["note"])} if item.get("note") else {}),
        })
    if require_complete and not norm_metrics:
        raise ValueError("项目验收计划至少需要一项量化指标")

    categories = document.get("categories", [])
    if not isinstance(categories, list):
        raise ValueError("categories 必须是列表")
    norm_categories: list[dict[str, Any]] = []
    seen_category_keys: set[str] = set()
    for index, category in enumerate(categories):
        category = _require_mapping(category, f"categories[{index}]")
        key = str(category.get("key") or f"cat{index + 1}").strip()
        name = str(category.get("name") or "").strip()
        if not name:
            raise ValueError(f"categories[{index}] 缺少 name")
        if key in seen_category_keys:
            raise ValueError(f"重复的验收分组 key: {key}")
        seen_category_keys.add(key)
        cards = category.get("cards", [])
        if not isinstance(cards, list):
            raise ValueError(f"{name} 的 cards 必须是列表")
        norm_cards: list[dict[str, Any]] = []
        seen_card_keys: set[str] = set()
        for card_index, card in enumerate(cards):
            card = _require_mapping(card, f"{name}.cards[{card_index}]")
            card_key = str(card.get("key") or f"{key}-{card_index + 1}").strip()
            card_title = str(card.get("title") or "").strip()
            if not card_title:
                raise ValueError(f"{name}.cards[{card_index}] 缺少 title")
            if card_key in seen_card_keys:
                raise ValueError(f"{name} 内重复的卡片 key: {card_key}")
            seen_card_keys.add(card_key)
            prefix = "".join(ch for ch in card_title if ch.isalnum())[:2].upper() or "A"
            if require_complete and not card.get("items"):
                raise ValueError(f"{card_title} 不能是空验收卡片")
            norm_cards.append({
                **dict(card),
                "key": card_key,
                "title": card_title,
                "items": _validate_items(
                    card.get("items", []), card_title, prefix,
                    known_requirement_ids=known_requirement_ids,
                    known_design_groups=known_design_groups,
                    require_complete=require_complete,
                    reference_errors=reference_errors,
                    covered_requirement_ids=covered_requirement_ids,
                ),
            })
        if require_complete and not norm_cards:
            raise ValueError(f"{name} 不能是空验收分组")
        norm_categories.append({**dict(category), "key": key, "name": name, "cards": norm_cards})
    if require_complete and not norm_categories:
        raise ValueError("项目验收计划至少需要一个验收分组")

    scope = str(document.get("scope") or "project")
    if require_complete and scope != "project":
        raise ValueError("完整验收计划的 scope 必须是 project")
    uncovered = sorted((required_requirement_ids or set()) - covered_requirement_ids)
    if uncovered:
        reference_errors.append(
            "当前规范性需求没有验收项覆盖: " + ", ".join(uncovered)
        )
    if reference_errors:
        raise ValueError(
            f"验收计划追踪门禁失败（共 {len(reference_errors)} 项）：\n- "
            + "\n- ".join(reference_errors)
        )

    return {
        **dict(document),
        "version": 1,
        "scope": scope,
        "metrics": norm_metrics,
        "categories": norm_categories,
        "confirmed": bool(document.get("confirmed")),
    }
