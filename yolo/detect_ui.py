from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2

YOLO_CONFIG_DIR = (Path(__file__).resolve().parent / "ultralytics_config").resolve()
YOLO_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(YOLO_CONFIG_DIR))

from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect UI elements in a screenshot with a local Ultralytics YOLO .pt model."
    )
    parser.add_argument("--model", required=True, type=Path, help="Local YOLO .pt model path.")
    parser.add_argument("--image", required=True, type=Path, help="Input screenshot image path.")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("yolo/outputs"),
        help="Output directory for annotated image and JSON result.",
    )
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold.")
    parser.add_argument("--iou", type=float, default=0.7, help="NMS IoU threshold.")
    parser.add_argument("--imgsz", type=int, default=1280, help="Inference image size.")
    parser.add_argument(
        "--device",
        default=None,
        help="Inference device, for example 'cpu', '0', or 'cuda:0'. Defaults to Ultralytics auto selection.",
    )
    parser.add_argument(
        "--save-crops",
        action="store_true",
        help="Save cropped detection regions under the output directory.",
    )
    return parser.parse_args()


def require_file(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"{label} file not found: {resolved}")
    return resolved


def class_name_from(names: Any, class_id: int) -> str:
    if isinstance(names, dict):
        return str(names.get(class_id, class_id))
    if isinstance(names, list) and 0 <= class_id < len(names):
        return str(names[class_id])
    return str(class_id)


def box_to_detection(box: Any, names: Any, image_width: int, image_height: int) -> dict[str, Any]:
    class_id = int(box.cls[0].item())
    confidence = float(box.conf[0].item())
    x1, y1, x2, y2 = [float(value) for value in box.xyxy[0].tolist()]
    width = x2 - x1
    height = y2 - y1

    return {
        "class_id": class_id,
        "class_name": class_name_from(names, class_id),
        "confidence": round(confidence, 4),
        "bbox": {
            "x1": round(x1, 2),
            "y1": round(y1, 2),
            "x2": round(x2, 2),
            "y2": round(y2, 2),
            "width": round(width, 2),
            "height": round(height, 2),
        },
        "center": {
            "x": round(x1 + width / 2, 2),
            "y": round(y1 + height / 2, 2),
        },
        "normalized_bbox": {
            "x1": round(x1 / image_width, 6),
            "y1": round(y1 / image_height, 6),
            "x2": round(x2 / image_width, 6),
            "y2": round(y2 / image_height, 6),
        },
    }


def save_detection_crops(image_path: Path, detections: list[dict[str, Any]], out_dir: Path) -> None:
    image = cv2.imread(str(image_path))
    if image is None:
        raise RuntimeError(f"Failed to read image for crop saving: {image_path}")

    crop_dir = out_dir / "crops"
    crop_dir.mkdir(parents=True, exist_ok=True)

    for index, detection in enumerate(detections, start=1):
        bbox = detection["bbox"]
        x1 = max(0, int(round(bbox["x1"])))
        y1 = max(0, int(round(bbox["y1"])))
        x2 = min(image.shape[1], int(round(bbox["x2"])))
        y2 = min(image.shape[0], int(round(bbox["y2"])))
        if x2 <= x1 or y2 <= y1:
            continue

        class_name = detection["class_name"].replace(" ", "_")
        crop_path = crop_dir / f"{index:04d}_{class_name}_{detection['confidence']:.2f}.png"
        cv2.imwrite(str(crop_path), image[y1:y2, x1:x2])


def main() -> None:
    args = parse_args()
    model_path = require_file(args.model, "Model")
    image_path = require_file(args.image, "Image")
    out_dir = args.out.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    annotated_path = out_dir / f"{image_path.stem}_{timestamp}_annotated.png"
    json_path = out_dir / f"{image_path.stem}_{timestamp}_detections.json"

    model = YOLO(str(model_path))
    predict_kwargs: dict[str, Any] = {
        "source": str(image_path),
        "conf": args.conf,
        "iou": args.iou,
        "imgsz": args.imgsz,
        "verbose": False,
    }
    if args.device:
        predict_kwargs["device"] = args.device

    results = model.predict(**predict_kwargs)
    result = results[0]

    image_height, image_width = result.orig_shape
    names = result.names or model.names
    detections = [
        box_to_detection(box, names, image_width=image_width, image_height=image_height)
        for box in result.boxes
    ]

    annotated_image = result.plot()
    if not cv2.imwrite(str(annotated_path), annotated_image):
        raise RuntimeError(f"Failed to save annotated image: {annotated_path}")

    if args.save_crops:
        save_detection_crops(image_path, detections, out_dir)

    payload = {
        "model": str(model_path),
        "image": str(image_path),
        "image_size": {"width": image_width, "height": image_height},
        "parameters": {
            "conf": args.conf,
            "iou": args.iou,
            "imgsz": args.imgsz,
            "device": args.device,
        },
        "output_image": str(annotated_path),
        "detections_count": len(detections),
        "detections": detections,
    }

    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
