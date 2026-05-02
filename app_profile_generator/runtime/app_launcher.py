import subprocess
import sys
from pathlib import Path


class LaunchedApp:
    def __init__(self, app_path: str, process: subprocess.Popen, launch_type: str):
        self.app_path = app_path
        self.process = process
        self.pid = process.pid
        self.launch_type = launch_type


def launch_app(app_path: str) -> LaunchedApp:
    path = Path(app_path)

    if not path.exists():
        raise FileNotFoundError(f"App path does not exist: {app_path}")

    suffix = path.suffix.lower()

    if suffix == ".py":
        process = subprocess.Popen([sys.executable, str(path)])
        return LaunchedApp(app_path=str(path), process=process, launch_type="python")

    if suffix == ".exe":
        process = subprocess.Popen([str(path)])
        return LaunchedApp(app_path=str(path), process=process, launch_type="exe")

    raise ValueError(f"Unsupported app type: {suffix}. Only .py and .exe are supported.")
