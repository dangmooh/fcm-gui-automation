from __future__ import annotations

from colorsys import rgb_to_hsv
from dataclasses import dataclass

from PIL import Image


@dataclass(frozen=True)
class ColorDetectionResult:
    target: str
    expected_color: str
    detected_ratio: float
    min_ratio: float
    region: dict
    matched_pixels: int
    considered_pixels: int


class ColorAdapter:
    SUPPORTED_COLORS = {"red", "green", "blue"}

    def verify_target_color(
        self,
        screenshot: Image.Image,
        target: str,
        region: dict,
        expected_color: str,
        min_ratio: float,
    ) -> ColorDetectionResult:
        # Verify the current visual state of a named target, not an arbitrary point.
        detected_ratio, matched_pixels, considered_pixels = self.calculate_color_ratio(
            screenshot=screenshot,
            region=region,
            expected_color=expected_color,
        )
        result = ColorDetectionResult(
            target=target,
            expected_color=expected_color,
            detected_ratio=detected_ratio,
            min_ratio=min_ratio,
            region=region,
            matched_pixels=matched_pixels,
            considered_pixels=considered_pixels,
        )

        if detected_ratio < min_ratio:
            raise AssertionError(
                "Target color verification failed. "
                f"target={target}, expected_color={expected_color}, "
                f"detected_ratio={detected_ratio:.4f}, min_ratio={min_ratio}, "
                f"region={region}"
            )

        return result

    def calculate_color_ratio(
        self,
        screenshot: Image.Image,
        region: dict,
        expected_color: str,
    ) -> tuple[float, int, int]:
        normalized_color = expected_color.lower()
        if normalized_color not in self.SUPPORTED_COLORS:
            raise ValueError(
                "Unsupported expected_color. "
                f"expected one of {sorted(self.SUPPORTED_COLORS)}, got {expected_color}"
            )

        cropped = self._crop_region(screenshot, region)
        matched_pixels = 0
        considered_pixels = 0

        for red, green, blue in cropped.convert("RGB").getdata():
            hue, saturation, value = self._rgb_to_hsv_degrees(red, green, blue)
            # Ignore dark or gray pixels so borders, shadows, and text do not dominate the ratio.
            if saturation < 50 or value < 50:
                continue

            considered_pixels += 1
            if self._matches_expected_hue(hue, normalized_color):
                matched_pixels += 1

        if considered_pixels == 0:
            return 0.0, matched_pixels, considered_pixels

        return matched_pixels / considered_pixels, matched_pixels, considered_pixels

    def detect_dominant_color(self, screenshot: Image.Image, region: dict) -> str | None:
        cropped = self._crop_region(screenshot, region)
        counts = {color: 0 for color in self.SUPPORTED_COLORS}

        for red, green, blue in cropped.convert("RGB").getdata():
            hue, saturation, value = self._rgb_to_hsv_degrees(red, green, blue)
            if saturation < 50 or value < 50:
                continue

            for color in self.SUPPORTED_COLORS:
                if self._matches_expected_hue(hue, color):
                    counts[color] += 1
                    break

        dominant_color, count = max(counts.items(), key=lambda item: item[1])
        return dominant_color if count > 0 else None

    def _crop_region(self, screenshot: Image.Image, region: dict) -> Image.Image:
        required_keys = ("x", "y", "width", "height")
        missing_keys = [key for key in required_keys if key not in region]
        if missing_keys:
            raise ValueError(f"Region is missing keys: {', '.join(missing_keys)}")

        x = int(region["x"])
        y = int(region["y"])
        width = int(region["width"])
        height = int(region["height"])
        if width <= 0 or height <= 0:
            raise ValueError(f"Region width and height must be positive: {region}")

        return screenshot.crop((x, y, x + width, y + height))

    def _rgb_to_hsv_degrees(self, red: int, green: int, blue: int) -> tuple[float, float, float]:
        hue, saturation, value = rgb_to_hsv(red / 255, green / 255, blue / 255)
        return hue * 180, saturation * 255, value * 255

    def _matches_expected_hue(self, hue: float, expected_color: str) -> bool:
        # Hue ranges follow OpenCV-style 0..180 HSV degrees for v1.1.0 MVP colors.
        if expected_color == "red":
            return 0 <= hue <= 10 or 170 <= hue <= 180
        if expected_color == "green":
            return 35 <= hue <= 85
        if expected_color == "blue":
            return 90 <= hue <= 130
        return False
