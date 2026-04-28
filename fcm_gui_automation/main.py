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
        action="append",
        help=(
            "Scenario YAML path. Repeat this option to run multiple scenarios "
            "in the given order. If omitted, a multi-select file picker opens."
        ),
    )
    return parser.parse_args()


def choose_app_path(initial_path: str | None) -> str | None:
    # Let the user choose the target app without editing config.yaml.
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


def choose_scenario_paths(initial_path: str | None) -> list[str]:
    # Multi-select keeps a batch run simple while preserving the selected order.
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    initial_dir = str(base_dir / "scenarios")
    if initial_path:
        initial_dir = str(Path(initial_path).expanduser().resolve().parent)

    selected = filedialog.askopenfilenames(
        title="Select scenario YAML files",
        initialdir=initial_dir,
        filetypes=[
            ("YAML files", "*.yaml;*.yml"),
            ("YAML files", "*.yaml"),
            ("YML files", "*.yml"),
            ("All files", "*.*"),
        ],
    )
    root.destroy()
    return list(selected)


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


def resolve_scenario_paths(cli_scenario_paths: list[str] | None) -> list[Path]:
    # The resolved list is the exact execution order for the scenario batch.
    default_scenario = base_dir / "scenarios" / "basic_test.yaml"
    selected = cli_scenario_paths or choose_scenario_paths(str(default_scenario))

    if selected:
        scenario_paths = [Path(path).expanduser().resolve() for path in selected]
    else:
        scenario_paths = [default_scenario.resolve()]

    for scenario_path in scenario_paths:
        if not scenario_path.is_file():
            raise FileNotFoundError(f"Scenario file not found: {scenario_path}")

    return scenario_paths


def main() -> int:
    args = parse_args()
    logger = build_logger(base_dir / "reports" / "logs")
    config = load_config(base_dir / "config.yaml")
    app_path = resolve_app_path(config, args.app_path)
    scenario_paths = resolve_scenario_paths(args.scenario)
    logger.info("Selected target app: %s", app_path)
    logger.info("Selected scenarios: %s", ", ".join(str(path) for path in scenario_paths))

    adapter = PyWinAutoAdapter(base_dir=base_dir, config=config, logger=logger)
    fail_safe = FailSafeManager(adapter=adapter, base_dir=base_dir, logger=logger)
    executor = ActionExecutor(adapter=adapter, logger=logger, fail_safe=fail_safe)

    try:
        for index, scenario_path in enumerate(scenario_paths, start=1):
            scenario = load_scenario(scenario_path)
            scenario_name = scenario.get("name", scenario_path.stem)
            logger.info(
                "Running scenario %s/%s: %s (%s)",
                index,
                len(scenario_paths),
                scenario_name,
                scenario_path,
            )
            executor.run(scenario)

        logger.info("All scenarios completed successfully.")
        return 0
    except Exception as error:
        logger.exception("Scenario batch failed: %s", error)
        fail_safe.handle_failure(error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
