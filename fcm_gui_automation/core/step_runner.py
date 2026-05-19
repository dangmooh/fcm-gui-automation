from __future__ import annotations

import time


class StepRunner:
    def __init__(self, executor, logger) -> None:
        self.executor = executor
        self.logger = logger

    def run_step(self, step: dict, scenario_fail_safe: dict | None = None) -> int:
        fail_safe_options = {**(scenario_fail_safe or {}), **(step.get("fail_safe", {}) or {})}
        retry_count = max(0, int(fail_safe_options.get("retry_count", 0)))
        retry_interval = max(0.0, float(fail_safe_options.get("retry_interval", 0.0)))
        max_attempts = retry_count + 1

        for attempt in range(1, max_attempts + 1):
            try:
                self.executor.execute_step(step)
                return attempt
            except Exception:
                if attempt >= max_attempts:
                    raise
                self.logger.warning(
                    "Step failed. Retrying current step: attempt=%s/%s action=%s",
                    attempt,
                    max_attempts,
                    step.get("action"),
                    exc_info=True,
                )
                if retry_interval > 0:
                    time.sleep(retry_interval)

        return max_attempts
