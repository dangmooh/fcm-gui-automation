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
from app_profile_generator.inspection.hierarchical_profile import build_hierarchical_profile
from app_profile_generator.inspection.hierarchical_profile import build_controls_dump_for_review
from app_profile_generator.inspection.hierarchical_profile import apply_review_names
from app_profile_generator.output.profile_writer import (
    make_output_dir,
    write_yaml,
    write_controls_map,
    write_profile_files,
)


DEFAULT_YOLO_MODEL = "yolo\\models\\gpa-gui-detector\\model.pt"


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
    parser.add_argument(
        "--discovery-scenario",
        action="append",
        default=[],
        help="Scenario YAML to run once and merge newly discovered screens into hierarchical_profile.yaml.",
    )
    parser.add_argument("--discovery-delay", type=float, default=0.5)
    parser.add_argument("--yolo-model", type=str, default=DEFAULT_YOLO_MODEL)
    parser.add_argument("--yolo-conf", type=float, default=0.25)
    parser.add_argument("--yolo-iou", type=float, default=0.7)
    parser.add_argument("--yolo-imgsz", type=int, default=1280)
    parser.add_argument("--yolo-device", type=str, default=None)
    parser.add_argument(
        "--no-yolo",
        action="store_true",
        help="Skip YOLO child scanning.",
    )
    parser.add_argument(
        "--sync-profile-dir",
        type=str,
        default=None,
        help=(
            "Regenerate hierarchical_profile.yaml from edited controls_dump.yaml "
            "using controls_raw.yaml in an existing output directory."
        ),
    )

    return parser


def main() -> int:
    if platform.system() != "Windows":
        print("This tool is intended for Windows GUI applications.")
        return 1

    parser = build_parser()
    args = parser.parse_args()
    yolo_model = None if args.no_yolo else args.yolo_model

    if args.sync_profile_dir:
        return sync_profile_dir(
            profile_dir=Path(args.sync_profile_dir).expanduser().resolve(),
            yolo_model=yolo_model,
            yolo_conf=args.yolo_conf,
            yolo_iou=args.yolo_iou,
            yolo_imgsz=args.yolo_imgsz,
            yolo_device=args.yolo_device,
        )

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

    from app_profile_generator.runtime.app_launcher import launch_app
    from app_profile_generator.runtime.screenshot_capture import capture_window_screenshot
    from app_profile_generator.runtime.window_resolver import resolve_window

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
    print("[5] Preparing output files...")
    output_dir = make_output_dir(args.output_dir, app_name)

    print("[6] Capturing screenshots...")
    screenshot_path = output_dir / "screenshot.png"
    try:
        capture_window_screenshot(window, screenshot_path)
        screenshot_status = "screenshot.png"
    except Exception as exc:
        screenshot_status = f"screenshot failed: {exc}"

    yolo_status = "skipped"
    if yolo_model and screenshot_path.is_file():
        from app_profile_generator.inspection.yolo_children import enrich_controls_with_yolo_children

        try:
            controls = enrich_controls_with_yolo_children(
                controls=controls,
                screenshot_path=screenshot_path,
                window_rect=window_info["window_rect"],
                model_path=Path(yolo_model),
                output_dir=output_dir,
                conf=args.yolo_conf,
                iou=args.yolo_iou,
                imgsz=args.yolo_imgsz,
                device=args.yolo_device,
            )
            yolo_status = f"completed with model: {yolo_model}"
        except Exception as exc:
            yolo_status = f"failed: {exc}"

    controls_dump = build_controls_dump_for_review(controls)
    elements = build_elements_from_controls(controls)
    hierarchical_profile = build_hierarchical_profile(
        app_info=app_info,
        controls=controls,
    )

    print("[7] Writing profile files...")
    write_profile_files(
        output_dir=output_dir,
        app_info=app_info,
        elements=elements,
        controls_dump=controls_dump,
        controls_raw=controls,
        hierarchical_profile=hierarchical_profile,
    )

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

    discovery_status = "not requested"
    if args.discovery_scenario:
        from app_profile_generator.inspection.scenario_discovery import (
            discover_profile_from_scenario,
            load_discovery_scenario,
        )

        discovered_count_before = len(hierarchical_profile.get("screens", {}))
        for scenario_path in args.discovery_scenario:
            scenario = load_discovery_scenario(Path(scenario_path).expanduser().resolve())
            hierarchical_profile = discover_profile_from_scenario(
                profile=hierarchical_profile,
                initial_window=window,
                scenario=scenario,
                delay=args.discovery_delay,
            )
        write_yaml(output_dir / "hierarchical_profile.yaml", hierarchical_profile)
        discovered_count_after = len(hierarchical_profile.get("screens", {}))
        discovery_status = (
            f"merged {discovered_count_after - discovered_count_before} discovered screens"
        )

    print("\\nProfile generated successfully.")
    print(f"Output directory: {output_dir.resolve()}")
    print("- app.yaml")
    print("- elements.yaml")
    print("- controls_dump.yaml")
    print("- controls_raw.yaml")
    print("- hierarchical_profile.yaml")
    print(f"- {screenshot_status}")
    print(f"- {annotated_status}")
    print(f"- yolo child scan: {yolo_status}")
    print(f"- scenario discovery: {discovery_status}")

    print("\\nNext step:")
    print("1. Open annotated_screenshot.png to see each control on the screen.")
    print("2. Edit controls_dump.yaml names when manual naming is needed.")
    print("3. Run --sync-profile-dir on this output directory to refresh hierarchical_profile.yaml.")
    print("4. Open controls_map.yaml only when raw debug details are needed.")

    return 0


