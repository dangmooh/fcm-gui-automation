from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

YOLO_CONFIG_DIR = (Path(__file__).resolve().parent / "ultralytics_config").resolve()
YOLO_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(YOLO_CONFIG_DIR))

from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune a YOLO model for UI element detection.")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("yolo/dataset/data.yaml"),
        help="YOLO dataset data.yaml path.",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=Path("yolo/models/yolo11n.pt"),
        help="Base YOLO .pt model path. Use a local file in closed-network environments.",
    )
    parser.add_argument("--epochs", type=int, default=100, help="Training epochs.")
    parser.add_argument("--imgsz", type=int, default=1280, help="Training image size.")
    parser.add_argument("--batch", type=int, default=8, help="Batch size.")
    parser.add_argument(
        "--device",
        default=None,
        help="Training device, for example 'cpu', '0', or 'cuda:0'. Defaults to Ultralytics auto selection.",
    )
    parser.add_argument("--workers", type=int, default=4, help="Data loader workers.")
    parser.add_argument("--patience", type=int, default=30, help="Early stopping patience.")
    parser.add_argument(
        "--project",
        type=Path,
        default=Path("yolo/runs"),
        help="Directory where training runs will be saved.",
    )
    parser.add_argument("--name", default="ui_yolo", help="Training run name.")
    parser.add_argument("--resume", action="store_true", help="Resume training from the given model checkpoint.")
    parser.add_argument(
        "--val-only",
        action="store_true",
        help="Run validation only instead of training.",
    )
    return parser.parse_args()


def require_file(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"{label} file not found: {resolved}")
    return resolved


def main() -> None:
    args = parse_args()
    data_path = require_file(args.data, "Dataset YAML")
    model_path = require_file(args.model, "Model")

    model = YOLO(str(model_path))
    common_kwargs: dict[str, Any] = {
        "data": str(data_path),
        "imgsz": args.imgsz,
        "batch": args.batch,
        "device": args.device,
        "workers": args.workers,
        "project": str(args.project),
        "name": args.name,
    }

    if args.val_only:
        metrics = model.val(**common_kwargs)
        print(metrics)
        return

    results = model.train(
        **common_kwargs,
        epochs=args.epochs,
        patience=args.patience,
        resume=args.resume,
    )
    print(results)


if __name__ == "__main__":
    main()
