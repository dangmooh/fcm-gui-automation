from __future__ import annotations

import time
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List

import yaml
from pywinauto import Desktop

from app_profile_generator.inspection.control_dumper import dump_controls, dump_window_info
from app_profile_generator.inspection.hierarchical_profile import build_hierarchical_profile


DISCOVERY_ACTIONS = {"click", "set_text"}
READ_ONLY_ACTIONS = {"launch_or_connect", "verify_text", "verify_color", "screenshot"}
STOP_ACTIONS = {"safe_close"}


def load_discovery_scenario(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Scenario root must be a mapping: {path}")
    return data


def load_discovery_scenarios_from_dir(path: Path) -> List[tuple[Path, Dict[str, Any]]]:
    if not path.is_dir():
        raise NotADirectoryError(f"Scenario directory not found: {path}")

    scenarios: List[tuple[Path, Dict[str, Any]]] = []
    for scenario_path in sorted(path.glob("*.yaml")):
        scenarios.append((scenario_path, load_discovery_scenario(scenario_path)))
    return scenarios


def discover_profile_from_scenario(
    profile: Dict[str, Any],
    initial_window,
    scenario: Dict[str, Any],
    delay: float = 0.5,
    scenario_path: Path | None = None,
    continue_on_step_error: bool = False,
    capture_existing_windows: bool = True,
    step_errors: List[Dict[str, Any]] | None = None,
    discovered_controls: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    pid = initial_window.process_id()
    initial_window_identity = _window_identity(initial_window)
    seen_signatures = _profile_signatures(profile)
    seen_signatures.add(_controls_signature(dump_controls(initial_window)))
    steps = scenario.get("steps", [])
    if not isinstance(steps, list):
        raise ValueError("Scenario steps must be a list.")

    scenario_name = str(scenario.get("name") or (scenario_path.stem if scenario_path else "unnamed_scenario"))
    for step_index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            continue

        action = step.get("action")
        if action in STOP_ACTIONS:
            break
        if action in READ_ONLY_ACTIONS:
            continue
        if action not in DISCOVERY_ACTIONS:
            continue

        trigger_target = step.get("target")
        try:
            _execute_step_for_discovery(pid, step)
        except Exception as exc:
            if step_errors is not None:
                step_errors.append(
                    {
                        "step_index": step_index,
                        "action": action,
                        "target": trigger_target,
                        "group": step.get("group"),
                        "error": str(exc),
                    }
                )
            if continue_on_step_error:
                continue
            raise
        time.sleep(delay)

        for window_index, window in enumerate(_visible_windows_for_pid(pid)):
            is_initial_window = _window_identity(window) == initial_window_identity
            if not capture_existing_windows and is_initial_window:
                controls = dump_controls(window)
                for embedded_index, embedded in enumerate(_embedded_window_control_groups(window, controls)):
                    signature = _controls_signature(embedded["controls"])
                    if signature in seen_signatures:
                        continue

                    screen_key = _unique_screen_key(
                        profile,
                        _screen_key(
                            scenario_name,
                            step_index,
                            action,
                            trigger_target,
                            embedded_index,
                            source="embedded",
                        ),
                    )
                    discovered_by = {
                        "type": "scenario_step",
                        "window_source": "embedded_window_control",
                        "scenario_name": scenario_name,
                        "scenario_path": str(scenario_path) if scenario_path else None,
                        "step_index": step_index,
                        "action": action,
                        "trigger_target": trigger_target,
                        "parent_screen": "main_window",
                    }
                    discovered_profile = build_hierarchical_profile(
                        app_info={
                            "window_title": embedded["title"],
                            "window_rect": embedded["window_rect"],
                        },
                        controls=embedded["controls"],
                        screen_key=screen_key,
                        discovered_by=discovered_by,
                    )
                    _merge_profile_screen(profile, discovered_profile, screen_key)
                    if discovered_controls is not None:
                        discovered_controls.extend(
                            _controls_for_output(
                                controls=embedded["controls"],
                                screen_key=screen_key,
                                screen_title=embedded["title"],
                                window_rect=embedded["window_rect"],
                                discovered_by=discovered_by,
                            )
                        )
                    seen_signatures.add(signature)
                continue

            controls = dump_controls(window)
            signature = _controls_signature(controls)
            if signature in seen_signatures:
                continue

            window_info = dump_window_info(window)
            screen_key = _unique_screen_key(
                profile,
                _screen_key(scenario_name, step_index, action, trigger_target, window_index),
            )
            discovered_by = {
                "type": "scenario_step",
                "window_source": "top_level_window",
                "scenario_name": scenario_name,
                "scenario_path": str(scenario_path) if scenario_path else None,
                "step_index": step_index,
                "action": action,
                "trigger_target": trigger_target,
                "parent_screen": "main_window",
            }
            discovered_profile = build_hierarchical_profile(
                app_info={
                    "window_title": window_info["window_title"],
                    "window_rect": window_info["window_rect"],
                },
                controls=controls,
                screen_key=screen_key,
                discovered_by=discovered_by,
            )
            _merge_profile_screen(profile, discovered_profile, screen_key)
            if discovered_controls is not None:
                discovered_controls.extend(
                    _controls_for_output(
                        controls=controls,
                        screen_key=screen_key,
                        screen_title=window_info["window_title"],
                        window_rect=window_info["window_rect"],
                        discovered_by=discovered_by,
                    )
                )
            seen_signatures.add(signature)

    return profile


def discover_profile_from_scenarios(
    profile: Dict[str, Any],
    initial_window,
    scenarios: List[tuple[Path, Dict[str, Any]]],
    delay: float = 0.5,
    discovered_controls: List[Dict[str, Any]] | None = None,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    summary: Dict[str, Any] = {
        "scenario_count": len(scenarios),
        "completed": [],
        "failed": [],
        "screens_before": len(profile.get("screens", {})),
        "screens_after": None,
        "discovered_screen_count": 0,
    }

    for scenario_path, scenario in scenarios:
        before = len(profile.get("screens", {}))
        step_errors: List[Dict[str, Any]] = []
        try:
            profile = discover_profile_from_scenario(
                profile=profile,
                initial_window=initial_window,
                scenario=scenario,
                delay=delay,
                scenario_path=scenario_path,
                continue_on_step_error=True,
                capture_existing_windows=False,
                step_errors=step_errors,
                discovered_controls=discovered_controls,
            )
            after = len(profile.get("screens", {}))
            summary["completed"].append(
                {
                    "path": str(scenario_path),
                    "name": scenario.get("name") or scenario_path.stem,
                    "new_screens": after - before,
                    "step_errors": step_errors,
                }
            )
        except Exception as exc:
            summary["failed"].append(
                {
                    "path": str(scenario_path),
                    "name": scenario.get("name") or scenario_path.stem,
                    "error": str(exc),
                }
            )

    summary["screens_after"] = len(profile.get("screens", {}))
    summary["discovered_screen_count"] = summary["screens_after"] - summary["screens_before"]
    return profile, summary


def _execute_step_for_discovery(pid: int, step: Dict[str, Any]) -> None:
    target = step.get("target")
    if not target:
        raise ValueError(f"Discovery action requires target: {step}")
    control = _find_control(pid, target, group=step.get("group"))

    if step["action"] == "click":
        _click(control)
        return

    if step["action"] == "set_text":
        value = str(step.get("value", ""))
        control.set_focus()
        try:
            control.set_edit_text(value)
        except Exception:
            control.type_keys("^a{BACKSPACE}", set_foreground=True)
            control.type_keys(value, with_spaces=True, set_foreground=True)
        return

    raise ValueError(f"Unsupported discovery action: {step['action']}")


def _click(control) -> None:
    for method_name in ("click", "click_input", "invoke"):
        try:
            control.set_focus()
            getattr(control, method_name)()
            return
        except Exception:
            pass
    control.set_focus()
    control.type_keys("{SPACE}", set_foreground=True)


def _slug(value: str) -> str:
    text = value.strip()
    text = re.sub(r"(?<!^)(?=[A-Z])", "_", text)
    text = re.sub(r"[^0-9A-Za-z_]+", "_", text).strip("_").lower()
    return re.sub(r"_+", "_", text)


def _rect_contains_center(container, control) -> bool:
    container_rect = container.rectangle()
    control_rect = control.rectangle()
    center_x = control_rect.left + (control_rect.width() / 2)
    center_y = control_rect.top + (control_rect.height() / 2)
    return (
        container_rect.left <= center_x <= container_rect.right
        and container_rect.top <= center_y <= container_rect.bottom
    )


def _is_group_match(control, group: str) -> bool:
    info = control.element_info
    group_slug = _slug(group)
    candidates = _control_match_candidates(control)
    return group_slug in candidates


def _is_target_match(control, target: str) -> bool:
    target_slug = _slug(target)
    candidates = _control_match_candidates(control)
    return target_slug in candidates


def _control_match_candidates(control) -> set[str]:
    info = control.element_info
    raw_values = [
        getattr(info, "name", "") or "",
        getattr(info, "automation_id", "") or "",
        getattr(info, "class_name", "") or "",
    ]
    try:
        raw_values.append(control.automation_id() or "")
    except Exception:
        pass

    expanded_values = []
    for value in raw_values:
        if not value:
            continue
        expanded_values.append(value)
        expanded_values.extend(segment for segment in value.split(".") if segment)
        if "." in value:
            expanded_values.append(value.rsplit(".", 1)[-1])

    candidates = {_slug(value) for value in expanded_values if value}
    for value in list(candidates):
        if "_" in value:
            candidates.add(value.rsplit("_", 1)[0])
    return {candidate for candidate in candidates if candidate}


def _find_control(pid: int, target: str, group: str | None = None):
    for window in _visible_windows_for_pid(pid):
        descendants = window.descendants()
        if group:
            group_controls = [control for control in descendants if _is_group_match(control, group)]
            for group_control in group_controls:
                for control in descendants:
                    if control == group_control:
                        continue
                    try:
                        if _rect_contains_center(group_control, control) and _is_target_match(
                            control,
                            target,
                        ):
                            return control
                    except Exception:
                        continue
        else:
            for control in descendants:
                if _is_target_match(control, target):
                    return control
    raise ValueError(f"Discovery target not found: {target}")


def _visible_windows_for_pid(pid: int) -> Iterable[Any]:
    desktop = Desktop(backend="uia")
    windows = []
    for window in desktop.windows():
        try:
            if window.process_id() == pid and window.is_visible():
                windows.append(window)
        except Exception:
            continue
    return windows


def _window_identity(window) -> int | str:
    try:
        return int(window.handle)
    except Exception:
        pass
    try:
        rect = window.rectangle()
        return f"{window.window_text()}:{rect.left}:{rect.top}:{rect.right}:{rect.bottom}"
    except Exception:
        return repr(window)


def _controls_signature(controls: List[Dict[str, Any]]) -> tuple:
    values = []
    for control in controls:
        if "error" in control:
            continue
        rect = control.get("rectangle", {}) or {}
        values.append(
            (
                control.get("automation_id", ""),
                control.get("name", ""),
                control.get("control_type", ""),
                rect.get("x"),
                rect.get("y"),
                rect.get("width"),
                rect.get("height"),
            )
        )
    return tuple(sorted(values))


def _profile_signatures(profile: Dict[str, Any]) -> set[tuple]:
    signatures = set()
    for screen in profile.get("screens", {}).values():
        values = []
        window_rect = screen.get("window_rect") or {}
        for group in screen.get("groups", {}).values():
            for control in group.get("controls", {}).values():
                rect = control.get("region", {}) or {}
                if control.get("region_units") == "window_ratio":
                    rect = _absolute_from_ratio(rect, window_rect)
                values.append(
                    (
                        control.get("automation_id", ""),
                        control.get("name", ""),
                        control.get("control_type", ""),
                        rect.get("x"),
                        rect.get("y"),
                        rect.get("width"),
                        rect.get("height"),
                    )
                )
        if values:
            signatures.add(tuple(sorted(values)))
    return signatures


def _absolute_from_ratio(region: Dict[str, Any], window_rect: Dict[str, Any]) -> Dict[str, int]:
    window_x = float(window_rect.get("x", 0))
    window_y = float(window_rect.get("y", 0))
    window_width = float(window_rect.get("width", 1))
    window_height = float(window_rect.get("height", 1))
    return {
        "x": int(round(window_x + float(region.get("x", 0)) * window_width)),
        "y": int(round(window_y + float(region.get("y", 0)) * window_height)),
        "width": int(round(float(region.get("width", 0)) * window_width)),
        "height": int(round(float(region.get("height", 0)) * window_height)),
    }


def _ratio_from_rect(rect: Dict[str, Any], window_rect: Dict[str, Any]) -> Dict[str, float]:
    window_width = max(1.0, float(window_rect.get("width", 0)))
    window_height = max(1.0, float(window_rect.get("height", 0)))
    window_x = float(window_rect.get("x", 0))
    window_y = float(window_rect.get("y", 0))
    return {
        "x": round((float(rect.get("x", 0)) - window_x) / window_width, 6),
        "y": round((float(rect.get("y", 0)) - window_y) / window_height, 6),
        "width": round(float(rect.get("width", 0)) / window_width, 6),
        "height": round(float(rect.get("height", 0)) / window_height, 6),
    }


def _controls_for_output(
    controls: List[Dict[str, Any]],
    screen_key: str,
    screen_title: str,
    window_rect: Dict[str, Any],
    discovered_by: Dict[str, Any],
) -> List[Dict[str, Any]]:
    tagged_controls = []
    for control in controls:
        tagged = dict(control)
        tagged["screen_key"] = screen_key
        tagged["screen_title"] = screen_title
        tagged["screen_window_rect"] = window_rect
        tagged["discovered_by"] = discovered_by
        tagged["rectangle_ratio"] = _ratio_from_rect(tagged.get("rectangle", {}) or {}, window_rect)
        tagged["rectangle_ratio_units"] = "window_ratio"
        tagged_controls.append(tagged)
    return tagged_controls


def _embedded_window_control_groups(window, controls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    try:
        parent_rect = window.rectangle()
        parent_title = window.window_text()
    except Exception:
        return []

    embedded_windows = []
    for control in controls:
        if control.get("control_type") != "Window":
            continue
        rect = control.get("rectangle", {}) or {}
        if _rect_matches_window(rect, parent_rect) and control.get("name", "") == parent_title:
            continue
        if int(rect.get("width", 0)) <= 0 or int(rect.get("height", 0)) <= 0:
            continue
        embedded_windows.append(control)

    groups = []
    for embedded in embedded_windows:
        embedded_rect = embedded.get("rectangle", {}) or {}
        embedded_prefix = embedded.get("automation_id") or ""
        embedded_controls = []
        for control in controls:
            if embedded_prefix and not _belongs_to_embedded_window(control, embedded_prefix):
                continue
            if _control_center_in_rect(control, embedded_rect):
                copied = dict(control)
                copied.pop("rectangle_ratio", None)
                copied.pop("rectangle_ratio_units", None)
                embedded_controls.append(copied)
        if embedded_controls:
            groups.append(
                {
                    "title": embedded.get("name") or "embedded_window",
                    "window_rect": embedded_rect,
                    "controls": embedded_controls,
                }
            )
    return groups


def _belongs_to_embedded_window(control: Dict[str, Any], embedded_prefix: str) -> bool:
    automation_id = control.get("automation_id") or ""
    return automation_id == embedded_prefix or automation_id.startswith(f"{embedded_prefix}.")


def _rect_matches_window(rect: Dict[str, Any], window_rect) -> bool:
    return (
        int(rect.get("x", 0)) == int(window_rect.left)
        and int(rect.get("y", 0)) == int(window_rect.top)
        and int(rect.get("width", 0)) == int(window_rect.width())
        and int(rect.get("height", 0)) == int(window_rect.height())
    )


def _control_center_in_rect(control: Dict[str, Any], rect: Dict[str, Any]) -> bool:
    control_rect = control.get("rectangle", {}) or {}
    width = float(control_rect.get("width", 0))
    height = float(control_rect.get("height", 0))
    if width <= 0 or height <= 0:
        return False
    center_x = float(control_rect.get("x", 0)) + (width / 2)
    center_y = float(control_rect.get("y", 0)) + (height / 2)
    return (
        float(rect.get("x", 0)) <= center_x <= float(rect.get("x", 0)) + float(rect.get("width", 0))
        and float(rect.get("y", 0)) <= center_y <= float(rect.get("y", 0)) + float(rect.get("height", 0))
    )


def _screen_key(
    scenario_name: str,
    step_index: int,
    action: str,
    target: str | None,
    window_index: int,
    source: str = "window",
) -> str:
    scenario_part = _slug(scenario_name) or "scenario"
    target_name = (target or "unknown").replace(".", "_")
    return f"{scenario_part}_step_{step_index:03d}_{action}_{target_name}_{source}_{window_index}"


def _unique_screen_key(profile: Dict[str, Any], base_key: str) -> str:
    screens = profile.setdefault("screens", {})
    if base_key not in screens:
        return base_key

    counter = 2
    while f"{base_key}_{counter}" in screens:
        counter += 1
    return f"{base_key}_{counter}"


def _merge_profile_screen(
    profile: Dict[str, Any],
    discovered_profile: Dict[str, Any],
    screen_key: str,
) -> None:
    profile.setdefault("screens", {})[screen_key] = discovered_profile["screens"][screen_key]