def sync_profile_dir(
    profile_dir: Path,
    yolo_model: str | None = DEFAULT_YOLO_MODEL,
    yolo_conf: float = 0.25,
    yolo_iou: float = 0.7,
    yolo_imgsz: int = 1280,
    yolo_device: str | None = None,
) -> int:
    app_path = profile_dir / "app.yaml"
    controls_dump_path = profile_dir / "controls_dump.yaml"
    controls_raw_path = profile_dir / "controls_raw.yaml"
    hierarchical_profile_path = profile_dir / "hierarchical_profile.yaml"

    for path in (app_path, controls_dump_path, controls_raw_path):
        if not path.is_file():
            print(f"[ERROR] Required file not found: {path}")
            return 1

    import yaml

    with app_path.open("r", encoding="utf-8") as file:
        app_info = (yaml.safe_load(file) or {}).get("app", {})
    with controls_dump_path.open("r", encoding="utf-8") as file:
        review_controls = (yaml.safe_load(file) or {}).get("controls", [])
    with controls_raw_path.open("r", encoding="utf-8") as file:
        raw_controls = (yaml.safe_load(file) or {}).get("controls", [])

    controls = apply_review_names(raw_controls, review_controls)
    yolo_status = "skipped"
    if yolo_model:
        screenshot_path = profile_dir / "screenshot.png"
        if not screenshot_path.is_file():
            print(f"[ERROR] Screenshot not found for YOLO sync: {screenshot_path}")
            return 1
        from app_profile_generator.inspection.yolo_children import enrich_controls_with_yolo_children

        controls = enrich_controls_with_yolo_children(
            controls=controls,
            screenshot_path=screenshot_path,
            window_rect=app_info.get("window_rect", {}),
            model_path=Path(yolo_model),
            output_dir=profile_dir,
            conf=yolo_conf,
            iou=yolo_iou,
            imgsz=yolo_imgsz,
            device=yolo_device,
        )
        write_yaml(controls_raw_path, {"controls": controls})
        yolo_status = f"completed with model: {yolo_model}"

    hierarchical_profile = build_hierarchical_profile(app_info=app_info, controls=controls)
    write_yaml(hierarchical_profile_path, hierarchical_profile)
    print(f"Synced hierarchical profile: {hierarchical_profile_path}")
    print(f"YOLO child scan: {yolo_status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
