from __future__ import annotations


class StateAnalyzer:
    def __init__(self, adapter, logger) -> None:
        self.adapter = adapter
        self.logger = logger

    def collect_state(self) -> dict:
        state = {
            "window_connected": getattr(self.adapter, "window", None) is not None,
            "process_started": bool(getattr(self.adapter, "process_started", False)),
        }

        window = getattr(self.adapter, "window", None)
        if window is None:
            return state

        try:
            state["window_text"] = window.window_text()
        except Exception as error:
            state["window_text_error"] = str(error)

        try:
            rectangle = window.rectangle()
            state["window_rectangle"] = {
                "left": rectangle.left,
                "top": rectangle.top,
                "right": rectangle.right,
                "bottom": rectangle.bottom,
            }
        except Exception as error:
            state["window_rectangle_error"] = str(error)

        return state
