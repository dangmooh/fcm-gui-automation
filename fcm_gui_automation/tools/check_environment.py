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
