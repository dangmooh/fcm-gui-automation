from pathlib import Path

from PIL import Image, ImageDraw, ImageGrab


def _window_size(window) -> tuple[int, int]:
    rect = window.rectangle()
    return max(1, rect.width()), max(1, rect.height())


def capture_window_image(window):
    try:
        return window.capture_as_image()
    except Exception:
        rect = window.rectangle()
        try:
            screenshot = ImageGrab.grab()
            return screenshot.crop((rect.left, rect.top, rect.right, rect.bottom))
        except Exception:
            width, height = _window_size(window)
            image = Image.new("RGB", (width, height), "white")
            draw = ImageDraw.Draw(image)
            draw.text((12, 12), "Screenshot capture unavailable", fill=(80, 80, 80))
            return image


def capture_window_screenshot(window, output_path: Path) -> None:
    image = capture_window_image(window)
    image.save(output_path)
