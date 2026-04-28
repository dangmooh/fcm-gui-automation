from pathlib import Path
from datetime import datetime


def build_screenshot_path(base_dir: Path, name: str) -> Path:
    screenshots_dir = base_dir / "reports" / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return screenshots_dir / f"{timestamp}_{name}.png"
