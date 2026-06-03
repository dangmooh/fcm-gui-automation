from __future__ import annotations

from pathlib import Path
import re
import time
from typing import Any

import yaml
from PIL import Image, ImageDraw
from PIL import ImageGrab
from pywinauto import Application
from pywinauto import Desktop
from pywinauto.findwindows import ElementNotFoundError
from pywinauto.timings import TimeoutError

from core.screenshot import build_screenshot_path
from recognition.base import RecognitionAdapter
from recognition.color_adapter import ColorAdapter


class PyWinAutoAdapter(RecognitionAdapter):
    def __init__(self, base_dir: Path, config: dict, logger) -> None:
        self.base_dir = base_dir
        self.config = config
        self.logger = logger
        self.app = None
        self.window = None
        self.process_started = False
        self.color_adapter = ColorAdapter()
        self.profile = self._load_profile()

    @property
    def app_config(self) -> dict:
        return self.config["app"]

    def launch_or_connect(self) -> None:
        backend = self.app_config.get("backend", "uia")
        title_re = self.app_config.get("title_re")
        timeout = self.app_config.get("focus_timeout", 10)

        self.app = Application(backend=backend)
        if title_re:
            try:
                self.app.connect(title_re=title_re, timeout=2)
                self.logger.info("Connected to existing window.")
            except (ElementNotFoundError, TimeoutError):
                command = self._build_command()
                self.logger.info("Starting target app: %s", command)
                self.app = Application(backend=backend).start(command, wait_for_idle=False)
                self.process_started = True
        else:
            command = self._build_command()
            self.logger.info("Starting target app: %s", command)
            self.app = Application(backend=backend).start(command, wait_for_idle=False)
            self.process_started = True

        if title_re:
            if self.process_started:
                time.sleep(1.0)
            self.window = self.app.window(title_re=title_re)
        else:
            self.window = self.app.top_window()

        self.window.wait("visible enabled ready", timeout=timeout)
        self.window.set_focus()
        time.sleep(0.5)

    def _build_command(self) -> str:
        python_command = self.app_config.get("python_command", "python")
        script_path = Path(self.app_config["script_path"]).expanduser().resolve()
        if script_path.suffix.lower() == ".py":
            return f'{python_command} "{script_path}"'
        return f'"{script_path}"'

    def _slug(self, value: str) -> str:
        text = value.strip()
        if not text.isupper():
            text = re.sub(r"(?<!^)(?=[A-Z])", "_", text)
        text = re.sub(r"[^0-9A-Za-z_]+", "_", text).strip("_").lower()
        text = re.sub(r"_+", "_", text)
        return text

    def _load_profile(self) -> dict[str, Any] | None:
        configured_path = self.app_config.get("profile_path")
        profile_path = None
        if configured_path:
            profile_path = Path(configured_path).expanduser()
            if not profile_path.is_absolute():
                profile_path = (self.base_dir / profile_path).resolve()
        else:
            generated_root = self.base_dir.parent / "profiles" / "generated"
            candidates = sorted(
                generated_root.glob("*/hierarchical_profile.yaml"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            ) if generated_root.exists() else []
            profile_path = candidates[0] if candidates else None

        if profile_path is None or not profile_path.is_file():
            return None

        with profile_path.open("r", encoding="utf-8") as file:
            profile = yaml.safe_load(file) or {}
        if not isinstance(profile, dict):
            return None
        self.logger.info("Loaded app profile: %s", profile_path)
        return profile

    def _rect_contains_center(self, container, control) -> bool:
        container_rect = container.rectangle()
        control_rect = control.rectangle()
        center_x = control_rect.left + (control_rect.width() / 2)
        center_y = control_rect.top + (control_rect.height() / 2)
        return (
            container_rect.left <= center_x <= container_rect.right
            and container_rect.top <= center_y <= container_rect.bottom
        )

    def _is_group_match(self, control, group: str) -> bool:
        group_slug = self._slug(group)
        return group_slug in self._control_match_candidates(control)

    def _is_target_match(self, control, target: str) -> bool:
        target_slug = self._slug(target)
        return target_slug in self._control_match_candidates(control)

    def _control_match_candidates(self, control) -> set[str]:
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

        candidates = {self._slug(value) for value in expanded_values if value}
        for value in list(candidates):
            if "_" in value:
                candidates.add(value.rsplit("_", 1)[0])
        return {candidate for candidate in candidates if candidate}

    def _find_profile_target(self, group: str | None, target: str) -> dict[str, Any] | None:
        if not self.profile:
            return None

        group_slug = self._slug(group or "")
        target_slug = self._slug(target)
        visible_name_match = None
        for screen in (self.profile.get("screens") or {}).values():
            for group_key, group_record in self._iter_profile_groups(screen.get("groups") or {}):
                if group:
                    group_names = {
                        group_key,
                        group_record.get("name", ""),
                        ((group_record.get("scenario_ref") or {}).get("group") or ""),
                    }
                    if group_slug not in {self._slug(name) for name in group_names if name}:
                        continue

                for control_key, control_record in (group_record.get("controls") or {}).items():
                    scenario_ref = control_record.get("scenario_ref") or {}
                    scenario_names = {
                        control_key,
                        scenario_ref.get("target", ""),
                    }
                    profile_match = {
                        "screen": screen,
                        "group": group_record,
                        "control": control_record,
                    }
                    if target_slug in {self._slug(name) for name in scenario_names if name}:
                        return profile_match
                    visible_name = control_record.get("name", "")
                    if visible_name and target_slug == self._slug(visible_name):
                        visible_name_match = profile_match
        if visible_name_match is not None:
            return visible_name_match
        return None

    def _iter_profile_groups(self, groups: dict[str, Any]):
        for group_key, group_record in groups.items():
            yield group_key, group_record
            yield from self._iter_profile_groups(group_record.get("child_groups") or {})

    def _current_region_from_profile(
        self,
        screen: dict[str, Any],
        region: dict[str, Any],
        region_units: str | None = None,
    ) -> dict[str, float]:
        if self.window is None:
            raise RuntimeError("Window is not connected.")

        current_window = self.window.rectangle()
        if region_units == "window_ratio" or self._looks_like_ratio_region(region):
            return {
                "left": current_window.left + (float(region.get("x", 0)) * current_window.width()),
                "top": current_window.top + (float(region.get("y", 0)) * current_window.height()),
                "width": float(region.get("width", 0)) * current_window.width(),
                "height": float(region.get("height", 0)) * current_window.height(),
            }

        profile_window = screen.get("window_rect") or {}
        profile_x = float(profile_window.get("x", current_window.left))
        profile_y = float(profile_window.get("y", current_window.top))
        profile_width = max(1.0, float(profile_window.get("width", current_window.width())))
        profile_height = max(1.0, float(profile_window.get("height", current_window.height())))

        scale_x = current_window.width() / profile_width
        scale_y = current_window.height() / profile_height
        return {
            "left": current_window.left + ((float(region.get("x", 0)) - profile_x) * scale_x),
            "top": current_window.top + ((float(region.get("y", 0)) - profile_y) * scale_y),
            "width": float(region.get("width", 0)) * scale_x,
            "height": float(region.get("height", 0)) * scale_y,
        }

    def _rect_area(self, control) -> int:
        rect = control.rectangle()
        return max(0, rect.width()) * max(0, rect.height())

    def _region_match_score(self, control, region: dict[str, float]) -> tuple[float, float]:
        rect = control.rectangle()
        left = max(rect.left, region["left"])
        top = max(rect.top, region["top"])
        right = min(rect.right, region["left"] + region["width"])
        bottom = min(rect.bottom, region["top"] + region["height"])
        overlap = max(0.0, right - left) * max(0.0, bottom - top)
        target_area = max(1.0, region["width"] * region["height"])
        area_delta = abs(self._rect_area(control) - target_area)
        return (overlap / target_area, -area_delta)

    def _center_in_region(self, control, region: dict[str, float]) -> bool:
        rect = control.rectangle()
        center_x = rect.left + (rect.width() / 2)
        center_y = rect.top + (rect.height() / 2)
        return (
            region["left"] <= center_x <= region["left"] + region["width"]
            and region["top"] <= center_y <= region["top"] + region["height"]
        )

    def _child_from_profile(self, target: str, group: str | None, descendants: list):
        profile_target = self._find_profile_target(group, target)
        if not profile_target:
            return None

        control_record = profile_target["control"]
        region = control_record.get("region") or {}
        current_region = self._current_region_from_profile(
            profile_target["screen"],
            region,
            region_units=control_record.get("region_units"),
        )
        candidates = []
        for control in descendants:
            try:
                if self._center_in_region(control, current_region):
                    candidates.append(control)
            except Exception:
                continue
        if not candidates:
            return None
        return max(candidates, key=lambda control: self._region_match_score(control, current_region))

    def _child(self, target: str, group: str | None = None):
        if self.window is None:
            raise RuntimeError("Window is not connected.")
        descendants = self.window.descendants()

        if group:
            profile_control = self._child_from_profile(target, group, descendants)
            if profile_control is not None:
                return profile_control

            group_controls = [control for control in descendants if self._is_group_match(control, group)]
            for group_control in group_controls:
                for control in descendants:
                    if control == group_control:
                        continue
                    try:
                        if self._rect_contains_center(group_control, control) and self._is_target_match(
                            control,
                            target,
                        ):
                            return control
                    except Exception:
                        continue
            raise ElementNotFoundError(
                {"group": group, "target": target, "backend": self.app_config.get("backend")}
            )

        for control in descendants:
            if self._is_target_match(control, target):
                return control
        profile_control = self._child_from_profile(target, group, descendants)
        if profile_control is not None:
            return profile_control
        raise ElementNotFoundError({"target": target, "backend": self.app_config.get("backend")})

    def set_text(self, target: str, value: str, group: str | None = None) -> None:
        control = self._child(target, group=group)
        wrote = False
        try:
            control.set_focus()
            control.set_edit_text(value)
            wrote = True
        except Exception:
            pass

        try:
            control.click_input()
            control.type_keys("^a{BACKSPACE}", set_foreground=True)
            control.type_keys(value, with_spaces=True, set_foreground=True)
            wrote = True
        except Exception:
            pass

        if not wrote:
            control.type_keys("^a{BACKSPACE}", set_foreground=True)
            control.type_keys(value, with_spaces=True, set_foreground=True)

    def click(self, target: str, group: str | None = None) -> None:
        control = self._child(target, group=group)
        try:
            control.set_focus()
            control.click_input()
            time.sleep(0.2)
            return
        except Exception:
            pass

        try:
            control.set_focus()
            control.invoke()
            time.sleep(0.2)
            return
        except Exception:
            pass

        try:
            control.set_focus()
            control.click()
            time.sleep(0.2)
            return
        except Exception:
            pass

        try:
            control.set_focus()
            control.type_keys("{ENTER}", set_foreground=True)
            time.sleep(0.2)
            return
        except Exception:
            pass

        control.set_focus()
        control.type_keys("{SPACE}", set_foreground=True)
        time.sleep(0.2)

    def wait_window(self, title_re: str | None = None, timeout: float = 10.0):
        if self.window is None:
            raise RuntimeError("Window is not connected.")
        deadline = time.monotonic() + timeout
        title_pattern = title_re or ".*"
        backend = self.app_config.get("backend", "uia")
        pid = self.window.process_id()
        last_error = None

        while time.monotonic() < deadline:
            try:
                for control in self.window.descendants(control_type="Window"):
                    title = control.window_text() or ""
                    if re.search(title_pattern, title):
                        try:
                            control.set_focus()
                        except Exception:
                            pass
                        self.logger.info("Detected child window: %s", title)
                        return control

                desktop = Desktop(backend=backend)
                for window in desktop.windows(process=pid, visible_only=True):
                    title = window.window_text() or ""
                    if re.search(title_pattern, title):
                        window.wait("visible enabled", timeout=1)
                        window.set_focus()
                        self.logger.info("Detected window: %s", title)
                        return window
            except Exception as exc:
                last_error = exc
            time.sleep(0.2)

        raise TimeoutError(f"Window not found: title_re={title_pattern!r}, last_error={last_error}")

    def select_file(
        self,
        file_path: str,
        dialog_title_re: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        path = Path(file_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"File to select not found: {path}")

        dialog = self._wait_file_dialog(dialog_title_re=dialog_title_re, timeout=timeout)
        dialog.set_focus()
        editor = self._write_file_dialog_path(dialog, str(path))
        self._confirm_file_dialog(dialog, editor=editor, timeout=timeout)
        self.logger.info("Selected file in dialog: %s", path)
        if self.window is not None:
            try:
                self.window.set_focus()
            except Exception:
                pass

    def _wait_file_dialog(self, dialog_title_re: str | None, timeout: float):
        deadline = time.monotonic() + timeout
        title_pattern = dialog_title_re or r".*(Open|열기|Select|선택|File).*"
        backend = self.app_config.get("backend", "uia")
        last_error = None

        while time.monotonic() < deadline:
            try:
                if self.window is not None:
                    for dialog in self.window.descendants(control_type="Window"):
                        title = dialog.window_text() or ""
                        if re.search(title_pattern, title) and self._has_file_name_editor(dialog):
                            try:
                                dialog.set_focus()
                            except Exception:
                                pass
                            return dialog

                desktop = Desktop(backend=backend)
                for dialog in desktop.windows(visible_only=True):
                    title = dialog.window_text() or ""
                    if not re.search(title_pattern, title):
                        continue
                    if self._has_file_name_editor(dialog):
                        dialog.wait("visible enabled", timeout=1)
                        return dialog
            except Exception as exc:
                last_error = exc
            time.sleep(0.2)

        raise TimeoutError(f"File dialog not found: title_re={title_pattern!r}, last_error={last_error}")

    def _has_file_name_editor(self, dialog) -> bool:
        try:
            return bool(dialog.descendants(control_type="Edit"))
        except Exception:
            return False

    def _write_file_dialog_path(self, dialog, file_path: str):
        editors = dialog.descendants(control_type="Edit")
        if not editors:
            raise ElementNotFoundError({"dialog": dialog.window_text(), "control_type": "Edit"})

        editor = max(editors, key=self._file_name_editor_score)
        wrote = False
        try:
            editor.set_focus()
            editor.set_edit_text(file_path)
            wrote = True
        except Exception:
            pass

        try:
            editor.click_input()
            editor.type_keys("^a{BACKSPACE}", set_foreground=True)
            editor.type_keys(file_path, with_spaces=True, set_foreground=True)
            wrote = True
        except Exception:
            pass

        if not wrote:
            editor.set_focus()
            editor.type_keys("^a{BACKSPACE}", set_foreground=True)
            editor.type_keys(file_path, with_spaces=True, set_foreground=True)
        return editor

    def _file_name_editor_score(self, editor) -> tuple[int, int]:
        try:
            automation_id = editor.element_info.automation_id or ""
        except Exception:
            automation_id = ""
        try:
            name = editor.window_text() or editor.element_info.name or ""
        except Exception:
            name = ""
        try:
            top = int(editor.rectangle().top)
        except Exception:
            top = 0

        score = 0
        if automation_id == "1148":
            score += 100
        if "file" in name.lower() or "파일" in name:
            score += 20
        return score, top

    def _confirm_file_dialog(self, dialog, editor=None, timeout: float = 10.0) -> None:
        if editor is not None:
            try:
                editor.set_focus()
                editor.type_keys("{ENTER}", set_foreground=True)
                if self._wait_until_dialog_closed(dialog, timeout=min(3.0, timeout)):
                    return
            except Exception:
                pass

        button_patterns = ("Open", "열기", "OK", "확인", "Select", "선택")
        for button in dialog.descendants(control_type="Button"):
            try:
                name = button.window_text() or button.element_info.name or ""
            except Exception:
                continue
            try:
                automation_id = button.element_info.automation_id or ""
            except Exception:
                automation_id = ""
            if automation_id != "1" and not any(pattern.lower() in name.lower() for pattern in button_patterns):
                continue
            try:
                button.click_input()
                if self._wait_until_dialog_closed(dialog, timeout=min(3.0, timeout)):
                    return
            except Exception:
                try:
                    button.invoke()
                    if self._wait_until_dialog_closed(dialog, timeout=min(3.0, timeout)):
                        return
                except Exception:
                    continue

        dialog.type_keys("{ENTER}", set_foreground=True)
        if not self._wait_until_dialog_closed(dialog, timeout=min(3.0, timeout)):
            raise TimeoutError(f"File dialog did not close after confirmation: {dialog.window_text()!r}")

    def _wait_until_dialog_closed(self, dialog, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                if not dialog.exists(timeout=0.1):
                    return True
            except Exception:
                return True
            time.sleep(0.2)
        return False

    def verify_text(self, target: str, expected: str, group: str | None = None) -> None:
        control = self._child(target, group=group)
        current_text = self._control_text(control)
        if expected not in current_text:
            raise AssertionError(
                f"Expected text not found. expected={expected!r}, actual={current_text!r}"
            )
        self.logger.info("Verified text: %s", expected)

    def _control_text(self, control) -> str:
        values = []
        for getter in (
            lambda: control.window_text(),
            lambda: "\n".join(control.texts()),
            lambda: control.iface_value.CurrentValue,
        ):
            try:
                value = getter()
            except Exception:
                continue
            if value:
                values.append(str(value))
        return "\n".join(dict.fromkeys(values))

    def verify_color(
        self,
        target: str,
        region: dict,
        expected_color: str,
        min_ratio: float,
    ) -> None:
        if self.window is None:
            raise RuntimeError("Window is not connected.")

        screenshot = self.window.capture_as_image()
        screenshot_region = self._screenshot_region(region, screenshot.size)
        result = self.color_adapter.verify_target_color(
            screenshot=screenshot,
            target=target,
            region=screenshot_region,
            expected_color=expected_color,
            min_ratio=min_ratio,
        )
        self.logger.info(
            "Verified target color: target=%s, expected_color=%s, "
            "detected_ratio=%.4f, min_ratio=%.4f, region=%s",
            result.target,
            result.expected_color,
            result.detected_ratio,
            result.min_ratio,
            result.region,
        )

    def _screenshot_region(self, region: dict, image_size: tuple[int, int]) -> dict:
        units = region.get("units") or region.get("region_units")
        if units == "window_ratio" or self._looks_like_ratio_region(region):
            width, height = image_size
            return {
                "x": int(float(region.get("x", 0)) * width),
                "y": int(float(region.get("y", 0)) * height),
                "width": int(float(region.get("width", 0)) * width),
                "height": int(float(region.get("height", 0)) * height),
            }
        return region

    def _looks_like_ratio_region(self, region: dict) -> bool:
        try:
            values = [float(region[key]) for key in ("x", "y", "width", "height")]
        except Exception:
            return False
        return all(0.0 <= value <= 1.0 for value in values)

    def capture_window(self, name: str) -> None:
        if self.window is None:
            raise RuntimeError("Window is not connected.")
        screenshot_path = build_screenshot_path(self.base_dir, name)
        self.capture_window_to(screenshot_path)

    def capture_window_to(self, path: Path) -> None:
        if self.window is None:
            raise RuntimeError("Window is not connected.")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            image = self.window.capture_as_image()
        except Exception:
            try:
                rect = self.window.rectangle()
                image = ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom))
            except Exception:
                rect = self.window.rectangle()
                width = max(1, rect.width())
                height = max(1, rect.height())
                image = Image.new("RGB", (width, height), "white")
                draw = ImageDraw.Draw(image)
                draw.text((20, 20), "Screenshot capture unavailable", fill="black")
        image.save(path)
        self.logger.info("Saved screenshot: %s", path)

    def dump_controls_to(self, path: Path) -> None:
        if self.window is None:
            raise RuntimeError("Window is not connected.")

        controls = []
        for control in self.window.descendants():
            element_info = control.element_info
            rectangle = None
            try:
                rect = control.rectangle()
                rectangle = {
                    "left": rect.left,
                    "top": rect.top,
                    "right": rect.right,
                    "bottom": rect.bottom,
                }
            except Exception:
                pass

            controls.append(
                {
                    "name": getattr(element_info, "name", "") or "",
                    "automation_id": getattr(element_info, "automation_id", "") or "",
                    "control_type": getattr(element_info, "control_type", "") or "",
                    "class_name": getattr(element_info, "class_name", "") or "",
                    "rectangle": rectangle,
                }
            )

        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            yaml.safe_dump({"controls": controls}, file, allow_unicode=True, sort_keys=False)
        self.logger.info("Saved controls dump: %s", path)

    def close(self) -> None:
        if self.window is None:
            return
        try:
            self.window.close()
        except Exception:
            if self.process_started and self.app is not None:
                self.app.kill()
