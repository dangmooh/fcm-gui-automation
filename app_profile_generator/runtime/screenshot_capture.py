from pathlib import Path


def capture_window_screenshot(window, output_path: Path) -> None:
    image = window.capture_as_image()
    image.save(output_path)
