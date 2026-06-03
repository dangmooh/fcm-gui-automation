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
