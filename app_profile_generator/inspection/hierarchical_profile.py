from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List


GROUP_CONTROL_TYPES = {"Group", "Pane", "Window", "Tab", "TabItem"}
SKIP_CONTROL_TYPES = {"TitleBar", "MenuBar", "MenuItem"}
GENERIC_AUTOMATION_NAMES = {
    "q_label",
    "q_push_button",
    "q_line_edit",
    "q_combo_box",
    "q_check_box",
    "q_list_widget",
    "q_text_edit",
    "button",
    "edit",
    "text",
}
STATE_WORDS = {"gray", "green", "blue", "red", "ready", "running", "stopped"}


def _slug(value: str, fallback: str) -> str:
    text = value.strip()
    if not text:
        return fallback

    if not text.isupper():
        text = re.sub(r"(?<!^)(?=[A-Z])", "_", text)
    text = re.sub(r"[^0-9A-Za-z_]+", "_", text).strip("_").lower()
    text = re.sub(r"_+", "_", text)
    return text or fallback


def _automation_segments(automation_id: str) -> list[str]:
    return [segment for segment in automation_id.split(".") if segment]


def _automation_leaf(control: Dict[str, Any]) -> str:
    segments = _automation_segments(control.get("automation_id", "") or "")
    if not segments:
        return ""
    return _slug(segments[-1], "")


def _visible_name(control: Dict[str, Any]) -> str:
    return control.get("name", "") or ""


def _target_from_visible_name(name: str, fallback: str) -> str:
    slug = _slug(name, fallback)
    if len(slug) > 64:
        return fallback
    parts = [part for part in slug.split("_") if part not in STATE_WORDS]
    return "_".join(parts) or slug or fallback


def _is_generic_automation_leaf(control: Dict[str, Any]) -> bool:
    leaf = _automation_leaf(control)
    class_name = _slug(control.get("class_name", "") or "", "")
    return not leaf or leaf in GENERIC_AUTOMATION_NAMES or leaf == class_name


def _suggest_group_name(control: Dict[str, Any]) -> str:
    automation_id = control.get("automation_id", "") or ""
    name = control.get("name", "") or ""
    index = control.get("index", "unknown")
    if name:
        return _slug(name, f"group_{index}")
    leaf = _automation_leaf({"automation_id": automation_id})
    if leaf:
        return leaf
    return f"group_{index}"


def _suggest_control_name(control: Dict[str, Any]) -> str:
    name = control.get("name", "") or ""
    index = control.get("index", "unknown")
    fallback = f"control_{index}"

    if name:
        return _target_from_visible_name(name, fallback)
    return fallback


def _is_group(control: Dict[str, Any]) -> bool:
    control_type = control.get("control_type", "")
    class_name = control.get("class_name", "")
    automation_id = control.get("automation_id", "") or ""
    automation_leaf = _automation_leaf(control)
    if class_name.endswith("GroupBox"):
        return True
    if automation_leaf == "central_widget":
        return True
    if control_type in {"Window", "Tab", "TabItem"}:
        return True
    if control_type in {"Group", "Pane"}:
        return bool(_visible_name(control))
    return automation_id.split(".")[-1].endswith("_group") if automation_id else False


def _is_profile_control(control: Dict[str, Any]) -> bool:
    if "error" in control:
        return False
    if control.get("control_type") in SKIP_CONTROL_TYPES:
        return False
    rect = control.get("rectangle", {}) or {}
    return int(rect.get("width", 0)) > 0 and int(rect.get("height", 0)) > 0


def _region(control: Dict[str, Any]) -> Dict[str, int]:
    rect = control.get("rectangle", {}) or {}
    return {
        "x": int(rect.get("x", 0)),
        "y": int(rect.get("y", 0)),
        "width": int(rect.get("width", 0)),
        "height": int(rect.get("height", 0)),
    }


def _control_record(
    control: Dict[str, Any],
    group_name: str,
    target_name: str,
) -> Dict[str, Any]:
    record = {
        "name": control.get("name", ""),
        "label_no": control.get("index"),
        "region": _region(control),
        "scenario_ref": {
            "group": group_name,
            "target": target_name,
        },
    }
    children = control.get("children")
    if children:
        record["children"] = children
    return record


def _group_record(control: Dict[str, Any], group_path: str) -> Dict[str, Any]:
    return {
        "name": _visible_name(control) or group_path,
        "label_no": control.get("index"),
        "region": _region(control),
        "scenario_ref": {
            "group": _visible_name(control) or group_path,
            "target": None,
        },
        "controls": {},
        "child_groups": {},
    }


def _area(control: Dict[str, Any]) -> int:
    region = _region(control)
    return region["width"] * region["height"]


def _center(control: Dict[str, Any]) -> tuple[float, float]:
    region = _region(control)
    return (
        region["x"] + (region["width"] / 2),
        region["y"] + (region["height"] / 2),
    )


def _contains_point(container: Dict[str, Any], point: tuple[float, float]) -> bool:
    region = _region(container)
    x, y = point
    return (
        region["x"] <= x <= region["x"] + region["width"]
        and region["y"] <= y <= region["y"] + region["height"]
    )


def _smallest_containing_group(
    control: Dict[str, Any],
    groups: list[tuple[str, Dict[str, Any]]],
    parent_must_be_larger: bool = False,
) -> str:
    point = _center(control)
    control_index = control.get("index")
    control_area = _area(control)
    candidates = [
        (group_path, group_control)
        for group_path, group_control in groups
        if group_control.get("index") != control_index
        and _contains_point(group_control, point)
        and (not parent_must_be_larger or _area(group_control) > control_area)
    ]
    if not candidates:
        return "ungrouped"
    return min(candidates, key=lambda item: _area(item[1]))[0]


