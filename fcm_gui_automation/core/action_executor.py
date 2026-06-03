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
            "verify_color": self._verify_color,
            "wait_window": self._wait_window,
            "select_file": self._select_file,
            "screenshot": self._screenshot,
            "safe_close": self._safe_close,
        }
        self.elements: dict = {}

    def set_context(self, scenario: dict) -> None:
        # v1.1.0: color actions resolve a named target through scenario elements.
        self.elements = scenario.get("elements", {})

    def execute_step(self, step: dict) -> None:
        action = step["action"]
        handler = self.action_handlers.get(action)
        if handler is None:
            raise ValueError(f"Unsupported action: {action}")

        handler(step)

    def run(self, scenario: dict) -> None:
        """Backward-compatible direct run without fail-safe decisions."""
        steps = scenario.get("steps", [])
        if not steps:
            raise ValueError("Scenario has no steps.")
        self.set_context(scenario)

        for index, step in enumerate(steps, start=1):
            self.logger.info("Step %s: %s", index, step["action"])
            self.execute_step(step)

    def _launch_or_connect(self, step: dict) -> None:
        self.adapter.launch_or_connect()

    def _set_text(self, step: dict) -> None:
        self.adapter.set_text(step["target"], step["value"], group=step.get("group"))

    def _click(self, step: dict) -> None:
        self.adapter.click(step["target"], group=step.get("group"))

    def _verify_text(self, step: dict) -> None:
        expected = step.get("value", step.get("expected"))
        if expected is None:
            raise ValueError("verify_text requires value or expected.")
        self.adapter.verify_text(step["target"], expected, group=step.get("group"))

    def _verify_color(self, step: dict) -> None:
        target = step["target"]
        # Keep scenarios target-based so test authors do not call color checks by raw coordinates.
        element = self.elements.get(target)
        if element is None:
            raise ValueError(f"Color target is not defined in scenario elements: {target}")

        # MVP uses region directly; later this can be replaced with a pywinauto rectangle lookup.
        region = element.get("region")
        if region is None:
            raise ValueError(f"Color target has no region: {target}")

        self.adapter.verify_color(
            target=target,
            region=region,
            expected_color=step["expected_color"],
            min_ratio=float(step["min_ratio"]),
        )

    def _wait_window(self, step: dict) -> None:
        self.adapter.wait_window(
            title_re=step.get("title") or step.get("title_re"),
            timeout=float(step.get("timeout", 10)),
        )

    def _select_file(self, step: dict) -> None:
        file_path = step.get("file_path") or step.get("path") or step.get("value")
        if not file_path:
            raise ValueError("select_file requires file_path.")
        self.adapter.select_file(
            file_path=file_path,
            dialog_title_re=step.get("dialog_title") or step.get("title") or step.get("title_re"),
            timeout=float(step.get("timeout", 10)),
        )

    def _screenshot(self, step: dict) -> None:
        self.adapter.capture_window(step["value"])

    def _safe_close(self, step: dict) -> None:
        self.fail_safe.safe_close()
