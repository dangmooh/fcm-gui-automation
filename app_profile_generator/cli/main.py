import argparse
import platform
import sys
from pathlib import Path
from typing import Optional

from app_profile_generator.imaging.annotated_screenshot import create_annotated_screenshot
from app_profile_generator.inspection.control_dumper import (
    build_elements_from_controls,
    dump_controls,
    dump_window_info,
)
from app_profile_generator.output.profile_writer import (
    make_output_dir,
    write_controls_map,
    write_profile_files,
)
from app_profile_generator.runtime.app_launcher import launch_app
from app_profile_generator.runtime.screenshot_capture import capture_window_screenshot
from app_profile_generator.runtime.window_resolver import resolve_window


def select_app_with_file_explorer() -> Optional[str]:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        selected_path = filedialog.askopenfilename(
            title="자동화 대상 프로그램을 선택하세요",
            filetypes=[
                ("Python or Executable", "*.py *.exe"),
                ("Python files", "*.py"),
                ("Executable files", "*.exe"),
                ("All files", "*.*"),
            ],
        )

        root.destroy()
        return selected_path or None

    except Exception as exc:
        print(f"[ERROR] 파일 선택 창을 열 수 없습니다: {exc}")
        return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate app profile from a selected Windows GUI application."
    )

    parser.add_argument("--app-path", type=str, default=None)
    parser.add_argument("--window-title", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default="profiles")
    parser.add_argument("--wait-timeout", type=int, default=10)

    return parser


def main() -> int:
    if platform.system() != "Windows":
        print("This tool is intended for Windows GUI applications.")
        return 1

    parser = build_parser()
    args = parser.parse_args()

    app_path = args.app_path

    if not app_path:
        print("[0] --app-path가 지정되지 않았습니다.")
        print("[0] 파일탐색기에서 자동화 대상 프로그램(.py 또는 .exe)을 선택하세요.")
        app_path = select_app_with_file_explorer()

    if not app_path:
        print("[ERROR] 자동화 대상 프로그램이 선택되지 않았습니다.")
        return 1

    app_path_obj = Path(app_path)

    if not app_path_obj.exists():
        print(f"[ERROR] 선택한 파일이 존재하지 않습니다: {app_path_obj}")
        return 1

    if app_path_obj.suffix.lower() not in [".py", ".exe"]:
        print(f"[ERROR] 지원하지 않는 파일 형식입니다: {app_path_obj.suffix}")
        print("지원 형식: .py, .exe")
        return 1

    app_name = app_path_obj.stem

    print(f"\\n[1] Launching app: {app_path_obj}")
    launched_app = launch_app(str(app_path_obj))

    print(f"[2] Resolving main window. pid={launched_app.pid}")
    window = resolve_window(
        pid=launched_app.pid,
        window_title=args.window_title,
        timeout=args.wait_timeout,
    )

    print(f"[3] Target window found: {window.window_text()}")

    print("[4] Dumping UIA controls...")
    controls = dump_controls(window)
    elements = build_elements_from_controls(controls)

    window_info = dump_window_info(window)

    app_info = {
        "name": app_name,
        "app_path": str(app_path_obj),
        "launch_type": launched_app.launch_type,
        "process_id": launched_app.pid,
        "window_title": window_info["window_title"],
        "backend": "uia",
        "window_rect": window_info["window_rect"],
        "default_timeout": 10,
    }

    print("[5] Writing profile files...")
    output_dir = make_output_dir(args.output_dir, app_name)

    write_profile_files(
        output_dir=output_dir,
        app_info=app_info,
        elements=elements,
        controls_dump=controls,
    )

    print("[6] Capturing screenshots...")
    try:
        capture_window_screenshot(window, output_dir / "screenshot.png")
        screenshot_status = "screenshot.png"
    except Exception as exc:
        screenshot_status = f"screenshot failed: {exc}"

    try:
        controls_map = create_annotated_screenshot(
            window=window,
            controls=controls,
            output_path=output_dir / "annotated_screenshot.png",
        )
        write_controls_map(output_dir, controls_map)
        annotated_status = "annotated_screenshot.png, controls_map.yaml"
    except Exception as exc:
        annotated_status = f"annotated screenshot failed: {exc}"

    print("\\nProfile generated successfully.")
    print(f"Output directory: {output_dir.resolve()}")
    print("- app.yaml")
    print("- elements.yaml")
    print("- controls_dump.yaml")
    print(f"- {screenshot_status}")
    print(f"- {annotated_status}")

    print("\\nNext step:")
    print("1. Open annotated_screenshot.png to see each control on the screen.")
    print("2. Open controls_map.yaml to check label number, automation_id, name, and region.")
    print("3. Open elements.yaml and rename auto_button_001, auto_input_001, etc.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
