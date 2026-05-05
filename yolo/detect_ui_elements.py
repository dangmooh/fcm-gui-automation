from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import cv2
from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Detect UI elements from a screenshot with a local Ultralytics YOLO .pt model, "
            "print detections, and save an annotated image."
        )
    )
    parser.add_argument(
        "--model",
        required=True,
        type=Path,
        help="Path to a local pretrained YOLO .pt file.",
    )
    parser.add_argument(
        "--image",
        required=True,
        type=Path,
        help="Path to the input screenshot image.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("result.jpg"),
        help="Path where the annotated result image will be saved.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Optional path to save detections as JSON.",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="Confidence threshold for detections.",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="Inference image size.",
    )
    return parser.parse_args()


def validate_file(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"{label} not found: {resolved}")
    return resolved


def detection_to_dict(box: Any, class_names: dict[int, str]) -> dict[str, Any]:
    class_id = int(box.cls[0].item())
    x1, y1, x2, y2 = [float(value) for value in box.xyxy[0].tolist()]

    return {
        "bbox": {
            "x1": round(x1, 2),
            "y1": round(y1, 2),
            "x2": round(x2, 2),
            "y2": round(y2, 2),
        },
        "class_id": class_id,
        "class_name": class_names.get(class_id, str(class_id)),
        "confidence": round(float(box.conf[0].item()), 4),
    }


def main() -> None:
    args = parse_args()

    model_path = validate_file(args.model, "Model")
    image_path = validate_file(args.image, "Image")
    output_path = args.output.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    model = YOLO(str(model_path))
    results = model.predict(source=str(image_path), conf=args.conf, imgsz=args.imgsz, verbose=False)
    result = results[0]

    class_names = result.names or model.names
    detections = [detection_to_dict(box, class_names) for box in result.boxes]

    annotated_image = result.plot()
    if not cv2.imwrite(str(output_path), annotated_image):
        raise RuntimeError(f"Failed to save annotated image: {output_path}")

    payload = {
        "image": str(image_path),
        "model": str(model_path),
        "output_image": str(output_path),
        "detections": detections,
    }

    print(json.dumps(payload, indent=2, ensure_ascii=False))

    if args.json_output:
        json_path = args.json_output.expanduser().resolve()
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
