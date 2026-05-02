import re
import time
from typing import Optional, List, Dict, Any

from pywinauto import Desktop


def _rect_to_dict(rect) -> Dict[str, int]:
    return {
        "x": rect.left,
        "y": rect.top,
        "width": rect.width(),
        "height": rect.height(),
    }


def list_visible_windows() -> List[Dict[str, Any]]:
    desktop = Desktop(backend="uia")
    windows = []

    for win in desktop.windows():
        title = win.window_text().strip()
        if not title:
            continue

        rect = win.rectangle()
        windows.append(
            {
                "index": len(windows),
                "title": title,
                "process_id": win.process_id(),
                "rectangle": _rect_to_dict(rect),
                "window": win,
            }
        )

    return windows


def find_window_by_pid(pid: int, timeout: int = 10):
    deadline = time.time() + timeout

    while time.time() < deadline:
        for item in list_visible_windows():
            if item["process_id"] == pid:
                return item["window"]
        time.sleep(0.5)

    return None


def find_window_by_title(window_title_pattern: str, timeout: int = 10):
    deadline = time.time() + timeout
    pattern = re.compile(window_title_pattern)

    while time.time() < deadline:
        for item in list_visible_windows():
            if pattern.search(item["title"]):
                return item["window"]
        time.sleep(0.5)

    return None


def choose_window_manually():
    windows = list_visible_windows()

    if not windows:
        raise RuntimeError("No visible windows found.")

    print("\\n[Window List]")
    for item in windows:
        rect = item["rectangle"]
        print(
            f'{item["index"]}: {item["title"]} '
            f'(pid={item["process_id"]}, '
            f'x={rect["x"]}, y={rect["y"]}, '
            f'w={rect["width"]}, h={rect["height"]})'
        )

    selected = int(input("\\nSelect target window index: "))

    for item in windows:
        if item["index"] == selected:
            return item["window"]

    raise ValueError(f"Invalid window index: {selected}")


def resolve_window(pid: Optional[int], window_title: Optional[str], timeout: int = 10):
    if pid is not None:
        win = find_window_by_pid(pid, timeout=timeout)
        if win is not None:
            return win

    if window_title:
        win = find_window_by_title(window_title, timeout=timeout)
        if win is not None:
            return win

    print("\\nCould not resolve window automatically. Switching to manual selection.")
    return choose_window_manually()
