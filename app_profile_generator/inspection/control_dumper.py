from collections import defaultdict
from typing import Dict, Any, List


CONTROL_TYPE_MAP = {
    "Button": "button",
    "Edit": "input",
    "Text": "text",
    "CheckBox": "checkbox",
    "ComboBox": "combobox",
    "TabItem": "tab",
    "MenuItem": "menu",
    "ListItem": "list_item",
}


def rect_to_dict(rect) -> Dict[str, int]:
    return {
        "x": rect.left,
        "y": rect.top,
        "width": rect.width(),
        "height": rect.height(),
    }


def map_control_type(control_type: str) -> str:
    return CONTROL_TYPE_MAP.get(control_type, "control")


def safe_getattr(obj, attr_name: str, default=None):
    try:
        value = getattr(obj, attr_name)
        if callable(value):
            return value()
        return value
    except Exception:
        return default


def dump_controls(window) -> List[Dict[str, Any]]:
    controls = []

    try:
        descendants = window.descendants()
    except Exception as exc:
        raise RuntimeError(f"Failed to get descendants: {exc}") from exc

    for idx, ctrl in enumerate(descendants):
        try:
            info = ctrl.element_info
            rect = ctrl.rectangle()

            if rect.width() <= 0 or rect.height() <= 0:
                continue

            control_type = info.control_type or "Unknown"
            element_type = map_control_type(control_type)

            controls.append(
                {
                    "index": idx,
                    "name": info.name or "",
                    "control_type": control_type,
                    "element_type": element_type,
                    "automation_id": safe_getattr(ctrl, "automation_id", ""),
                    "class_name": info.class_name or "",
                    "rectangle": rect_to_dict(rect),
                    "enabled": safe_getattr(ctrl, "is_enabled", None),
                    "visible": safe_getattr(ctrl, "is_visible", None),
                }
            )

        except Exception as exc:
            controls.append({"index": idx, "error": str(exc)})

    return controls


def build_elements_from_controls(controls: List[Dict[str, Any]]) -> Dict[str, Any]:
    counters = defaultdict(int)
    elements = {}

    for control in controls:
        if "error" in control:
            continue

        element_type = control.get("element_type", "control")
        counters[element_type] += 1
        element_id = f"auto_{element_type}_{counters[element_type]:03d}"
        rect = control.get("rectangle", {})

        elements[element_id] = {
            "type": element_type,
            "text": control.get("name", ""),
            "find_by": {
                "priority": ["uia", "region"],
                "uia": {
                    "title": control.get("name", ""),
                    "control_type": control.get("control_type", ""),
                    "automation_id": control.get("automation_id", ""),
                    "class_name": control.get("class_name", ""),
                },
                "region": {
                    "x": rect.get("x", 0),
                    "y": rect.get("y", 0),
                    "width": rect.get("width", 0),
                    "height": rect.get("height", 0),
                },
            },
        }

    return elements


def dump_window_info(window) -> Dict[str, Any]:
    rect = window.rectangle()
    return {
        "window_title": window.window_text(),
        "process_id": window.process_id(),
        "window_rect": rect_to_dict(rect),
        "backend": "uia",
    }