def _unique_key(base_key: str, used_keys: set[str]) -> str:
    if base_key not in used_keys:
        used_keys.add(base_key)
        return base_key

    counter = 2
    while f"{base_key}_{counter}" in used_keys:
        counter += 1
    key = f"{base_key}_{counter}"
    used_keys.add(key)
    return key


def build_hierarchical_profile(
    app_info: Dict[str, Any],
    controls: List[Dict[str, Any]],
    screen_key: str = "main_window",
    discovered_by: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    discovered_by = discovered_by or {
        "type": "initial_launch",
        "trigger_target": None,
        "parent_screen": None,
    }
    profile: Dict[str, Any] = {
        "profile_version": 1,
        "naming_policy": {
            "mode": "manual_review",
            "description": (
                "Generator groups controls by rectangle containment and suggests scenario targets from visible names. "
                "A human should review names before scenario authoring."
            ),
        },
        "screens": {
            screen_key: {
                "title": app_info.get("window_title", ""),
                "discovered_by": discovered_by,
                "window_rect": app_info.get("window_rect", {}),
                "grouping_strategy": "center_point_containment_with_smallest_parent_group",
                "groups": {
                    "ungrouped": {
                        "name": "ungrouped",
                        "label_no": None,
                        "region": None,
                        "scenario_ref": {
                            "group": "ungrouped",
                            "target": None,
                        },
                        "controls": {},
                        "child_groups": {},
                    }
                },
            }
        },
    }

    screen = profile["screens"][screen_key]
    groups = screen["groups"]
    group_nodes: Dict[str, Dict[str, Any]] = {}
    group_controls: list[tuple[str, Dict[str, Any]]] = []
    parent_group_by_group: Dict[str, str] = {}
    used_group_keys: set[str] = {"ungrouped"}

    for control in controls:
        if not _is_profile_control(control) or not _is_group(control):
            continue
        group_key = _unique_key(_suggest_group_name(control), used_group_keys)
        group_path = group_key
        group_nodes[group_key] = _group_record(control, group_path)
        group_controls.append((group_path, control))

    for group_path, group_control in group_controls:
        parent_group = _smallest_containing_group(
            group_control,
            group_controls,
            parent_must_be_larger=True,
        )
        parent_group_by_group[group_path] = parent_group

    for group_path, parent_path in parent_group_by_group.items():
        group = group_nodes[group_path]
        if parent_path == "ungrouped":
            groups[group_path] = group
            continue
        parent = group_nodes.get(parent_path)
        if parent is not None:
            parent["child_groups"][group_path] = group

    used_control_keys_by_group: Dict[str, set[str]] = defaultdict(set)
    for control in controls:
        if not _is_profile_control(control) or _is_group(control):
            continue

        group_path = _smallest_containing_group(control, group_controls)
        group = group_nodes.get(group_path, groups["ungrouped"])
        suggested_name = _suggest_control_name(control)
        control_key = _unique_key(suggested_name, used_control_keys_by_group[group_path])
        record = _control_record(
            control=control,
            group_name=group.get("name", group_path),
            target_name=control_key,
        )

        group["controls"][control_key] = record

    return profile


def build_controls_dump_for_review(
    controls: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    group_controls: list[tuple[str, Dict[str, Any]]] = []
    used_group_keys: set[str] = {"ungrouped"}
    group_name_by_path = {"ungrouped": "ungrouped"}

    for control in controls:
        if not _is_profile_control(control) or not _is_group(control):
            continue
        group_key = _unique_key(_suggest_group_name(control), used_group_keys)
        group_controls.append((group_key, control))
        group_name_by_path[group_key] = _visible_name(control) or group_key

    review_controls = []
    for control in controls:
        if not _is_profile_control(control):
            continue

        if _is_group(control):
            group_path = _smallest_containing_group(
                control,
                group_controls,
                parent_must_be_larger=True,
            )
        else:
            group_path = _smallest_containing_group(control, group_controls)

        review_controls.append(
            {
                "index": control.get("index"),
                "name": control.get("name", ""),
                "group": group_name_by_path.get(group_path, group_path),
                "rectangle": _region(control),
            }
        )
        if is_yolo_scan_candidate(control):
            review_controls[-1]["scan_children"] = True

    return review_controls


def apply_review_names(
    raw_controls: List[Dict[str, Any]],
    review_controls: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    review_by_index = {
        control.get("index"): control
        for control in review_controls
        if isinstance(control, dict) and control.get("index") is not None
    }
    updated_controls = []
    for control in raw_controls:
        updated = dict(control)
        review = review_by_index.get(control.get("index"))
        if review is not None and "name" in review:
            updated["name"] = review.get("name", "")
        if review is not None and "scan_children" in review:
            updated["scan_children"] = bool(review.get("scan_children"))
        updated_controls.append(updated)
    return updated_controls


def is_yolo_scan_candidate(control: Dict[str, Any]) -> bool:
    if control.get("scan_children"):
        return True

    control_type = control.get("control_type", "") or ""
    class_name = control.get("class_name", "") or ""
    name = control.get("name", "") or ""
    automation_id = control.get("automation_id", "") or ""
    structural_text = f"{class_name} {automation_id}".lower()
    container_text = f"{class_name} {automation_id} {name}".lower()

    if class_name.endswith("Lamp"):
        return False
    if control_type in {"DataGrid", "Table", "List"}:
        return True
    if control_type == "Custom":
        return any(token in structural_text for token in ("grid", "table", "canvas", "paint"))
    if control_type in {"Group", "Pane"}:
        return any(token in container_text for token in ("grid", "table", "canvas"))
    return False
