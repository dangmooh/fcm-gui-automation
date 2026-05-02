from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import yaml


def sanitize_name(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in name)
    cleaned = cleaned.strip("_")
    return cleaned or "generated_app"


def make_output_dir(base_dir: str, app_name: str) -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    safe_app_name = sanitize_name(app_name)
    output_dir = Path(base_dir) / "generated" / f"{safe_app_name}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_yaml(path: Path, data: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def write_profile_files(
    output_dir: Path,
    app_info: Dict[str, Any],
    elements: Dict[str, Any],
    controls_dump: List[Dict[str, Any]],
) -> None:
    write_yaml(output_dir / "app.yaml", {"app": app_info})
    write_yaml(output_dir / "elements.yaml", {"elements": elements})
    write_yaml(output_dir / "controls_dump.yaml", {"controls": controls_dump})


def write_controls_map(output_dir: Path, controls_map: List[Dict[str, Any]]) -> None:
    write_yaml(output_dir / "controls_map.yaml", {"controls_map": controls_map})
