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


def discover_profile_from_scenario(
    profile: Dict[str, Any],
    initial_window,
    scenario: Dict[str, Any],
    delay: float = 0.5,
) -> Dict[str, Any]:
    pid = initial_window.process_id()
    seen_signatures = _profile_signatures(profile)
    seen_signatures.add(_controls_signature(dump_controls(initial_window)))
    steps = scenario.get("steps", [])
    if not isinstance(steps, list):
        raise ValueError("Scenario steps must be a list.")

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
        _execute_step_for_discovery(pid, step)
        time.sleep(delay)

        for window_index, window in enumerate(_visible_windows_for_pid(pid)):
            controls = dump_controls(window)
            signature = _controls_signature(controls)
            if signature in seen_signatures:
                continue

            window_info = dump_window_info(window)
            screen_key = _unique_screen_key(
                profile,
                _screen_key(step_index, action, trigger_target, window_index),
            )
            discovered_profile = build_hierarchical_profile(
                app_info={
                    "window_title": window_info["window_title"],
                    "window_rect": window_info["window_rect"],
                },
                controls=controls,
                screen_key=screen_key,
                discovered_by={
                    "type": "scenario_step",
                    "step_index": step_index,
                    "action": action,
                    "trigger_target": trigger_target,
                    "parent_screen": "main_window",
                },
            )
            _merge_profile_screen(profile, discovered_profile, screen_key)
            seen_signatures.add(signature)

    return profile


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
    return group_slug == _slug(getattr(info, "name", "") or "")


def _is_target_match(control, target: str) -> bool:
    info = control.element_info
    target_slug = _slug(target)
    return target_slug == _slug(getattr(info, "name", "") or "")


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
        for group in screen.get("groups", {}).values():
            for control in group.get("controls", {}).values():
                rect = control.get("region", {}) or {}
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


def _screen_key(step_index: int, action: str, target: str | None, window_index: int) -> str:
    target_name = (target or "unknown").replace(".", "_")
    return f"step_{step_index:03d}_{action}_{target_name}_window_{window_index}"


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
