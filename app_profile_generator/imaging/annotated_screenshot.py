from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import ImageDraw, ImageFont

from app_profile_generator.runtime.screenshot_capture import capture_window_image


def _make_display_label(control: Dict[str, Any], fallback_index: int) -> str:
    automation_id = (control.get("automation_id") or "").strip()
    name = (control.get("name") or "").strip()
    control_type = (control.get("control_type") or "").strip()

    if automation_id:
        return automation_id
    if name:
        return name
    if control_type:
        return f"{control_type}_{fallback_index:03d}"
    return f"control_{fallback_index:03d}"


def _make_detail_label(control: Dict[str, Any], fallback_index: int) -> str:
    automation_id = (control.get("automation_id") or "").strip()
    name = (control.get("name") or "").strip()
    control_type = (control.get("control_type") or "").strip()
    element_type = (control.get("element_type") or "").strip()
    class_name = (control.get("class_name") or "").strip()

    parts = [f"#{fallback_index:03d}"]
    if automation_id:
        parts.append(f"id={automation_id}")
    if name:
        parts.append(f"name={name}")
    if control_type:
        parts.append(f"type={control_type}")
    if element_type:
        parts.append(f"element={element_type}")
    if class_name:
        parts.append(f"class={class_name}")
    return " | ".join(parts)


def _choose_box_color(control_type: str) -> Tuple[int, int, int]:
    color_map = {
        "Button": (255, 0, 0),
        "Edit": (0, 128, 255),
        "Text": (0, 180, 0),
        "CheckBox": (180, 0, 180),
        "ComboBox": (255, 128, 0),
        "TabItem": (128, 64, 255),
        "MenuItem": (128, 128, 0),
        "ListItem": (0, 180, 180),
    }
    return color_map.get(control_type, (80, 80, 80))


def _safe_text(draw: ImageDraw.ImageDraw, xy: Tuple[int, int], text: str, fill, font) -> None:
    try:
        draw.text(xy, text, fill=fill, font=font)
    except UnicodeEncodeError:
        safe_text = text.encode("ascii", errors="ignore").decode("ascii") or "control"
        draw.text(xy, safe_text, fill=fill, font=font)


def create_annotated_screenshot(
    window,
    controls: List[Dict[str, Any]],
    output_path: Path,
) -> List[Dict[str, Any]]:
    image = capture_window_image(window).convert("RGB")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    window_rect = window.rectangle()
    window_left = window_rect.left
    window_top = window_rect.top

    controls_map: List[Dict[str, Any]] = []

    for fallback_i, control in enumerate(controls):
        if "error" in control:
            continue
        control_index = int(control.get("index", fallback_i))

        rect = control.get("rectangle", {}) or {}
        x = int(rect.get("x", 0))
        y = int(rect.get("y", 0))
        w = int(rect.get("width", 0))
        h = int(rect.get("height", 0))

        if w <= 0 or h <= 0:
            continue

        rel_x1 = x - window_left
        rel_y1 = y - window_top
        rel_x2 = rel_x1 + w
        rel_y2 = rel_y1 + h

        if rel_x2 < 0 or rel_y2 < 0 or rel_x1 > image.width or rel_y1 > image.height:
            continue

        control_type = control.get("control_type", "")
        box_color = _choose_box_color(control_type)
        display_label = _make_display_label(control, control_index)
        detail_label = _make_detail_label(control, control_index)

        draw.rectangle([(rel_x1, rel_y1), (rel_x2, rel_y2)], outline=box_color, width=2)

        label = f"{control_index:03d}: {display_label}"
        label_x = max(rel_x1, 0)
        label_y = max(rel_y1 - 14, 0)

        try:
            bbox = draw.textbbox((label_x, label_y), label, font=font)
            draw.rectangle(bbox, fill=(255, 255, 255))
        except Exception:
            pass

        _safe_text(draw, (label_x, label_y), label, fill=box_color, font=font)

        controls_map.append(
            {
                "label_no": control_index,
                "display_label": display_label,
                "detail_label": detail_label,
                "automation_id": control.get("automation_id", ""),
                "name": control.get("name", ""),
                "control_type": control.get("control_type", ""),
                "element_type": control.get("element_type", ""),
                "class_name": control.get("class_name", ""),
                "absolute_region": {"x": x, "y": y, "width": w, "height": h},
                "window_relative_region": {
                    "x": rel_x1,
                    "y": rel_y1,
                    "width": w,
                    "height": h,
                },
                "window_ratio_region": {
                    "x": round(rel_x1 / max(1, image.width), 6),
                    "y": round(rel_y1 / max(1, image.height), 6),
                    "width": round(w / max(1, image.width), 6),
                    "height": round(h / max(1, image.height), 6),
                },
            }
        )

    image.save(output_path)
    return controls_map
