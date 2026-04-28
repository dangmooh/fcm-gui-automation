from __future__ import annotations

from pathlib import Path
import time

from pywinauto import Application
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

        if self.process_started:
            time.sleep(1.0)
            self.window = self.app.top_window()
        else:
            self.window = self.app.window(title_re=title_re)

        self.window.wait("visible enabled ready", timeout=timeout)
        self.window.set_focus()
        time.sleep(0.5)

    def _build_command(self) -> str:
        python_command = self.app_config.get("python_command", "python")
        script_path = Path(self.app_config["script_path"]).expanduser().resolve()
        if script_path.suffix.lower() == ".py":
            return f'{python_command} "{script_path}"'
        return f'"{script_path}"'

    def _child(self, target: str):
        if self.window is None:
            raise RuntimeError("Window is not connected.")
        descendants = self.window.descendants()
        for control in descendants:
            auto_id = getattr(control.element_info, "automation_id", "") or ""
            if auto_id == target or auto_id.endswith(f".{target}"):
                return control
        raise ElementNotFoundError({"target": target, "backend": self.app_config.get("backend")})

    def set_text(self, target: str, value: str) -> None:
        control = self._child(target)
        control.set_focus()
        try:
            control.set_edit_text(value)
        except Exception:
            control.type_keys("^a{BACKSPACE}", set_foreground=True)
            control.type_keys(value, with_spaces=True, set_foreground=True)

    def click(self, target: str) -> None:
        control = self._child(target)
        try:
            control.set_focus()
            control.click()
            time.sleep(0.2)
            return
        except Exception:
            pass

        try:
            control.set_focus()
            control.click_input()
            time.sleep(0.2)
            return
        except Exception:
            pass

        try:
            control.invoke()
            time.sleep(0.2)
            return
        except Exception:
            pass

        control.set_focus()
        control.type_keys("{SPACE}", set_foreground=True)
        time.sleep(0.2)

    def verify_text(self, target: str, expected: str) -> None:
        control = self._child(target)
        current_text = control.window_text()
        if expected not in current_text:
            raise AssertionError(
                f"Expected text not found. expected={expected!r}, actual={current_text!r}"
            )
        self.logger.info("Verified text: %s", expected)

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
        result = self.color_adapter.verify_target_color(
            screenshot=screenshot,
            target=target,
            region=region,
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

    def capture_window(self, name: str) -> None:
        if self.window is None:
            raise RuntimeError("Window is not connected.")
        screenshot_path = build_screenshot_path(self.base_dir, name)
        image = self.window.capture_as_image()
        image.save(screenshot_path)
        self.logger.info("Saved screenshot: %s", screenshot_path)

    def close(self) -> None:
        if self.window is None:
            return
        try:
            self.window.close()
        except Exception:
            if self.process_started and self.app is not None:
                self.app.kill()
