from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image, ImageDraw, ImageFont

from app_profile_generator.inspection.control_dumper import build_elements_from_controls
from app_profile_generator.inspection.control_dumper import dump_controls
from app_profile_generator.inspection.hierarchical_profile import (
    build_controls_dump_for_review,
    build_hierarchical_profile,
)
from app_profile_generator.output.profile_writer import write_yaml
from fcm_gui_automation.recognition.ocr_adapter import OCRAdapter


@dataclass(frozen=True)
class FakeRect:
    left: int
    top: int
    right: int
    bottom: int

    def width(self) -> int:
        return self.right - self.left

    def height(self) -> int:
        return self.bottom - self.top


class FakeWindow:
    def __init__(self, image: Image.Image, rect: FakeRect, controls: List["FakeControl"]) -> None:
        self._image = image
        self._rect = rect
        self._controls = controls

    def capture_as_image(self) -> Image.Image:
        return self._image.copy()

    def rectangle(self) -> FakeRect:
        return self._rect

    def descendants(self) -> List["FakeControl"]:
        return self._controls


@dataclass(frozen=True)
class FakeElementInfo:
    name: str
    control_type: str
    class_name: str


class FakeControl:
    def __init__(
        self,
        name: str,
        control_type: str,
        class_name: str,
        automation_id: str,
        rect: FakeRect,
    ) -> None:
        self.element_info = FakeElementInfo(
            name=name,
            control_type=control_type,
            class_name=class_name,
        )
        self._automation_id = automation_id
        self._rect = rect

    def rectangle(self) -> FakeRect:
        return self._rect

    def automation_id(self) -> str:
        return self._automation_id

    def is_enabled(self) -> bool:
        return True

    def is_visible(self) -> bool:
        return True


def main() -> int:
    output_dir = Path("profiles") / "validation" / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)

    window_rect = {"x": 100, "y": 200, "width": 800, "height": 500}
    grid_region = {"x": 220, "y": 290, "width": 360, "height": 160}

    screenshot = _make_grid_screenshot(window_rect, grid_region)
    screenshot_path = output_dir / "mfc_grid_input.png"
    screenshot.save(screenshot_path)

    fake_grid = FakeControl(
        name="Validation Grid",
        control_type="Custom",
        class_name="MFCGridCtrl",
        automation_id="validation_grid",
        rect=FakeRect(
            grid_region["x"],
            grid_region["y"],
            grid_region["x"] + grid_region["width"],
            grid_region["y"] + grid_region["height"],
        ),
    )
    window = FakeWindow(
        image=screenshot,
        rect=FakeRect(
            window_rect["x"],
            window_rect["y"],
            window_rect["x"] + window_rect["width"],
            window_rect["y"] + window_rect["height"],
        ),
        controls=[fake_grid],
    )
    controls = dump_controls(window)
    cell_controls = [control for control in controls if control.get("element_type") == "grid_cell"]

    app_info = {
        "name": "validation_mfc_grid",
        "window_title": "Validation MFCGridCtrl Window",
        "backend": "uia",
        "window_rect": window_rect,
        "default_timeout": 10,
    }
    hierarchical_profile = build_hierarchical_profile(app_info=app_info, controls=controls)
    elements = build_elements_from_controls(controls, window_rect=window_rect)
    controls_dump = build_controls_dump_for_review(controls)

    ocr_result = _validate_numeric_ocr(output_dir)
    summary = {
        "output_dir": str(output_dir.resolve()),
        "grid": {
            "input_image": str(screenshot_path.name),
            "source_class_name": "MFCGridCtrl",
            "expected_rows": 4,
            "expected_columns": 3,
            "expected_cell_count": 12,
            "detected_cell_count": len(cell_controls),
            "detected_cells": [
                {
                    "name": control["name"],
                    "automation_id": control["automation_id"],
                    "grid_cell": control["grid_cell"],
                    "rectangle": dict(control["rectangle"]),
                    "rectangle_ratio": dict(control["rectangle_ratio"]),
                }
                for control in cell_controls
            ],
        },
        "coordinate_system": {
            "profile_coordinate_system": hierarchical_profile.get("coordinate_system"),
            "first_cell_region": _first_cell_region(hierarchical_profile),
            "first_cell_region_units": _first_cell_region_units(hierarchical_profile),
        },
        "ocr": ocr_result,
    }

    write_yaml(output_dir / "controls_raw.yaml", {"controls": controls})
    write_yaml(output_dir / "controls_dump.yaml", {"controls": controls_dump})
    write_yaml(output_dir / "elements.yaml", {"elements": elements})
    write_yaml(output_dir / "hierarchical_profile.yaml", hierarchical_profile)
    write_yaml(output_dir / "validation_summary.yaml", summary)
    _write_report(output_dir / "README.md", summary)

    print(f"Validation output written: {output_dir.resolve()}")
    print(f"Detected MFCGridCtrl cells: {len(cell_controls)} / 12")
    print(f"Profile coordinate system: {hierarchical_profile.get('coordinate_system')}")
    print(f"OCR numeric status: {ocr_result['status']}")
    return 0


