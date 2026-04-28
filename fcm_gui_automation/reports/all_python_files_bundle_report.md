# Python 파일 전체 코드 모음 보고서

작성일: 2026-04-28
목적: 지금까지 작성한 Python 파일을 다른 곳에서 복사해서 재구성할 수 있도록 한곳에 모은 문서입니다.

## 사용 방법

- 아래 각 섹션의 파일 경로와 같은 위치에 파일을 만들고, 코드 블록 안의 내용을 붙여넣으면 됩니다.
- __pycache__ 파일은 자동 생성물이므로 옮길 필요가 없습니다.
- Python 외 설정 파일인 config.yaml, requirements.txt, scenarios/*.yaml은 별도 파일로 함께 옮겨야 실행됩니다.

## 포함된 Python 파일

- fcm_desktop.py
- fcm_gui_automation\main.py
- fcm_gui_automation\core\action_executor.py
- fcm_gui_automation\core\fail_safe.py
- fcm_gui_automation\core\logger.py
- fcm_gui_automation\core\scenario_loader.py
- fcm_gui_automation\core\screenshot.py
- fcm_gui_automation\recognition\base.py
- fcm_gui_automation\recognition\pywinauto_adapter.py
- fcm_gui_automation\recognition\opencv_adapter.py
- fcm_gui_automation\recognition\ocr_adapter.py
- fcm_gui_automation\tools\check_environment.py
- fcm_gui_automation\tools\collect_templates.py
- fcm_gui_automation\tools\generate_pdf_report.py

## fcm_desktop.py

```python
import sys

from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ControlPanelWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PyQt Input Panel")
        self.resize(700, 520)
        self._build_ui()

    def _build_ui(self) -> None:
        central_widget = QWidget()
        central_widget.setObjectName("central_widget")

        root_layout = QVBoxLayout()
        root_layout.setSpacing(16)
        root_layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel("Input Panel")
        title_label.setObjectName("title_label")
        title_label.setStyleSheet("font-size: 22px; font-weight: bold;")

        description_label = QLabel(
            "This sample app contains multiple buttons, descriptions, and key/value fields."
        )
        description_label.setObjectName("description_label")
        description_label.setWordWrap(True)

        input_group = QGroupBox("Input Area")
        input_group.setObjectName("input_group")
        input_layout = QGridLayout()

        key_label = QLabel("Key")
        self.key_input = QLineEdit()
        self.key_input.setObjectName("key_input")
        self.key_input.setPlaceholderText("Enter key")

        value_label = QLabel("Value")
        self.value_input = QLineEdit()
        self.value_input.setObjectName("value_input")
        self.value_input.setPlaceholderText("Enter value")

        extra_value_label = QLabel("Value 2")
        self.extra_value_input = QLineEdit()
        self.extra_value_input.setObjectName("value2_input")
        self.extra_value_input.setPlaceholderText("Enter extra value")

        input_layout.addWidget(key_label, 0, 0)
        input_layout.addWidget(self.key_input, 0, 1)
        input_layout.addWidget(value_label, 1, 0)
        input_layout.addWidget(self.value_input, 1, 1)
        input_layout.addWidget(extra_value_label, 2, 0)
        input_layout.addWidget(self.extra_value_input, 2, 1)
        input_group.setLayout(input_layout)

        button_group = QGroupBox("Actions")
        button_group.setObjectName("button_group")
        button_layout = QGridLayout()

        self.button_info = {
            "save_button": "Save: reflects the current key/value values in the status area.",
            "load_button": "Load: example action that checks values using the current key.",
            "reset_button": "Reset: clears every input field.",
            "apply_button": "Apply: marks the current values as applied.",
        }

        save_button = QPushButton("Save")
        save_button.setObjectName("save_button")
        load_button = QPushButton("Load")
        load_button.setObjectName("load_button")
        reset_button = QPushButton("Reset")
        reset_button.setObjectName("reset_button")
        apply_button = QPushButton("Apply")
        apply_button.setObjectName("apply_button")

        save_button.clicked.connect(lambda: self.handle_action("save_button"))
        load_button.clicked.connect(lambda: self.handle_action("load_button"))
        reset_button.clicked.connect(lambda: self.handle_action("reset_button"))
        apply_button.clicked.connect(lambda: self.handle_action("apply_button"))

        button_layout.addWidget(save_button, 0, 0)
        button_layout.addWidget(QLabel(self.button_info["save_button"]), 0, 1)
        button_layout.addWidget(load_button, 1, 0)
        button_layout.addWidget(QLabel(self.button_info["load_button"]), 1, 1)
        button_layout.addWidget(reset_button, 2, 0)
        button_layout.addWidget(QLabel(self.button_info["reset_button"]), 2, 1)
        button_layout.addWidget(apply_button, 3, 0)
        button_layout.addWidget(QLabel(self.button_info["apply_button"]), 3, 1)
        button_group.setLayout(button_layout)

        status_title = QLabel("Status")
        status_title.setObjectName("status_title")
        status_title.setStyleSheet("font-weight: bold;")

        self.status_box = QTextEdit()
        self.status_box.setObjectName("status_box")
        self.status_box.setReadOnly(True)
        self.status_box.setPlaceholderText("Action results appear here.")

        root_layout.addWidget(title_label)
        root_layout.addWidget(description_label)
        root_layout.addWidget(input_group)
        root_layout.addWidget(button_group)
        root_layout.addWidget(status_title)
        root_layout.addWidget(self.status_box)

        central_widget.setLayout(root_layout)
        self.setCentralWidget(central_widget)

    def handle_action(self, action_name: str) -> None:
        key = self.key_input.text().strip()
        value = self.value_input.text().strip()
        extra_value = self.extra_value_input.text().strip()

        if action_name == "reset_button":
            self.key_input.clear()
            self.value_input.clear()
            self.extra_value_input.clear()
            self.status_box.setPlainText("Inputs cleared.")
            return

        action_text = self.button_info[action_name]
        lines = [
            f"Selected action: {action_text}",
            f"Key: {key or '(empty)'}",
            f"Value: {value or '(empty)'}",
            f"Value 2: {extra_value or '(empty)'}",
        ]
        self.status_box.setPlainText("\n".join(lines))


def main() -> None:
    app = QApplication(sys.argv)
    window = ControlPanelWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

## fcm_gui_automation\main.py

```python
import argparse
from pathlib import Path
import os
import sys
import tkinter as tk
from tkinter import filedialog


base_dir = Path(__file__).resolve().parent
comtypes_cache_dir = base_dir / ".cache" / "comtypes"
comtypes_cache_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("COMTYPES_CACHE", str(comtypes_cache_dir))

from core.action_executor import ActionExecutor
from core.fail_safe import FailSafeManager
from core.logger import build_logger
from core.scenario_loader import load_config, load_scenario
from recognition.pywinauto_adapter import PyWinAutoAdapter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--app-path",
        help="Target application path (.py or .exe). If omitted, a file picker opens.",
    )
    parser.add_argument(
        "--scenario",
        help="Scenario YAML path. If omitted, a file picker opens.",
    )
    return parser.parse_args()


def choose_app_path(initial_path: str | None) -> str | None:
    # 실행 대상을 매번 바꿔 쓸 수 있도록 앱 파일 선택 창을 연다.
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    initial_dir = ""
    if initial_path:
        initial_dir = str(Path(initial_path).expanduser().resolve().parent)

    selected = filedialog.askopenfilename(
        title="Select target application",
        initialdir=initial_dir or str(base_dir.parent),
        filetypes=[
            ("Python or Executable", "*.py;*.exe"),
            ("Python files", "*.py"),
            ("Executable files", "*.exe"),
            ("All files", "*.*"),
        ],
    )
    root.destroy()
    return selected or None


def choose_scenario_path(initial_path: str | None) -> str | None:
    # 여러 테스트 케이스를 재사용할 수 있도록 시나리오 YAML도 파일 선택으로 받는다.
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    initial_dir = str(base_dir / "scenarios")
    if initial_path:
        initial_dir = str(Path(initial_path).expanduser().resolve().parent)

    selected = filedialog.askopenfilename(
        title="Select scenario YAML",
        initialdir=initial_dir,
        filetypes=[
            ("YAML files", "*.yaml;*.yml"),
            ("YAML files", "*.yaml"),
            ("YML files", "*.yml"),
            ("All files", "*.*"),
        ],
    )
    root.destroy()
    return selected or None


def resolve_app_path(config: dict, cli_app_path: str | None) -> Path:
    configured_path = config["app"].get("script_path", "")
    selected = cli_app_path or choose_app_path(configured_path)

    if selected:
        app_path = Path(selected).expanduser().resolve()
    elif configured_path:
        app_path = (base_dir / configured_path).resolve()
    else:
        raise ValueError("No target application path was selected.")

    if not app_path.is_file():
        raise FileNotFoundError(f"Target application not found: {app_path}")

    config["app"]["script_path"] = str(app_path)
    return app_path


def resolve_scenario_path(cli_scenario_path: str | None) -> Path:
    # 시나리오 인자가 없으면 사용자가 원하는 YAML을 직접 고르게 한다.
    default_scenario = base_dir / "scenarios" / "basic_test.yaml"
    selected = cli_scenario_path or choose_scenario_path(str(default_scenario))

    if selected:
        scenario_path = Path(selected).expanduser().resolve()
    else:
        scenario_path = default_scenario.resolve()

    if not scenario_path.is_file():
        raise FileNotFoundError(f"Scenario file not found: {scenario_path}")

    return scenario_path


def main() -> int:
    args = parse_args()
    logger = build_logger(base_dir / "reports" / "logs")
    config = load_config(base_dir / "config.yaml")
    app_path = resolve_app_path(config, args.app_path)
    scenario_path = resolve_scenario_path(args.scenario)
    scenario = load_scenario(scenario_path)
    logger.info("Selected target app: %s", app_path)
    logger.info("Selected scenario: %s", scenario_path)

    adapter = PyWinAutoAdapter(base_dir=base_dir, config=config, logger=logger)
    fail_safe = FailSafeManager(adapter=adapter, base_dir=base_dir, logger=logger)
    executor = ActionExecutor(adapter=adapter, logger=logger, fail_safe=fail_safe)

    try:
        executor.run(scenario)
        logger.info("Scenario completed successfully.")
        return 0
    except Exception as error:
        logger.exception("Scenario failed: %s", error)
        fail_safe.handle_failure(error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

## fcm_gui_automation\core\action_executor.py

```python
from __future__ import annotations


class ActionExecutor:
    def __init__(self, adapter, logger, fail_safe) -> None:
        self.adapter = adapter
        self.logger = logger
        self.fail_safe = fail_safe

    def run(self, scenario: dict) -> None:
        steps = scenario.get("steps", [])
        if not steps:
            raise ValueError("Scenario has no steps.")

        for index, step in enumerate(steps, start=1):
            action = step["action"]
            self.logger.info("Step %s: %s", index, action)

            if action == "launch_or_connect":
                self.adapter.launch_or_connect()
            elif action == "set_text":
                self.adapter.set_text(step["target"], step["value"])
            elif action == "click":
                self.adapter.click(step["target"])
            elif action == "verify_text":
                self.adapter.verify_text(step["target"], step["value"])
            elif action == "screenshot":
                self.adapter.capture_window(step["value"])
            elif action == "safe_close":
                self.fail_safe.safe_close()
            else:
                raise ValueError(f"Unsupported action: {action}")
```

## fcm_gui_automation\core\fail_safe.py

```python
from __future__ import annotations


class FailSafeManager:
    def __init__(self, adapter, base_dir, logger) -> None:
        self.adapter = adapter
        self.base_dir = base_dir
        self.logger = logger

    def handle_failure(self, error: Exception) -> None:
        self.logger.error("Handling failure: %s", error)
        try:
            self.adapter.capture_window("failure")
        except Exception as screenshot_error:
            self.logger.warning("Failure screenshot skipped: %s", screenshot_error)
        finally:
            self.safe_close()

    def safe_close(self) -> None:
        try:
            self.adapter.close()
        except Exception as close_error:
            self.logger.warning("Safe close skipped: %s", close_error)
```

## fcm_gui_automation\core\logger.py

```python
from pathlib import Path
import logging


def build_logger(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("fcm_gui_automation")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_dir / "automation.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
```

## fcm_gui_automation\core\scenario_loader.py

```python
from pathlib import Path

import yaml


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def load_config(path: Path) -> dict:
    return _load_yaml(path)


def load_scenario(path: Path) -> dict:
    return _load_yaml(path)
```

## fcm_gui_automation\core\screenshot.py

```python
from pathlib import Path
from datetime import datetime


def build_screenshot_path(base_dir: Path, name: str) -> Path:
    screenshots_dir = base_dir / "reports" / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return screenshots_dir / f"{timestamp}_{name}.png"
```

## fcm_gui_automation\recognition\base.py

```python
class RecognitionAdapter:
    def launch_or_connect(self) -> None:
        raise NotImplementedError

    def set_text(self, target: str, value: str) -> None:
        raise NotImplementedError

    def click(self, target: str) -> None:
        raise NotImplementedError

    def verify_text(self, target: str, expected: str) -> None:
        raise NotImplementedError

    def capture_window(self, name: str) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError
```

## fcm_gui_automation\recognition\pywinauto_adapter.py

```python
from __future__ import annotations

from pathlib import Path
import time

from pywinauto import Application
from pywinauto.findwindows import ElementNotFoundError
from pywinauto.timings import TimeoutError

from core.screenshot import build_screenshot_path
from recognition.base import RecognitionAdapter


class PyWinAutoAdapter(RecognitionAdapter):
    def __init__(self, base_dir: Path, config: dict, logger) -> None:
        self.base_dir = base_dir
        self.config = config
        self.logger = logger
        self.app = None
        self.window = None
        self.process_started = False

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
        control.click_input()

    def verify_text(self, target: str, expected: str) -> None:
        control = self._child(target)
        current_text = control.window_text()
        if expected not in current_text:
            raise AssertionError(
                f"Expected text not found. expected={expected!r}, actual={current_text!r}"
            )
        self.logger.info("Verified text: %s", expected)

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
```

## fcm_gui_automation\recognition\opencv_adapter.py

```python
class OpenCVAdapter:
    def __init__(self) -> None:
        raise NotImplementedError("OpenCV adapter is reserved for a later phase.")
```

## fcm_gui_automation\recognition\ocr_adapter.py

```python
class OCRAdapter:
    def __init__(self) -> None:
        raise NotImplementedError("OCR adapter is reserved for a later phase.")
```

## fcm_gui_automation\tools\check_environment.py

```python
from pathlib import Path
import importlib
import os
import sys


REQUIRED_MODULES = ["pywinauto", "yaml", "PIL"]


def main() -> int:
    cache_dir = Path(__file__).resolve().parents[1] / ".cache" / "comtypes"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("COMTYPES_CACHE", str(cache_dir))

    missing = []
    for module_name in REQUIRED_MODULES:
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(module_name)

    print(f"Python executable: {sys.executable}")
    print(f"Working directory: {Path.cwd()}")

    if missing:
        print("Missing modules:", ", ".join(missing))
        return 1

    print("Environment check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## fcm_gui_automation\tools\collect_templates.py

```python
def main() -> int:
    print("Template collection is planned for the image-matching phase.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## fcm_gui_automation\tools\generate_pdf_report.py

```python
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont
import PIL.JpegImagePlugin  # noqa: F401


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_MD = ROOT / "reports" / "automation_process_report.md"
DEFAULT_OUTPUT_PDF = ROOT / "reports" / "automation_process_report.pdf"
FONT_PATH = Path(r"C:\Windows\Fonts\malgun.ttf")
FONT_BOLD_PATH = Path(r"C:\Windows\Fonts\malgunbd.ttf")

PAGE_SIZE = (1240, 1754)
MARGIN_X = 90
MARGIN_Y = 90
LINE_GAP = 10
PARAGRAPH_GAP = 18


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = FONT_BOLD_PATH if bold else FONT_PATH
    if path.exists():
        return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


TITLE_FONT = load_font(30, bold=True)
HEADER_FONT = load_font(24, bold=True)
BODY_FONT = load_font(18, bold=False)
CAPTION_FONT = load_font(16, bold=False)


def sanitize_markdown_line(line: str) -> tuple[str, str]:
    stripped = line.rstrip()
    if stripped.startswith("# "):
        return "title", stripped[2:].strip()
    if stripped.startswith("## "):
        return "header", stripped[3:].strip()
    if stripped.startswith("### "):
        return "subheader", stripped[4:].strip()
    if stripped.startswith("- "):
        return "bullet", "- " + stripped[2:].strip()
    if stripped[:3].isdigit() and stripped[1:3] == ". ":
        return "body", stripped
    return "body", stripped


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    if not text:
        return [""]
    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        width = draw.textlength(candidate, font=font)
        if width <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


def draw_wrapped_lines(draw: ImageDraw.ImageDraw, y: int, text: str, font, kind: str) -> tuple[int, bool]:
    max_width = PAGE_SIZE[0] - (MARGIN_X * 2)
    indent = 18 if kind == "bullet" else 0
    lines = wrap_text(draw, text, font, max_width - indent)
    line_height = font.size + LINE_GAP
    needed = len(lines) * line_height + PARAGRAPH_GAP
    if y + needed > PAGE_SIZE[1] - MARGIN_Y:
        return y, False
    for index, line in enumerate(lines):
        x = MARGIN_X + (indent if index > 0 and kind == "bullet" else 0)
        draw.text((x, y), line, fill="black", font=font)
        y += line_height
    y += PARAGRAPH_GAP
    return y, True


def make_blank_page() -> Image.Image:
    return Image.new("RGB", PAGE_SIZE, "white")


def render_text_pages(lines: Iterable[str]) -> list[Image.Image]:
    pages: list[Image.Image] = []
    page = make_blank_page()
    draw = ImageDraw.Draw(page)
    y = MARGIN_Y

    for raw_line in lines:
        kind, text = sanitize_markdown_line(raw_line)
        font = BODY_FONT
        if kind == "title":
            font = TITLE_FONT
        elif kind in {"header", "subheader"}:
            font = HEADER_FONT

        y, drawn = draw_wrapped_lines(draw, y, text, font, kind)
        if drawn:
            continue

        pages.append(page)
        page = make_blank_page()
        draw = ImageDraw.Draw(page)
        y = MARGIN_Y
        y, _ = draw_wrapped_lines(draw, y, text, font, kind)

    pages.append(page)
    return pages


def fit_image(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
    copied = image.copy()
    copied.thumbnail((max_width, max_height))
    return copied


def render_image_page(title: str, image_path: Path) -> Image.Image:
    page = make_blank_page()
    draw = ImageDraw.Draw(page)
    y = MARGIN_Y
    draw.text((MARGIN_X, y), title, fill="black", font=HEADER_FONT)
    y += HEADER_FONT.size + 30

    with Image.open(image_path) as source:
        source = source.convert("RGB")
        fitted = fit_image(source, PAGE_SIZE[0] - (MARGIN_X * 2), PAGE_SIZE[1] - y - 120)
        x = (PAGE_SIZE[0] - fitted.width) // 2
        page.paste(fitted, (x, y))
        draw.text(
            (MARGIN_X, PAGE_SIZE[1] - MARGIN_Y - 30),
            image_path.name,
            fill="black",
            font=CAPTION_FONT,
        )

    return page


def parse_image_spec(spec: str) -> tuple[str, Path]:
    if "=" not in spec:
        raise ValueError(f"Image spec must be title=path: {spec}")
    title, raw_path = spec.split("=", 1)
    return title.strip(), Path(raw_path.strip())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("markdown", nargs="?", default=str(DEFAULT_REPORT_MD))
    parser.add_argument("output", nargs="?", default=str(DEFAULT_OUTPUT_PDF))
    parser.add_argument(
        "--image",
        action="append",
        default=[],
        help="Attach an image page using the form 'Title=path/to/image.png'",
    )
    args = parser.parse_args()

    report_md = Path(args.markdown)
    output_pdf = Path(args.output)

    lines = report_md.read_text(encoding="utf-8").splitlines()
    pages = render_text_pages(lines)

    screenshots = [
        ("Failure Screenshot 1", ROOT / "reports" / "screenshots" / "20260427_224325_failure.png"),
        ("Failure Screenshot 2", ROOT / "reports" / "screenshots" / "20260427_224523_failure.png"),
        ("Success Screenshot", ROOT / "reports" / "screenshots" / "20260427_224542_basic_test_success.png"),
    ]
    screenshots.extend(parse_image_spec(spec) for spec in args.image)

    for title, path in screenshots:
        if path.exists():
            pages.append(render_image_page(title, path))

    first, rest = pages[0], pages[1:]
    first.save(output_pdf, save_all=True, append_images=rest, resolution=150.0)
    print(output_pdf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

