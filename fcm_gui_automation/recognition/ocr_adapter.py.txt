from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil
from typing import Union

from PIL import Image, ImageOps
import pytesseract
from pytesseract import TesseractNotFoundError


ImageSource = Union[str, Path, Image.Image]


class OCRAdapter:
    def __init__(
        self,
        tesseract_cmd: str | None = None,
        lang: str = "eng",
        config: str = "--psm 6 -c tessedit_char_whitelist=0123456789.-+",
    ) -> None:
        resolved_cmd = tesseract_cmd or self._find_tesseract_cmd()
        if resolved_cmd:
            pytesseract.pytesseract.tesseract_cmd = str(resolved_cmd)
        self.lang = lang
        self.config = config

    def read_text(self, source: ImageSource, preprocess: bool = True) -> str:
        image = self._open_image(source)
        if preprocess:
            image = self._preprocess(image)

        try:
            text = pytesseract.image_to_string(
                image,
                lang=self.lang,
                config=self.config,
            )
        except TesseractNotFoundError as error:
            raise RuntimeError(
                "Tesseract executable was not found. Install Tesseract OCR "
                "or pass its path to OCRAdapter(tesseract_cmd=...)."
            ) from error

        return self._normalize_text(text)

    def read_number(self, source: ImageSource, preprocess: bool = True) -> float:
        text = self.read_text(source, preprocess=preprocess)
        match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
        if not match:
            raise ValueError(f"OCR numeric value not found: {text!r}")
        return float(match.group(0))

    def read_text_from_file(self, image_path: str | Path, preprocess: bool = True) -> str:
        return self.read_text(image_path, preprocess=preprocess)

    def verify_text(
        self,
        source: ImageSource,
        expected: str,
        preprocess: bool = True,
    ) -> None:
        actual = self.read_text(source, preprocess=preprocess)
        if expected not in actual:
            raise AssertionError(
                f"Expected OCR text not found. expected={expected!r}, actual={actual!r}"
            )

    def _open_image(self, source: ImageSource) -> Image.Image:
        if isinstance(source, Image.Image):
            return source.copy()

        image_path = Path(source).expanduser().resolve()
        if not image_path.is_file():
            raise FileNotFoundError(f"OCR image file not found: {image_path}")

        return Image.open(image_path)

    def _preprocess(self, image: Image.Image) -> Image.Image:
        grayscale = ImageOps.grayscale(image)
        scaled = grayscale.resize(
            (grayscale.width * 2, grayscale.height * 2),
            Image.Resampling.LANCZOS,
        )
        return scaled.point(lambda pixel: 255 if pixel > 180 else 0)

    def _normalize_text(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line)

    def _find_tesseract_cmd(self) -> str | None:
        found = shutil.which("tesseract")
        if found:
            return found

        candidates = [
            Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
            Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
        ]
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)

        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read a numeric value from an image with OCR.")
    parser.add_argument("image", help="Image path to read.")
    parser.add_argument("--lang", default="eng", help="Tesseract language code.")
    parser.add_argument(
        "--tesseract-cmd",
        help="Path to tesseract.exe when it is not available in PATH.",
    )
    parser.add_argument(
        "--no-preprocess",
        action="store_true",
        help="Read the original image without grayscale/upscale/threshold preprocessing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    adapter = OCRAdapter(tesseract_cmd=args.tesseract_cmd, lang=args.lang)
    print(adapter.read_number(args.image, preprocess=not args.no_preprocess))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
