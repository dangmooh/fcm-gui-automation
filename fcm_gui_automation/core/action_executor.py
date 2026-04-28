from __future__ import annotations

from typing import Callable


class ActionExecutor:
    def __init__(self, adapter, logger, fail_safe) -> None:
        self.adapter = adapter
        self.logger = logger
        self.fail_safe = fail_safe
        # Map action names to handlers so new actions do not lengthen run().
        self.action_handlers: dict[str, Callable[[dict], None]] = {
            "launch_or_connect": self._launch_or_connect,
            "set_text": self._set_text,
            "click": self._click,
            "verify_text": self._verify_text,
            "screenshot": self._screenshot,
            "safe_close": self._safe_close,
        }

    def run(self, scenario: dict) -> None:
        steps = scenario.get("steps", [])
        if not steps:
            raise ValueError("Scenario has no steps.")

        for index, step in enumerate(steps, start=1):
            action = step["action"]
            self.logger.info("Step %s: %s", index, action)

            handler = self.action_handlers.get(action)
            if handler is None:
                raise ValueError(f"Unsupported action: {action}")

            handler(step)

    def _launch_or_connect(self, step: dict) -> None:
        self.adapter.launch_or_connect()

    def _set_text(self, step: dict) -> None:
        self.adapter.set_text(step["target"], step["value"])

    def _click(self, step: dict) -> None:
        self.adapter.click(step["target"])

    def _verify_text(self, step: dict) -> None:
        self.adapter.verify_text(step["target"], step["value"])

    def _screenshot(self, step: dict) -> None:
        self.adapter.capture_window(step["value"])

    def _safe_close(self, step: dict) -> None:
        self.fail_safe.safe_close()
