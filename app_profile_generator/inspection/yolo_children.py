from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image

from app_profile_generator.inspection.hierarchical_profile import is_yolo_scan_candidate


YOLO_CONFIG_DIR = (Path(__file__).resolve().parents[2] / "yolo" / "ultralytics_config").resolve()
YOLO_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(YOLO_CONFIG_DIR))


def enrich_controls_with_yolo_children(
    controls: List[Dict[str, Any]],
    screenshot_path: Path,
    window_rect: Dict[str, Any],
    model_path: Path,
    output_dir: Path,
    conf: float = 0.25,
    iou: float = 0.7,
    imgsz: int = 1280,
    device: str | None = None,
) -> List[Dict[str, Any]]:
    model_path = model_path.expanduser().resolve()
    if not model_path.is_file():
        raise FileNotFoundError(f"YOLO model not found: {model_path}")
    if not screenshot_path.is_file():
        raise FileNotFoundError(f"Screenshot not found: {screenshot_path}")

    from ultralytics import YOLO

    model = YOLO(str(model_path))
    screenshot = Image.open(screenshot_path).convert("RGB")
    yolo_dir = output_dir / "yolo_children"
    yolo_dir.mkdir(parents=True, exist_ok=True)

    enriched = []
    for control in controls:
        updated = dict(control)
        if not is_yolo_scan_candidate(updated):
            enriched.append(updated)
            continue

        crop = _crop_control(screenshot, updated, window_rect)
        if crop is None:
            enriched.append(updated)
            continue

        crop_path = yolo_dir / f"control_{updated.get('index')}_crop.png"
        crop.save(crop_path)
        detections = _detect_children(
            model=model,
            crop_path=crop_path,
            parent_control=updated,
            conf=conf,
            iou=iou,
            imgsz=imgsz,
            device=device,
        )
        if detections:
            updated["children"] = detections
        enriched.append(updated)

    return enriched


def _crop_control(
    screenshot: Image.Image,
    control: Dict[str, Any],
    window_rect: Dict[str, Any],
) -> Image.Image | None:
    region = control.get("rectangle", {}) or {}
    left = int(region.get("x", 0)) - int(window_rect.get("x", 0))
    top = int(region.get("y", 0)) - int(window_rect.get("y", 0))
    right = left + int(region.get("width", 0))
    bottom = top + int(region.get("height", 0))

    left = max(0, min(left, screenshot.width))
    top = max(0, min(top, screenshot.height))
    right = max(0, min(right, screenshot.width))
    bottom = max(0, min(bottom, screenshot.height))
    if right <= left or bottom <= top:
        return None
    return screenshot.crop((left, top, right, bottom))


def _detect_children(
    model,
    crop_path: Path,
    parent_control: Dict[str, Any],
    conf: float,
    iou: float,
    imgsz: int,
    device: str | None,
) -> List[Dict[str, Any]]:
    predict_kwargs: dict[str, Any] = {
        "source": str(crop_path),
        "conf": conf,
        "iou": iou,
        "imgsz": imgsz,
        "verbose": False,
    }
    if device:
        predict_kwargs["device"] = device

    result = model.predict(**predict_kwargs)[0]
    names = result.names or model.names
    parent_region = parent_control.get("rectangle", {}) or {}
    parent_x = int(parent_region.get("x", 0))
    parent_y = int(parent_region.get("y", 0))

    children = []
    used_names: set[str] = set()
    for index, box in enumerate(result.boxes, start=1):
        class_id = int(box.cls[0].item())
        class_name = _class_name(names, class_id)
        confidence = float(box.conf[0].item())
        x1, y1, x2, y2 = [float(value) for value in box.xyxy[0].tolist()]
        width = max(0, int(round(x2 - x1)))
        height = max(0, int(round(y2 - y1)))
        if width <= 0 or height <= 0:
            continue

        child_name = _unique_name(_slug(class_name, f"detected_{index}"), used_names)
        rel_x = int(round(x1))
        rel_y = int(round(y1))
        children.append(
            {
                "name": child_name,
                "source": "yolo",
                "class_name": class_name,
                "confidence": round(confidence, 4),
                "region": {
                    "x": parent_x + rel_x,
                    "y": parent_y + rel_y,
                    "width": width,
                    "height": height,
                },
                "relative_region": {
                    "x": rel_x,
                    "y": rel_y,
                    "width": width,
                    "height": height,
                },
            }
        )
    return children


def _class_name(names: Any, class_id: int) -> str:
    if isinstance(names, dict):
        return str(names.get(class_id, class_id))
    if isinstance(names, list) and 0 <= class_id < len(names):
        return str(names[class_id])
    return str(class_id)


def _slug(value: str, fallback: str) -> str:
    text = value.strip()
    if not text:
        return fallback
    if not text.isupper():
        text = re.sub(r"(?<!^)(?=[A-Z])", "_", text)
    text = re.sub(r"[^0-9A-Za-z_]+", "_", text).strip("_").lower()
    text = re.sub(r"_+", "_", text)
    return text or fallback


def _unique_name(base_name: str, used_names: set[str]) -> str:
    if base_name not in used_names:
        used_names.add(base_name)
        return base_name

    counter = 2
    while f"{base_name}_{counter}" in used_names:
        counter += 1
    name = f"{base_name}_{counter}"
    used_names.add(name)
    return name