def _make_grid_screenshot(window_rect: Dict[str, int], grid_region: Dict[str, int]) -> Image.Image:
    image = Image.new("RGB", (window_rect["width"], window_rect["height"]), "white")
    draw = ImageDraw.Draw(image)
    rel_x = grid_region["x"] - window_rect["x"]
    rel_y = grid_region["y"] - window_rect["y"]
    width = grid_region["width"]
    height = grid_region["height"]

    draw.rectangle((rel_x, rel_y, rel_x + width, rel_y + height), fill=(248, 250, 252), outline=(15, 23, 42), width=2)
    for col in range(4):
        x = rel_x + round((width / 3) * col)
        draw.line((x, rel_y, x, rel_y + height), fill=(15, 23, 42), width=2)
    for row in range(5):
        y = rel_y + round((height / 4) * row)
        draw.line((rel_x, y, rel_x + width, y), fill=(15, 23, 42), width=2)

    font = ImageFont.load_default()
    for row in range(4):
        for col in range(3):
            draw.text((rel_x + 12 + col * 120, rel_y + 12 + row * 40), f"R{row + 1}C{col + 1}", fill=(51, 65, 85), font=font)
    return image


def _validate_numeric_ocr(output_dir: Path) -> Dict[str, Any]:
    image = Image.new("RGB", (260, 90), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 42)
    except Exception:
        font = ImageFont.load_default()
    expected = "123.45"
    draw.text((28, 20), expected, fill="black", font=font)
    image_path = output_dir / "numeric_ocr_input.png"
    image.save(image_path)

    try:
        adapter = OCRAdapter(config="--psm 7 -c tessedit_char_whitelist=0123456789.-+")
        actual = adapter.read_number(image_path)
        status = "pass" if abs(actual - 123.45) < 0.01 else "fail"
        error = None
    except Exception as exc:
        actual = None
        status = "error"
        error = str(exc)

    return {
        "input_image": image_path.name,
        "expected_number": 123.45,
        "actual_number": actual,
        "status": status,
        "error": error,
    }


def _first_cell_region(profile: Dict[str, Any]) -> Dict[str, Any] | None:
    for screen in (profile.get("screens") or {}).values():
        for group in (screen.get("groups") or {}).values():
            for control in (group.get("controls") or {}).values():
                if control.get("name", "").endswith("cell 1,1"):
                    return dict(control.get("region") or {})
    return None


def _first_cell_region_units(profile: Dict[str, Any]) -> str | None:
    for screen in (profile.get("screens") or {}).values():
        for group in (screen.get("groups") or {}).values():
            for control in (group.get("controls") or {}).values():
                if control.get("name", "").endswith("cell 1,1"):
                    return control.get("region_units")
    return None


def _write_report(path: Path, summary: Dict[str, Any]) -> None:
    grid = summary["grid"]
    coordinate_system = summary["coordinate_system"]
    ocr = summary["ocr"]
    lines = [
        "# New Profile Feature Validation",
        "",
        "## MFCGridCtrl Cell Detection",
        "",
        f"- Input image: `{grid['input_image']}`",
        f"- Detected cells: `{grid['detected_cell_count']}` / `{grid['expected_cell_count']}`",
        f"- Source class: `{grid['source_class_name']}`",
        "",
        "## Coordinate System",
        "",
        f"- Profile coordinate system: `{coordinate_system['profile_coordinate_system']}`",
        f"- First cell units: `{coordinate_system['first_cell_region_units']}`",
        f"- First cell region: `{coordinate_system['first_cell_region']}`",
        "",
        "## Numeric OCR",
        "",
        f"- Input image: `{ocr['input_image']}`",
        f"- Expected: `{ocr['expected_number']}`",
        f"- Actual: `{ocr['actual_number']}`",
        f"- Status: `{ocr['status']}`",
    ]
    if ocr.get("error"):
        lines.append(f"- Error: `{ocr['error']}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
